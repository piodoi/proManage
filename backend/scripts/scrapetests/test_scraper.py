"""
Test script for web scraper configuration.
Allows testing scraper configs without going through the full sync process.
"""

import asyncio
import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.web_scraper import WebScraper, load_scraper_config
import logging

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_test_credentials(supplier_name: str) -> dict:
    """Load test credentials from config file.
    
    Looks for credentials in:
    1. scraper_configs/{supplier}_credentials.json
    2. test_credentials.json (with supplier key)
    
    Returns dict with 'username' and 'password' keys, or None if not found.
    """
    config_dir = Path(__file__).parent / "scraper_configs"
    
    # Try supplier-specific credentials file first
    creds_file = config_dir / f"{supplier_name.lower()}_credentials.json"
    if creds_file.exists():
        try:
            with open(creds_file, 'r', encoding='utf-8') as f:
                creds = json.load(f)
                if 'username' in creds and 'password' in creds:
                    return creds
        except Exception as e:
            logger.warning(f"Failed to load credentials from {creds_file}: {e}")
    
    # Try general test_credentials.json
    creds_file = Path(__file__).parent / "test_credentials.json"
    if creds_file.exists():
        try:
            with open(creds_file, 'r', encoding='utf-8') as f:
                all_creds = json.load(f)
                # Check if it's a dict with supplier keys
                if isinstance(all_creds, dict):
                    supplier_key = supplier_name.lower()
                    if supplier_key in all_creds:
                        creds = all_creds[supplier_key]
                        if isinstance(creds, dict) and 'username' in creds and 'password' in creds:
                            return creds
        except Exception as e:
            logger.warning(f"Failed to load credentials from {creds_file}: {e}")
    
    return None


async def test_scraper(supplier_name: str, username: str, password: str):
    """Test scraper for a given supplier"""
    logger.info(f"Testing scraper for {supplier_name}")
    
    # Load config
    config = load_scraper_config(supplier_name)
    if not config:
        logger.error(f"Config not found for {supplier_name}")
        print(f"\n[ERROR] Config file not found: backend/scraper_configs/{supplier_name.lower()}.json")
        return False
    
    print(f"\n[OK] Loaded config for {supplier_name}")
    print(f"   Base URL: {config.base_url}")
    print(f"   Login URL: {config.login_url}")
    print(f"   Bills URL: {config.bills_url}")
    
    # Create scraper with HTML dumps enabled
    scraper = WebScraper(config, save_html_dumps=True)
    
    try:
        # Test login
        print(f"\n[LOGIN] Attempting login...")
        logged_in = await scraper.login(username, password)
        
        if not logged_in:
            print(f"[FAILED] Login failed")
            return False
        
        print(f"[SUCCESS] Login successful!")
        
        # Test getting bills
        print(f"\n[FETCH] Fetching bills...")
        bills = await scraper.get_bills()
        
        print(f"[OK] Found {len(bills)} bill(s)")
        
        if bills:
            print(f"\n[BILLS] Bills found:")
            for i, bill in enumerate(bills, 1):
                print(f"\n   Bill #{i}:")
                if bill.bill_number:
                    print(f"      Number: {bill.bill_number}")
                if bill.amount:
                    print(f"      Amount: {bill.amount}")
                if bill.due_date:
                    print(f"      Due Date: {bill.due_date}")
                if bill.pdf_url:
                    print(f"      PDF URL: {bill.pdf_url}")
                if bill.pdf_content:
                    print(f"      PDF Size: {len(bill.pdf_content)} bytes")
        else:
            print(f"[WARN] No bills found - check your selectors in the config file")
        
        return True
    
    except Exception as e:
        logger.error(f"Error testing scraper: {e}", exc_info=True)
        print(f"\n[ERROR] {e}")
        return False
    
    finally:
        await scraper.close()


async def test_login_only(supplier_name: str, username: str, password: str):
    """Test just the login process"""
    logger.info(f"Testing login for {supplier_name}")
    
    config = load_scraper_config(supplier_name)
    if not config:
        print(f"[ERROR] Config not found")
        return False
    
    scraper = WebScraper(config, save_html_dumps=True)  # Enable HTML dumps
    
    try:
        print(f"\n[LOGIN] Testing login to {config.login_url}...")
        logged_in = await scraper.login(username, password)
        
        if logged_in:
            print(f"[SUCCESS] Login successful!")
            return True
        else:
            print(f"[FAILED] Login failed - check credentials and login_success_indicator in config")
            return False
    
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        print(f"\n[ERROR] {e}")
        return False
    
    finally:
        await scraper.close()
        # Show where HTML dumps were saved
        if scraper.save_html_dumps and scraper.dump_counter > 0:
            dump_dir = Path(__file__).parent / "scraper_dumps"
            print(f"\n[INFO] HTML dumps saved to: {dump_dir.resolve()}")
        elif scraper.save_html_dumps:
            dump_dir = Path(__file__).parent / "scraper_dumps"
            print(f"\n[WARN] HTML dumps enabled but no files were saved. Check if _save_html_dump was called.")


async def inspect_login_page(supplier_name: str):
    """Fetch and save login page HTML structure"""
    import httpx
    
    config = load_scraper_config(supplier_name)
    if not config:
        print(f"[ERROR] Config not found")
        return
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        print(f"\n[FETCH] Fetching login page: {config.login_url}")
        response = await client.get(config.login_url)
        
        print(f"   Status: {response.status_code}")
        print(f"   Final URL: {response.url}")
        
        # Save HTML to file
        dump_file = Path(__file__).parent / f"{supplier_name.lower()}_login_dump.html"
        with open(dump_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f"[OK] Saved HTML to: {dump_file}")
        print(f"   Open this file in a browser to inspect the login form structure")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test web scraper configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using command-line arguments:
  python test_scraper.py e-bloc --username user@example.com --password mypass
  
  # Using credentials config file (recommended for passwords with special characters):
  # Create scraper_configs/e-bloc_credentials.json:
  # {
  #   "username": "user@example.com",
  #   "password": "pass&word"
  # }
  python test_scraper.py e-bloc
  
  # Or use test_credentials.json with supplier key:
  # {
  #   "e-bloc": {
  #     "username": "user@example.com",
  #     "password": "pass&word"
  #   }
  # }
  python test_scraper.py e-bloc
        """
    )
    parser.add_argument("supplier", help="Supplier name (e.g., 'Hidroelectrica', 'e-bloc')")
    parser.add_argument("--username", help="Username for login (optional if using config file)")
    parser.add_argument("--password", help="Password for login (optional if using config file)")
    parser.add_argument("--login-only", action="store_true", help="Only test login")
    parser.add_argument("--inspect", action="store_true", help="Inspect login page structure")
    
    args = parser.parse_args()
    
    # Load credentials
    username = args.username
    password = args.password
    
    # Try to load from config file if not provided via command line
    if not username or not password:
        creds = load_test_credentials(args.supplier)
        if creds:
            if not username:
                username = creds.get('username')
            if not password:
                password = creds.get('password')
            print(f"[INFO] Loaded credentials from config file")
        else:
            if not username or not password:
                print(f"[ERROR] Credentials not provided and config file not found.")
                print(f"   Either provide --username and --password arguments,")
                print(f"   or create scraper_configs/{args.supplier.lower()}_credentials.json")
                print(f"   or create test_credentials.json with '{args.supplier.lower()}' key")
                sys.exit(1)
    
    if args.inspect:
        asyncio.run(inspect_login_page(args.supplier))
    elif args.login_only:
        success = asyncio.run(test_login_only(args.supplier, username, password))
        sys.exit(0 if success else 1)
    else:
        success = asyncio.run(test_scraper(args.supplier, username, password))
        sys.exit(0 if success else 1)

