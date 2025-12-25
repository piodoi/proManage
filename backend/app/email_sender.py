import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

_executor = ThreadPoolExecutor(max_workers=2)


def is_email_configured() -> bool:
    """Check if email sending is configured."""
    return bool(SMTP_USER and SMTP_PASSWORD)


def _send_email_sync(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    """Synchronous email sending (runs in threadpool)."""
    if not is_email_configured():
        logger.warning("[Email] SMTP not configured, skipping email send")
        return False
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM_EMAIL or SMTP_USER
        msg["To"] = to_email
        
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(msg["From"], to_email, msg.as_string())
        
        logger.info(f"[Email] Sent email to {to_email}")
        return True
    except Exception as e:
        logger.error(f"[Email] Failed to send email to {to_email}: {e}")
        return False


async def send_email(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    """Send email asynchronously using threadpool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _send_email_sync, to_email, subject, html_body, text_body)


async def send_confirmation_email(to_email: str, name: str, confirmation_token: str) -> bool:
    """Send email confirmation link."""
    confirmation_url = f"{FRONTEND_URL}/confirm-email?token={confirmation_token}"
    
    subject = "Confirm your ProManage account"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .button {{ 
                display: inline-block; 
                padding: 12px 24px; 
                background-color: #10b981; 
                color: white; 
                text-decoration: none; 
                border-radius: 6px;
                margin: 20px 0;
            }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Welcome to ProManage, {name}!</h2>
            <p>Thank you for registering. Please confirm your email address by clicking the button below:</p>
            <a href="{confirmation_url}" class="button">Confirm Email</a>
            <p>Or copy and paste this link into your browser:</p>
            <p><a href="{confirmation_url}">{confirmation_url}</a></p>
            <p>This link will expire in 1 hour.</p>
            <div class="footer">
                <p>If you didn't create an account, you can safely ignore this email.</p>
                <p>ProManage - Property & Rent Management</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
Welcome to ProManage, {name}!

Thank you for registering. Please confirm your email address by clicking the link below:

{confirmation_url}

This link will expire in 1 hour.

If you didn't create an account, you can safely ignore this email.

ProManage - Property & Rent Management
    """
    
    return await send_email(to_email, subject, html_body, text_body)
