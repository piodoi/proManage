"""
General-purpose web scraper for supplier websites.
Data-driven configuration allows easy addition of new suppliers.
"""

import httpx
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
    
    # Navigation configuration
    bills_page_url: Optional[str] = None
    bills_list_selector: Optional[str] = None  # CSS selector for bills list container
    
    # Bill extraction configuration
    bill_item_selector: Optional[str] = None  # CSS selector for individual bill items
    bill_number_selector: Optional[str] = None
    bill_amount_selector: Optional[str] = None
    bill_due_date_selector: Optional[str] = None
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


class WebScraper:
    """General-purpose web scraper for supplier websites"""
    
    def __init__(self, config: ScraperConfig, save_html_dumps: bool = False):
        self.config = config
        self.client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=config.timeout,
            headers=config.custom_headers or {}
        )
        self.logged_in = False
        self.session_cookies: Dict[str, str] = {}
        self.save_html_dumps = save_html_dumps
        self.dump_counter = 0
    
    async def login(self, username: str, password: str) -> bool:
        """Login to the supplier website"""
        try:
            logger.info(f"[{self.config.supplier_name} Scraper] Starting login...")
            
            if self.config.login_method == "form":
                return await self._login_form(username, password)
            elif self.config.login_method == "api":
                return await self._login_api(username, password)
            else:
                raise ValueError(f"Unknown login method: {self.config.login_method}")
        
        except Exception as e:
            logger.error(f"[{self.config.supplier_name} Scraper] Login failed: {e}")
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
        """Login using form submission"""
        # Get login page
        login_page = await self.client.get(self.config.login_url)
        if login_page.status_code != 200:
            logger.error(f"[{self.config.supplier_name} Scraper] Failed to load login page: {login_page.status_code}")
            return False
        
        self._save_html_dump(login_page.text, "login")
        
        soup = BeautifulSoup(login_page.text, "html.parser")
        
        # Find login form
        form = None
        if self.config.login_form_selector:
            form = soup.select_one(self.config.login_form_selector)
        else:
            form = soup.find("form")
        
        if not form:
            logger.error(f"[{self.config.supplier_name} Scraper] Login form not found")
            return False
        
        # Build form data and auto-detect username/password fields
        form_data = {}
        username_field = None
        password_field = None
        submit_button_name = None
        submit_button_value = None
        
        for inp in form.find_all("input"):
            name = inp.get("name", "")
            inp_name_lower = name.lower()
            inp_type = inp.get("type", "").lower()
            if name:
                form_data[name] = inp.get("value", "")
                
                # Auto-detect username and password fields
                if not username_field:
                    if (self.config.username_field and name == self.config.username_field) or \
                       (not self.config.username_field and (inp_type == "text" or inp_type == "email" or "user" in inp_name_lower or "email" in inp_name_lower or "login" in inp_name_lower)):
                        username_field = name
                if not password_field:
                    if (self.config.password_field and name == self.config.password_field) or \
                       (not self.config.password_field and (inp_type == "password" or "pass" in inp_name_lower or "pwd" in inp_name_lower)):
                        password_field = name
                
                # Auto-detect submit button (ASP.NET forms often need this)
                if inp_type == "submit" and not submit_button_name:
                    submit_button_name = name
                    submit_button_value = inp.get("value", "")
        
        # Use configured fields or auto-detected ones, fallback to defaults
        if not username_field:
            username_field = self.config.username_field or "username"
        if not password_field:
            password_field = self.config.password_field or "password"
        
        # Set username and password
        form_data[username_field] = username
        form_data[password_field] = password
        
        # Include submit button if found (important for ASP.NET forms)
        # Always override the button value even if it's already in form_data (might have wrong value)
        if submit_button_name:
            form_data[submit_button_name] = submit_button_value
            logger.debug(f"[{self.config.supplier_name} Scraper] Including submit button in form data: {submit_button_name}={submit_button_value}")
        
        logger.debug(f"[{self.config.supplier_name} Scraper] Submitting form with {len(form_data)} fields")
        
        # Submit form
        form_action = form.get("action", "")
        if form_action.startswith("/"):
            form_url = f"{self.config.base_url}{form_action}"
        elif form_action.startswith("http"):
            form_url = form_action
        else:
            form_url = self.config.login_url
        
        response = await self.client.post(form_url, data=form_data)
        
        self._save_html_dump(response.text, "after_login")
        
        # Check if login was successful - try multiple indicators
        login_success = False
        success_reason = ""
        
        # First, check if we were redirected to a different URL (common for ASP.NET)
        if response.status_code == 200:
            response_url_str = str(response.url)
            login_url_str = str(self.config.login_url)
            if response_url_str != login_url_str and "default.aspx" not in response_url_str.lower():
                login_success = True
                success_reason = f"redirected to {response.url}"
        
        # Also check configured success indicator
        if not login_success and self.config.login_success_indicator:
            if self.config.login_success_indicator.startswith("selector:"):
                selector = self.config.login_success_indicator.replace("selector:", "").strip()
                soup = BeautifulSoup(response.text, "html.parser")
                found_element = soup.select_one(selector)
                if found_element:
                    login_success = True
                    success_reason = f"found selector: {selector}"
            elif self.config.login_success_indicator in response.text:
                login_success = True
                success_reason = "found text indicator"
        
        if login_success:
            self.logged_in = True
            logger.info(f"[{self.config.supplier_name} Scraper] Login successful ({success_reason})")
            return True
        
        logger.warning(f"[{self.config.supplier_name} Scraper] Login may have failed - status: {response.status_code}, URL: {response.url}")
        logger.info(f"[{self.config.supplier_name} Scraper] Check HTML dump file to see what the page contains after login")
        return False
    
    async def _login_api(self, username: str, password: str) -> bool:
        """Login using API endpoint (for future use)"""
        # This would be for API-based authentication
        # For now, we'll use form-based login
        raise NotImplementedError("API-based login not yet implemented")
    
    async def get_bills(self) -> List[ScrapedBill]:
        """Scrape bills from the supplier website"""
        if not self.logged_in:
            raise Exception("Not logged in. Call login() first.")
        
        bills = []
        
        try:
            # Navigate to bills page
            bills_url = self.config.bills_url or self.config.bills_page_url
            if not bills_url:
                logger.warning(f"[{self.config.supplier_name} Scraper] No bills URL configured")
                return bills
            
            logger.info(f"[{self.config.supplier_name} Scraper] Fetching bills page...")
            response = await self.client.get(bills_url)
            
            if response.status_code != 200:
                logger.error(f"[{self.config.supplier_name} Scraper] Failed to load bills page: {response.status_code}")
                return bills
            
            self._save_html_dump(response.text, "bills_page")
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find bills list
            bills_container = None
            if self.config.bills_list_selector:
                bills_container = soup.select_one(self.config.bills_list_selector)
            else:
                # Try to find common bill list containers
                for selector in ["table", ".bills", "#bills", ".invoices", "#invoices"]:
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
                # Default: try table rows or list items
                bill_items = bills_container.find_all(["tr", "li", "div"], class_=re.compile(r"bill|invoice", re.I))
            
            logger.info(f"[{self.config.supplier_name} Scraper] Found {len(bill_items)} bill items")
            
            for item in bill_items:
                bill = await self._extract_bill_from_item(item, str(response.url))
                if bill:
                    bills.append(bill)
            
        except Exception as e:
            logger.error(f"[{self.config.supplier_name} Scraper] Error scraping bills: {e}", exc_info=True)
        
        return bills
    
    async def _extract_bill_from_item(self, item, base_url: str = None) -> Optional[ScrapedBill]:
        """Extract bill data from a single HTML item"""
        try:
            bill = ScrapedBill()
            
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
            
            # Extract amount
            if self.config.bill_amount_selector:
                elem = item.select_one(self.config.bill_amount_selector)
                if elem:
                    amount_text = elem.get_text(strip=True)
                    bill.amount = self._parse_amount(amount_text)
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
            if self.config.bill_pdf_link_selector:
                link_elem = item.select_one(self.config.bill_pdf_link_selector)
                if link_elem:
                    href = link_elem.get("href", "")
                    if href:
                        if href.startswith("http"):
                            bill.pdf_url = href
                        else:
                            bill.pdf_url = f"{self.config.base_url}{href}"
            
            # Try to find any PDF link in the item
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
            
            # Download PDF if URL found
            if bill.pdf_url:
                try:
                    pdf_response = await self.client.get(bill.pdf_url)
                    if pdf_response.status_code == 200:
                        bill.pdf_content = pdf_response.content
                        logger.debug(f"[{self.config.supplier_name} Scraper] Downloaded PDF: {len(bill.pdf_content)} bytes")
                except Exception as e:
                    logger.warning(f"[{self.config.supplier_name} Scraper] Failed to download PDF from {bill.pdf_url}: {e}")
            
            return bill if bill.bill_number or bill.amount else None
        
        except Exception as e:
            logger.warning(f"[{self.config.supplier_name} Scraper] Error extracting bill: {e}")
            return None
    
    def _parse_amount(self, text: str) -> Optional[float]:
        """Parse amount from text"""
        # Remove currency symbols and whitespace
        text = re.sub(r'[^\d.,]', '', text)
        # Replace comma with dot if comma is decimal separator
        if ',' in text and '.' in text:
            # Assume comma is thousands separator
            text = text.replace(',', '')
        elif ',' in text:
            text = text.replace(',', '.')
        try:
            return float(text)
        except:
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
        """Close the HTTP client"""
        await self.client.aclose()


def load_scraper_config(supplier_name: str) -> Optional[ScraperConfig]:
    """Load scraper configuration from JSON file"""
    config_dir = Path(__file__).parent.parent / "scraper_configs"
    config_file = config_dir / f"{supplier_name.lower()}.json"
    
    if not config_file.exists():
        logger.warning(f"Scraper config not found: {config_file}")
        return None
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return ScraperConfig(**data)
    except Exception as e:
        logger.error(f"Error loading scraper config: {e}")
        return None

