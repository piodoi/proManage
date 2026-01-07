"""
General-purpose web scraper for supplier websites.
Data-driven configuration allows easy addition of new suppliers.
Uses httpx and BeautifulSoup for lightweight scraping without browser automation.
"""

import httpx
from bs4 import BeautifulSoup
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
import re
from pathlib import Path
import json

from app.utils.parsers import parse_amount as parse_amount_utility

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
    timeout: float = 45.0  # Increased timeout for slow supplier websites
    multiple_contracts_possible: bool = False  # If True, user may have multiple contracts/addresses
    
    # Cookie configuration (for sites that use cookies to switch between associations/apartments)
    cookie_config: Optional[Dict[str, Any]] = None  # e.g., {"asoc-cur": "{association_id}", "home-ap-cur": "{association_id}_{apartment_id}"}


class WebScraper:
    """General-purpose web scraper for supplier websites using httpx + BeautifulSoup"""
    
    def __init__(self, config: ScraperConfig, save_html_dumps: bool = False):
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None
        self.logged_in = False
        self.save_html_dumps = save_html_dumps
        self.dump_counter = 0
        self.last_response_url = None  # Track the final URL after redirects
        self.current_url = None  # Track current page URL
        self.login_response_html = None  # Store login response HTML for property discovery
    
    async def _init_client(self):
        """Initialize httpx client"""
        if not self.client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Add custom headers from config
            if self.config.custom_headers:
                headers.update(self.config.custom_headers)
            
            # Use granular timeout: longer read timeout for slow responses
            timeout_config = httpx.Timeout(
                connect=15.0,  # Time to establish connection
                read=self.config.timeout,  # Time to read response
                write=10.0,  # Time to write request
                pool=5.0  # Time to get connection from pool
            )
            
            self.client = httpx.AsyncClient(
                follow_redirects=True, 
                timeout=timeout_config,
                headers=headers
            )
    
    async def _set_cookies_from_config(self, association_id: Optional[str] = None, apartment_id: Optional[str] = None):
        """Set cookies from config, replacing placeholders with actual values.
        Only sets cookies when association_id is provided (required for cookie placeholders)."""
        if not self.config.cookie_config or not self.client:
            return
        
        # Only set cookies if we have association_id (required for placeholders)
        if not association_id:
            return
        
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(self.config.base_url)
            domain = parsed_url.netloc.replace("www.", "")  # Remove www. for cookie domain
            
            for cookie_name, cookie_template in self.config.cookie_config.items():
                cookie_value = cookie_template
                # Replace placeholders
                if association_id:
                    cookie_value = cookie_value.replace("{association_id}", association_id)
                if apartment_id:
                    cookie_value = cookie_value.replace("{apartment_id}", apartment_id)
                if association_id and apartment_id:
                    cookie_value = cookie_value.replace("{association_id}_{apartment_id}", f"{association_id}_{apartment_id}")
                
                # Set cookie on the httpx client
                self.client.cookies.set(cookie_name, cookie_value, domain=domain)
                logger.info(f"[{self.config.supplier_name} Scraper] Set cookie: {cookie_name}={cookie_value}")
        except Exception as e:
            logger.warning(f"[{self.config.supplier_name} Scraper] Failed to set cookies: {e}")
    
    def set_association_cookies(self, association_id: str, apartment_id: Optional[str] = None):
        """Set cookies for association/apartment selection (for e-bloc style sites) - synchronous wrapper"""
        if not self.client:
            logger.warning(f"[{self.config.supplier_name} Scraper] Cannot set cookies - client not initialized")
            return
        
        # Call async method (will be called from async context)
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create task if loop is running
                asyncio.create_task(self._set_cookies_from_config(association_id, apartment_id))
            else:
                # Run directly if no loop
                loop.run_until_complete(self._set_cookies_from_config(association_id, apartment_id))
        except Exception as e:
            logger.warning(f"[{self.config.supplier_name} Scraper] Error scheduling cookie set: {e}")
    
    async def login(self, username: str, password: str) -> bool:
        """Login to the supplier website"""
        try:
            logger.info(f"[{self.config.supplier_name} Scraper] Starting login...")
            
            await self._init_client()
            logger.info(f"[{self.config.supplier_name} Scraper] HTTP client initialized, proceeding with login...")
            
            if self.config.login_method == "form":
                login_result = await self._login_form(username, password)
                return login_result
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
        """Login using form submission with httpx"""
        try:
            # Get login page
            logger.info(f"[{self.config.supplier_name} Scraper] Getting login page...")
            login_page = await self.client.get(self.config.login_url)
            self.current_url = str(login_page.url)
            logger.info(f"[{self.config.supplier_name} Scraper] Login page status: {login_page.status_code}, URL: {login_page.url}")
            
            # Save HTML dump of login page
            self._save_html_dump(login_page.text, "login")
            
            # Parse form to extract fields
            soup = BeautifulSoup(login_page.text, "html.parser")
            form = soup.find("form")
            form_data = {}
            
            if form:
                logger.info(f"[{self.config.supplier_name} Scraper] Found form with action: {form.get('action', 'N/A')}")
                # Extract all form fields (including hidden fields, CSRF tokens, etc.)
                for inp in form.find_all("input"):
                    name = inp.get("name")
                    if name:
                        form_data[name] = inp.get("value", "")
                        logger.debug(f"[{self.config.supplier_name} Scraper] Form input: {name} = {inp.get('value', '')[:20]}")
            
            # Set username and password fields
            username_field = self.config.username_field or "txtLogin"
            password_field = self.config.password_field or "txtpwd"
            
            form_data[username_field] = username
            form_data[password_field] = password
            
            # Try common field name variations
            if "user" in form_data:
                form_data["user"] = username
            if "pass" in form_data:
                form_data["pass"] = password
            if "email" in form_data:
                form_data["email"] = username
            if "password" in form_data:
                form_data["password"] = password
            
            logger.info(f"[{self.config.supplier_name} Scraper] Submitting login form with data keys: {list(form_data.keys())}")
            
            # Submit the form
            response = await self.client.post(self.config.login_url, data=form_data)
            self.current_url = str(response.url)
            self.last_response_url = str(response.url)
            logger.info(f"[{self.config.supplier_name} Scraper] Login response status: {response.status_code}, final URL: {response.url}")
            
            # Save HTML dump after login
            self._save_html_dump(response.text, "after_login")
            
            # Check if login was successful
            login_success = False
            success_reason = ""
            page_html = response.text
            page_html_lower = page_html.lower()
            
            # Check if we were redirected to Dashboard.aspx
            if "dashboard.aspx" in self.current_url.lower() and "default.aspx" not in self.current_url.lower():
                login_success = True
                success_reason = f"redirected to {self.current_url}"
            
            # Check configured success indicator
            if not login_success and self.config.login_success_indicator:
                if self.config.login_success_indicator.startswith("selector:"):
                    selector = self.config.login_success_indicator.replace("selector:", "").strip()
                    # Use BeautifulSoup to check for selector
                    soup = BeautifulSoup(page_html, "html.parser")
                    element = soup.select_one(selector)
                    if element:
                        login_success = True
                        success_reason = f"found selector: {selector}"
                elif self.config.login_success_indicator.startswith("url:"):
                    url_pattern = self.config.login_success_indicator.replace("url:", "").strip()
                    if url_pattern in self.current_url:
                        login_success = True
                        success_reason = f"URL contains: {url_pattern}"
                elif self.config.login_success_indicator.lower() in page_html_lower:
                    login_success = True
                    success_reason = "found text indicator"
            
            # Look for logout link or similar indicators
            if not login_success:
                has_logout = "logout" in page_html_lower or "deconectare" in page_html_lower or "iesire" in page_html_lower or "sign out" in page_html_lower
                still_has_login = username_field.lower() in page_html_lower and password_field.lower() in page_html_lower
                
                if has_logout and not still_has_login:
                    login_success = True
                    success_reason = "found logout link"
            
            # Final check: if we're on Dashboard (not default), it's success
            if not login_success:
                if "dashboard" in self.current_url.lower() and "default.aspx" not in self.current_url.lower():
                    login_success = True
                    success_reason = "on Dashboard page"
            
            if login_success:
                self.logged_in = True
                self.login_response_html = page_html  # Store for property discovery
                logger.info(f"[{self.config.supplier_name} Scraper] Login successful ({success_reason})")
                return True
            
            logger.warning(f"[{self.config.supplier_name} Scraper] Login may have failed - URL: {self.current_url}")
            logger.info(f"[{self.config.supplier_name} Scraper] Check HTML dump file to see what the page contains after login")
            return False
        
        except Exception as e:
            logger.error(f"[{self.config.supplier_name} Scraper] Login error: {e}", exc_info=True)
            return False
    
    async def _login_api(self, username: str, password: str) -> bool:
        """Login using API endpoint (for future use)"""
        # This would be for API-based authentication
        # For now, we'll use form-based login
        raise NotImplementedError("API-based login not yet implemented")
    
    async def get_bills(
        self, 
        association_id: Optional[str] = None, 
        apartment_id: Optional[str] = None,
        association_ids: Optional[List[Tuple[str, Optional[str]]]] = None
    ) -> List[ScrapedBill]:
        """Scrape bills from the supplier website
        
        Args:
            association_id: Optional association ID for cookie-based selection (e-bloc style)
            apartment_id: Optional apartment ID for cookie-based selection (e-bloc style)
            association_ids: Optional list of (association_id, apartment_id) tuples for multiple associations (e-bloc style)
                            If provided, bills will be fetched for each association/apartment combination
        """
        if not self.logged_in:
            raise Exception("Not logged in. Call login() first.")
        
        if not self.client:
            await self._init_client()
        
        bills = []
        
        # Handle multiple associations (e-bloc style)
        if association_ids and self.config.cookie_config:
            # Fetch bills for each association/apartment combination
            for idx, (assoc_id, apt_id) in enumerate(association_ids, 1):
                # Set cookies for this association/apartment
                await self._set_cookies_from_config(assoc_id, apt_id)
                
                # Navigate to base URL to ensure cookies are set
                await self.client.get(self.config.base_url)
                
                # Get bills for this association
                assoc_bills = await self._fetch_bills_page()
                
                # Set contract_id (association_id) on each bill for proper distribution
                for bill in assoc_bills:
                    if not bill.contract_id:
                        bill.contract_id = assoc_id
                bills.extend(assoc_bills)
                
                # Summary log per association cycle
                logger.info(f"[{self.config.supplier_name} Scraper] Association {idx}/{len(association_ids)} ({assoc_id}): Found {len(assoc_bills)} bill(s)")
            
            return bills
        
        # Single association (existing behavior)
        if association_id and self.config.cookie_config:
            await self._set_cookies_from_config(association_id, apartment_id)
            # Navigate to base URL to ensure cookies are set
            await self.client.get(self.config.base_url)
        
        bills = await self._fetch_bills_page()
        return bills
    
    async def _fetch_bills_page(self) -> List[ScrapedBill]:
        """Internal method to fetch bills from the bills page (after cookies are set)"""
        bills = []
        
        try:
            # Navigate to bills page
            bills_url = self.config.bills_url or self.config.bills_page_url
            if not bills_url:
                logger.warning(f"[{self.config.supplier_name} Scraper] No bills URL configured")
                return bills
            
            logger.info(f"[{self.config.supplier_name} Scraper] Fetching bills page: {bills_url}")
            response = await self.client.get(bills_url)
            self.current_url = str(response.url)
            logger.info(f"[{self.config.supplier_name} Scraper] Bills page received, status: {response.status_code}")
            
            if response.status_code != 200:
                logger.warning(f"[{self.config.supplier_name} Scraper] Bills page returned non-200 status: {response.status_code}")
                return bills
            
            page_html = response.text
            self._save_html_dump(page_html, "bills_page")
            
            logger.info(f"[{self.config.supplier_name} Scraper] Starting bill extraction...")
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
                # Extract bill from item
                bill = await self._extract_bill_from_item(item, self.current_url, soup)
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
            
            # Extract PDF link
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
                        # Store the params for later use
                        bill.pdf_url = f"javascript:BillClick('{bill_params}')"
                        # Try to download PDF by reconstructing the URL
                        # This might not work for all sites - some require JavaScript execution
                        logger.debug(f"[{self.config.supplier_name} Scraper] Found JavaScript PDF link: {bill_params}")
                        # Note: Without browser automation, we can't execute JavaScript
                        # The PDF URL will need to be constructed based on the site's pattern
                        # Or the bill will be marked as having a PDF but we can't download it here
                else:
                    # Regular href link
                    href = pdf_link_elem.get("href", "")
                    if href and href != "javascript:" and href != "#":
                        if href.startswith("http"):
                            bill.pdf_url = href
                        elif href.startswith("/"):
                            bill.pdf_url = f"{self.config.base_url}{href}"
                        else:
                            bill.pdf_url = f"{self.config.base_url}/{href}"
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
    
    async def _download_pdf_from_url(self, bill: ScrapedBill):
        """Download PDF from a direct URL using httpx"""
        try:
            if not bill.pdf_url or bill.pdf_url.startswith("javascript:"):
                logger.debug(f"[{self.config.supplier_name} Scraper] Cannot download PDF - URL is JavaScript or missing")
                return
            
            pdf_response = await self.client.get(bill.pdf_url)
            if pdf_response.status_code == 200:
                bill.pdf_content = pdf_response.content
                logger.debug(f"[{self.config.supplier_name} Scraper] Downloaded PDF: {len(bill.pdf_content)} bytes")
                
                # Save PDF temporarily for debugging
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
            # Sanitize bill number for filename
            bill_num = bill.bill_number or 'unknown'
            # Remove special characters
            bill_num = re.sub(r'[^\w\s-]', '', bill_num).strip()
            bill_num = re.sub(r'[-\s]+', '-', bill_num)
            filename = f"{self.config.supplier_name.lower()}_{self.dump_counter:02d}_bill_{bill_num}.pdf"
            dump_file = dump_dir / filename
            with open(dump_file, 'wb') as f:
                f.write(bill.pdf_content)
            abs_path = dump_file.resolve()
            print(f"[SAVED] PDF dump: {abs_path}", flush=True)
            logger.info(f"[{self.config.supplier_name} Scraper] Saved PDF dump: {abs_path}")
        except Exception as e:
            logger.warning(f"[{self.config.supplier_name} Scraper] Failed to save PDF dump: {e}")
    
    def _parse_amount(self, text: str) -> Optional[float]:
        """Parse amount from text using standard utility."""
        return parse_amount_utility(text)
    
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
        """Close the HTTP client and cleanup"""
        if self.client:
            await self.client.aclose()
            self.client = None


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

