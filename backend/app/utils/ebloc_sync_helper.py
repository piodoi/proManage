"""Helper utilities for E-bloc supplier synchronization"""
import logging
import re
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

from app.database import db
from app.models import Property, BillStatus, BillType
from app.utils.ebloc_association_matcher import find_matching_associations
from app.web_scraper import WebScraper, load_scraper_config

logger = logging.getLogger(__name__)


def extract_apartment_number_from_address(address: Optional[str]) -> Optional[str]:
    """Extract apartment number from property address.
    Looks for patterns like 'Ap. 5', 'Ap 5', 'Ap:5', 'apartament 5', etc.
    """
    if not address:
        return None
    
    # Try various patterns for apartment number
    patterns = [
        r'Ap\.?\s*:?\s*(\d+)',  # Ap. 5, Ap 5, Ap:5
        r'apartament\.?\s*:?\s*(\d+)',  # apartament 5
        r'apt\.?\s*:?\s*(\d+)',  # apt 5
    ]
    
    for pattern in patterns:
        match = re.search(pattern, address, re.I)
        if match:
            return match.group(1)
    
    return None


async def _log_all_ebloc_associations(login_html: str):
    """Parse and log all associations and apartments found in E-bloc login HTML for debugging"""
    try:
        # Parse gInfoAsoc to get all associations
        gInfoAsoc_block_match = re.search(
            r'gInfoAsoc\s*\[\s*\d+\s*\]\s*=.*?(?=gInfoAp|gContAsoc|</script>|$)',
            login_html,
            re.DOTALL
        )
        
        associations_data = []
        if gInfoAsoc_block_match:
            gInfoAsoc_block = gInfoAsoc_block_match.group(0)
            asoc_indices = set(re.findall(r'gInfoAsoc\s*\[\s*(\d+)\s*\]', gInfoAsoc_block))
            
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
                
                if "id" in asoc_data:
                    associations_data.append(asoc_data)
        
        # Parse gInfoAp to get all apartments
        gInfoAp_block_match = re.search(
            r'gInfoAp\s*\[\s*\d+\s*\]\s*=.*?(?=gContAsoc|</script>|$)',
            login_html,
            re.DOTALL
        )
        
        apartments_data = []
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
                
                if "id_asoc" in apt_data and "id_ap" in apt_data:
                    apartments_data.append(apt_data)
        
        # Log all found associations
        logger.info(f"[E-bloc] Found {len(associations_data)} association(s) in login HTML:")
        for asoc in associations_data:
            logger.info(f"  - Association ID: {asoc.get('id')}, Name: {asoc.get('nume', 'N/A')}, "
                       f"Address: {asoc.get('adr_strada', '')} {asoc.get('adr_nr', '')}, "
                       f"Bloc: {asoc.get('adr_bloc', '')}")
        
        # Log all found apartments (without apartment ID to avoid confusion)
        logger.info(f"[E-bloc] Found {len(apartments_data)} apartment(s) in login HTML:")
        for apt in apartments_data:
            logger.info(f"  - Association: {apt.get('id_asoc')}, "
                       f"Apartment: {apt.get('ap', 'N/A')}, Address: {apt.get('bloc', 'N/A')}")
    except Exception as e:
        logger.warning(f"[E-bloc] Error logging associations: {e}", exc_info=True)


async def match_property_to_association_with_apartment(
    property_obj: Property,
    login_html: str
) -> Optional[Tuple[str, Optional[str]]]:
    """
    Match a property to E-bloc association and apartment using property name and address.
    
    First matches by property name to find the association, then refines by apartment number
    from the property address.
    
    Args:
        property_obj: Property object to match
        login_html: HTML content from login page containing association data
    
    Returns:
        Tuple of (association_id, apartment_id) or None if no match
    """
    # First, match by property name to get associations
    matches = await find_matching_associations(login_html, property_obj.name)
    
    if not matches:
        logger.warning(f"[E-bloc] No associations found for property '{property_obj.name}'")
        return None
    
    # Extract apartment number from property address (looks for "Ap: [number]" pattern)
    apt_number_from_address = extract_apartment_number_from_address(property_obj.address)
    
    if apt_number_from_address:
        # If we have an apartment number, try to refine by apartment number
        # Parse gInfoAp to find apartments with matching apartment numbers
        gInfoAp_block_match = re.search(
            r'gInfoAp\s*\[\s*\d+\s*\]\s*=.*?(?=gContAsoc|</script>|$)',
            login_html,
            re.DOTALL
        )
        
        if gInfoAp_block_match:
            gInfoAp_block = gInfoAp_block_match.group(0)
            apt_indices = set(re.findall(r'gInfoAp\s*\[\s*(\d+)\s*\]', gInfoAp_block))
            
            # Find apartments that match the apartment number
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
                apt_number = apt_data.get("ap", "").strip()
                
                # Check if this apartment number matches our property address apartment number
                if apt_number and apt_number == apt_number_from_address:
                    # Verify this association is in our matches
                    for match in matches:
                        if match["id"] == apt_id_asoc:
                            logger.info(f"[E-bloc] Matched property '{property_obj.name}' to association {apt_id_asoc}, apartment {apt_number} (Ap. {apt_number} from address)")
                            return (apt_id_asoc, apt_id_ap)
    
    # If no apartment match but we have matches, try matching by association name only
    # and use the first apartment found for that association
    if matches and apt_number_from_address:
        # Try to find any apartment in any matched association that has the same apartment number
        gInfoAp_block_match = re.search(
            r'gInfoAp\s*\[\s*\d+\s*\]\s*=.*?(?=gContAsoc|</script>|$)',
            login_html,
            re.DOTALL
        )
        if gInfoAp_block_match:
            gInfoAp_block = gInfoAp_block_match.group(0)
            apt_indices = set(re.findall(r'gInfoAp\s*\[\s*(\d+)\s*\]', gInfoAp_block))
            
            # Check all apartments for matching apartment number across all matched associations
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
                apt_number = apt_data.get("ap", "").strip()
                
                # Check if apartment number matches and association is in our matches
                if apt_number and apt_number == apt_number_from_address:
                    for match in matches:
                        if match["id"] == apt_id_asoc:
                            logger.info(f"[E-bloc] Matched property '{property_obj.name}' to association {apt_id_asoc}, apartment {apt_number} (cross-matched by apartment number)")
                            return (apt_id_asoc, apt_id_ap)
    
    # Fallback: use the best match (highest score)
    best_match = max(matches, key=lambda m: m.get("score", 0))
    association_id = best_match["id"]
    apartment_id = best_match.get("apartment_id")
    
    logger.info(f"[E-bloc] Matched property '{property_obj.name}' to association {association_id}, apartment {apartment_id}")
    return (association_id, apartment_id)


async def sync_ebloc_all_properties(
    properties: List[Tuple[str, Optional[str]]],  # List of (property_id, contract_id) tuples
    username: str,
    password: str
) -> Tuple[List[Dict[str, Any]], Dict[str, Tuple[str, Optional[str]]]]:
    """
    Sync E-bloc supplier for multiple properties.
    
    Args:
        properties: List of (property_id, contract_id) tuples
        username: E-bloc username
        password: E-bloc password
    
    Returns:
        Tuple of (list of discovered bills, property_to_association mapping)
    """
    # Load scraper config
    config = load_scraper_config("e-bloc")
    if not config:
        raise Exception("E-bloc scraper config not found")
    
    scraper = WebScraper(config, save_html_dumps=False)
    
    try:
        # Login once
        logged_in = await scraper.login(username, password)
        if not logged_in:
            raise Exception("Invalid E-bloc credentials")
        
        # Get login page HTML for association matching
        login_html = await scraper.page.content()
        
        # First, parse and log ALL associations/apartments found in the login HTML
        await _log_all_ebloc_associations(login_html)
        
        # Match properties to associations
        property_to_association = {}
        property_objects = []
        property_to_contract = {}
        all_found_associations = set()  # Track all associations found (even unmatched)
        
        for prop_id, contract_id in properties:
            prop = db.get_property(prop_id)
            if not prop:
                continue
            
            property_objects.append(prop)
            property_to_contract[prop_id] = contract_id
            
            # IMPORTANT: contract_id (like "A54BB6E") is NOT the same as association_id
            # contract_id is only used later to match bills if needed
            # For matching, we ALWAYS match by property name and apartment number
            # Match by property name and address
            match_result = await match_property_to_association_with_apartment(prop, login_html)
            if match_result:
                assoc_id, apt_id = match_result
                property_to_association[prop_id] = match_result
                all_found_associations.add(assoc_id)
            else:
                # If no match found, still try to find associations by property name (without apartment refinement)
                # This ensures we sync all associations even if apartment doesn't match
                matches = await find_matching_associations(login_html, prop.name)
                if matches:
                    best_match = max(matches, key=lambda m: m.get("score", 0))
                    assoc_id = best_match["id"]
                    apartment_id = best_match.get("apartment_id")
                    property_to_association[prop_id] = (assoc_id, apartment_id)
                    all_found_associations.add(assoc_id)
                    logger.warning(f"[E-bloc] Property '{prop.name}' matched to association {assoc_id} (apartment {apartment_id}) but apartment number may not match")
        
        # Collect unique association IDs - use ALL found associations, not just matched ones
        association_ids_list = []
        for prop_id, (assoc_id, apt_id) in property_to_association.items():
            if (assoc_id, apt_id) not in association_ids_list:
                association_ids_list.append((assoc_id, apt_id))
        
        # Also add any unmatched associations that were found
        # Parse gInfoAsoc to get all association IDs
        gInfoAsoc_block_match = re.search(
            r'gInfoAsoc\s*\[\s*\d+\s*\]\s*=.*?(?=gInfoAp|gContAsoc|</script>|$)',
            login_html,
            re.DOTALL
        )
        if gInfoAsoc_block_match:
            gInfoAsoc_block = gInfoAsoc_block_match.group(0)
            asoc_indices = set(re.findall(r'gInfoAsoc\s*\[\s*(\d+)\s*\]', gInfoAsoc_block))
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
                
                if "id" in asoc_data:
                    asoc_id = asoc_data["id"]
                    # If this association wasn't matched to any property, add it with None apartment_id
                    if asoc_id not in all_found_associations:
                        association_ids_list.append((asoc_id, None))
                        logger.info(f"[E-bloc] Including unmatched association {asoc_id} for syncing")
        
        if not association_ids_list:
            raise Exception("Could not find any associations to sync")
        
        # Fetch bills for all associations at once
        scraped_bills = await scraper.get_bills(association_ids=association_ids_list)
        
        # Convert scraped bills to bill_data format
        group_bills = []
        for scraped_bill in scraped_bills:
            if not scraped_bill.bill_number or scraped_bill.amount is None:
                continue
            
            bill_status = BillStatus.OVERDUE if scraped_bill.amount > 0 else BillStatus.PAID
            due_date = scraped_bill.due_date if scraped_bill.due_date else datetime.utcnow()
            
            # Filter out special blanket contract_id "A000000" - never save it
            contract_id = scraped_bill.contract_id
            if contract_id and str(contract_id).strip().upper() == "A000000":
                contract_id = None
            
            bill_data = {
                "property_id": None,  # Will be set during distribution
                "renter_id": None,
                "bill_type": BillType.EBLOC.value,
                "description": "E-bloc",
                "amount": scraped_bill.amount or 0.0,
                "currency": "RON",  # Default for E-bloc
                "due_date": due_date.isoformat() if isinstance(due_date, datetime) else due_date,
                "iban": None,
                "bill_number": scraped_bill.bill_number,
                "extraction_pattern_id": None,
                "contract_id": contract_id,  # This is the association_id for E-bloc (or None if A000000)
                "status": bill_status.value
            }
            group_bills.append(bill_data)
        
        return group_bills, property_to_association
    
    finally:
        await scraper.close()
