"""Currency conversion utilities."""
import httpx
import asyncio
import logging
from typing import Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Default exchange rates (fallback if API fails)
DEFAULT_EXCHANGE_RATES = {
    "EUR": 1.0,
    "USD": 1.1,
    "RON": 4.97,
}

# Cache for exchange rates - shared across all requests/users
_exchange_rates_cache: Dict[str, float] | None = None
_cache_timestamp: datetime | None = None
_fetch_in_progress: bool = False
_refresh_task: asyncio.Task | None = None
CACHE_DURATION_MINUTES = 120  # Cache for 1 hour
REFRESH_INTERVAL_MINUTES = 60  # Refresh every 60 minutes to keep rates fresh


async def _fetch_rates():
    """Fetch exchange rates from API and update cache."""
    global _exchange_rates_cache, _cache_timestamp, _fetch_in_progress
    
    if _fetch_in_progress:
        return False
    
    _fetch_in_progress = True
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://api.exchangerate-api.com/v4/latest/EUR")
            if response.status_code == 200:
                data = response.json()
                rates = {
                    "EUR": 1.0,
                    "USD": data.get("rates", {}).get("USD", DEFAULT_EXCHANGE_RATES["USD"]),
                    "RON": data.get("rates", {}).get("RON", DEFAULT_EXCHANGE_RATES["RON"]),
                }
                # Update cache - this is shared across all users/requests
                _exchange_rates_cache = rates
                _cache_timestamp = datetime.now()
                logger.info(f"[ExchangeRates] Updated rates: EUR=1.0, USD={rates['USD']}, RON={rates['RON']}")
                return True
    except Exception as e:
        logger.warning(f"[ExchangeRates] Failed to fetch rates: {e}")
    finally:
        _fetch_in_progress = False
    return False


async def _exchange_rate_refresh_loop():
    """Background task that periodically refreshes exchange rates."""
    logger.info("[ExchangeRates] Background refresh task started")
    while True:
        try:
            await asyncio.sleep(REFRESH_INTERVAL_MINUTES * 60)
            logger.info("[ExchangeRates] Refreshing exchange rates...")
            await _fetch_rates()
        except asyncio.CancelledError:
            logger.info("[ExchangeRates] Background refresh task cancelled")
            break
        except Exception as e:
            logger.error(f"[ExchangeRates] Error in refresh loop: {e}")
            await asyncio.sleep(60)  # Wait a bit before retrying


async def initialize_exchange_rates():
    """Initialize exchange rates on startup. Call this during app startup."""
    global _refresh_task
    
    logger.info("[ExchangeRates] Initializing exchange rates on startup...")
    
    # Fetch rates immediately (blocking on startup to ensure rates are available)
    success = await _fetch_rates()
    if success:
        logger.info("[ExchangeRates] Successfully fetched initial exchange rates")
    else:
        logger.warning("[ExchangeRates] Failed to fetch initial rates, using defaults")
    
    # Start background refresh task to keep rates updated for all users
    if _refresh_task is None or _refresh_task.done():
        _refresh_task = asyncio.create_task(_exchange_rate_refresh_loop())
        logger.info("[ExchangeRates] Started background refresh task")


async def shutdown_exchange_rates():
    """Cleanup exchange rate background tasks. Call this during app shutdown."""
    global _refresh_task
    
    if _refresh_task and not _refresh_task.done():
        _refresh_task.cancel()
        try:
            await _refresh_task
        except asyncio.CancelledError:
            pass
        logger.info("[ExchangeRates] Background refresh task stopped")


async def get_exchange_rates() -> Dict[str, float]:
    """Get exchange rates from shared cache.
    
    Returns cached rates immediately. If cache is empty or stale,
    triggers a background refresh but still returns current/default rates.
    The background task ensures rates stay fresh for all users.
    """
    global _exchange_rates_cache, _cache_timestamp
    
    # Check if cache needs refresh
    needs_refresh = False
    if _exchange_rates_cache is None or _cache_timestamp is None:
        needs_refresh = True
    else:
        age = datetime.now() - _cache_timestamp
        if age >= timedelta(minutes=CACHE_DURATION_MINUTES):
            needs_refresh = True
    
    # If cache needs refresh and no background task is running, trigger fetch
    if needs_refresh and not _fetch_in_progress:
        asyncio.create_task(_fetch_rates())
    
    # Return cached rates immediately, or defaults if no cache exists
    if _exchange_rates_cache is not None:
        return _exchange_rates_cache.copy()
    else:
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

