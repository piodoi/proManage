"""Currency conversion utilities."""
import httpx
from typing import Dict

# Default exchange rates (fallback if API fails)
DEFAULT_EXCHANGE_RATES = {
    "EUR": 1.0,
    "USD": 1.1,
    "RON": 4.97,
}


async def get_exchange_rates() -> Dict[str, float]:
    """Fetch current exchange rates from API. Returns rates relative to EUR."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://api.exchangerate-api.com/v4/latest/EUR")
            if response.status_code == 200:
                data = response.json()
                return {
                    "EUR": 1.0,
                    "USD": data.get("rates", {}).get("USD", DEFAULT_EXCHANGE_RATES["USD"]),
                    "RON": data.get("rates", {}).get("RON", DEFAULT_EXCHANGE_RATES["RON"]),
                }
    except Exception:
        pass
    # Fallback to default rates
    return DEFAULT_EXCHANGE_RATES.copy()


def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
    exchange_rates: Dict[str, float]
) -> float:
    """Convert amount from one currency to another using exchange rates.
    
    Exchange rates should be relative to EUR (e.g., rates.RON = 4.97 means 1 EUR = 4.97 RON)
    
    Args:
        amount: Amount to convert
        from_currency: Source currency code (EUR, USD, RON)
        to_currency: Target currency code (EUR, USD, RON)
        exchange_rates: Exchange rates dictionary with EUR, USD, RON keys
    
    Returns:
        Converted amount
    """
    if from_currency == to_currency:
        return amount

    from_upper = from_currency.upper()
    to_upper = to_currency.upper()

    # Convert: fromCurrency -> EUR -> toCurrency

    # Step 1: Convert from source currency to EUR
    if from_upper == "EUR":
        amount_in_eur = amount
    elif from_upper == "USD":
        amount_in_eur = amount / exchange_rates.get("USD", DEFAULT_EXCHANGE_RATES["USD"])
    elif from_upper == "RON":
        amount_in_eur = amount / exchange_rates.get("RON", DEFAULT_EXCHANGE_RATES["RON"])
    else:
        # Unknown currency, assume RON
        amount_in_eur = amount / exchange_rates.get("RON", DEFAULT_EXCHANGE_RATES["RON"])

    # Step 2: Convert from EUR to target currency
    if to_upper == "EUR":
        return amount_in_eur
    elif to_upper == "USD":
        return amount_in_eur * exchange_rates.get("USD", DEFAULT_EXCHANGE_RATES["USD"])
    elif to_upper == "RON":
        return amount_in_eur * exchange_rates.get("RON", DEFAULT_EXCHANGE_RATES["RON"])
    else:
        # Unknown currency, assume RON
        return amount_in_eur * exchange_rates.get("RON", DEFAULT_EXCHANGE_RATES["RON"])

