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
        
        # If we found properties from JS, we're done
        if len(self.available_properties) > initial_count:
            logger.info(f"[E-Bloc Scraper] Successfully parsed {len(self.available_properties) - initial_count} properties from JavaScript")
            return
        
        # Fallback to HTML parsing if JS parsing didn't work
        logger.info("[E-Bloc Scraper] JavaScript parsing didn't find properties, trying HTML parsing...")
        soup = BeautifulSoup(html, "html.parser")
        
        # Strategy 1: Look for ALL select dropdowns (combo boxes) - especially in upper right
        print(f"[E-Bloc Scraper] Looking for select dropdowns...")
        logger.info("[E-Bloc Scraper] Looking for select dropdowns...")
        all_selects = soup.find_all("select")
        print(f"[E-Bloc Scraper] Found {len(all_selects)} select elements total")
        logger.info(f"[E-Bloc Scraper] Found {len(all_selects)} select elements total")
        
        # Try to find select in upper right area (common pattern)
        # Look for selects in header, top navigation, or right-aligned containers
        header_selects = []
        for container in soup.find_all(["header", "div", "nav"], class_=re.compile(r'header|top|nav|right|upper', re.I)):
            selects_in_container = container.find_all("select")
            if selects_in_container:
                header_selects.extend(selects_in_container)
                logger.info(f"[E-Bloc Scraper] Found {len(selects_in_container)} select(s) in {container.name} with classes: {container.get('class', [])}")
        
        # Also check for selects with common property-related attributes
        property_selects = soup.find_all("select", {
            "id": re.compile(r'property|imobil|page|select', re.I)
        }) + soup.find_all("select", {
            "name": re.compile(r'property|imobil|page|select', re.I)
        }) + soup.find_all("select", {
            "class": re.compile(r'property|imobil|select', re.I)
        })
        
        # Combine all potential property selects
        all_potential_selects = list(set(all_selects + header_selects + property_selects))
        logger.info(f"[E-Bloc Scraper] Found {len(all_potential_selects)} potential property select elements")
        
        # Process each select element
        for idx, select in enumerate(all_potential_selects):
            select_id = select.get("id", "N/A")
            select_name = select.get("name", "N/A")
            select_class = select.get("class", [])
            print(f"[E-Bloc Scraper] Processing select #{idx+1}: id='{select_id}', name='{select_name}', class={select_class}")
            logger.info(f"[E-Bloc Scraper] Processing select #{idx+1}: id='{select_id}', name='{select_name}', class={select_class}")
            
            options = select.find_all("option")
            print(f"[E-Bloc Scraper] Select #{idx+1} has {len(options)} options")
            logger.info(f"[E-Bloc Scraper] Select #{idx+1} has {len(options)} options")
            
            for opt_idx, option in enumerate(options):
                value = option.get("value", "")
                name = option.get_text(strip=True)
                # Also try to get name from title or data attributes
                if not name or name == value:
                    name = option.get("title", "") or option.get("data-name", "") or name
                
                print(f"[E-Bloc Scraper]   Option #{opt_idx+1}: value='{value}', name='{name}'")
                logger.info(f"[E-Bloc Scraper]   Option #{opt_idx+1}: value='{value}', name='{name}'")
                
                # Accept any option with a value (even "0" might be valid, but skip empty)
                if value and value != "":
                    # Skip placeholder/empty options
                    if name and name.lower() not in ["select", "alege", "choose", "selectează", ""]:
                        url = f"{self.LOGIN_URL}?page={value}&t={int(datetime.now().timestamp())}"
                        if not any(p.page_id == value for p in self.available_properties):
                            self.available_properties.append(EblocProperty(page_id=value, name=name, url=url))
                            print(f"[E-Bloc Scraper] ✓ Added property from select: '{name}' (page_id: {value})")
                            logger.info(f"[E-Bloc Scraper] ✓ Added property from select: '{name}' (page_id: {value})")
                        else:
                            logger.debug(f"[E-Bloc Scraper]   Skipped duplicate property: {value}")
                    else:
                        logger.debug(f"[E-Bloc Scraper]   Skipped option with placeholder name: '{name}'")
                else:
                    logger.debug(f"[E-Bloc Scraper]   Skipped option with no value")
        
        # If still no properties, try the first non-empty select we find
        if len(self.available_properties) == 0 and all_selects:
            logger.warning("[E-Bloc Scraper] No properties found in any select, trying first select with options...")
            for select in all_selects:
                options = select.find_all("option")
                valid_options = [opt for opt in options if opt.get("value") and opt.get("value") != ""]
                if len(valid_options) > 0:
                    logger.info(f"[E-Bloc Scraper] Trying fallback: first select with {len(valid_options)} valid options")
                    for option in valid_options:
                        value = option.get("value", "")
                        name = option.get_text(strip=True) or f"Property {value}"
                        if value:
                            url = f"{self.LOGIN_URL}?page={value}&t={int(datetime.now().timestamp())}"
                            self.available_properties.append(EblocProperty(page_id=value, name=name, url=url))
                            logger.info(f"[E-Bloc Scraper] ✓ Added property (fallback): '{name}' (page_id: {value})")
                    break
        
        # Strategy 2: Look for links with page= parameter
        logger.debug("[E-Bloc Scraper] Looking for links with page= parameter...")
        links = soup.find_all("a", href=True)
        logger.debug(f"[E-Bloc Scraper] Found {len(links)} links total")
        for link in links:
            href = link.get("href", "")
            if "page=" in href:
                match = re.search(r'page=(\d+)', href)
                if match:
                    page_id = match.group(1)
                    name = link.get_text(strip=True) or link.get("title", "") or f"Property {page_id}"
                    # Try to get better name from parent or nearby elements
                    parent = link.find_parent()
                    if parent:
                        parent_text = parent.get_text(strip=True)
                        if parent_text and len(parent_text) > len(name):
                            name = parent_text[:100]  # Limit length
                    
                    if not any(p.page_id == page_id for p in self.available_properties):
                        url = f"{self.LOGIN_URL}?page={page_id}&t={int(datetime.now().timestamp())}"
                        self.available_properties.append(EblocProperty(page_id=page_id, name=name, url=url))
                        logger.info(f"[E-Bloc Scraper] Added property from link: {name} (page_id: {page_id})")
        
        # Strategy 3: Look for navigation menus or property lists
        logger.debug("[E-Bloc Scraper] Looking for navigation menus...")
        nav_elements = soup.find_all(["nav", "ul", "div"], class_=re.compile(r'nav|menu|property|imobil', re.I))
        for nav in nav_elements:
            nav_links = nav.find_all("a", href=True)
            for link in nav_links:
                href = link.get("href", "")
                if "page=" in href or "id=" in href:
                    match = re.search(r'(?:page|id)=(\d+)', href)
                    if match:
                        page_id = match.group(1)
                        name = link.get_text(strip=True) or link.get("title", "") or f"Property {page_id}"
                        if not any(p.page_id == page_id for p in self.available_properties):
                            url = f"{self.LOGIN_URL}?page={page_id}&t={int(datetime.now().timestamp())}"
                            self.available_properties.append(EblocProperty(page_id=page_id, name=name, url=url))
                            logger.info(f"[E-Bloc Scraper] Added property from nav: {name} (page_id: {page_id})")
        
        # Strategy 4: Look for any form inputs or hidden fields that might contain property IDs
        logger.debug("[E-Bloc Scraper] Looking for form inputs with property info...")
        inputs = soup.find_all("input", {"type": "hidden"})
        for inp in inputs:
            name_attr = inp.get("name", "")
            value = inp.get("value", "")
            if "property" in name_attr.lower() or "page" in name_attr.lower() or "id" in name_attr.lower():
                if value and value.isdigit():
                    page_id = value
                    # Try to find associated label or text
                    parent = inp.find_parent()
                    name = f"Property {page_id}"
                    if parent:
                        label = parent.find("label")
                        if label:
                            name = label.get_text(strip=True)
                        else:
                            text = parent.get_text(strip=True)
                            if text and len(text) < 100:
                                name = text
                    
                    if not any(p.page_id == page_id for p in self.available_properties):
                        url = f"{self.LOGIN_URL}?page={page_id}&t={int(datetime.now().timestamp())}"
                        self.available_properties.append(EblocProperty(page_id=page_id, name=name, url=url))
                        logger.info(f"[E-Bloc Scraper] Added property from input: {name} (page_id: {page_id})")
        
        new_count = len(self.available_properties) - initial_count
        print(f"[E-Bloc Scraper] Property parsing complete. Added {new_count} new properties. Total: {len(self.available_properties)}")
        logger.info(f"[E-Bloc Scraper] Property parsing complete. Added {new_count} new properties. Total: {len(self.available_properties)}")
        
        # Log all found properties for debugging
        if len(self.available_properties) > 0:
            print("[E-Bloc Scraper] Found properties:")
            logger.info("[E-Bloc Scraper] Found properties:")
            for prop in self.available_properties:
                print(f"  - {prop.name} (page_id: {prop.page_id})")
                logger.info(f"  - {prop.name} (page_id: {prop.page_id})")
        else:
            print("[E-Bloc Scraper] No properties found! HTML structure might have changed.")
            logger.warning("[E-Bloc Scraper] No properties found! HTML structure might have changed.")
            # Log all select elements found for debugging
            all_selects_found = soup.find_all("select")
            logger.warning(f"[E-Bloc Scraper] Found {len(all_selects_found)} select elements but none had valid properties")
            for sel in all_selects_found:
                logger.warning(f"[E-Bloc Scraper]   Select: id='{sel.get('id')}', name='{sel.get('name')}', class={sel.get('class')}, options={len(sel.find_all('option'))}")
            
            # Save a sample of the HTML for debugging
            html_sample = html[:5000] if len(html) > 5000 else html
            logger.warning(f"[E-Bloc Scraper] HTML sample (first 5000 chars):\n{html_sample}")
            
            # Also try to find any elements that might contain property info
            logger.warning("[E-Bloc Scraper] Searching for any elements with 'page', 'property', or 'imobil' in attributes...")
            property_elements = soup.find_all(attrs={"id": re.compile(r'page|property|imobil', re.I)})
            property_elements += soup.find_all(attrs={"name": re.compile(r'page|property|imobil', re.I)})
            property_elements += soup.find_all(attrs={"class": re.compile(r'page|property|imobil', re.I)})
            logger.warning(f"[E-Bloc Scraper] Found {len(property_elements)} elements with property-related attributes")
            for elem in property_elements[:10]:  # Log first 10
                logger.warning(f"[E-Bloc Scraper]   Element: {elem.name}, id='{elem.get('id')}', name='{elem.get('name')}', class={elem.get('class')}")

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
                        address = property_data["bloc"]
                        # Get id_asoc and id_ap to construct page_id
                        id_asoc = property_data.get("id_asoc", "")
                        id_ap = property_data.get("id_ap", "")
                        
                        # The page_id might be the id_asoc or a combination
                        # Looking at the URL pattern, it seems like page_id is id_asoc
                        page_id = id_asoc if id_asoc else f"{index}"
                        
                        # Use "bloc" as the name, or construct from other fields
                        name = address
                        if "nume" in property_data:
                            owner_name = property_data["nume"]
                            # Combine address with owner if available
                            name = f"{address} ({owner_name})"
                        
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
        # If we already have properties from login, return them
        if self.available_properties:
            return self.available_properties
        
        # If login was successful but no properties found, try using Playwright for JS-rendered content
        if self.logged_in:
            try:
                return await self._get_properties_with_playwright()
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"[E-Bloc Scraper] Playwright method failed: {e}")
        
        return self.available_properties
    
    async def _get_properties_with_playwright(self) -> list[EblocProperty]:
        """Use Playwright to get properties from JavaScript-rendered page"""
        try:
            from playwright.async_api import async_playwright
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info("[E-Bloc Scraper] Using Playwright to get JavaScript-rendered properties...")
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                
                # Copy cookies from httpx session to Playwright
                cookies = []
                for cookie in self.client.cookies.jar:
                    cookies.append({
                        "name": cookie.name,
                        "value": cookie.value,
                        "domain": cookie.domain or ".e-bloc.ro",
                        "path": cookie.path or "/",
                    })
                if cookies:
                    await context.add_cookies(cookies)
                
                page = await context.new_page()
                await page.goto(self.LOGIN_URL, wait_until="networkidle")
                
                # Wait for property selector to appear (might be loaded via JS)
                try:
                    # Wait for select element to appear
                    await page.wait_for_selector("select", timeout=10000)
                except:
                    logger.warning("[E-Bloc Scraper] Select element not found, trying to wait for page load...")
                    await page.wait_for_timeout(3000)  # Wait 3 seconds for JS to execute
                
                # Get the page HTML after JavaScript execution
                html = await page.content()
                await browser.close()
                
                # Parse the HTML
                await self._parse_property_selector(html)
                logger.info(f"[E-Bloc Scraper] Playwright found {len(self.available_properties)} properties")
                
        except ImportError:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("[E-Bloc Scraper] Playwright not installed. Install with: poetry add playwright && playwright install chromium")
            raise
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[E-Bloc Scraper] Playwright error: {e}", exc_info=True)
            raise
        
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

    async def get_balance(self, page_id: Optional[str] = None) -> Optional[EblocBalance]:
        """Get outstanding balance information for a property"""
        if not self.logged_in:
            return None
        try:
            if page_id:
                url = f"{self.LOGIN_URL}?page={page_id}&t={int(datetime.now().timestamp())}"
            else:
                url = self.LOGIN_URL
            response = await self.client.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Look for debt/balance information
            debt_text = None
            debt_elements = soup.find_all(string=re.compile(r'datorie|restanță|debt', re.I))
            for elem in debt_elements:
                parent = elem.find_parent()
                if parent:
                    text = parent.get_text()
                    # Try to extract amount
                    amount_match = re.search(r'(\d+[.,]\d+|\d+)\s*(?:RON|lei)', text, re.I)
                    if amount_match:
                        debt_text = amount_match.group(1).replace(',', '.')
                        break
            
            outstanding_debt = float(debt_text) if debt_text else 0.0
            
            # Look for last payment date
            last_payment_date = None
            payment_date_elements = soup.find_all(string=re.compile(r'ultima.*plată|last.*payment', re.I))
            for elem in payment_date_elements:
                parent = elem.find_parent()
                if parent:
                    text = parent.get_text()
                    date_match = re.search(r'(\d{1,2})[./-](\d{1,2})[./-](\d{4})', text)
                    if date_match:
                        try:
                            day, month, year = date_match.groups()
                            last_payment_date = datetime(int(year), int(month), int(day))
                            break
                        except ValueError:
                            pass
            
            # Look for oldest debt month
            oldest_debt_month = None
            oldest_elements = soup.find_all(string=re.compile(r'cea mai veche|luna.*veche', re.I))
            for elem in oldest_elements:
                parent = elem.find_parent()
                if parent:
                    text = parent.get_text()
                    month_match = re.search(r'(\w+\s+\d{4})', text, re.I)
                    if month_match:
                        oldest_debt_month = month_match.group(1)
                        break
            
            # Debt level
            debt_level = None
            if outstanding_debt > 0:
                if outstanding_debt < 100:
                    debt_level = "low"
                elif outstanding_debt < 500:
                    debt_level = "medium"
                else:
                    debt_level = "high"
            
            return EblocBalance(
                outstanding_debt=outstanding_debt,
                last_payment_date=last_payment_date,
                oldest_debt_month=oldest_debt_month,
                debt_level=debt_level
            )
        except Exception as e:
            print(f"Error getting balance: {e}")
            return None

    async def get_payments(self, page_id: Optional[str] = None) -> List[EblocPayment]:
        """Get payment receipts (chitante) for a property"""
        if not self.logged_in:
            return []
        try:
            if page_id:
                url = f"{self.LOGIN_URL}?page={page_id}&t={int(datetime.now().timestamp())}"
            else:
                url = self.LOGIN_URL
            response = await self.client.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            payments = []
            
            # Look for payment/receipt tables or lists
            # Try to find tables with payment information
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 3:
                        # Look for receipt number pattern
                        receipt_text = cells[0].get_text(strip=True) if len(cells) > 0 else ""
                        date_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                        amount_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                        
                        # Check if this looks like a payment row
                        if re.search(r'\d{10,}', receipt_text) and re.search(r'\d+[.,]\d+', amount_text):
                            receipt_number = re.search(r'\d{10,}', receipt_text).group(0) if re.search(r'\d{10,}', receipt_text) else receipt_text
                            
                            # Parse date
                            payment_date = None
                            date_match = re.search(r'(\d{1,2})[./-](\d{1,2})[./-](\d{4})', date_text)
                            if date_match:
                                try:
                                    day, month, year = date_match.groups()
                                    payment_date = datetime(int(year), int(month), int(day))
                                except ValueError:
                                    pass
                            
                            # Parse amount
                            amount = 0.0
                            amount_match = re.search(r'(\d+[.,]\d+|\d+)', amount_text.replace(',', '.'))
                            if amount_match:
                                try:
                                    amount = float(amount_match.group(1))
                                except ValueError:
                                    pass
                            
                            if receipt_number and payment_date and amount > 0:
                                payments.append(EblocPayment(
                                    receipt_number=receipt_number,
                                    payment_date=payment_date,
                                    amount=amount
                                ))
            
            # Also try to find payment information in divs or other structures
            payment_divs = soup.find_all(["div", "li"], class_=re.compile(r'payment|chitanță|receipt', re.I))
            for div in payment_divs:
                text = div.get_text()
                receipt_match = re.search(r'(\d{10,})', text)
                date_match = re.search(r'(\d{1,2})[./-](\d{1,2})[./-](\d{4})', text)
                amount_match = re.search(r'(\d+[.,]\d+|\d+)\s*(?:RON|lei)', text, re.I)
                
                if receipt_match and date_match and amount_match:
                    receipt_number = receipt_match.group(1)
                    day, month, year = date_match.groups()
                    try:
                        payment_date = datetime(int(year), int(month), int(day))
                        amount = float(amount_match.group(1).replace(',', '.'))
                        payments.append(EblocPayment(
                            receipt_number=receipt_number,
                            payment_date=payment_date,
                            amount=amount
                        ))
                    except (ValueError, IndexError):
                        pass
            
            return payments
        except Exception as e:
            print(f"Error getting payments: {e}")
            return []

    async def close(self):
        await self.client.aclose()
