"""
Synchronous version of web scraper using Playwright sync API.
This is used on Windows where the async API has event loop issues.
Runs in a thread executor to avoid blocking the main event loop.
"""

# Removed event loop policy setting - let the system handle it

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from bs4 import BeautifulSoup
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import logging
import json
import re
import httpx

from app.web_scraper import ScraperConfig, ScrapedBill

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Ensure handler exists if not already configured
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.propagate = True


class WebScraperSync:
    """Synchronous web scraper using Playwright sync API"""
    
    def __init__(self, config: ScraperConfig, save_html_dumps: bool = False):
        self.config = config
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.logged_in = False
        self.save_html_dumps = save_html_dumps
        self.dump_counter = 0
    
    def _save_html_dump(self, html_content: str, page_name: str):
        """Save HTML content to file for inspection"""
        if not self.save_html_dumps:
            return
        
        dump_dir = Path(__file__).parent.parent / "scraper_dumps"
        dump_dir.mkdir(exist_ok=True)
        self.dump_counter += 1
        dump_file = dump_dir / f"{self.config.supplier_name.lower()}_{self.dump_counter:02d}_{page_name}.html"
        try:
            with open(dump_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            abs_path = dump_file.resolve()
            print(f"[SAVED] HTML dump: {abs_path}", flush=True)
            logger.info(f"[{self.config.supplier_name} Scraper] Saved HTML dump: {abs_path}")
        except Exception as e:
            print(f"[ERROR] Failed to save HTML dump: {e}", flush=True)
            logger.error(f"[{self.config.supplier_name} Scraper] Failed to save HTML dump: {e}", exc_info=True)
    
    def _init_browser(self):
        """Initialize Playwright browser using sync API"""
        if not self.playwright:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            self.page = self.context.new_page()
    
    def login(self, username: str, password: str) -> bool:
        """Login to the supplier website using sync API"""
        try:
            # Log credentials for debugging (only for Hidroelectrica)
            if self.config.supplier_name.lower() == "hidroelectrica":
                logger.info(f"[{self.config.supplier_name} Scraper] Starting login with username: {username}, password: {password}")
            else:
                logger.info(f"[{self.config.supplier_name} Scraper] Starting login...")
            
            self._init_browser()
            logger.info(f"[{self.config.supplier_name} Scraper] Browser initialized, proceeding with login...")
            
            if self.config.login_method == "form":
                return self._login_form(username, password)
            elif self.config.login_method == "api":
                return self._login_api(username, password)
            else:
                raise ValueError(f"Unknown login method: {self.config.login_method}")
        
        except Exception as e:
            logger.error(f"[{self.config.supplier_name} Scraper] Login failed: {e}", exc_info=True)
            return False
    
    def _login_form(self, username: str, password: str) -> bool:
        """Login using form submission with Playwright sync API"""
        # Navigate to login page
        self.page.goto(self.config.login_url, wait_until="networkidle")
        
        # Save HTML dump of login page
        login_html = self.page.content()
        self._save_html_dump(login_html, "login")
        
        # Find username and password fields
        username_field = self.config.username_field or "txtLogin"
        password_field = self.config.password_field or "txtpwd"
        
        # Fill in username and password
        try:
            self.page.fill(f'input[name="{username_field}"]', username)
            self.page.fill(f'input[name="{password_field}"]', password)
        except Exception as e:
            logger.error(f"[{self.config.supplier_name} Scraper] Failed to fill login fields: {e}")
            return False
        
        # Wait a bit for any JavaScript to initialize (like reCAPTCHA)
        self.page.wait_for_timeout(1000)
        
        # Click the submit button
        try:
            self.page.wait_for_selector('input[name="btnlogin"]', state="visible")
            self.page.click('input[name="btnlogin"]')
            self.page.wait_for_load_state("networkidle", timeout=int(self.config.timeout * 1000))
        except Exception as e:
            logger.warning(f"[{self.config.supplier_name} Scraper] Error clicking submit button: {e}")
            self.page.press(f'input[name="{password_field}"]', "Enter")
            self.page.wait_for_load_state("networkidle", timeout=int(self.config.timeout * 1000))
        
        # Wait after login as configured
        if self.config.wait_after_login > 0:
            self.page.wait_for_timeout(int(self.config.wait_after_login * 1000))
        
        # Get current URL and page content
        current_url = self.page.url
        page_html = self.page.content()
        self._save_html_dump(page_html, "after_login")
        
        logger.debug(f"[{self.config.supplier_name} Scraper] Current URL after login: {current_url}")
        
        # Check if login was successful
        login_success = False
        success_reason = ""
        
        if "dashboard.aspx" in current_url.lower() and "default.aspx" not in current_url.lower():
            login_success = True
            success_reason = f"redirected to {current_url}"
        
        if not login_success and self.config.login_success_indicator:
            if self.config.login_success_indicator.startswith("url:"):
                url_pattern = self.config.login_success_indicator.replace("url:", "").strip()
                if url_pattern.lower() in current_url.lower():
                    login_success = True
                    success_reason = f"URL contains {url_pattern}"
        
        if login_success:
            self.logged_in = True
            logger.info(f"[{self.config.supplier_name} Scraper] Login successful: {success_reason}")
            return True
        else:
            logger.warning(f"[{self.config.supplier_name} Scraper] Login failed - URL is still: {current_url}")
            return False
    
    def _login_api(self, username: str, password: str) -> bool:
        """Login using API (not implemented for sync version)"""
        raise NotImplementedError("API login not implemented for sync scraper")
    
    def get_bills(self) -> List[ScrapedBill]:
        """Get bills from the supplier website"""
        if not self.logged_in:
            logger.error(f"[{self.config.supplier_name} Scraper] Not logged in, cannot get bills")
            return []
        
        bills = []
        bills_url = self.config.bills_url or self.config.base_url
        
        try:
            logger.info(f"[{self.config.supplier_name} Scraper] Navigating to bills page: {bills_url}")
            self.page.goto(bills_url, wait_until="networkidle")
            
            page_html = self.page.content()
            self._save_html_dump(page_html, "bills_page")
            
            soup = BeautifulSoup(page_html, "html.parser")
            
            # Find bills list
            bills_container = None
            if self.config.bills_list_selector:
                bills_container = soup.select_one(self.config.bills_list_selector)
            else:
                for selector in ["table", ".bills", "#bills", ".invoices", "#invoices", "#data-table"]:
                    bills_container = soup.select_one(selector)
                    if bills_container:
                        break
            
            if not bills_container:
                logger.warning(f"[{self.config.supplier_name} Scraper] Bills container not found")
                return bills
            
            # Extract individual bills
            if self.config.bill_item_selector:
                bill_items = bills_container.select(self.config.bill_item_selector)
            else:
                bill_items = bills_container.find_all(["tr", "li", "div"], class_=re.compile(r"bill|invoice", re.I))
            
            logger.info(f"[{self.config.supplier_name} Scraper] Found {len(bill_items)} bill items")
            
            for idx, item in enumerate(bill_items):
                bill = self._extract_bill_from_item(item, self.page.url)
                if bill:
                    # Download PDF if needed
                    if bill.pdf_url and not bill.pdf_content:
                        self._download_pdf(bill)
                    bills.append(bill)
            
            logger.info(f"[{self.config.supplier_name} Scraper] Extracted {len(bills)} bill(s)")
            return bills
            
        except Exception as e:
            logger.error(f"[{self.config.supplier_name} Scraper] Error getting bills: {e}", exc_info=True)
            return bills
    
    def _extract_bill_from_item(self, item, base_url: str) -> Optional[ScrapedBill]:
        """Extract bill information from HTML element"""
        try:
            # Extract bill number
            bill_number = None
            if self.config.bill_number_selector:
                bill_el = item.select_one(self.config.bill_number_selector)
                if bill_el:
                    bill_number = bill_el.get_text(strip=True)
            
            # Extract amount - assume value is in bani, strip all commas/dots, then divide by 100
            amount = None
            if self.config.bill_amount_selector:
                amount_el = item.select_one(self.config.bill_amount_selector)
                if amount_el:
                    amount_text = amount_el.get_text(strip=True)
                    # Extract numeric value - strip all commas, dots, and spaces
                    amount_match = re.search(r'[\d,.]+', amount_text)
                    if amount_match:
                        # Strip all commas and dots - assume value is in bani
                        cleaned = amount_match.group().replace(',', '').replace('.', '').replace(' ', '')
                        try:
                            # Convert to int (bani) then divide by 100 to get lei
                            amount_bani = int(cleaned)
                            amount = amount_bani / 100.0
                        except ValueError:
                            pass
            
            # Extract due date
            due_date = None
            if self.config.bill_due_date_selector:
                due_el = item.select_one(self.config.bill_due_date_selector)
                if due_el:
                    due_text = due_el.get_text(strip=True)
                    # Try to parse date
                    for fmt in ["%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
                        try:
                            due_date = datetime.strptime(due_text.strip(), fmt)
                            break
                        except:
                            continue
            
            # Extract contract_id (usually in the same row or nearby)
            contract_id = None
            if self.config.bill_contract_id_selector:
                contract_el = item.select_one(self.config.bill_contract_id_selector)
                if contract_el:
                    contract_id = contract_el.get_text(strip=True)
            
            # Extract PDF link
            pdf_url = None
            if self.config.bill_pdf_link_selector:
                pdf_link = item.select_one(self.config.bill_pdf_link_selector)
                if pdf_link and pdf_link.get("href"):
                    pdf_url = pdf_link.get("href")
                    if not pdf_url.startswith("http"):
                        if pdf_url.startswith("/"):
                            pdf_url = f"{self.config.base_url}{pdf_url}"
                        else:
                            pdf_url = f"{base_url}/{pdf_url}"
            
            # Also check for JavaScript onclick handlers (like BillClick)
            if not pdf_url:
                onclick = item.get("onclick") or (item.find("a") and item.find("a").get("onclick"))
                if onclick and "BillClick" in onclick:
                    # Extract parameters from BillClick function call
                    match = re.search(r"BillClick\(['\"]([^'\"]+)['\"]\)", onclick)
                    if match:
                        bill_params = match.group(1)
                        # Store params for later PDF download
                        pdf_url = f"javascript:BillClick('{bill_params}')"
            
            if bill_number or amount or pdf_url:
                return ScrapedBill(
                    bill_number=bill_number,
                    amount=amount,
                    due_date=due_date,
                    pdf_url=pdf_url,
                    contract_id=contract_id,
                    raw_data={}
                )
        except Exception as e:
            logger.warning(f"[{self.config.supplier_name} Scraper] Error extracting bill: {e}")
        
        return None
    
    def _download_pdf(self, bill: ScrapedBill):
        """Download PDF for a bill"""
        if not bill.pdf_url or bill.pdf_content:
            return
        
        try:
            if bill.pdf_url.startswith("javascript:"):
                # Handle JavaScript-based PDF download
                self._download_pdf_via_javascript(bill, bill.pdf_url.replace("javascript:BillClick('", "").replace("')", ""))
            elif bill.pdf_url.startswith("http"):
                # Direct URL download
                self._download_pdf_from_url(bill)
        except Exception as e:
            logger.warning(f"[{self.config.supplier_name} Scraper] Failed to download PDF: {e}")
    
    def _download_pdf_via_javascript(self, bill: ScrapedBill, bill_params: str):
        """Download PDF by calling JavaScript BillClick function"""
        try:
            # Use event listener to intercept the AJAX response
            pdf_url_from_json = [None]  # Use list to allow modification in closure
            
            def handle_response(response):
                try:
                    if response.url and ("BillDashboard.aspx" in response.url or "GetBill" in response.url):
                        pdf_url_from_json[0] = response.json().get("d")
                except:
                    pass
            
            # Set up response listener
            self.page.on("response", handle_response)
            
            try:
                # Call BillClick function
                self.page.evaluate(f"BillClick('{bill_params}')")
                
                # Wait for response (with timeout)
                self.page.wait_for_timeout(3000)
            finally:
                # Remove listener
                self.page.remove_listener("response", handle_response)
            
            # Parse JSON response to get PDF URL
            if pdf_url_from_json[0]:
                pdf_path = pdf_url_from_json[0]
                if isinstance(pdf_path, str):
                    if pdf_path.startswith('"') and pdf_path.endswith('"'):
                        pdf_path = pdf_path[1:-1]
                    pdf_path = pdf_path.replace("\\u0026", "&").replace("\\", "")
                    
                    if pdf_path.startswith("Upload.ashx"):
                        bill.pdf_url = f"{self.config.base_url}/portal/{pdf_path}"
                    elif pdf_path.startswith("/"):
                        bill.pdf_url = f"{self.config.base_url}{pdf_path}"
                    elif pdf_path.startswith("http"):
                        bill.pdf_url = pdf_path
                    else:
                        bill.pdf_url = f"{self.config.base_url}/portal/{pdf_path}"
                    
                    # Now download the actual PDF
                    self._download_pdf_from_url(bill)
        except Exception as e:
            logger.warning(f"[{self.config.supplier_name} Scraper] Failed to download PDF via JavaScript: {e}", exc_info=True)
    
    def _download_pdf_from_url(self, bill: ScrapedBill):
        """Download PDF from a direct URL"""
        try:
            response = self.page.request.get(bill.pdf_url)
            if response.status == 200:
                bill.pdf_content = response.body()
                logger.debug(f"[{self.config.supplier_name} Scraper] Downloaded PDF: {len(bill.pdf_content)} bytes")
                
                if self.save_html_dumps and bill.pdf_content:
                    self._save_pdf_dump(bill)
        except Exception as e:
            logger.warning(f"[{self.config.supplier_name} Scraper] Failed to download PDF from {bill.pdf_url}: {e}")
    
    def _save_pdf_dump(self, bill: ScrapedBill):
        """Save PDF to file for debugging"""
        try:
            dump_dir = Path(__file__).parent.parent / "scraper_dumps"
            dump_dir.mkdir(exist_ok=True)
            self.dump_counter += 1
            filename = f"{self.config.supplier_name.lower()}_{self.dump_counter:02d}_bill_{bill.bill_number or 'unknown'}.pdf"
            dump_file = dump_dir / filename
            with open(dump_file, 'wb') as f:
                f.write(bill.pdf_content)
            logger.info(f"[{self.config.supplier_name} Scraper] Saved PDF dump: {dump_file.resolve()}")
        except Exception as e:
            logger.error(f"[{self.config.supplier_name} Scraper] Failed to save PDF dump: {e}")
    
    def close(self):
        """Close browser and cleanup"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            logger.warning(f"[{self.config.supplier_name} Scraper] Error during cleanup: {e}")

