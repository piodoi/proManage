"""
Email monitoring service for automatic bill import.

This module connects to Gmail via IMAP to fetch unread emails sent to 
proManage.bill+{user_id}@gmail.com, extracts PDF attachments, and creates 
bills using the existing text pattern extraction system.
"""
import os
import re
import imaplib
import email
from email.message import Message
from typing import Optional, List, Tuple
import logging
from io import BytesIO

from app.models import Bill, BillType, BillStatus
from app.database import db
from app.pdf_parser import parse_pdf_with_patterns

logger = logging.getLogger(__name__)


class EmailMonitor:
    """Monitors Gmail inbox for bill emails."""
    
    def __init__(self):
        self.host = os.getenv("EMAIL_MONITOR_HOST", "imap.gmail.com")
        self.port = int(os.getenv("EMAIL_MONITOR_PORT", "993"))
        self.username = os.getenv("EMAIL_MONITOR_USERNAME", "")
        self.password = os.getenv("EMAIL_MONITOR_PASSWORD", "")
        self.base_email = os.getenv("EMAIL_MONITOR_ADDRESS", "promanage.bill@gmail.com")
        
    def is_configured(self) -> bool:
        """Check if email monitoring is properly configured."""
        return bool(self.username and self.password)
    
    def extract_user_id_from_email(self, to_address: str) -> Optional[str]:
        """
        Extract user_id from email address like: promanage.bill+{user_id}@gmail.com
        
        Args:
            to_address: Email address to parse
            
        Returns:
            user_id if found, None otherwise
        """
        # Match pattern: promanage.bill+{user_id}@gmail.com
        match = re.search(r'promanage\.bill\+([a-f0-9\-]+)@gmail\.com', to_address.lower())
        if match:
            return match.group(1)
        return None
    
    def connect(self) -> imaplib.IMAP4_SSL:
        """Connect to Gmail IMAP server."""
        if not self.is_configured():
            raise ValueError("Email monitoring not configured. Check EMAIL_MONITOR_* env variables.")
        
        logger.info(f"Connecting to {self.host}:{self.port} as {self.username}")
        mail = imaplib.IMAP4_SSL(self.host, self.port)
        mail.login(self.username, self.password)
        return mail
    
    def fetch_unread_emails(self, user_id: Optional[str] = None) -> List[Tuple[str, Message, str]]:
        """
        Fetch unread emails from inbox.
        
        Args:
            user_id: If provided, only fetch emails for this user
            
        Returns:
            List of tuples: (email_id, email_message, user_id)
        """
        mail = self.connect()
        results = []
        
        try:
            # Select inbox
            mail.select('INBOX')
            
            # Search for unread emails
            status, messages = mail.search(None, 'UNSEEN')
            
            if status != 'OK':
                logger.warning("No unread messages found")
                return results
            
            email_ids = messages[0].split()
            logger.info(f"Found {len(email_ids)} unread emails")
            
            for email_id in email_ids:
                try:
                    # Fetch email
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        continue
                    
                    # Parse email
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    # Extract TO address
                    to_address = msg.get('To', '')
                    
                    # Extract user_id from TO address
                    extracted_user_id = self.extract_user_id_from_email(to_address)
                    
                    if not extracted_user_id:
                        logger.debug(f"Email {email_id.decode()} not addressed to proManage.bill+userid@gmail.com")
                        continue
                    
                    # If user_id filter is specified, check if it matches
                    if user_id and extracted_user_id != user_id:
                        logger.debug(f"Email {email_id.decode()} is for user {extracted_user_id}, not {user_id}")
                        continue
                    
                    logger.info(f"Processing email {email_id.decode()} for user {extracted_user_id}")
                    results.append((email_id.decode(), msg, extracted_user_id))
                    
                except Exception as e:
                    logger.error(f"Error processing email {email_id}: {e}")
                    continue
            
        finally:
            mail.close()
            mail.logout()
        
        return results
    
    def extract_pdf_attachments(self, msg: Message) -> List[Tuple[str, bytes]]:
        """
        Extract PDF attachments from email message.
        
        Args:
            msg: Email message object
            
        Returns:
            List of tuples: (filename, pdf_bytes)
        """
        attachments = []
        
        for part in msg.walk():
            # Check if part is an attachment
            if part.get_content_maintype() == 'multipart':
                continue
            
            if part.get('Content-Disposition') is None:
                continue
            
            filename = part.get_filename()
            if not filename:
                continue
            
            # Check if it's a PDF
            if filename.lower().endswith('.pdf'):
                pdf_data = part.get_payload(decode=True)
                if pdf_data:
                    attachments.append((filename, pdf_data))
                    logger.info(f"Found PDF attachment: {filename}")
        
        return attachments
    
    def mark_as_read(self, email_id: str):
        """Mark email as read."""
        mail = self.connect()
        try:
            mail.select('INBOX')
            mail.store(email_id, '+FLAGS', '\\Seen')
            logger.info(f"Marked email {email_id} as read")
        finally:
            mail.close()
            mail.logout()
    
    def process_email_bills(self, user_id: Optional[str] = None) -> dict:
        """
        Process unread emails and create bills from PDF attachments.
        
        Args:
            user_id: If provided, only process emails for this user
            
        Returns:
            Dictionary with processing results
        """
        if not self.is_configured():
            return {
                'status': 'error',
                'message': 'Email monitoring not configured. Set EMAIL_MONITOR_* environment variables.',
                'emails_processed': 0,
                'bills_created': 0,
                'errors': []
            }
        
        emails_processed = 0
        bills_created = 0
        errors = []
        bills = []
        
        try:
            # Fetch unread emails
            unread_emails = self.fetch_unread_emails(user_id)
            
            if not unread_emails:
                return {
                    'status': 'success',
                    'message': 'No unread emails found',
                    'emails_processed': 0,
                    'bills_created': 0,
                    'errors': []
                }
            
            # Process each email
            for email_id, msg, extracted_user_id in unread_emails:
                try:
                    emails_processed += 1
                    
                    # Verify user exists
                    user = db.get_user(extracted_user_id)
                    if not user:
                        error_msg = f"User {extracted_user_id} not found"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        continue
                    
                    # Extract PDF attachments
                    pdf_attachments = self.extract_pdf_attachments(msg)
                    
                    if not pdf_attachments:
                        logger.info(f"No PDF attachments in email {email_id}")
                        # Mark as read anyway to avoid reprocessing
                        self.mark_as_read(email_id)
                        continue
                    
                    # Process each PDF attachment
                    for filename, pdf_data in pdf_attachments:
                        try:
                            # Get all extraction patterns from database
                            patterns = db.list_extraction_patterns()
                            
                            if not patterns:
                                error_msg = "No extraction patterns configured"
                                logger.warning(error_msg)
                                errors.append(error_msg)
                                continue
                            
                            # Use pattern matching to extract bill info
                            extraction_result, matched_pattern = parse_pdf_with_patterns(pdf_data, patterns)
                            
                            if not matched_pattern:
                                error_msg = f"No pattern matched for {filename}"
                                logger.warning(error_msg)
                                errors.append(error_msg)
                                continue
                            
                            # Get user's properties to match address
                            properties = db.list_properties(landlord_id=extracted_user_id)
                            
                            if not properties:
                                error_msg = f"No properties found for user {extracted_user_id}"
                                logger.warning(error_msg)
                                errors.append(error_msg)
                                continue
                            
                            # Try to match address to a property
                            matched_property = None
                            if extraction_result.address or extraction_result.consumption_location:
                                address_to_match = extraction_result.consumption_location or extraction_result.address
                                # Simple matching - can be improved
                                for prop in properties:
                                    if address_to_match and address_to_match.lower() in prop.address.lower():
                                        matched_property = prop
                                        break
                            
                            # If no match, use first property or skip
                            if not matched_property:
                                if len(properties) == 1:
                                    matched_property = properties[0]
                                    logger.info(f"Using single property for bill: {matched_property.name}")
                                else:
                                    error_msg = f"Could not match bill to property for {filename}. Address: {extraction_result.address}"
                                    logger.warning(error_msg)
                                    errors.append(error_msg)
                                    continue
                            
                            # Create bill
                            from datetime import datetime
                            
                            # Parse due date if it's a string
                            due_date = datetime.utcnow()
                            if extraction_result.due_date:
                                try:
                                    due_date = datetime.fromisoformat(extraction_result.due_date)
                                except (ValueError, AttributeError):
                                    # If due_date is not ISO format or parsing fails, use current time
                                    pass
                            
                            bill = Bill(
                                property_id=matched_property.id,
                                renter_id=None,  # Applies to all renters
                                bill_type=BillType.UTILITIES,
                                description=f"Bill from {matched_pattern.supplier or matched_pattern.name} - {filename}",
                                amount=extraction_result.amount or 0.0,
                                currency="RON",
                                due_date=due_date,
                                bill_date=datetime.utcnow(),
                                legal_name=extraction_result.business_name,
                                iban=extraction_result.iban,
                                bill_number=extraction_result.bill_number,
                                extraction_pattern_id=matched_pattern.id,
                                contract_id=extraction_result.contract_id,
                                payment_details={'client_code': extraction_result.client_code} if extraction_result.client_code else None,
                                status=BillStatus.PENDING,
                                source_email_id=email_id
                            )
                            
                            db.save_bill(bill)
                            bills.append(bill)
                            bills_created += 1
                            logger.info(f"Created bill {bill.id} for property {matched_property.name}")
                            
                        except Exception as e:
                            error_msg = f"Error processing PDF {filename}: {str(e)}"
                            logger.error(error_msg)
                            errors.append(error_msg)
                    
                    # Mark email as read after processing
                    self.mark_as_read(email_id)
                    
                except Exception as e:
                    error_msg = f"Error processing email {email_id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            return {
                'status': 'success',
                'message': f'Processed {emails_processed} emails, created {bills_created} bills',
                'emails_processed': emails_processed,
                'bills_created': bills_created,
                'bills': [{'id': b.id, 'amount': b.amount, 'description': b.description} for b in bills],
                'errors': errors if errors else None
            }
            
        except Exception as e:
            logger.error(f"Error in process_email_bills: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'emails_processed': emails_processed,
                'bills_created': bills_created,
                'errors': errors
            }


# Global instance
email_monitor = EmailMonitor()

