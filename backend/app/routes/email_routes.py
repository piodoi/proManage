"""Email processing routes."""
from datetime import datetime
from fastapi import APIRouter, Depends
from app.models import Bill, BillType, TokenData
from app.auth import require_landlord
from app.database import db
from app.email_scraper import extract_bill_info, match_address_to_property

router = APIRouter(prefix="/email", tags=["email"])


@router.post("/process")
async def process_email(
    subject: str, body: str, sender: str, current_user: TokenData = Depends(require_landlord)
):
    info = extract_bill_info(body, subject)
    landlord_properties = db.list_properties(landlord_id=current_user.user_id)
    property_id = match_address_to_property(info.address, landlord_properties)
    if not property_id:
        return {"status": "no_match", "extracted": info, "message": "Could not match to property"}
    # Create bill for the property (applies to all renters)
    bill = Bill(
        property_id=property_id,
        renter_id=None,  # Applies to all renters in the property
        bill_type=BillType.UTILITIES,
        description=f"Bill from {sender}: {subject}",
        amount=info.amount or 0,
        due_date=datetime.utcnow(),
        iban=info.iban,
        bill_number=info.bill_number,
    )
    db.save_bill(bill)
    return {"status": "created", "bill": bill, "extracted": info}

