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
from app.text_pattern_extractor import extract_bill_from_pdf_auto
from app.utils.address_matcher import calculate_address_confidence
from app.utils.parsers import parse_amount

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
        
        try:
            mail = imaplib.IMAP4_SSL(self.host, self.port)
            mail.login(self.username, self.password)
            return mail
        except imaplib.IMAP4.error as e:
            logger.error(f"[Email Monitor] Gmail authentication failed: {e}")
            raise ValueError(f"Gmail authentication failed: {e}. Check your EMAIL_MONITOR_USERNAME and EMAIL_MONITOR_PASSWORD in .env")
        except Exception as e:
            logger.error(f"[Email Monitor] Connection error: {e}")
            raise ValueError(f"Failed to connect to Gmail: {e}")
    
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
                return results
            
            email_ids = messages[0].split()
            logger.info(f"[Email Monitor] Found {len(email_ids)} unread emails")
            
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
                        continue
                    
                    # If user_id filter is specified, check if it matches
                    if user_id and extracted_user_id != user_id:
                        continue
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
        from email.header import decode_header
        import re
        
        attachments = []
        part_num = 0
        
        for part in msg.walk():
            part_num += 1
            content_type = part.get_content_type()
            content_maintype = part.get_content_maintype()
            content_disposition = part.get('Content-Disposition')
            
            logger.debug(f"[Email] Part {part_num}: type={content_type}, maintype={content_maintype}, disposition={content_disposition}")
            
            # Skip multipart containers
            if content_maintype == 'multipart':
                continue
            
            # Try to get filename (handles encoded filenames)
            filename = part.get_filename()
            
            # Decode filename if it's encoded (RFC 2047)
            if filename:
                try:
                    decoded_parts = decode_header(filename)
                    decoded_filename = ''
                    for part_text, encoding in decoded_parts:
                        if isinstance(part_text, bytes):
                            decoded_filename += part_text.decode(encoding or 'utf-8', errors='replace')
                        else:
                            decoded_filename += part_text
                    filename = decoded_filename
                    logger.debug(f"[Email] Decoded filename: {filename}")
                except Exception as e:
                    logger.warning(f"[Email] Failed to decode filename: {e}")
            
            # Check if it's a PDF by filename OR content type
            is_pdf = False
            
            if filename and filename.lower().endswith('.pdf'):
                is_pdf = True
                logger.debug(f"[Email] Found PDF by filename: {filename}")
            elif content_type == 'application/pdf':
                is_pdf = True
                if not filename:
                    filename = f"attachment_{part_num}.pdf"
                logger.debug(f"[Email] Found PDF by content type: {filename}")
            elif content_disposition and 'attachment' in content_disposition.lower():
                # Check payload for PDF magic bytes (%PDF)
                payload = part.get_payload(decode=True)
                if payload and payload[:4] == b'%PDF':
                    is_pdf = True
                    if not filename:
                        filename = f"attachment_{part_num}.pdf"
                    logger.info(f"[Email] Found PDF by magic bytes: {filename}")
            
            if is_pdf:
                pdf_data = part.get_payload(decode=True)
                if pdf_data and len(pdf_data) > 0:
                    logger.info(f"[Email] Extracted PDF attachment: {filename} ({len(pdf_data)} bytes)")
                    attachments.append((filename, pdf_data))
                else:
                    logger.warning(f"[Email] PDF attachment {filename} has no data")
            elif content_disposition and 'attachment' in content_disposition.lower():
                logger.debug(f"[Email] Skipping non-PDF attachment: {filename or 'unnamed'} (type: {content_type})")
        
        return attachments
    
    def mark_as_read(self, email_id: str):
        """Mark email as read."""
        mail = self.connect()
        try:
            mail.select('INBOX')
            mail.store(email_id, '+FLAGS', '\\Seen')
        finally:
            mail.close()
            mail.logout()
    
    def delete_email(self, email_id: str):
        """
        Delete email from inbox.
        
        For Gmail: moves to Trash folder (Gmail auto-deletes after 30 days).
        For other providers: permanently deletes via IMAP.
        
        Note: IMAP message IDs are ephemeral. If email was moved manually,
        the ID will be invalid and deletion will fail silently.
        """
        mail = self.connect()
        try:
            mail.select('INBOX')
            
            # Ensure email_id is bytes if needed
            if isinstance(email_id, str):
                email_id_bytes = email_id.encode() if email_id else email_id
            else:
                email_id_bytes = email_id
            
            # Verify email exists before trying to delete
            status, check_data = mail.fetch(email_id_bytes, '(FLAGS)')
            if status != 'OK':
                logger.warning(f"[Email Delete] Email {email_id} not found in INBOX (may have been moved/deleted manually)")
                return  # Skip deletion if email doesn't exist
            
            # Gmail-specific: Move to Trash (Gmail auto-deletes from Trash after 30 days)
            if 'gmail' in self.host.lower():
                try:
                    # Copy to Trash folder first - try Gmail folder names
                    result = None
                    trash_used = None
                    for trash_folder in ['[Gmail]/Trash', '[Gmail]/Bin', 'Trash']:
                        try:
                            result = mail.copy(email_id_bytes, trash_folder)
                            if result[0] == 'OK':
                                trash_used = trash_folder
                                break
                        except Exception:
                            continue
                    
                    # Only mark as deleted in INBOX (keeps copy in Trash)
                    # This removes from INBOX but email stays in Trash for 30 days
                    mail.store(email_id_bytes, '+FLAGS', '\\Deleted')
                    mail.expunge()
                    
                    if trash_used:
                        logger.info(f"[Email Delete] ✓ Moved email {email_id} to {trash_used}")
                except Exception as gmail_err:
                    logger.warning(f"[Email Delete] Gmail-specific deletion failed: {gmail_err}, trying standard method")
                    # Fallback to standard deletion
                    mail.store(email_id_bytes, '+FLAGS', '\\Deleted')
                    mail.expunge()
                    logger.info(f"[Email Delete] ✓ Deleted email {email_id} (standard method)")
            else:
                # Standard IMAP deletion for non-Gmail providers
                mail.store(email_id_bytes, '+FLAGS', '\\Deleted')
                mail.expunge()
                logger.info(f"[Email Delete] ✓ Deleted email {email_id}")
        except Exception as e:
            # Don't raise - log and continue with other emails
            logger.warning(f"[Email Delete] Failed to delete email {email_id}: {e}")
        finally:
            try:
                mail.close()
                mail.logout()
            except:
                pass
    
    def process_email_bills(self, user_id: Optional[str] = None, create_bills: bool = False) -> dict:
        """
        Process unread emails and extract bills from PDF attachments.
        
        Args:
            user_id: If provided, only process emails for this user
            create_bills: If True, creates bills in DB. If False, returns discovered bills for review.
            
        Returns:
            Dictionary with processing results and discovered bills
        """
        if not self.is_configured():
            return {
                'status': 'error',
                'message': 'Email monitoring not configured. Set EMAIL_MONITOR_* environment variables.',
                'emails_processed': 0,
                'bills_discovered': 0,
                'bills_created': 0,
                'discovered_bills': [],
                'errors': []
            }
        
        emails_processed = 0
        bills_created = 0
        errors = []
        discovered_bills = []
        
        try:
            # Fetch unread emails
            unread_emails = self.fetch_unread_emails(user_id)
            
            if not unread_emails:
                return {
                    'status': 'success',
                    'message': 'No unread emails found',
                    'emails_processed': 0,
                    'bills_discovered': 0,
                    'bills_created': 0,
                    'discovered_bills': [],
                    'errors': []
                }
            
            # Process each email
            for email_id, msg, extracted_user_id in unread_emails:
                try:
                    emails_processed += 1
                    logger.info(f"[Email Monitor] Processing email {email_id} for user {extracted_user_id}")
                    
                    # Verify user exists
                    user = db.get_user(extracted_user_id)
                    if not user:
                        error_msg = f"User {extracted_user_id} not found"
                        logger.warning(f"[Email Monitor] {error_msg}")
                        errors.append(error_msg)
                        continue
                    
                    # Extract PDF attachments
                    pdf_attachments = self.extract_pdf_attachments(msg)
                    logger.info(f"[Email Monitor] Found {len(pdf_attachments)} PDF attachments in email {email_id}")
                    
                    if not pdf_attachments:
                        logger.info(f"[Email Monitor] No PDF attachments in email {email_id}, marking as read")
                        # Mark as read anyway to avoid reprocessing
                        self.mark_as_read(email_id)
                        continue
                    
                    # Process each PDF attachment
                    for filename, pdf_data in pdf_attachments:
                        try:
                            logger.info(f"[Email Monitor] Processing PDF: {filename} ({len(pdf_data)} bytes)")
                            
                            # Use text pattern extraction (from text_patterns folder)
                            extracted_data, pattern_id, pattern_name = extract_bill_from_pdf_auto(pdf_data)
                            
                            if not extracted_data:
                                error_msg = f"No pattern matched for {filename}"
                                logger.warning(f"[Email Monitor] {error_msg}")
                                errors.append(error_msg)
                                continue
                            
                            logger.info(f"[Email Monitor] Matched pattern: {pattern_name} (ID: {pattern_id}) for {filename}")
                            
                            # Get user's properties to match address
                            properties = db.list_properties(landlord_id=extracted_user_id)
                            
                            if not properties:
                                error_msg = f"No properties found for user {extracted_user_id}"
                                logger.warning(error_msg)
                                errors.append(error_msg)
                                continue
                            
                            # Extract relevant fields for matching
                            extracted_address = extracted_data.get('address') or extracted_data.get('consumption_location')
                            extracted_contract_id = extracted_data.get('contract_id')
                            extracted_supplier = pattern_name  # Use pattern name as supplier
                            
                            # Try to match property
                            matched_property = None
                            match_reason = None
                            best_score = 0
                            
                            # Strategy 1: Match by contract_id if available
                            if extracted_contract_id:
                                for prop in properties:
                                    # Get suppliers for this property
                                    property_suppliers = db.list_property_suppliers(prop.id)
                                    for prop_supplier in property_suppliers:
                                        # Get the actual Supplier object to access its name
                                        supplier = db.get_supplier(prop_supplier.supplier_id)
                                        if not supplier:
                                            continue
                                        
                                        # Check if supplier name matches pattern name
                                        if supplier.name and extracted_supplier:
                                            supplier_name_lower = supplier.name.lower()
                                            pattern_name_lower = extracted_supplier.lower()
                                            if supplier_name_lower in pattern_name_lower or pattern_name_lower in supplier_name_lower:
                                                # Check if contract_id matches
                                                if prop_supplier.contract_id and prop_supplier.contract_id.lower() == extracted_contract_id.lower():
                                                    matched_property = prop
                                                    match_reason = f"contract_id match ({extracted_contract_id})"
                                                    break
                                    if matched_property:
                                        break
                            
                            # Strategy 2: Match by address scoring (always use best match, user decides in UI)
                            if not matched_property and extracted_address:
                                best_match_property = None
                                for prop in properties:
                                    confidence, debug_info = calculate_address_confidence(extracted_address, prop.address)
                                    
                                    if confidence > best_score:
                                        best_score = confidence
                                        best_match_property = prop
                                
                                # Always use best match if we have one (no threshold filtering)
                                if best_match_property and best_score > 0:
                                    matched_property = best_match_property
                                    match_reason = f"address match ({best_score}% confidence)"
                            
                            # Strategy 3: If only one property exists, use it
                            if not matched_property and len(properties) == 1:
                                matched_property = properties[0]
                                match_reason = "single property for user"
                            
                            # Parse due date if it's a string (dates come in YYYY-MM-DD format from utils)
                            from datetime import datetime
                            due_date = None
                            if extracted_data.get('due_date'):
                                try:
                                    # Handle YYYY-MM-DD format
                                    due_date = datetime.fromisoformat(extracted_data['due_date'])
                                except (ValueError, AttributeError) as e:
                                    logger.warning(f"[Email Bill] Could not parse due_date: {extracted_data.get('due_date')} - {e}")
                                    # Use current date as fallback
                                    due_date = datetime.utcnow()
                            else:
                                # If no due_date extracted, use current date as fallback
                                due_date = datetime.utcnow()
                            
                            # Parse bill date
                            bill_date = None
                            if extracted_data.get('bill_date'):
                                try:
                                    bill_date = datetime.fromisoformat(extracted_data['bill_date'])
                                except (ValueError, AttributeError) as e:
                                    logger.warning(f"[Email Bill] Could not parse bill_date: {extracted_data.get('bill_date')} - {e}")
                            
                            # Parse amount using standard utility (removes dots/commas/spaces, divides by 100)
                            amount = 0.0
                            if extracted_data.get('amount'):
                                # Amount should already be parsed by text_pattern_utils, but verify it's a float
                                try:
                                    amount = float(extracted_data['amount'])
                                except (ValueError, TypeError):
                                    # Fallback: try parsing with utility if it's still a string
                                    parsed = parse_amount(str(extracted_data['amount']))
                                    if parsed is not None:
                                        amount = parsed
                                    else:
                                        logger.warning(f"[Email Bill] Could not parse amount: {extracted_data.get('amount')}")
                            
                            # Create discovered bill object
                            discovered_bill = {
                                'id': f"email_{email_id}_{filename}",  # Temporary ID
                                'email_id': email_id,
                                'filename': filename,
                                'property_id': matched_property.id if matched_property else None,
                                'property_name': matched_property.name if matched_property else None,
                                'property_address': matched_property.address if matched_property else None,
                                'supplier': pattern_name,  # Supplier from pattern name (for backend processing)
                                'supplier_name': pattern_name,  # Supplier name for display
                                'description': extracted_data.get('description') or pattern_name,  # Use description from pattern or supplier name
                                'amount': amount,
                                'currency': 'RON',
                                'due_date': due_date.isoformat(),
                                'bill_date': bill_date.isoformat() if bill_date else datetime.utcnow().isoformat(),
                                'legal_name': extracted_data.get('legal_name'),
                                'iban': extracted_data.get('iban'),
                                'bill_number': extracted_data.get('bill_number'),
                                'contract_id': extracted_contract_id,
                                'pattern_id': pattern_id,
                                'pattern_name': pattern_name,
                                'extracted_address': extracted_address,
                                'match_reason': match_reason if matched_property else 'No match',
                                'address_confidence': best_score if extracted_address else None,
                                'user_id': extracted_user_id,
                                'source': 'email',
                                # Note: pdf_data not included in response as it's binary and can't be JSON serialized
                                # If needed later, we can re-fetch from email or store separately
                            }
                            
                            discovered_bills.append(discovered_bill)
                            
                            # If create_bills is True, create the bill immediately
                            if create_bills and matched_property:
                                # Resolve supplier_id for this email bill
                                from app.routes.sync_routes import resolve_supplier_id
                                supplier_id = resolve_supplier_id(
                                    property_id=matched_property.id,
                                    supplier_name=pattern_name,
                                    extraction_pattern_id=None,  # Text patterns don't have extraction_pattern_id
                                    contract_id=extracted_contract_id
                                )
                                
                                bill = Bill(
                                    property_id=matched_property.id,
                                    renter_id=None,  # Applies to all renters
                                    bill_type=BillType.UTILITIES,
                                    description=discovered_bill['description'],
                                    amount=amount,
                                    currency="RON",
                                    due_date=due_date if due_date else datetime.utcnow(),
                                    bill_date=bill_date if bill_date else datetime.utcnow(),
                                    legal_name=discovered_bill['legal_name'],
                                    iban=discovered_bill['iban'],
                                    bill_number=discovered_bill['bill_number'],
                                    extraction_pattern_id=None,  # Text patterns don't have DB IDs
                                    supplier_id=supplier_id,
                                    contract_id=extracted_data.get('contract_id'),
                                    payment_details=None,
                                    status=BillStatus.PENDING,
                                    source_email_id=email_id
                                )
                                
                                db.save_bill(bill)
                                bills_created += 1
                            
                        except Exception as e:
                            error_msg = f"Error processing PDF {filename}: {str(e)}"
                            logger.error(f"[Email Monitor] {error_msg}", exc_info=True)
                            errors.append(error_msg)
                    
                    # Mark email as read after processing (only if create_bills is True)
                    if create_bills:
                        self.mark_as_read(email_id)
                    
                except Exception as e:
                    error_msg = f"Error processing email {email_id}: {str(e)}"
                    logger.error(f"[Email Monitor] {error_msg}", exc_info=True)
                    errors.append(error_msg)
            
            return {
                'status': 'success',
                'message': f'Processed {emails_processed} emails, discovered {len(discovered_bills)} bills, created {bills_created} bills',
                'emails_processed': emails_processed,
                'bills_discovered': len(discovered_bills),
                'bills_created': bills_created,
                'discovered_bills': discovered_bills,
                'errors': errors if errors else None
            }
            
        except Exception as e:
            logger.error(f"[Email Monitor] Critical error in monitor_emails_for_user: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e),
                'emails_processed': emails_processed,
                'bills_discovered': len(discovered_bills),
                'bills_created': bills_created,
                'discovered_bills': discovered_bills,
                'errors': errors
            }


# Global instance
email_monitor = EmailMonitor()

