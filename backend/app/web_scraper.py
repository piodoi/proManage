"""
General-purpose web scraper for supplier websites.
Data-driven configuration allows easy addition of new suppliers.
Uses Playwright for JavaScript-enabled sites with reCAPTCHA.
"""

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from bs4 import BeautifulSoup
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import logging
import re
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class ScrapedBill:
    """Represents a bill scraped from a supplier website"""
    bill_number: Optional[str] = None
    amount: Optional[float] = None
    due_date: Optional[datetime] = None
    issue_date: Optional[datetime] = None
    period_from: Optional[datetime] = None
    period_to: Optional[datetime] = None
    contract_id: Optional[str] = None
    pdf_url: Optional[str] = None
    pdf_content: Optional[bytes] = None
    raw_data: Optional[Dict] = None


@dataclass
class ScraperConfig:
    """Configuration for a supplier scraper"""
    supplier_name: str
    base_url: str
    login_url: str
    bills_url: Optional[str] = None
    
    # Login configuration
    login_method: str = "form"  # "form" or "api"
    login_form_selector: Optional[str] = None  # CSS selector for login form
    login_success_indicator: Optional[str] = None  # Text or selector indicating successful login
    # Note: username_field and password_field are detected automatically from form, but can be overridden if needed
    username_field: Optional[str] = None  # Optional: field name for username (auto-detected if not set)
    password_field: Optional[str] = None  # Optional: field name for password (auto-detected if not set)
    login_submit_button_selector: Optional[str] = None  # Optional: CSS selector for submit button (default: input[name="btnlogin"])
    
    # Navigation configuration
    bills_page_url: Optional[str] = None
    bills_list_selector: Optional[str] = None  # CSS selector for bills list container
    
    # Bill extraction configuration
    bill_item_selector: Optional[str] = None  # CSS selector for individual bill items
    bill_number_selector: Optional[str] = None
    bill_amount_selector: Optional[str] = None
    bill_due_date_selector: Optional[str] = None
    bill_issue_date_selector: Optional[str] = None
    bill_contract_id_selector: Optional[str] = None
    bill_pdf_link_selector: Optional[str] = None
    
    # Custom extraction functions (as string patterns or regex)
    bill_number_pattern: Optional[str] = None
    bill_amount_pattern: Optional[str] = None
    bill_due_date_pattern: Optional[str] = None
    
    # Headers
    custom_headers: Optional[Dict[str, str]] = None
    
    # Additional configuration
    requires_js: bool = False  # If True, would need Selenium/Playwright (not implemented yet)
    wait_after_login: float = 1.0  # Seconds to wait after login
    timeout: float = 30.0
    multiple_contracts_possible: bool = False  # If True, user may have multiple contracts/addresses
    
    # Cookie configuration (for sites that use cookies to switch between associations/apartments)
    cookie_config: Optional[Dict[str, Any]] = None  # e.g., {"asoc-cur": "{association_id}", "home-ap-cur": "{association_id}_{apartment_id}"}


class WebScraper:
    """General-purpose web scraper for supplier websites using Playwright"""
    
    def __init__(self, config: ScraperConfig, save_html_dumps: bool = False):
        self.config = config
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.logged_in = False
        self.save_html_dumps = save_html_dumps
        self.dump_counter = 0
    
    async def _init_browser(self):
        """Initialize Playwright browser"""
        if not self.playwright:
            try:
                self.playwright = await async_playwright().start()
            except NotImplementedError as e:
                # On Windows with ProactorEventLoop, Playwright can't create subprocesses
                # This happens when FastAPI/uvicorn uses ProactorEventLoop on Windows
                # The test_scraper works because it uses asyncio.run() which creates SelectorEventLoop
                import platform
                if platform.system() == 'Windows':
                    error_msg = (
                        "Playwright cannot start on Windows with ProactorEventLoop. "
                        "This is a known limitation. Please run the server with: "
                        "`uvicorn app.main:app --loop asyncio` or use WindowsSelectorEventLoop policy."
                    )
                    logger.error(f"[{self.config.supplier_name} Scraper] {error_msg}")
                    raise RuntimeError(error_msg) from e
                raise
            
            self.browser = await self.playwright.chromium.launch(headless=True)
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            self.page = await self.context.new_page()
            # Note: Cookies with association_id/apartment_id will be set later in get_bills() when IDs are available
    
    async def _set_cookies_from_config(self, association_id: Optional[str] = None, apartment_id: Optional[str] = None):
        """Set cookies from config, replacing placeholders with actual values.
        Only sets cookies when association_id is provided (required for cookie placeholders)."""
        if not self.config.cookie_config or not self.page:
            return
        
        # Only set cookies if we have association_id (required for placeholders)
        if not association_id:
            return
        
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(self.config.base_url)
            domain = parsed_url.netloc
            
            cookies = []
            for cookie_name, cookie_template in self.config.cookie_config.items():
                cookie_value = cookie_template
                # Replace placeholders
                if association_id:
                    cookie_value = cookie_value.replace("{association_id}", association_id)
                if apartment_id:
                    cookie_value = cookie_value.replace("{apartment_id}", apartment_id)
                if association_id and apartment_id:
                    cookie_value = cookie_value.replace("{association_id}_{apartment_id}", f"{association_id}_{apartment_id}")
                
                cookies.append({
                    "name": cookie_name,
                    "value": cookie_value,
                    "domain": domain,
                    "path": "/"
                })
            
            if cookies:
                await self.context.add_cookies(cookies)
                logger.info(f"[{self.config.supplier_name} Scraper] Set cookies: {[c['name'] for c in cookies]}")
        except Exception as e:
            logger.warning(f"[{self.config.supplier_name} Scraper] Failed to set cookies: {e}")
    
    def set_association_cookies(self, association_id: str, apartment_id: Optional[str] = None):
        """Set cookies for association/apartment selection (for e-bloc style sites)"""
        if not self.page:
            logger.warning(f"[{self.config.supplier_name} Scraper] Cannot set cookies - page not initialized")
            return
        
        # Update cookies asynchronously
        import asyncio
        if asyncio.iscoroutinefunction(self._set_cookies_from_config):
            # If we're in an async context, schedule it
            asyncio.create_task(self._set_cookies_from_config(association_id, apartment_id))
        else:
            # Otherwise, we'll need to call it from an async method
            pass
    
    async def login(self, username: str, password: str) -> bool:
        """Login to the supplier website"""
        try:
            # Log credentials for debugging (only for Hidroelectrica)
            logger.info(f"[{self.config.supplier_name} Scraper] Starting login...")
            
            await self._init_browser()
            logger.info(f"[{self.config.supplier_name} Scraper] Browser initialized, proceeding with login...")
            
            if self.config.login_method == "form":
                return await self._login_form(username, password)
            elif self.config.login_method == "api":
                return await self._login_api(username, password)
            else:
                raise ValueError(f"Unknown login method: {self.config.login_method}")
        
        except Exception as e:
            logger.error(f"[{self.config.supplier_name} Scraper] Login failed: {e}", exc_info=True)
            return False
    
    def _save_html_dump(self, html_content: str, page_name: str):
        """Save HTML content to file for inspection"""
        if not self.save_html_dumps:
            return
        
        # Use absolute path to ensure we're saving in the right place
        # Path(__file__) = backend/app/web_scraper.py
        # .parent = backend/app
        # .parent = backend
        # / "scraper_dumps" = backend/scraper_dumps
        dump_dir = Path(__file__).parent.parent / "scraper_dumps"
        dump_dir.mkdir(exist_ok=True)
        self.dump_counter += 1
        dump_file = dump_dir / f"{self.config.supplier_name.lower()}_{self.dump_counter:02d}_{page_name}.html"
        try:
            with open(dump_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            abs_path = dump_file.resolve()
            # Print to stdout (not just logger) so it shows in console
            print(f"[SAVED] HTML dump: {abs_path}", flush=True)
            logger.info(f"[{self.config.supplier_name} Scraper] Saved HTML dump: {abs_path}")
        except Exception as e:
            print(f"[ERROR] Failed to save HTML dump: {e}", flush=True)
            logger.error(f"[{self.config.supplier_name} Scraper] Failed to save HTML dump: {e}", exc_info=True)
    
    async def _login_form(self, username: str, password: str) -> bool:
        """Login using form submission with Playwright"""
        # Navigate to login page
        await self.page.goto(self.config.login_url, wait_until="networkidle")
        
        # Save HTML dump of login page
        login_html = await self.page.content()
        self._save_html_dump(login_html, "login")
        
        # Find username and password fields
        username_field = self.config.username_field or "txtLogin"
        password_field = self.config.password_field or "txtpwd"
        
        # Fill in username and password
        try:
            await self.page.fill(f'input[name="{username_field}"]', username)
            await self.page.fill(f'input[name="{password_field}"]', password)
        except Exception as e:
            logger.error(f"[{self.config.supplier_name} Scraper] Failed to fill login fields: {e}")
            return False
        
        # Wait a bit for any JavaScript to initialize (like reCAPTCHA)
        await self.page.wait_for_timeout(1000)
        
        # Click the submit button
        submit_button_selector = self.config.login_submit_button_selector or 'input[name="btnlogin"]'
        try:
            # Wait for the submit button to be ready
            await self.page.wait_for_selector(submit_button_selector, state="visible", timeout=5000)
            # Click the submit button and wait for navigation
            await self.page.click(submit_button_selector)
            # Wait for navigation to complete (either redirect or page change)
            await self.page.wait_for_load_state("networkidle", timeout=int(self.config.timeout * 1000))
        except Exception as e:
            logger.warning(f"[{self.config.supplier_name} Scraper] Error clicking submit button with selector '{submit_button_selector}': {e}")
            # Try alternative: press Enter on password field
            try:
                await self.page.press(f'input[name="{password_field}"]', "Enter")
                await self.page.wait_for_load_state("networkidle", timeout=int(self.config.timeout * 1000))
            except Exception as e2:
                logger.warning(f"[{self.config.supplier_name} Scraper] Alternative submit (Enter key) also failed: {e2}")
                # Form might submit automatically, just wait a bit
                await self.page.wait_for_timeout(2000)
        
        # Wait after login as configured
        if self.config.wait_after_login > 0:
            await self.page.wait_for_timeout(int(self.config.wait_after_login * 1000))
        
        # Get current URL and page content
        current_url = self.page.url
        page_html = await self.page.content()
        self._save_html_dump(page_html, "after_login")
        
        logger.debug(f"[{self.config.supplier_name} Scraper] Current URL after login: {current_url}")
        
        # Check if login was successful - successful login redirects to Dashboard.aspx
        login_success = False
        success_reason = ""
        
        # Check if we were redirected to Dashboard.aspx
        if "dashboard.aspx" in current_url.lower() and "default.aspx" not in current_url.lower():
            login_success = True
            success_reason = f"redirected to {current_url}"
        
        # Also check configured success indicator
        if not login_success and self.config.login_success_indicator:
            if self.config.login_success_indicator.startswith("selector:"):
                selector = self.config.login_success_indicator.replace("selector:", "").strip()
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        login_success = True
                        success_reason = f"found selector: {selector}"
                except:
                    pass
            elif self.config.login_success_indicator.startswith("url:"):
                url_pattern = self.config.login_success_indicator.replace("url:", "").strip()
                if url_pattern in current_url:
                    login_success = True
                    success_reason = f"URL contains: {url_pattern}"
            elif self.config.login_success_indicator in page_html:
                login_success = True
                success_reason = "found text indicator"
        
        # Final check: if we're on Dashboard (not default), it's success
        if not login_success:
            if "dashboard" in current_url.lower() and "default.aspx" not in current_url.lower():
                login_success = True
                success_reason = "on Dashboard page"
        
        if login_success:
            self.logged_in = True
            logger.info(f"[{self.config.supplier_name} Scraper] Login successful ({success_reason})")
            # Note: Cookies with association_id/apartment_id will be set in get_bills() when IDs are available
            return True
        
        logger.warning(f"[{self.config.supplier_name} Scraper] Login may have failed - URL: {current_url}")
        logger.info(f"[{self.config.supplier_name} Scraper] Check HTML dump file to see what the page contains after login")
        return False
    
    async def _login_api(self, username: str, password: str) -> bool:
        """Login using API endpoint (for future use)"""
        # This would be for API-based authentication
        # For now, we'll use form-based login
        raise NotImplementedError("API-based login not yet implemented")
    
    async def get_bills(self, association_id: Optional[str] = None, apartment_id: Optional[str] = None) -> List[ScrapedBill]:
        """Scrape bills from the supplier website
        
        Args:
            association_id: Optional association ID for cookie-based selection (e-bloc style)
            apartment_id: Optional apartment ID for cookie-based selection (e-bloc style)
        """
        if not self.logged_in:
            raise Exception("Not logged in. Call login() first.")
        
        if not self.page:
            await self._init_browser()
        
        # Set cookies if association/apartment IDs are provided
        if association_id and self.config.cookie_config:
            await self._set_cookies_from_config(association_id, apartment_id)
            # Navigate to a page to ensure cookies are set
            await self.page.goto(self.config.base_url, wait_until="networkidle")
            await self.page.wait_for_timeout(500)
        
        bills = []
        
        try:
            # Navigate to bills page
            bills_url = self.config.bills_url or self.config.bills_page_url
            if not bills_url:
                logger.warning(f"[{self.config.supplier_name} Scraper] No bills URL configured")
                return bills
            
            logger.info(f"[{self.config.supplier_name} Scraper] Fetching bills page...")
            await self.page.goto(bills_url, wait_until="networkidle")
            
            # Wait a bit for dynamic content to load
            await self.page.wait_for_timeout(2000)
            
            page_html = await self.page.content()
            self._save_html_dump(page_html, "bills_page")
            
            soup = BeautifulSoup(page_html, "html.parser")
            
            # Find bills list
            bills_container = None
            if self.config.bills_list_selector:
                bills_container = soup.select_one(self.config.bills_list_selector)
            else:
                # Try to find common bill list containers
                for selector in ["table", ".bills", "#bills", ".invoices", "#invoices", "#data-table"]:
                    bills_container = soup.select_one(selector)
                    if bills_container:
                        break
            
            if not bills_container:
                logger.warning(f"[{self.config.supplier_name} Scraper] Bills container not found")
                return bills
            
            # For e-bloc style sites, extract bill number from page header
            bill_number_from_header = None
            if self.config.bill_number_pattern:
                # Try to find bill number in page header (e.g., "Lista de plată afişată Octombrie 2025")
                header_text = soup.get_text()
                month_year_match = re.search(self.config.bill_number_pattern, header_text, re.I)
                if month_year_match:
                    bill_number_from_header = month_year_match.group(1) if month_year_match.groups() else month_year_match.group(0)
                    # Try to extract apartment number from "Datoria curentă - Ap. 53"
                    apt_match = re.search(r'Datoria curentă.*?Ap\.\s*(\d+)', header_text, re.I)
                    if not apt_match:
                        # Fallback: try to extract from select dropdown "Apartament 8"
                        apt_select = soup.select_one('#home-ap option[selected], #home-ap option')
                        if apt_select:
                            apt_text = apt_select.get_text(strip=True)
                            apt_num_match = re.search(r'Apartament\s+(\d+)', apt_text, re.I)
                            if apt_num_match:
                                apt_match = apt_num_match
                    if apt_match:
                        apartment_num = apt_match.group(1)
                        bill_number_from_header = f"{bill_number_from_header} Ap.{apartment_num}"
                    logger.info(f"[{self.config.supplier_name} Scraper] Extracted bill number from header: {bill_number_from_header}")
            
            # Extract individual bills
            if self.config.bill_item_selector:
                bill_items = bills_container.select(self.config.bill_item_selector)
            else:
                # Default: try table rows or list items
                bill_items = bills_container.find_all(["tr", "li", "div"], class_=re.compile(r"bill|invoice", re.I))
            
            logger.info(f"[{self.config.supplier_name} Scraper] Found {len(bill_items)} bill items")
            
            for idx, item in enumerate(bill_items):
                # Use Playwright page for extraction if available (for JavaScript links)
                bill = await self._extract_bill_from_item(item, self.page.url if self.page else None, soup)
                if bill:
                    # Use bill number from header if available and bill doesn't have one
                    if bill_number_from_header and not bill.bill_number:
                        bill.bill_number = bill_number_from_header
                        logger.debug(f"[{self.config.supplier_name} Scraper] Set bill number from header: {bill.bill_number}")
                    
                    # Validate bill: must have both amount (can be 0) and bill_number (not None/empty)
                    if bill.bill_number and bill.amount is not None:
                        bills.append(bill)
                        # Only log at debug level to reduce noise
                        logger.debug(f"[{self.config.supplier_name} Scraper] Extracted bill #{idx+1}: number={bill.bill_number}, amount={bill.amount}, contract_id={bill.contract_id}")
                    else:
                        missing = []
                        if not bill.bill_number:
                            missing.append("bill_number")
                        if bill.amount is None:
                            missing.append("amount")
                        logger.debug(f"[{self.config.supplier_name} Scraper] Skipping bill #{idx+1} - missing required fields: {', '.join(missing)}")
                else:
                    logger.warning(f"[{self.config.supplier_name} Scraper] Failed to extract bill from item #{idx+1}")
            
        except Exception as e:
            logger.error(f"[{self.config.supplier_name} Scraper] Error scraping bills: {e}", exc_info=True)
        
        return bills
    
    async def _extract_bill_from_item(self, item, base_url: str = None, full_soup: BeautifulSoup = None) -> Optional[ScrapedBill]:
        """Extract bill data from a single HTML item"""
        try:
            bill = ScrapedBill()
            
            # Extract contract_id
            if self.config.bill_contract_id_selector:
                elem = item.select_one(self.config.bill_contract_id_selector)
                # If not found and selector starts with # (ID selector), try searching in full_soup
                if not elem and self.config.bill_contract_id_selector.startswith('#') and full_soup:
                    elem = full_soup.select_one(self.config.bill_contract_id_selector)
                if elem:
                    # Check if contract_id is in an attribute (e.g., cod_client="A54BB6E")
                    contract_id = elem.get('cod_client') or elem.get('data-contract-id') or elem.get('contract_id')
                    if contract_id:
                        bill.contract_id = contract_id
                    else:
                        bill.contract_id = elem.get_text(strip=True)
            
            # Extract bill number
            if self.config.bill_number_selector:
                elem = item.select_one(self.config.bill_number_selector)
                if elem:
                    bill.bill_number = elem.get_text(strip=True)
            elif self.config.bill_number_pattern:
                text = item.get_text()
                match = re.search(self.config.bill_number_pattern, text)
                if match:
                    bill.bill_number = match.group(1) if match.groups() else match.group(0)
            
            # Extract issue date
            if self.config.bill_issue_date_selector:
                elem = item.select_one(self.config.bill_issue_date_selector)
                if elem:
                    date_text = elem.get_text(strip=True)
                    bill.issue_date = self._parse_date(date_text)
            
            # Extract amount
            if self.config.bill_amount_selector:
                elem = item.select_one(self.config.bill_amount_selector)
                # If not found and selector starts with # (ID selector), try searching in full_soup
                if not elem and self.config.bill_amount_selector.startswith('#') and full_soup:
                    elem = full_soup.select_one(self.config.bill_amount_selector)
                if elem:
                    amount_text = elem.get_text(strip=True)
                    bill.amount = self._parse_amount(amount_text)
                    # Only log at debug level to reduce noise
                    logger.debug(f"[{self.config.supplier_name} Scraper] Extracted amount: {bill.amount} from selector {self.config.bill_amount_selector}")
                else:
                    logger.debug(f"[{self.config.supplier_name} Scraper] Amount selector '{self.config.bill_amount_selector}' not found")
            elif self.config.bill_amount_pattern:
                text = item.get_text()
                match = re.search(self.config.bill_amount_pattern, text)
                if match:
                    amount_text = match.group(1) if match.groups() else match.group(0)
                    bill.amount = self._parse_amount(amount_text)
            
            # Extract due date
            if self.config.bill_due_date_selector:
                elem = item.select_one(self.config.bill_due_date_selector)
                if elem:
                    date_text = elem.get_text(strip=True)
                    bill.due_date = self._parse_date(date_text)
            elif self.config.bill_due_date_pattern:
                text = item.get_text()
                match = re.search(self.config.bill_due_date_pattern, text)
                if match:
                    date_text = match.group(1) if match.groups() else match.group(0)
                    bill.due_date = self._parse_date(date_text)
            
            # Extract PDF link - handle JavaScript onclick links
            pdf_link_elem = None
            if self.config.bill_pdf_link_selector:
                pdf_link_elem = item.select_one(self.config.bill_pdf_link_selector)
            
            # If no selector found, try to find any link with onclick containing BillClick
            if not pdf_link_elem:
                pdf_link_elem = item.find("a", onclick=re.compile(r"BillClick", re.I))
            
            if pdf_link_elem:
                # Check if it's a JavaScript link (onclick)
                onclick = pdf_link_elem.get("onclick", "")
                if onclick and "BillClick" in onclick:
                    # Extract the parameter from BillClick('...')
                    match = re.search(r"BillClick\('([^']+)'\)", onclick)
                    if match:
                        bill_params = match.group(1)
                        # Store the params for later use - we'll call BillClick via Playwright
                        bill.pdf_url = f"javascript:BillClick('{bill_params}')"
                        # Download PDF by calling the JavaScript function
                        await self._download_pdf_via_javascript(bill, bill_params)
                else:
                    # Regular href link
                    href = pdf_link_elem.get("href", "")
                    if href and href != "javascript:":
                        if href.startswith("http"):
                            bill.pdf_url = href
                        else:
                            bill.pdf_url = f"{self.config.base_url}{href}"
                        # Download PDF
                        await self._download_pdf_from_url(bill)
            
            # Try to find any PDF link in the item (fallback)
            if not bill.pdf_url:
                pdf_link = item.find("a", href=re.compile(r"\.pdf", re.I))
                if pdf_link:
                    href = pdf_link.get("href", "")
                    if href.startswith("http"):
                        bill.pdf_url = href
                    elif href.startswith("/"):
                        bill.pdf_url = f"{self.config.base_url}{href}"
                    else:
                        # Relative URL
                        if base_url:
                            from urllib.parse import urljoin
                            bill.pdf_url = urljoin(base_url, href)
                        else:
                            bill.pdf_url = f"{self.config.base_url}/{href}"
                    await self._download_pdf_from_url(bill)
            
            # Return bill if it has at least bill_number, amount, or contract_id (for e-bloc style sites)
            # bill_number might be set from header after extraction, so we allow bills with just amount or contract_id
            if bill.bill_number or bill.amount or bill.contract_id:
                logger.debug(f"[{self.config.supplier_name} Scraper] Extracted bill: number={bill.bill_number}, amount={bill.amount}, contract_id={bill.contract_id}")
                return bill
            else:
                logger.debug(f"[{self.config.supplier_name} Scraper] Bill item has no bill_number, amount, or contract_id - skipping")
                return None
        
        except Exception as e:
            logger.warning(f"[{self.config.supplier_name} Scraper] Error extracting bill: {e}", exc_info=True)
            return None
    
    async def _download_pdf_via_javascript(self, bill: ScrapedBill, bill_params: str):
        """Download PDF by calling JavaScript BillClick function"""
        try:
            # BillClick makes an AJAX call that returns JSON with the PDF URL
            # Intercept the AJAX response
            pdf_url_from_json = None
            
            # Set up response listener to catch the AJAX response (JSON with PDF URL)
            async with self.page.expect_response(lambda response: 
                "BillDashboard.aspx" in response.url or 
                "GetBill" in response.url or
                "ViewBill" in response.url or
                response.headers.get("content-type", "").startswith("application/json")
            ) as response_info:
                # Call the BillClick function
                await self.page.evaluate(f"BillClick('{bill_params}')")
            
            response = await response_info.value
            if response.status == 200:
                response_text = await response.text()
                logger.debug(f"[{self.config.supplier_name} Scraper] BillClick response: {response_text[:200]}")
                
                # Parse JSON response to get PDF URL
                try:
                    import json
                    response_json = json.loads(response_text)
                    # The response is like: {"d":"\"Upload.ashx?q=...&EncType=I,Bill...pdf\""}
                    if "d" in response_json:
                        pdf_path = response_json["d"]
                        # Remove outer quotes if present
                        if isinstance(pdf_path, str):
                            if pdf_path.startswith('"') and pdf_path.endswith('"'):
                                pdf_path = pdf_path[1:-1]
                            # Remove escape sequences
                            pdf_path = pdf_path.replace("\\u0026", "&")
                            pdf_path = pdf_path.replace("\\", "")
                        # Build full URL
                        if pdf_path.startswith("Upload.ashx"):
                            bill.pdf_url = f"{self.config.base_url}/portal/{pdf_path}"
                        elif pdf_path.startswith("/"):
                            bill.pdf_url = f"{self.config.base_url}{pdf_path}"
                        elif pdf_path.startswith("http"):
                            bill.pdf_url = pdf_path
                        else:
                            bill.pdf_url = f"{self.config.base_url}/portal/{pdf_path}"
                        
                        logger.debug(f"[{self.config.supplier_name} Scraper] Extracted PDF URL from JSON: {bill.pdf_url}")
                        
                        # Now download the actual PDF
                        await self._download_pdf_from_url(bill)
                except json.JSONDecodeError:
                    # Maybe it's already a PDF?
                    content_type = response.headers.get("content-type", "")
                    if "pdf" in content_type.lower():
                        bill.pdf_content = await response.body()
                        bill.pdf_url = response.url
                        logger.debug(f"[{self.config.supplier_name} Scraper] Downloaded PDF directly: {len(bill.pdf_content)} bytes")
                        if self.save_html_dumps and bill.pdf_content:
                            await self._save_pdf_dump(bill)
                    else:
                        raise Exception(f"Unexpected response format: {response_text[:200]}")
        except Exception as e:
            logger.warning(f"[{self.config.supplier_name} Scraper] Failed to download PDF via JavaScript: {e}", exc_info=True)
            # Try alternative: look for PDF in modal or iframe
            try:
                # Wait for modal to appear
                await self.page.wait_for_selector("#pdfpopupmodal", timeout=5000)
                # Look for PDF embed or iframe
                pdf_iframe = await self.page.query_selector("#pdfpopupmodal embed, #pdfpopupmodal iframe")
                if pdf_iframe:
                    pdf_src = await pdf_iframe.get_attribute("src")
                    if pdf_src:
                        bill.pdf_url = pdf_src
                        await self._download_pdf_from_url(bill)
            except Exception as e2:
                logger.debug(f"[{self.config.supplier_name} Scraper] Alternative PDF download also failed: {e2}")
    
    async def _download_pdf_from_url(self, bill: ScrapedBill):
        """Download PDF from a direct URL"""
        try:
            pdf_response = await self.page.request.get(bill.pdf_url)
            if pdf_response.status == 200:
                bill.pdf_content = await pdf_response.body()
                logger.debug(f"[{self.config.supplier_name} Scraper] Downloaded PDF: {len(bill.pdf_content)} bytes")
                
                # Save PDF temporarily for debugging
                if self.save_html_dumps and bill.pdf_content:
                    await self._save_pdf_dump(bill)
        except Exception as e:
            logger.warning(f"[{self.config.supplier_name} Scraper] Failed to download PDF from {bill.pdf_url}: {e}")
    
    async def _save_pdf_dump(self, bill: ScrapedBill):
        """Save PDF to file for debugging"""
        try:
            dump_dir = Path(__file__).parent.parent / "scraper_dumps"
            dump_dir.mkdir(exist_ok=True)
            self.dump_counter += 1
            filename = f"{self.config.supplier_name.lower()}_{self.dump_counter:02d}_bill_{bill.bill_number or 'unknown'}.pdf"
            dump_file = dump_dir / filename
            with open(dump_file, 'wb') as f:
                f.write(bill.pdf_content)
            abs_path = dump_file.resolve()
            print(f"[SAVED] PDF dump: {abs_path}", flush=True)
            logger.info(f"[{self.config.supplier_name} Scraper] Saved PDF dump: {abs_path}")
        except Exception as e:
            logger.warning(f"[{self.config.supplier_name} Scraper] Failed to save PDF dump: {e}")
    
    def _parse_amount(self, text: str) -> Optional[float]:
        """Parse amount from text. Assumes amount is in bani (smallest unit), strips all commas/dots, then divides by 100 to get lei."""
        # Remove currency symbols and whitespace, keeping only digits, commas, and dots
        text = re.sub(r'[^\d.,]', '', text)
        # Strip all commas and dots - assume value is in bani
        cleaned = text.replace(',', '').replace('.', '')
        try:
            # Convert to int (bani) then divide by 100 to get lei
            amount_bani = int(cleaned)
            return amount_bani / 100.0
        except ValueError:
            return None
    
    def _parse_date(self, text: str) -> Optional[datetime]:
        """Parse date from text"""
        # Common date formats
        date_formats = [
            "%d/%m/%Y",
            "%d.%m.%Y",
            "%Y-%m-%d",
            "%d %B %Y",
            "%d %b %Y",
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(text.strip(), fmt)
            except:
                continue
        
        return None
    
    async def close(self):
        """Close the browser and cleanup"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


def load_scraper_config(supplier_name: str) -> Optional[ScraperConfig]:
    """Load scraper configuration from JSON file"""
    config_dir = Path(__file__).parent.parent / "scraper_configs"
    config_file = config_dir / f"{supplier_name.lower()}.json"
    
    if not config_file.exists():
        logger.debug(f"Scraper config not found: {config_file}")
        return None
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return ScraperConfig(**data)
    except Exception as e:
        logger.error(f"Error loading scraper config: {e}")
        return None

