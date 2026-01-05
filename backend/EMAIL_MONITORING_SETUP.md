# Email Bill Monitoring Setup Guide

This guide explains how to set up automatic bill monitoring via email for proManage.

## Overview

The email monitoring feature allows proManage to automatically fetch bills from a Gmail inbox. Users forward their utility bills to their unique email address (`proManage.bill+{user_id}@gmail.com`), and the system automatically:

1. Monitors the Gmail inbox for unread emails
2. Extracts PDF attachments from emails
3. Uses text pattern extraction to parse bill information
4. Automatically creates bills in the system

## Prerequisites

1. A Gmail account dedicated to bill monitoring (e.g., `promanage.bill@gmail.com`)
2. Gmail App Password (required for IMAP access)

## Setup Steps

### 1. Create Gmail App Password

1. Go to your Google Account settings
2. Navigate to Security > 2-Step Verification
3. Scroll down to "App passwords"
4. Generate a new app password for "Mail"
5. Save this password securely

### 2. Configure Environment Variables

Add the following to your `.env` file in the `backend/` directory:

```env
# Email Monitor Configuration (for receiving/monitoring bills)
EMAIL_MONITOR_HOST=imap.gmail.com
EMAIL_MONITOR_PORT=993
EMAIL_MONITOR_USERNAME=promanage.bill@gmail.com
EMAIL_MONITOR_PASSWORD=your-16-character-app-password
EMAIL_MONITOR_ADDRESS=promanage.bill@gmail.com
```

Replace `your-16-character-app-password` with the app password you generated.

### 3. Configure Gmail Filters (Optional but Recommended)

To automatically label and organize incoming bills:

1. Go to Gmail Settings > Filters and Blocked Addresses
2. Create a new filter with these criteria:
   - To: `promanage.bill+*@gmail.com`
3. Apply actions:
   - Skip Inbox (Archive it)
   - Apply label: "Bills"
   - Mark as important

This keeps your inbox clean while allowing the system to process bills.

## Usage

### For Users

1. Users can find their unique email address in **Settings > Email Bill Import**
2. The email format is: `proManage.bill+{user_id}@gmail.com`
3. Users should forward utility bills (as PDF attachments) to this address

### Syncing Bills

#### Manual Sync (User)
- Go to **Properties** tab
- Click the **"Sync Email Bills"** button (blue button with mail icon)
- This syncs bills only for the current user

#### Automatic Sync (Future Enhancement)
You can set up a cron job or scheduled task to periodically sync bills:

```bash
# Example cron job (runs every hour)
0 * * * * cd /path/to/proManage/backend && poetry run python -c "from app.email_monitor import email_monitor; email_monitor.process_email_bills()"
```

## How It Works

1. **Email Reception**: Users forward bills to `proManage.bill+{user_id}@gmail.com`
2. **IMAP Connection**: System connects to Gmail via IMAP (secure)
3. **Email Parsing**: 
   - Extracts user ID from the "To" address
   - Finds PDF attachments
4. **PDF Processing**:
   - Extracts text from PDF
   - Matches against configured text patterns (in `extraction_patterns` table)
   - Extracts: amount, due date, IBAN, bill number, etc.
5. **Property Matching**: 
   - Attempts to match bill address to user's properties
   - Falls back to single property if user has only one
6. **Bill Creation**: Creates a bill record in the database
7. **Email Marking**: Marks email as read to prevent reprocessing

## Text Patterns

The system uses text patterns from the database to extract bill information. Make sure you have patterns configured for your utility providers:

- Vodafone
- Digi
- Hidroelectrica
- E-bloc
- Engie
- etc.

Patterns can be managed in the admin panel or via the patterns API.

## Troubleshooting

### "Email monitoring not configured" error

- Check that all `EMAIL_MONITOR_*` environment variables are set
- Restart the backend server after adding environment variables

### Bills not being created

1. Check that text patterns are configured for the utility provider
2. Verify the PDF contains extractable text (not just images)
3. Check backend logs for pattern matching errors
4. Ensure the user has at least one property configured

### Gmail authentication errors

- Verify the app password is correct
- Ensure 2-Step Verification is enabled on the Gmail account
- Check that IMAP is enabled in Gmail settings

### Multiple users with overlapping addresses

- The system uses the `+{user_id}` suffix to route emails correctly
- If a bill address matches multiple properties, it will use the first match
- Consider adding more specific address patterns or using the contract ID field

## Security Considerations

1. **App Password**: Store the Gmail app password securely in `.env` (never commit to git)
2. **IMAP Access**: Uses SSL/TLS encryption (port 993)
3. **User Isolation**: Each user's bills are only accessible via their unique email suffix
4. **Email Marking**: Emails are marked as read after processing to prevent reprocessing

## API Endpoints

### Sync Email Bills (User)
```
POST /email/sync
Authorization: Bearer {token}
```

Response:
```json
{
  "status": "success",
  "message": "Processed 3 emails, created 2 bills",
  "emails_processed": 3,
  "bills_created": 2,
  "bills": [
    {
      "id": "bill-id",
      "amount": 150.50,
      "description": "Bill from Vodafone"
    }
  ],
  "errors": []
}
```

### Sync All Email Bills (Admin)
```
POST /email/sync-all
Authorization: Bearer {admin-token}
```

Processes emails for all users.

## Future Enhancements

1. **Scheduled Sync**: Automatic background job to sync bills periodically
2. **Email Notifications**: Notify users when new bills are imported
3. **Duplicate Detection**: Prevent creating duplicate bills from same email
4. **Manual Property Selection**: UI for resolving ambiguous property matches
5. **Email Body Parsing**: Extract bill info from email body (not just PDFs)

