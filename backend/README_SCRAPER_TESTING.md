# Scraper Testing Guide

## Overview
The web scraper can be tested independently before integrating it into the main sync button. This helps debug configuration issues without affecting the production sync functionality.

## Testing Tools

### 1. Standalone Test Script
Use the `test_scraper.py` script to test scraper configurations from the command line.

#### Basic Usage
```bash
# Test full scraper (login + bills extraction)
poetry run python backend/test_scraper.py Hidroelectrica --username "your_username" --password "your_password"

# Test login only
poetry run python backend/test_scraper.py Hidroelectrica --username "your_username" --password "your_password" --login-only

# Inspect login page structure (no credentials needed)
poetry run python backend/test_scraper.py Hidroelectrica --inspect
```

#### What it does:
- Loads the scraper config from `backend/scraper_configs/{supplier_name}.json`
- Tests login with provided credentials
- Tests bill extraction (if login-only not specified)
- Shows detailed output of what was found

### 2. Admin API Endpoint
Use the `/admin/test-scraper` endpoint to test via API (requires admin authentication).

#### Example using curl:
```bash
curl -X POST "http://localhost:8000/admin/test-scraper?supplier_name=Hidroelectrica&username=your_username&password=your_password&login_only=false" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

#### Response format:
```json
{
  "supplier_name": "Hidroelectrica",
  "config_loaded": true,
  "login_success": true,
  "bills_found": 2,
  "bills": [
    {
      "bill_number": "12345",
      "amount": 150.50,
      "due_date": "2024-01-15T00:00:00",
      "pdf_url": "https://...",
      "has_pdf": true,
      "pdf_size": 12345
    }
  ],
  "error": null
}
```

## Configuration Checklist

When setting up a new supplier scraper, check:

1. ✅ **Login URL** - Correct URL for login page
2. ✅ **Bills URL** - Correct URL for bills listing page
3. ✅ **Login form selector** - CSS selector to find the login form
4. ✅ **Login success indicator** - How to detect successful login (selector or text)
5. ✅ **Bills list selector** - CSS selector for the container holding all bills
6. ✅ **Bill item selector** - CSS selector for individual bill items
7. ✅ **Field selectors** - Selectors for bill number, amount, due date, PDF link

## Common Issues

### Login fails
- Check if `login_success_indicator` is correct
- Verify username/password field names (can use `--inspect` to see form structure)
- Check if the site uses JavaScript for login (may need Selenium/Playwright instead)

### No bills found
- Verify `bills_url` is correct and accessible after login
- Check `bills_list_selector` matches the actual HTML structure
- Use browser DevTools to inspect the bills page HTML

### Bills found but data is wrong
- Verify field selectors (bill_number_selector, bill_amount_selector, etc.)
- Check if selectors are too broad/narrow
- Consider using regex patterns instead of CSS selectors

## Next Steps

Once the scraper is working in test mode:
1. Verify it works with the test script/endpoint
2. Check that bills are extracted correctly
3. Verify PDFs are downloaded if available
4. Then use the sync button - it will use the same scraper code

