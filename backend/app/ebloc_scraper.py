import httpx
from bs4 import BeautifulSoup
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime
import re
import logging

# Configure logging for this module
logging.basicConfig(level=logging.INFO)


@dataclass
class EblocBill:
    month: str
    amount: float
    due_date: Optional[datetime]
    details_url: Optional[str]
    iban: Optional[str] = None
    bill_number: Optional[str] = None


@dataclass
class EblocProperty:
    page_id: str
    name: str
    url: str
    address: Optional[str] = None


@dataclass
class EblocBalance:
    outstanding_debt: float
    last_payment_date: Optional[datetime]
    oldest_debt_month: Optional[str]
    debt_level: Optional[str]


@dataclass
class EblocPayment:
    receipt_number: str
    payment_date: datetime
    amount: float


class EblocScraper:
    BASE_URL = "https://www.e-bloc.ro"
    LOGIN_URL = f"{BASE_URL}/index.php"

    def __init__(self, debug: bool = False):
        # Use follow_redirects=True so we can access the final page after redirect
        self.client = httpx.AsyncClient(follow_redirects=True, timeout=30.0)
        self.logged_in = False
        self.available_properties: list[EblocProperty] = []
        self.debug = debug
        self.last_response_url = None  # Track the final URL after redirects

    async def login(self, username: str, password: str) -> bool:
        import logging
        logger = logging.getLogger(__name__)
        try:
            logger.info("[E-Bloc Scraper] Getting login page...")
            login_page = await self.client.get(self.LOGIN_URL)
            logger.info(f"[E-Bloc Scraper] Login page status: {login_page.status_code}, URL: {login_page.url}")
            
            soup = BeautifulSoup(login_page.text, "html.parser")
            form = soup.find("form")
            form_data = {}
            if form:
                logger.info(f"[E-Bloc Scraper] Found form with action: {form.get('action', 'N/A')}")
                for inp in form.find_all("input"):
                    name = inp.get("name")
                    if name:
                        form_data[name] = inp.get("value", "")
                        logger.debug(f"[E-Bloc Scraper] Form input: {name} = {inp.get('value', '')[:20]}")
            
            # Use the actual form field names from the HTML
            form_data["pUser"] = username
            form_data["pPass"] = password
            # Also try common variations
            if "user" in form_data:
                form_data["user"] = username
            if "pass" in form_data:
                form_data["pass"] = password
            if "email" in form_data:
                form_data["email"] = username
            if "password" in form_data:
                form_data["password"] = password
            
            logger.info(f"[E-Bloc Scraper] Submitting login form with data: {list(form_data.keys())}")
            # POST with redirects enabled - e-bloc redirects to property page on success
            response = await self.client.post(self.LOGIN_URL, data=form_data)
            self.last_response_url = str(response.url)
            logger.info(f"[E-Bloc Scraper] Login response status: {response.status_code}, final URL: {response.url}")
            
            # Check if login was successful - look for indicators in the response
            response_text_lower = response.text.lower()
            has_logout = "logout" in response_text_lower or "deconectare" in response_text_lower or "iesire" in response_text_lower
            still_has_login_form = "puser" in response_text_lower and "ppass" in response_text_lower
            has_property_page = "page=" in str(response.url)  # Redirected to a property page (e.g., ?page=19)
            
            # Login is successful if:
            # 1. We got redirected to a property page (page= in URL) - this is the main indicator for e-bloc
            # 2. OR we have logout link and no login form
            self.logged_in = (response.status_code == 200 and has_property_page) or (has_logout and not still_has_login_form)
            logger.info(f"[E-Bloc Scraper] Login check: status={response.status_code}, has_logout={has_logout}, still_has_login={still_has_login_form}, has_property_page={has_property_page}, logged_in={self.logged_in}")
            
            # Extract page ID from URL if redirected to a property
            if has_property_page:
                page_match = re.search(r'page=(\d+)', str(response.url))
                if page_match:
                    default_page_id = page_match.group(1)
                    logger.info(f"[E-Bloc Scraper] Detected default property page_id: {default_page_id}")
            if self.logged_in:
                logger.info("[E-Bloc Scraper] Login successful, parsing properties...")
                
                # Save HTML for debugging if enabled
                if self.debug:
                    try:
                        import os
                        from pathlib import Path
                        debug_dir = Path("debug_html")
                        debug_dir.mkdir(exist_ok=True)
                        html_file = debug_dir / "login_response.html"
                        html_file.write_text(response.text, encoding="utf-8")
                        logger.info(f"[E-Bloc Scraper] Saved login response HTML to {html_file.absolute()}")
                        logger.info(f"[E-Bloc Scraper] HTML file size: {len(response.text)} bytes")
                    except Exception as e:
                        logger.error(f"[E-Bloc Scraper] Could not save debug HTML: {e}", exc_info=True)
                
                # Log HTML structure for debugging
                html_preview = response.text[:3000] if len(response.text) > 3000 else response.text
                logger.info(f"[E-Bloc Scraper] Response HTML preview (first 3000 chars):\n{html_preview}")
                
                # Check for common indicators of successful login
                if "logout" in response.text.lower() or "deconectare" in response.text.lower():
                    logger.info("[E-Bloc Scraper] Login confirmed - found logout link")
                
                # Count select elements in HTML
                select_count = response.text.lower().count("<select")
                logger.info(f"[E-Bloc Scraper] Found {select_count} '<select' tags in HTML")
                
                # Look for select elements in the raw HTML to see their structure
                import re as regex_module
                select_pattern = regex_module.compile(r'<select[^>]*>.*?</select>', regex_module.DOTALL | regex_module.IGNORECASE)
                select_matches = select_pattern.findall(response.text)
                logger.info(f"[E-Bloc Scraper] Found {len(select_matches)} select blocks in HTML")
                for i, match in enumerate(select_matches[:5]):  # Log first 5
                    match_preview = match[:500] if len(match) > 500 else match
                    logger.info(f"[E-Bloc Scraper] Select block #{i+1} preview:\n{match_preview}")
                
                # Parse properties from the current page
                await self._parse_property_selector(response.text)
                logger.info(f"[E-Bloc Scraper] Found {len(self.available_properties)} properties after parsing login response")
                
                # If no properties found, try navigating to the main index page (without page parameter)
                if len(self.available_properties) == 0:
                    logger.warning("[E-Bloc Scraper] No properties found in login response, trying main index page...")
                    main_page = await self.client.get(self.LOGIN_URL)
                    if self.debug:
                        try:
                            from pathlib import Path
                            debug_dir = Path("debug_html")
                            debug_dir.mkdir(exist_ok=True)
                            html_file = debug_dir / "main_page.html"
                            html_file.write_text(main_page.text, encoding="utf-8")
                            logger.info(f"[E-Bloc Scraper] Saved main page HTML to {html_file.absolute()}")
                        except Exception as e:
                            logger.error(f"[E-Bloc Scraper] Could not save debug HTML: {e}", exc_info=True)
                    await self._parse_property_selector(main_page.text)
                    logger.info(f"[E-Bloc Scraper] Found {len(self.available_properties)} properties after checking main page")
            else:
                logger.warning(f"[E-Bloc Scraper] Login failed - status: {response.status_code}")
            
            return self.logged_in
        except Exception as e:
            logger.error(f"[E-Bloc Scraper] Login error: {str(e)}", exc_info=True)
            return False

    async def _parse_property_selector(self, html: str) -> None:
        import logging
        logger = logging.getLogger(__name__)
        
        initial_count = len(self.available_properties)
        
        # First, try to parse JavaScript variables (gInfoAp array)
        logger.info("[E-Bloc Scraper] Parsing JavaScript variables (gInfoAp array)...")
        properties_from_js = await self._parse_javascript_properties(html)
        if properties_from_js:
            logger.info(f"[E-Bloc Scraper] Found {len(properties_from_js)} properties from JavaScript variables")
            for prop in properties_from_js:
                if not any(p.page_id == prop.page_id for p in self.available_properties):
                    self.available_properties.append(prop)
                    logger.info(f"[E-Bloc Scraper] ✓ Added property from JS: '{prop.name}' (page_id: {prop.page_id}, address: {prop.address})")
        
        # Log results
        new_count = len(self.available_properties) - initial_count
        if new_count > 0:
            logger.info(f"[E-Bloc Scraper] Successfully parsed {new_count} properties from JavaScript")
            print(f"[E-Bloc Scraper] Found {new_count} properties:")
            for prop in self.available_properties[initial_count:]:
                print(f"  - {prop.name} (page_id: {prop.page_id}, address: {prop.address})")
                logger.info(f"  - {prop.name} (page_id: {prop.page_id}, address: {prop.address})")
        else:
            logger.warning("[E-Bloc Scraper] No properties found in JavaScript gInfoAp array")

    async def _parse_javascript_properties(self, html: str) -> list[EblocProperty]:
        """Parse properties from JavaScript gInfoAp array"""
        import logging
        logger = logging.getLogger(__name__)
        properties = []
        
        try:
            # Find the script tag containing gInfoAp
            # Look for the pattern: gInfoAp[ index ][ "bloc" ] = "address"
            # The data is in a long line like: gInfoAp[ 0 ] = new Array();gInfoAp[ 0 ][ "id_asoc" ] = "24477";...
            
            # Extract gPageId to understand the current page
            page_id_match = re.search(r'gPageId\s*=\s*["\']?(\d+)["\']?', html)
            current_page_id = page_id_match.group(1) if page_id_match else None
            logger.info(f"[E-Bloc Scraper] Found gPageId: {current_page_id}")
            
            # First, parse gInfoAsoc to get association information (including adr_bloc)
            gInfoAsoc_block_match = re.search(
                r'gInfoAsoc\s*\[\s*\d+\s*\]\s*=.*?(?=gInfoAp|gContAsoc|</script>|$)',
                html,
                re.DOTALL
            )
            associations = {}  # Map id_asoc -> association data
            if gInfoAsoc_block_match:
                gInfoAsoc_block = gInfoAsoc_block_match.group(0)
                logger.debug(f"[E-Bloc Scraper] Found gInfoAsoc block (first 500 chars): {gInfoAsoc_block[:500]}")
                
                # Find all association indices
                asoc_indices = set(re.findall(r'gInfoAsoc\s*\[\s*(\d+)\s*\]', gInfoAsoc_block))
                logger.info(f"[E-Bloc Scraper] Found association indices: {sorted(asoc_indices)}")
                
                for asoc_index in sorted(asoc_indices):
                    # Extract all assignments for this association
                    kv_pattern = re.compile(
                        r'gInfoAsoc\s*\[\s*' + re.escape(asoc_index) + r'\s*\]\s*\[\s*["\']([^"\']+)["\']\s*\]\s*=\s*["\']([^"\']*)["\']',
                        re.DOTALL
                    )
                    asoc_data = {}
                    for kv_match in kv_pattern.finditer(gInfoAsoc_block):
                        key = kv_match.group(1)
                        value = kv_match.group(2)
                        asoc_data[key] = value
                    
                    if "id" in asoc_data:
                        asoc_id = asoc_data["id"]
                        associations[asoc_id] = asoc_data
                        logger.debug(f"[E-Bloc Scraper]   Association {asoc_index}: id={asoc_id}, adr_bloc={asoc_data.get('adr_bloc', 'N/A')}")
            
            # Extract all gInfoAp entries - they're in format: gInfoAp[ index ] = new Array();gInfoAp[ index ][ "key" ] = "value";
            # We need to find all array indices and their properties
            gInfoAp_pattern = re.compile(
                r'gInfoAp\s*\[\s*(\d+)\s*\]\s*=\s*new\s+Array\(\);(.*?)(?=gInfoAp\s*\[\s*\d+|</script>|$)',
                re.DOTALL
            )
            
            # Alternative: find the entire gInfoAp block and parse it
            # The data is usually in one long line, so we'll extract the whole block
            gInfoAp_block_match = re.search(
                r'gInfoAp\s*\[\s*\d+\s*\]\s*=.*?(?=gContAsoc|</script>|$)',
                html,
                re.DOTALL
            )
            
            if gInfoAp_block_match:
                gInfoAp_block = gInfoAp_block_match.group(0)
                logger.debug(f"[E-Bloc Scraper] Found gInfoAp block (first 1000 chars): {gInfoAp_block[:1000]}")
                
                # The data is in format: gInfoAp[ 0 ] = new Array();gInfoAp[ 0 ][ "key" ] = "value";gInfoAp[ 1 ] = ...
                # We need to find all indices first
                indices = set(re.findall(r'gInfoAp\s*\[\s*(\d+)\s*\]', gInfoAp_block))
                logger.info(f"[E-Bloc Scraper] Found property indices: {sorted(indices)}")
                
                for index in sorted(indices):
                    # Extract all assignments for this index
                    # Pattern: gInfoAp[ index ][ "key" ] = "value"
                    kv_pattern = re.compile(
                        r'gInfoAp\s*\[\s*' + re.escape(index) + r'\s*\]\s*\[\s*["\']([^"\']+)["\']\s*\]\s*=\s*["\']([^"\']*)["\']',
                        re.DOTALL
                    )
                    property_data = {}
                    for kv_match in kv_pattern.finditer(gInfoAp_block):
                        key = kv_match.group(1)
                        value = kv_match.group(2)
                        property_data[key] = value
                        logger.debug(f"[E-Bloc Scraper]   Property {index}: {key} = {value}")
                    
                    # Extract the "bloc" field which is the address/name
                    if "bloc" in property_data:
                        address_base = property_data["bloc"]
                        # Get id_asoc and id_ap to construct page_id
                        id_asoc = property_data.get("id_asoc", "")
                        id_ap = property_data.get("id_ap", "")
                        
                        # The page_id is id_asoc
                        page_id = id_asoc if id_asoc else f"{index}"
                        
                        # Property name is just the address (no owner name in brackets)
                        name = address_base
                        
                        # Address: base address + "Bl:" + adr_bloc + "Sc:" + scara + "Ap:" + ap (if available)
                        address_parts = [address_base]
                        
                        # Get bloc information from association data
                        adr_bloc = ""
                        if id_asoc and id_asoc in associations:
                            adr_bloc = associations[id_asoc].get("adr_bloc", "").strip()
                        
                        scara = property_data.get("scara", "").strip()
                        ap = property_data.get("ap", "").strip()
                        
                        if adr_bloc:
                            address_parts.append(f"Bl: {adr_bloc}")
                        if scara:
                            address_parts.append(f"Sc: {scara}")
                        if ap:
                            address_parts.append(f"Ap: {ap}")
                        address = " ".join(address_parts)
                        
                        url = f"{self.LOGIN_URL}?page={page_id}&t={int(datetime.now().timestamp())}"
                        
                        prop = EblocProperty(
                            page_id=page_id,
                            name=name,
                            url=url,
                            address=address
                        )
                        properties.append(prop)
                        logger.info(f"[E-Bloc Scraper] Parsed property: index={index}, page_id={page_id}, name='{name}', address='{address}'")
            
            logger.info(f"[E-Bloc Scraper] Parsed {len(properties)} properties from JavaScript gInfoAp array")
            
        except Exception as e:
            logger.error(f"[E-Bloc Scraper] Error parsing JavaScript properties: {e}", exc_info=True)
        
        return properties
    
    async def get_available_properties(self) -> list[EblocProperty]:
        return self.available_properties

    async def select_property(self, page_id: str) -> bool:
        try:
            url = f"{self.LOGIN_URL}?page={page_id}&t={int(datetime.now().timestamp())}"
            response = await self.client.get(url)
            return response.status_code == 200
        except Exception:
            return False

    async def get_bills(self, page_id: Optional[str] = None) -> list[EblocBill]:
        if not self.logged_in:
            return []
        try:
            if page_id:
                url = f"{self.LOGIN_URL}?page={page_id}&t={int(datetime.now().timestamp())}"
            else:
                url = self.LOGIN_URL
            response = await self.client.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            bills = []
            bill_rows = soup.find_all("tr", class_="bill-row") or soup.find_all(
                "div", class_="bill-item"
            )
            for row in bill_rows:
                month_el = row.find(class_="month") or row.find("td", {"data-label": "Luna"})
                amount_el = row.find(class_="amount") or row.find("td", {"data-label": "Suma"})
                due_el = row.find(class_="due-date") or row.find("td", {"data-label": "Scadenta"})
                link_el = row.find("a", href=True)
                month = month_el.get_text(strip=True) if month_el else "Unknown"
                amount_text = amount_el.get_text(strip=True) if amount_el else "0"
                amount = float(
                    amount_text.replace("lei", "").replace("RON", "").replace(",", ".").strip()
                    or "0"
                )
                due_text = due_el.get_text(strip=True) if due_el else None
                due_date = None
                if due_text:
                    try:
                        due_date = datetime.strptime(due_text, "%d.%m.%Y")
                    except ValueError:
                        pass
                details_url = link_el.get("href") if link_el else None
                if details_url and not details_url.startswith("http"):
                    details_url = f"{self.BASE_URL}{details_url}"
                bills.append(
                    EblocBill(
                        month=month,
                        amount=amount,
                        due_date=due_date,
                        details_url=details_url,
                    )
                )
            return bills
        except Exception:
            return []

    async def get_bill_details(self, details_url: str) -> Optional[EblocBill]:
        if not self.logged_in or not details_url:
            return None
        try:
            response = await self.client.get(details_url)
            soup = BeautifulSoup(response.text, "html.parser")
            iban_el = soup.find(string=lambda t: t and "IBAN" in t if t else False)
            iban = None
            if iban_el:
                parent = iban_el.find_parent()
                if parent:
                    iban_text = parent.get_text()
                    import re

                    iban_match = re.search(r"[A-Z]{2}\d{2}[A-Z0-9]{4,30}", iban_text)
                    iban = iban_match.group(0) if iban_match else None
            bill_num_el = soup.find(string=lambda t: t and "Nr." in t if t else False)
            bill_number = None
            if bill_num_el:
                parent = bill_num_el.find_parent()
                if parent:
                    bill_number = parent.get_text(strip=True)
            return EblocBill(
                month="",
                amount=0,
                due_date=None,
                details_url=details_url,
                iban=iban,
                bill_number=bill_number,
            )
        except Exception:
            return None

    async def select_property_by_name(self, property_name: str) -> Optional[str]:
        """Select property from combo box by matching property name with gInfoAsoc['nume']"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.logged_in:
            return None
        
        try:
            # Get the current page to parse JavaScript variables
            response = await self.client.get(self.LOGIN_URL)
            html = response.text
            
            # Parse gInfoAsoc to find matching association
            gInfoAsoc_block_match = re.search(
                r'gInfoAsoc\s*\[\s*\d+\s*\]\s*=.*?(?=gInfoAp|gContAsoc|</script>|$)',
                html,
                re.DOTALL
            )
            
            if not gInfoAsoc_block_match:
                logger.warning("[E-Bloc Scraper] Could not find gInfoAsoc block")
                return None
            
            gInfoAsoc_block = gInfoAsoc_block_match.group(0)
            
            # Find all association indices
            asoc_indices = set(re.findall(r'gInfoAsoc\s*\[\s*(\d+)\s*\]', gInfoAsoc_block))
            logger.info(f"[E-Bloc Scraper] Found association indices: {sorted(asoc_indices)}")
            
            matched_asoc_id = None
            property_name_lower = property_name.lower()
            
            for asoc_index in sorted(asoc_indices):
                # Extract all assignments for this association
                kv_pattern = re.compile(
                    r'gInfoAsoc\s*\[\s*' + re.escape(asoc_index) + r'\s*\]\s*\[\s*["\']([^"\']+)["\']\s*\]\s*=\s*["\']([^"\']*)["\']',
                    re.DOTALL
                )
                asoc_data = {}
                for kv_match in kv_pattern.finditer(gInfoAsoc_block):
                    key = kv_match.group(1)
                    value = kv_match.group(2)
                    asoc_data[key] = value
                
                if "id" in asoc_data and "nume" in asoc_data:
                    asoc_name = asoc_data["nume"].lower()
                    # Match property name with association name (partial match)
                    if property_name_lower in asoc_name or asoc_name in property_name_lower:
                        matched_asoc_id = asoc_data["id"]
                        logger.info(f"[E-Bloc Scraper] Matched property '{property_name}' with association '{asoc_data['nume']}' (id: {matched_asoc_id})")
                        break
            
            if not matched_asoc_id:
                logger.warning(f"[E-Bloc Scraper] Could not match property name '{property_name}' with any association")
                return None
            
            # Navigate to the matched property page
            url = f"{self.LOGIN_URL}?page={matched_asoc_id}&t={int(datetime.now().timestamp())}"
            response = await self.client.get(url)
            logger.info(f"[E-Bloc Scraper] Navigated to property page: {url}")
            
            return matched_asoc_id
        except Exception as e:
            logger.error(f"[E-Bloc Scraper] Error selecting property by name: {e}", exc_info=True)
            return None

    async def navigate_to_datorii(self, page_id: str) -> bool:
        """Navigate to Datorii (Debts) page (page=11)"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            url = f"{self.LOGIN_URL}?page=11&t={int(datetime.now().timestamp())}"
            response = await self.client.get(url)
            logger.info(f"[E-Bloc Scraper] Navigated to Datorii page: {url}, status: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"[E-Bloc Scraper] Error navigating to Datorii: {e}", exc_info=True)
            return False

    async def get_balance(self, property_name: Optional[str] = None, page_id: Optional[str] = None) -> Optional[EblocBalance]:
        """Get outstanding balance information from Datorii page"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.logged_in:
            return None
        
        try:
            # If property_name is provided, select it first
            if property_name:
                selected_page_id = await self.select_property_by_name(property_name)
                if not selected_page_id:
                    logger.warning(f"[E-Bloc Scraper] Could not select property '{property_name}'")
                    return None
                page_id = selected_page_id
            
            # Navigate to Datorii page
            if not await self.navigate_to_datorii(page_id or ""):
                logger.warning("[E-Bloc Scraper] Could not navigate to Datorii page")
                return None
            
            # Get the Datorii page content
            url = f"{self.LOGIN_URL}?page=11&t={int(datetime.now().timestamp())}"
            response = await self.client.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Look for "Datoria curentă" or "Suma de plată" text
            outstanding_debt = 0.0
            debt_text = None
            
            # Search for "Suma de plată" followed by amount
            suma_text = soup.find(string=re.compile(r'Suma de plată', re.I))
            if suma_text:
                parent = suma_text.find_parent()
                if parent:
                    text = parent.get_text()
                    # Extract amount: "Suma de plată 442,38 Lei"
                    amount_match = re.search(r'Suma de plată\s+(\d+[.,]\d+|\d+)\s*(?:Lei|RON)', text, re.I)
                    if amount_match:
                        debt_text = amount_match.group(1).replace(',', '.')
                        outstanding_debt = float(debt_text)
                        logger.info(f"[E-Bloc Scraper] Found outstanding debt: {outstanding_debt}")
            
            # Look for apartment number in "Datoria curentă - Ap. 53"
            apartment_match = None
            datoria_text = soup.find(string=re.compile(r'Datoria curentă', re.I))
            if datoria_text:
                parent = datoria_text.find_parent()
                if parent:
                    text = parent.get_text()
                    # Extract apartment: "Datoria curentă - Ap. 53"
                    apt_match = re.search(r'Ap\.\s*(\d+)', text, re.I)
                    if apt_match:
                        apartment_match = apt_match.group(1)
                        logger.info(f"[E-Bloc Scraper] Found apartment: {apartment_match}")
            
            # Look for last payment date from payment history
            last_payment_date = None
            payment_history_text = soup.find(string=re.compile(r'Istoricul plăţilor', re.I))
            if payment_history_text:
                # Look for dates in the payment history section
                parent = payment_history_text.find_parent()
                if parent:
                    # Find all date patterns in the section
                    date_matches = re.findall(r'Data:\s*(\d{1,2})\s+(\w+)\s+(\d{4})', parent.get_text(), re.I)
                    if date_matches:
                        # Get the most recent date (last one)
                        day, month_str, year = date_matches[-1]
                        try:
                            # Convert Romanian month names to numbers
                            month_map = {
                                'ianuarie': 1, 'februarie': 2, 'martie': 3, 'aprilie': 4,
                                'mai': 5, 'iunie': 6, 'iulie': 7, 'august': 8,
                                'septembrie': 9, 'octombrie': 10, 'noiembrie': 11, 'decembrie': 12
                            }
                            month = month_map.get(month_str.lower(), int(month_str) if month_str.isdigit() else None)
                            if month:
                                last_payment_date = datetime(int(year), month, int(day))
                                logger.info(f"[E-Bloc Scraper] Found last payment date: {last_payment_date}")
                        except (ValueError, KeyError):
                            pass
            
            # Look for oldest debt month from payment history
            oldest_debt_month = None
            if payment_history_text:
                parent = payment_history_text.find_parent()
                if parent:
                    # Look for month patterns like "Oct 25" or "Sept 25"
                    month_matches = re.findall(r'(\w+)\s+(\d{2})', parent.get_text(), re.I)
                    if month_matches:
                        # Get the oldest month (first one)
                        month_str, year_short = month_matches[0]
                        oldest_debt_month = f"{month_str} {year_short}"
                        logger.info(f"[E-Bloc Scraper] Found oldest debt month: {oldest_debt_month}")
            
            return EblocBalance(
                outstanding_debt=outstanding_debt,
                last_payment_date=last_payment_date,
                oldest_debt_month=oldest_debt_month,
                debt_level=None
            )
        except Exception as e:
            logger.error(f"[E-Bloc Scraper] Error getting balance: {e}", exc_info=True)
            return None

    async def get_payments(self, property_name: Optional[str] = None, page_id: Optional[str] = None) -> List[EblocPayment]:
        """Get payment receipts (chitante) from Datorii page"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.logged_in:
            return []
        
        try:
            # If property_name is provided, select it first
            if property_name:
                selected_page_id = await self.select_property_by_name(property_name)
                if not selected_page_id:
                    logger.warning(f"[E-Bloc Scraper] Could not select property '{property_name}'")
                    return []
                page_id = selected_page_id
            
            # Navigate to Datorii page
            if not await self.navigate_to_datorii(page_id or ""):
                logger.warning("[E-Bloc Scraper] Could not navigate to Datorii page")
                return []
            
            # Get the Datorii page content
            url = f"{self.LOGIN_URL}?page=11&t={int(datetime.now().timestamp())}"
            response = await self.client.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            payments = []
            
            # Look for "Istoricul plăţilor" section
            payment_history_text = soup.find(string=re.compile(r'Istoricul plăţilor', re.I))
            if not payment_history_text:
                logger.warning("[E-Bloc Scraper] Could not find payment history section")
                return []
            
            # Get the parent container of the payment history
            parent = payment_history_text.find_parent()
            if not parent:
                return []
            
            # Extract all payment entries from the text
            # Format: "Ordin de plată 312,28 Lei\nNumărul: 1826641348291,24 Întreţinere Oct 25\nData: 15 Decembrie 2025"
            text = parent.get_text()
            
            # Split by "Ordin de plată" to get individual payments
            payment_blocks = re.split(r'Ordin de plată', text, flags=re.I)
            
            for block in payment_blocks[1:]:  # Skip first empty block
                # Extract amount: "312,28 Lei"
                amount_match = re.search(r'(\d+[.,]\d+|\d+)\s*(?:Lei|RON)', block, re.I)
                if not amount_match:
                    continue
                
                amount = float(amount_match.group(1).replace(',', '.'))
                
                # Extract receipt number: "Numărul: 1826641348291,24"
                receipt_match = re.search(r'Numărul:\s*(\d+[.,]?\d*)', block, re.I)
                receipt_number = receipt_match.group(1).replace(',', '').replace('.', '') if receipt_match else ""
                
                # Extract date: "Data: 15 Decembrie 2025"
                date_match = re.search(r'Data:\s*(\d{1,2})\s+(\w+)\s+(\d{4})', block, re.I)
                payment_date = None
                if date_match:
                    day, month_str, year = date_match.groups()
                    try:
                        # Convert Romanian month names to numbers
                        month_map = {
                            'ianuarie': 1, 'februarie': 2, 'martie': 3, 'aprilie': 4,
                            'mai': 5, 'iunie': 6, 'iulie': 7, 'august': 8,
                            'septembrie': 9, 'octombrie': 10, 'noiembrie': 11, 'decembrie': 12
                        }
                        month = month_map.get(month_str.lower(), int(month_str) if month_str.isdigit() else None)
                        if month:
                            payment_date = datetime(int(year), month, int(day))
                    except (ValueError, KeyError):
                        pass
                
                if receipt_number and payment_date and amount > 0:
                    payments.append(EblocPayment(
                        receipt_number=receipt_number,
                        payment_date=payment_date,
                        amount=amount
                    ))
                    logger.info(f"[E-Bloc Scraper] Found payment: {receipt_number}, {payment_date}, {amount} Lei")
            
            logger.info(f"[E-Bloc Scraper] Found {len(payments)} payments")
            return payments
        except Exception as e:
            logger.error(f"[E-Bloc Scraper] Error getting payments: {e}", exc_info=True)
            return []

    async def close(self):
        await self.client.aclose()
