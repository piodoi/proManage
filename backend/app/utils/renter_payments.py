from datetime import datetime
from typing import Any, Dict, List, Sequence, Tuple, cast

from app.models import Bill, BillStatus, BillType
from app.utils.currency import convert_currency


def round_money(amount: float) -> float:
    return round(float(amount or 0.0) + 1e-9, 2)


def merge_credit_amount(
    current_credit: float,
    current_currency: str,
    added_credit: float,
    added_currency: str,
    exchange_rates: Dict[str, float],
) -> Tuple[float, str]:
    target_currency = (added_currency or current_currency or "RON").upper()
    merged_credit = round_money(
        convert_currency(current_credit, current_currency, target_currency, exchange_rates)
    )
    merged_credit += round_money(convert_currency(added_credit, added_currency, target_currency, exchange_rates))
    return round_money(merged_credit), target_currency


def get_credit_currency(renter: Any) -> str:
    return ((getattr(renter, "credit_currency", None) or getattr(renter, "rent_currency", None) or "RON")).upper()


def get_bill_currency(bill: Bill) -> str:
    return ((bill.currency or "RON")).upper()


def _bill_due_sort_key(bill: Bill) -> Tuple[datetime, str]:
    due_date = bill.due_date
    if isinstance(due_date, str):
        try:
            due_date_str = cast(str, due_date)
            due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
        except ValueError:
            due_date = datetime.max
    elif not isinstance(due_date, datetime):
        due_date = datetime.combine(due_date, datetime.min.time())
    return due_date, bill.id


def get_prioritized_renter_bills(renter_id: str, bills: Sequence[Bill]) -> List[Bill]:
    eligible = [
        bill for bill in bills
        if (bill.renter_id is None or bill.renter_id == 'all' or bill.renter_id == renter_id)
        and bill.status != BillStatus.PAID
        and round_money(bill.amount) > 0
    ]

    def sort_key(bill: Bill) -> Tuple[datetime, int, int, str]:
        due_date, bill_id = _bill_due_sort_key(bill)
        renter_specific_rank = 0 if bill.renter_id == renter_id else 1
        rent_rank = 0 if bill.bill_type == BillType.RENT else 1
        return due_date, renter_specific_rank, rent_rank, bill_id

    return sorted(eligible, key=sort_key)


def recalculate_bill_status_after_payment(bill: Bill) -> BillStatus:
    if round_money(bill.amount) <= 0:
        return BillStatus.PAID

    due_date = bill.due_date
    if isinstance(due_date, str):
        try:
            due_date_str = cast(str, due_date)
            due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
        except ValueError:
            return BillStatus.PENDING
    elif not isinstance(due_date, datetime):
        due_date = datetime.combine(due_date, datetime.min.time())

    return BillStatus.OVERDUE if due_date.date() < datetime.utcnow().date() else BillStatus.PENDING


def allocate_payment_to_bills(
    renter: Any,
    bills: Sequence[Bill],
    payment_amount: float,
    payment_currency: str,
    exchange_rates: Dict[str, float],
) -> Tuple[List[Dict[str, Any]], float, str]:
    target_credit_currency = payment_currency.upper()
    existing_credit = round_money(getattr(renter, 'credit', 0.0))
    existing_credit_currency = get_credit_currency(renter)
    remaining_credit = round_money(
        convert_currency(existing_credit, existing_credit_currency, target_credit_currency, exchange_rates)
    )
    remaining_credit += round_money(convert_currency(payment_amount, payment_currency, target_credit_currency, exchange_rates))
    applied: List[Dict[str, Any]] = []

    for bill in get_prioritized_renter_bills(renter.id, bills):
        if remaining_credit <= 0:
            break

        bill_currency = get_bill_currency(bill)
        available_in_bill_currency = round_money(
            convert_currency(remaining_credit, target_credit_currency, bill_currency, exchange_rates)
        )
        if available_in_bill_currency <= 0:
            continue

        current_amount = round_money(bill.amount)
        applied_in_bill_currency = min(current_amount, available_in_bill_currency)
        if applied_in_bill_currency <= 0:
            continue

        consumed_credit = round_money(
            convert_currency(applied_in_bill_currency, bill_currency, target_credit_currency, exchange_rates)
        )
        remaining_credit = max(0.0, round_money(remaining_credit - consumed_credit))

        bill.amount = round_money(current_amount - applied_in_bill_currency)
        bill.status = recalculate_bill_status_after_payment(bill)

        applied.append({
            "bill_id": bill.id,
            "description": bill.description,
            "bill_type": bill.bill_type,
            "applied_amount": applied_in_bill_currency,
            "bill_currency": bill_currency,
            "remaining_bill_amount": round_money(bill.amount),
            "status": bill.status,
        })

    return applied, remaining_credit, target_credit_currency


def preview_credit_application(
    renter_id: str,
    credit_amount: float,
    credit_currency: str,
    bill_entries: Sequence[Dict[str, Any]],
    exchange_rates: Dict[str, float],
) -> Tuple[Dict[str, Dict[str, float]], float]:
    remaining_credit = round_money(credit_amount)
    adjustments: Dict[str, Dict[str, float]] = {}
    valid_entries = [entry for entry in bill_entries if round_money(entry.get("remaining", 0.0)) > 0 and entry.get("bill")]
    prioritized_bills = get_prioritized_renter_bills(renter_id, [entry["bill"] for entry in valid_entries])
    entries_by_bill_id = {entry["bill"].id: entry for entry in valid_entries}

    for bill in prioritized_bills:
        if remaining_credit <= 0:
            break

        entry = entries_by_bill_id.get(bill.id)
        if not entry:
            continue

        remaining = round_money(entry.get("remaining", 0.0))
        if remaining <= 0:
            continue

        bill_currency = get_bill_currency(bill)
        available_in_bill_currency = round_money(
            convert_currency(remaining_credit, credit_currency, bill_currency, exchange_rates)
        )
        credit_applied = min(remaining, available_in_bill_currency)
        if credit_applied <= 0:
            continue

        consumed_credit = round_money(
            convert_currency(credit_applied, bill_currency, credit_currency, exchange_rates)
        )
        remaining_credit = max(0.0, round_money(remaining_credit - consumed_credit))
        adjustments[bill.id] = {
            "credit_applied": credit_applied,
            "adjusted_remaining": round_money(remaining - credit_applied),
        }

    return adjustments, remaining_credit