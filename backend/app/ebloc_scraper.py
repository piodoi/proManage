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
        self.login_response_html = None  # Store login response HTML to avoid redundant requests
    
    def set_apartment_cookies(self, association_id: str, apartment_id: str):
        """Set cookies for apartment selection: asoc-cur and home-ap-cur"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Set asoc-cur to the association ID
        # httpx cookies are set per domain, so we set them for the base domain
        self.client.cookies.set("asoc-cur", association_id, domain="e-bloc.ro")
        # Set home-ap-cur to {association_id}_{apartment_id}
        home_ap_cur = f"{association_id}_{apartment_id}"
        self.client.cookies.set("home-ap-cur", home_ap_cur, domain="e-bloc.ro")

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
                # Store login response HTML to reuse in find_matching_associations
                self.login_response_html = response.text
                
                # Parse properties from the current page
                await self._parse_property_selector(response.text)
                
                # If no properties found, try navigating to the main index page (without page parameter)
                if len(self.available_properties) == 0:
                    logger.warning("[E-Bloc Scraper] No properties found in login response, trying main index page...")
                    main_page = await self.client.get(self.LOGIN_URL)
                    self.login_response_html = main_page.text  # Update stored HTML
                    await self._parse_property_selector(main_page.text)
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
            
            # First, parse gInfoAsoc to get association information (including adr_bloc)
            gInfoAsoc_block_match = re.search(
                r'gInfoAsoc\s*\[\s*\d+\s*\]\s*=.*?(?=gInfoAp|gContAsoc|</script>|$)',
                html,
                re.DOTALL
            )
            associations = {}  # Map id_asoc -> association data
            if gInfoAsoc_block_match:
                gInfoAsoc_block = gInfoAsoc_block_match.group(0)
                
                # Find all association indices
                asoc_indices = set(re.findall(r'gInfoAsoc\s*\[\s*(\d+)\s*\]', gInfoAsoc_block))
                
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
                # Strip all commas, dots, and currency symbols - assume value is in bani
                cleaned = amount_text.replace("lei", "").replace("RON", "").replace(",", "").replace(".", "").strip() or "0"
                try:
                    # Convert to int (bani) then divide by 100 to get lei
                    amount_bani = int(cleaned)
                    amount = amount_bani / 100.0
                except ValueError:
                    amount = 0.0
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

    async def find_matching_associations(self, property_name: str) -> List[dict]:
        """Find matching associations by comparing address fields from gInfoAsoc with property name, also finds corresponding apartment index"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.logged_in:
            return []
        
        try:
            # Reuse login response HTML to avoid redundant navigation
            if self.login_response_html:
                html = self.login_response_html
            else:
                # Fallback: get the page if HTML wasn't stored
                response = await self.client.get(self.LOGIN_URL)
                html = response.text
            
            # Parse gInfoAsoc to find matching associations
            gInfoAsoc_block_match = re.search(
                r'gInfoAsoc\s*\[\s*\d+\s*\]\s*=.*?(?=gInfoAp|gContAsoc|</script>|$)',
                html,
                re.DOTALL
            )
            
            if not gInfoAsoc_block_match:
                logger.warning("[E-Bloc Scraper] Could not find gInfoAsoc block")
                return []
            
            gInfoAsoc_block = gInfoAsoc_block_match.group(0)
            
            # Also parse gInfoAp to find apartment indices
            gInfoAp_block_match = re.search(
                r'gInfoAp\s*\[\s*\d+\s*\]\s*=.*?(?=gContAsoc|</script>|$)',
                html,
                re.DOTALL
            )
            
            # Build a map of association_id -> (apartment_index, apartment_id) from gInfoAp
            apartment_map = {}  # association_id -> {"apt_index": int, "id_ap": str}
            if gInfoAp_block_match:
                gInfoAp_block = gInfoAp_block_match.group(0)
                apt_indices = set(re.findall(r'gInfoAp\s*\[\s*(\d+)\s*\]', gInfoAp_block))
                
                for apt_index in sorted(apt_indices):
                    kv_pattern = re.compile(
                        r'gInfoAp\s*\[\s*' + re.escape(apt_index) + r'\s*\]\s*\[\s*["\']([^"\']+)["\']\s*\]\s*=\s*["\']([^"\']*)["\']',
                        re.DOTALL
                    )
                    apt_data = {}
                    for kv_match in kv_pattern.finditer(gInfoAp_block):
                        key = kv_match.group(1)
                        value = kv_match.group(2)
                        apt_data[key] = value
                    
                    apt_id_asoc = apt_data.get("id_asoc", "")
                    apt_id_ap = apt_data.get("id_ap", "")
                    if apt_id_asoc and apt_id_ap:
                        # Store the apartment index and apartment ID for this association
                        apartment_map[apt_id_asoc] = {
                            "apt_index": int(apt_index),
                            "id_ap": apt_id_ap
                        }
            
            # Find all association indices
            asoc_indices = set(re.findall(r'gInfoAsoc\s*\[\s*(\d+)\s*\]', gInfoAsoc_block))
            
            matches = []
            property_name_lower = property_name.lower()
            
            # Normalize property name - remove common prefixes and normalize
            normalized_prop = property_name_lower
            normalized_prop = re.sub(r'^(strada|str\.?|st\.?)\s+', '', normalized_prop, flags=re.I)
            normalized_prop = re.sub(r'\s+nr\.?\s*', ' ', normalized_prop, flags=re.I)
            normalized_prop = normalized_prop.strip()
            
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
                
                if "id" not in asoc_data:
                    continue
                
                asoc_id = asoc_data["id"]
                
                # Build address components for matching
                adr_strada = asoc_data.get("adr_strada", "").lower().strip()
                adr_nr = asoc_data.get("adr_nr", "").lower().strip()
                adr_bloc = asoc_data.get("adr_bloc", "").lower().strip()
                
                # Normalize street name
                normalized_street = re.sub(r'^(strada|str\.?|st\.?)\s+', '', adr_strada, flags=re.I).strip()
                
                
                # Check for matches using multiple criteria
                match_score = 0
                match_reasons = []
                
                # Word-by-word matching for better abbreviation handling
                # Split into words and check for matches
                prop_words = set(normalized_prop.split())
                street_words = set(normalized_street.split())
                
                # Remove common words that don't help matching
                common_words = {'nr', 'nr.', 'bloc', 'bl', 'sc', 'scara', 'ap', 'sector', 'str', 'str.', 'strada', 'st'}
                prop_words = {w for w in prop_words if w.lower() not in common_words and len(w) > 2}
                street_words = {w for w in street_words if w.lower() not in common_words and len(w) > 2}
                
                logger.debug(f"[E-Bloc Scraper] Association {asoc_index}: prop_words={prop_words}, street_words={street_words}")
                
                # Count matching words (handles abbreviations like "Plut." matching "Plutonier")
                matching_words = 0
                for prop_word in prop_words:
                    for street_word in street_words:
                        # Check if words match (exact or one contains the other)
                        if prop_word.lower() == street_word.lower():
                            matching_words += 1
                            break
                        # Handle abbreviations: "plut" matches "plutonier", "radu" matches "radu"
                        elif prop_word.lower() in street_word.lower() or street_word.lower() in prop_word.lower():
                            # Only count if the shorter word is at least 3 characters (to avoid false matches)
                            min_len = min(len(prop_word), len(street_word))
                            if min_len >= 3:
                                matching_words += 1
                                break
                
                if matching_words > 0:
                    match_score += matching_words * 8  # 8 points per matching word
                    match_reasons.append(f"words: {matching_words} matching")
                
                # Match street name (partial match) - fallback
                if normalized_street and normalized_street in normalized_prop:
                    match_score += 10
                    match_reasons.append(f"street: '{adr_strada}'")
                
                # Match street name (reverse - property contains street)
                if normalized_street and normalized_prop in normalized_street:
                    match_score += 10
                    match_reasons.append(f"street: '{adr_strada}'")
                
                # Match number
                if adr_nr and adr_nr in normalized_prop:
                    match_score += 5
                    match_reasons.append(f"number: '{adr_nr}'")
                
                # Match bloc - check both in property name and association name
                asoc_name = asoc_data.get("nume", "").lower()
                if adr_bloc:
                    if adr_bloc in normalized_prop:
                        match_score += 3
                        match_reasons.append(f"bloc: '{adr_bloc}'")
                    elif adr_bloc in asoc_name:
                        # Bloc found in association name (e.g., "Bloc M6")
                        match_score += 2
                        match_reasons.append(f"bloc in name: '{adr_bloc}'")
                
                # Match association name as fallback
                if property_name_lower in asoc_name or asoc_name in property_name_lower:
                    match_score += 2
                    match_reasons.append(f"name: '{asoc_data.get('nume', '')}'")
                
                # Only include matches with score > 5 (weaker matches are filtered out, fallback shows all if no matches)
                if match_score > 5:
                    # Get the apartment info from gInfoAp
                    apt_info = apartment_map.get(asoc_id, {})
                    apt_id_ap = apt_info.get("id_ap", "")
                    
                    # Use the gInfoAsoc index directly (this is the combo box index)
                    apartment_index = int(asoc_index)
                    
                    matches.append({
                        "id": asoc_id,
                        "nume": asoc_data.get("nume", ""),
                        "adr_strada": adr_strada,
                        "adr_nr": adr_nr,
                        "adr_bloc": adr_bloc,
                        "score": match_score,
                        "reasons": match_reasons,
                        "apartment_index": apartment_index,  # gInfoAsoc index for combo box
                        "apartment_id": apt_id_ap  # id_ap from gInfoAp for cookie (home-ap-cur)
                    })
            
            # Sort by score (highest first)
            matches.sort(key=lambda x: x["score"], reverse=True)
            
            if not matches:
                logger.warning(f"[E-Bloc Scraper] Could not match property name '{property_name}' with any association, returning all {len(asoc_indices)} associations as fallback")
                for asoc_index in sorted(asoc_indices):
                    kv_pattern = re.compile(
                        r'gInfoAsoc\s*\[\s*' + re.escape(asoc_index) + r'\s*\]\s*\[\s*["\']([^"\']+)["\']\s*\]\s*=\s*["\']([^"\']*)["\']',
                        re.DOTALL
                    )
                    asoc_data = {}
                    for kv_match in kv_pattern.finditer(gInfoAsoc_block):
                        key = kv_match.group(1)
                        value = kv_match.group(2)
                        asoc_data[key] = value
                    
                    if "id" not in asoc_data:
                        continue
                    
                    asoc_id = asoc_data["id"]
                    apt_info = apartment_map.get(asoc_id, {})
                    apt_id_ap = apt_info.get("id_ap", "")
                    
                    matches.append({
                        "id": asoc_id,
                        "nume": asoc_data.get("nume", ""),
                        "adr_strada": asoc_data.get("adr_strada", ""),
                        "adr_nr": asoc_data.get("adr_nr", ""),
                        "adr_bloc": asoc_data.get("adr_bloc", ""),
                        "score": 0,  # No match score
                        "reasons": ["fallback: no match found"],
                        "apartment_index": int(asoc_index),
                        "apartment_id": apt_id_ap
                    })
            
            return matches
        except Exception as e:
            logger.error(f"[E-Bloc Scraper] Error finding matching associations: {e}", exc_info=True)
            return []

    async def find_matching_apartment(self, property_name: str, association_id: str) -> Optional[int]:
        """Find the apartment index from gInfoAp that matches the property name for the given association"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.logged_in:
            return None
        
        try:
            # Get the current page to parse JavaScript variables
            response = await self.client.get(self.LOGIN_URL)
            html = response.text
            
            # Parse gInfoAp to find matching apartment
            gInfoAp_block_match = re.search(
                r'gInfoAp\s*\[\s*\d+\s*\]\s*=.*?(?=gContAsoc|</script>|$)',
                html,
                re.DOTALL
            )
            
            if not gInfoAp_block_match:
                logger.warning("[E-Bloc Scraper] Could not find gInfoAp block")
                return None
            
            gInfoAp_block = gInfoAp_block_match.group(0)
            
            # Find all apartment indices
            apt_indices = set(re.findall(r'gInfoAp\s*\[\s*(\d+)\s*\]', gInfoAp_block))
            logger.info(f"[E-Bloc Scraper] Found apartment indices: {sorted(apt_indices)}")
            
            property_name_lower = property_name.lower()
            normalized_prop = property_name_lower
            normalized_prop = re.sub(r'^(strada|str\.?|st\.?)\s+', '', normalized_prop, flags=re.I)
            normalized_prop = re.sub(r'\s+nr\.?\s*', ' ', normalized_prop, flags=re.I)
            normalized_prop = normalized_prop.strip()
            
            best_match = None
            best_score = 0
            
            for apt_index in sorted(apt_indices):
                # Extract all assignments for this apartment
                kv_pattern = re.compile(
                    r'gInfoAp\s*\[\s*' + re.escape(apt_index) + r'\s*\]\s*\[\s*["\']([^"\']+)["\']\s*\]\s*=\s*["\']([^"\']*)["\']',
                    re.DOTALL
                )
                apt_data = {}
                for kv_match in kv_pattern.finditer(gInfoAp_block):
                    key = kv_match.group(1)
                    value = kv_match.group(2)
                    apt_data[key] = value
                
                # Check if this apartment belongs to the target association
                apt_id_asoc = apt_data.get("id_asoc", "")
                if apt_id_asoc != association_id:
                    continue
                
                # Get the bloc (address) field
                apt_bloc = apt_data.get("bloc", "").lower().strip()
                apt_ap = apt_data.get("ap", "").strip()
                
                # Normalize apartment address
                normalized_apt_bloc = re.sub(r'^(strada|str\.?|st\.?)\s+', '', apt_bloc, flags=re.I)
                normalized_apt_bloc = re.sub(r'\s+nr\.?\s*', ' ', normalized_apt_bloc, flags=re.I)
                normalized_apt_bloc = normalized_apt_bloc.strip()
                
                # Score the match
                match_score = 0
                
                # Exact match of normalized addresses
                if normalized_apt_bloc == normalized_prop:
                    match_score = 100
                # Property contains apartment address
                elif normalized_apt_bloc and normalized_apt_bloc in normalized_prop:
                    match_score = 50
                # Apartment address contains property
                elif normalized_apt_bloc and normalized_prop in normalized_apt_bloc:
                    match_score = 50
                # Partial match
                elif normalized_apt_bloc and any(word in normalized_prop for word in normalized_apt_bloc.split() if len(word) > 3):
                    match_score = 25
                
                if match_score > best_score:
                    best_score = match_score
                    best_match = int(apt_index)
                    logger.info(f"[E-Bloc Scraper] Found matching apartment: index={apt_index}, id_asoc={apt_id_asoc}, ap={apt_ap}, bloc='{apt_data.get('bloc', '')}', score={match_score}")
            
            if best_match is not None:
                logger.info(f"[E-Bloc Scraper] Selected apartment index {best_match} for property '{property_name}' in association {association_id}")
            else:
                logger.warning(f"[E-Bloc Scraper] Could not find matching apartment for property '{property_name}' in association {association_id}")
            
            return best_match
        except Exception as e:
            logger.error(f"[E-Bloc Scraper] Error finding matching apartment: {e}", exc_info=True)
            return None

    async def select_apartment(self, apartment_index: int) -> bool:
        """Select apartment from combo box by making a POST request"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.logged_in:
            return False
        
        try:
            # The combo box selection might require a POST request
            # Based on typical e-bloc behavior, we might need to POST with the apartment index
            # Let's try to set the apartment by making a request with the apartment parameter
            # First, get the current page to see the form structure
            response = await self.client.get(self.LOGIN_URL)
            html = response.text
            
            # Try to find the form or API endpoint for apartment selection
            # Common pattern: POST to same page with apartment parameter
            # Or navigate with apartment in query string
            # For now, we'll try to POST with the apartment index
            
            # Extract any required form fields (CSRF tokens, etc.)
            soup = BeautifulSoup(html, "html.parser")
            
            # Try POST request to select apartment
            # The form might be at the same URL or a specific endpoint
            post_data = {
                "home-ap": str(apartment_index),
                "action": "select_ap"
            }
            
            # Try POST to the login URL
            response = await self.client.post(self.LOGIN_URL, data=post_data, follow_redirects=True)
            logger.info(f"[E-Bloc Scraper] Posted apartment selection: index={apartment_index}, status={response.status_code}")
            
            # Verify the apartment was selected by checking the response
            # The page should reflect the selected apartment
            return response.status_code == 200
        except Exception as e:
            logger.error(f"[E-Bloc Scraper] Error selecting apartment: {e}", exc_info=True)
            return False

    async def select_property_by_name(self, property_name: str, association_id: Optional[str] = None, apartment_index: Optional[int] = None, apartment_id: Optional[str] = None) -> tuple[Optional[str], Optional[int]]:
        """Select property from combo box by matching property name with address fields from gInfoAsoc.
        Sets cookies (asoc-cur and home-ap-cur) to select the apartment.
        Returns (association_id, apartment_index)"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.logged_in:
            return None, None
        
        try:
            matched_asoc_id = None
            matched_apartment_index = apartment_index
            matched_apartment_id = apartment_id
            
            # If association_id is provided, use it directly
            if association_id:
                matched_asoc_id = association_id
            else:
                # Otherwise, find matches
                matches = await self.find_matching_associations(property_name)
                
                if not matches:
                    return None, None
                
                # Use the best match
                best_match = matches[0]
                matched_asoc_id = best_match["id"]
                # Get apartment index and ID from the match if not provided
                if matched_apartment_index is None:
                    matched_apartment_index = best_match.get("apartment_index")
                if matched_apartment_id is None:
                    matched_apartment_id = best_match.get("apartment_id")
                logger.info(f"[E-Bloc Scraper] Found association {matched_asoc_id}, apartment_index: {matched_apartment_index}, apartment_id: {matched_apartment_id}")
            
            # Set cookies to select the apartment
            if matched_asoc_id and matched_apartment_id:
                self.set_apartment_cookies(matched_asoc_id, matched_apartment_id)
            elif matched_asoc_id:
                # If we don't have apartment_id, just set asoc-cur
                self.client.cookies.set("asoc-cur", matched_asoc_id, domain=".e-bloc.ro")
                logger.info(f"[E-Bloc Scraper] Set cookie: asoc-cur={matched_asoc_id} (no apartment_id available)")
            
            # Navigate to the association page to ensure cookies are sent
            url = f"{self.LOGIN_URL}?page={matched_asoc_id}&t={int(datetime.now().timestamp())}"
            response = await self.client.get(url)
            logger.info(f"[E-Bloc Scraper] Navigated to association page: {url}, status: {response.status_code}")
            
            return matched_asoc_id, matched_apartment_index
        except Exception as e:
            logger.error(f"[E-Bloc Scraper] Error selecting property by name: {e}", exc_info=True)
            return None, None

    async def navigate_to_datorii(self, page_id: str, apartment_index: Optional[int] = None) -> tuple[bool, str, Optional[BeautifulSoup]]:
        """Navigate to Datorii (Debts) page (page=11). Cookies handle apartment selection.
        Returns (success, url_used, soup) so caller can use the parsed HTML directly."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Cookies handle apartment selection, no need for home-ap in URL
            url = f"{self.LOGIN_URL}?page=11&t={int(datetime.now().timestamp())}"
            response = await self.client.get(url)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                return (True, url, soup)
            else:
                return (False, url, None)
        except Exception as e:
            logger.error(f"[E-Bloc Scraper] Error navigating to Datorii: {e}", exc_info=True)
            return (False, url if 'url' in locals() else "", None)

    async def ensure_cookies_and_navigate(self, property_name: Optional[str] = None, association_id: Optional[str] = None, apartment_index: Optional[int] = None, apartment_id: Optional[str] = None) -> tuple[Optional[str], Optional[BeautifulSoup]]:
        """Ensure cookies are set and navigate to Datorii page. Returns (association_id, soup)."""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.logged_in:
            return None, None
        
        try:
            matched_asoc_id = None
            
            # If association_id is provided, use it directly
            if association_id:
                matched_asoc_id = association_id
                # Set cookies if we have apartment_id (only if not already set correctly)
                if apartment_id:
                    current_asoc = self.client.cookies.get("asoc-cur")
                    current_home_ap = self.client.cookies.get("home-ap-cur")
                    expected_home_ap = f"{association_id}_{apartment_id}"
                    if current_asoc != association_id or current_home_ap != expected_home_ap:
                        self.set_apartment_cookies(association_id, apartment_id)
                        # No need to navigate to association page - cookies will be sent with next request
            # If property_name is provided, select it first
            elif property_name:
                selected_page_id, apt_idx = await self.select_property_by_name(property_name, association_id=association_id, apartment_index=apartment_index, apartment_id=apartment_id)
                if not selected_page_id:
                    logger.warning(f"[E-Bloc Scraper] Could not select property '{property_name}'")
                    return None, None
                matched_asoc_id = selected_page_id
                if apartment_index is None:
                    apartment_index = apt_idx
            
            # Navigate directly to Datorii page (cookies handle apartment selection)
            success, datorii_url, soup = await self.navigate_to_datorii(matched_asoc_id or "", apartment_index)
            if not success or soup is None:
                logger.warning("[E-Bloc Scraper] Could not navigate to Datorii page")
                return None, None
            
            return matched_asoc_id, soup
        except Exception as e:
            logger.error(f"[E-Bloc Scraper] Error ensuring cookies and navigating: {e}", exc_info=True)
            return None, None

    async def get_balance(self, property_name: Optional[str] = None, association_id: Optional[str] = None, page_id: Optional[str] = None, apartment_index: Optional[int] = None, apartment_id: Optional[str] = None, soup: Optional[BeautifulSoup] = None) -> Optional[EblocBalance]:
        """Get outstanding balance information from Datorii page"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.logged_in:
            return None
        
        try:
            # If soup is not provided, navigate to Datorii page
            if soup is None:
                matched_asoc_id, soup = await self.ensure_cookies_and_navigate(property_name, association_id, apartment_index, apartment_id)
                if soup is None:
                    return None
            
            # Look for outstanding debt using the total_plata attribute on the table
            outstanding_debt = 0.0
            
            # Find the table with class "plateste_tabel_datorii_curente" which has total_plata attribute
            debt_table = soup.find("table", class_="plateste_tabel_datorii_curente")
            if debt_table:
                total_plata = debt_table.get("total_plata")
                if total_plata:
                    # total_plata is in bani (cents), so divide by 100 to get Lei
                    outstanding_debt = float(total_plata) / 100.0
                    logger.info(f"[E-Bloc Scraper] Found outstanding debt from total_plata: {outstanding_debt} Lei (raw: {total_plata} bani)")
                else:
                    logger.warning("[E-Bloc Scraper] Table found but no total_plata attribute")
            else:
                # Fallback: try to find the span with class "plateste_suma_datorata_titlu"
                suma_span = soup.find("span", class_="plateste_suma_datorata_titlu")
                if suma_span:
                    text = suma_span.get_text(strip=True)
                    # Extract amount: "442,38 Lei" - assume value is in bani
                    amount_match = re.search(r'(\d+[.,]?\d*)\s*(?:Lei|RON)?', text, re.I)
                    if amount_match:
                        # Strip all commas and dots - assume value is in bani
                        cleaned = amount_match.group(1).replace(',', '').replace('.', '').strip()
                        try:
                            # Convert to int (bani) then divide by 100 to get lei
                            amount_bani = int(cleaned)
                            outstanding_debt = amount_bani / 100.0
                            logger.info(f"[E-Bloc Scraper] Found outstanding debt from span: {outstanding_debt} Lei")
                        except ValueError:
                            pass
                    else:
                        logger.warning(f"[E-Bloc Scraper] Could not extract amount from suma span: {text}")
                else:
                    logger.warning("[E-Bloc Scraper] Could not find debt table or suma span")
            
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

    async def get_payments(self, property_name: Optional[str] = None, association_id: Optional[str] = None, page_id: Optional[str] = None, apartment_index: Optional[int] = None, apartment_id: Optional[str] = None, soup: Optional[BeautifulSoup] = None) -> List[EblocPayment]:
        """Get payment receipts (chitante) from Datorii page"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.logged_in:
            return []
        
        try:
            # If soup is not provided, navigate to Datorii page
            if soup is None:
                matched_asoc_id, soup = await self.ensure_cookies_and_navigate(property_name, association_id, apartment_index, apartment_id)
                if soup is None:
                    return []
            payments = []
            
            # Find the payment history table with class "plateste_tabel_istoric_plati"
            payment_table = soup.find("table", class_="plateste_tabel_istoric_plati")
            if not payment_table:
                logger.warning("[E-Bloc Scraper] Could not find payment history table")
                return []
            
            # Find all payment rows (rows with class "plateste_line_nolink" that contain "Ordin de plată")
            payment_rows = payment_table.find_all("tr", class_="plateste_line_nolink")
            
            for row in payment_rows:
                # Check if this row contains "Ordin de plată" (skip the "Afişează toate chitanţele" row)
                row_text = row.get_text()
                if "Ordin de plată" not in row_text:
                    continue
                
                # Extract amount from span with class "plateste_titlu" that has float: right
                amount_span = row.find("span", class_="plateste_titlu", style=re.compile(r"float:\s*right"))
                if not amount_span:
                    continue
                
                amount_text = amount_span.get_text(strip=True)
                amount_match = re.search(r'(\d+[.,]?\d*)\s*(?:Lei|RON)?', amount_text, re.I)
                if not amount_match:
                    continue
                
                # Strip all commas and dots - assume value is in bani
                cleaned = amount_match.group(1).replace(',', '').replace('.', '').strip()
                try:
                    # Convert to int (bani) then divide by 100 to get lei
                    amount_bani = int(cleaned)
                    amount = amount_bani / 100.0
                except ValueError:
                    continue
                
                # Extract receipt number from span with class "plateste_descriere" containing "Numărul:"
                receipt_span = row.find("span", class_="plateste_descriere")
                receipt_number = ""
                if receipt_span:
                    # Look for <b> tag inside the span
                    receipt_b = receipt_span.find("b")
                    if receipt_b:
                        receipt_number = receipt_b.get_text(strip=True)
                    else:
                        # Fallback: extract from text
                        receipt_text = receipt_span.get_text()
                        receipt_match = re.search(r'Numărul:\s*(\d+)', receipt_text, re.I)
                        if receipt_match:
                            receipt_number = receipt_match.group(1)
                
                # Extract date from span with class "plateste_data" containing "Data:"
                # Find the span that contains "Data:" (it should have clear: left style)
                date_spans = row.find_all("span", class_="plateste_data")
                payment_date = None
                for date_span in date_spans:
                    date_text = date_span.get_text()
                    if "Data:" in date_text:
                        # Look for <b> tag inside the span
                        date_b = date_span.find("b")
                        if date_b:
                            date_text = date_b.get_text(strip=True)
                        else:
                            # Extract from full text
                            date_text = date_text.replace("Data:", "").strip()
                        
                        # Parse date: "23 Octombrie 2025"
                        date_match = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4})', date_text, re.I)
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
                                    break
                            except (ValueError, KeyError) as e:
                                logger.debug(f"[E-Bloc Scraper] Error parsing date: {e}")
                
                if receipt_number and payment_date and amount > 0:
                    payments.append(EblocPayment(
                        receipt_number=receipt_number,
                        payment_date=payment_date,
                        amount=amount
                    ))
                    logger.info(f"[E-Bloc Scraper] Found payment: {amount} Lei, receipt: {receipt_number}, date: {payment_date}")
            
            logger.info(f"[E-Bloc Scraper] Found {len(payments)} payments")
            return payments
        except Exception as e:
            logger.error(f"[E-Bloc Scraper] Error getting payments: {e}", exc_info=True)
            return []

    async def close(self):
        await self.client.aclose()
