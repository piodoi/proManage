import { useState, useEffect } from 'react';
import { ExchangeRates, DEFAULT_EXCHANGE_RATES } from '../utils/currency';

/**
 * Hook to fetch and manage exchange rates
 * Fetches rates from exchangerate-api.com with EUR as base currency
 */
export function useExchangeRates() {
  const [exchangeRates, setExchangeRates] = useState<ExchangeRates>(DEFAULT_EXCHANGE_RATES);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadExchangeRates = async () => {
      try {
        const response = await fetch('https://api.exchangerate-api.com/v4/latest/EUR');
        if (!response.ok) throw new Error('Failed to fetch exchange rates');
        const data = await response.json();
        setExchangeRates({
          EUR: 1,
          USD: data.rates?.USD || DEFAULT_EXCHANGE_RATES.USD,
          RON: data.rates?.RON || DEFAULT_EXCHANGE_RATES.RON,
        });
        setError(null);
      } catch (err) {
        console.error('[useExchangeRates] Failed to load exchange rates:', err);
        setExchangeRates(DEFAULT_EXCHANGE_RATES);
        setError(err instanceof Error ? err.message : 'Failed to load exchange rates');
      } finally {
        setLoading(false);
      }
    };

    loadExchangeRates();
  }, []);

  return { exchangeRates, loading, error };
}

