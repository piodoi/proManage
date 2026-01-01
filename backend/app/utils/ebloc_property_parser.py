"""Utility for parsing e-bloc properties from login HTML"""
import re
import logging
from typing import List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class EblocProperty:
    page_id: str
    name: str
    url: str
    address: Optional[str] = None


async def parse_ebloc_properties(html: str) -> List[EblocProperty]:
    """Parse properties from JavaScript gInfoAp array in e-bloc login HTML"""
    properties = []
    
    try:
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
        
        # Extract all gInfoAp entries
        gInfoAp_block_match = re.search(
            r'gInfoAp\s*\[\s*\d+\s*\]\s*=.*?(?=gContAsoc|</script>|$)',
            html,
            re.DOTALL
        )
        
        if gInfoAp_block_match:
            gInfoAp_block = gInfoAp_block_match.group(0)
            indices = set(re.findall(r'gInfoAp\s*\[\s*(\d+)\s*\]', gInfoAp_block))
            
            for index in sorted(indices):
                # Extract all assignments for this index
                kv_pattern = re.compile(
                    r'gInfoAp\s*\[\s*' + re.escape(index) + r'\s*\]\s*\[\s*["\']([^"\']+)["\']\s*\]\s*=\s*["\']([^"\']*)["\']',
                    re.DOTALL
                )
                property_data = {}
                for kv_match in kv_pattern.finditer(gInfoAp_block):
                    key = kv_match.group(1)
                    value = kv_match.group(2)
                    property_data[key] = value
                
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
                    
                    url = f"https://www.e-bloc.ro/index.php?page={page_id}&t={int(datetime.now().timestamp())}"
                    
                    prop = EblocProperty(
                        page_id=page_id,
                        name=name,
                        url=url,
                        address=address
                    )
                    properties.append(prop)
                    logger.info(f"[E-Bloc] Parsed property: index={index}, page_id={page_id}, name='{name}', address='{address}'")
        
        logger.info(f"[E-Bloc] Parsed {len(properties)} properties from JavaScript gInfoAp array")
        
    except Exception as e:
        logger.error(f"[E-Bloc] Error parsing JavaScript properties: {e}", exc_info=True)
    
    return properties

