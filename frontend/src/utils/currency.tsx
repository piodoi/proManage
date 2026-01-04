/**
 * Currency conversion and formatting utilities
 */

export type ExchangeRates = {
  EUR: number;
  USD: number;
  RON: number;
};

export const DEFAULT_EXCHANGE_RATES: ExchangeRates = {
  EUR: 1,
  USD: 1.1,
  RON: 4.97,
};

/**
 * Convert amount from one currency to another using exchange rates.
 * Exchange rates are relative to EUR (e.g., rates.RON = 4.97 means 1 EUR = 4.97 RON)
 * 
 * @param amount - Amount to convert
 * @param fromCurrency - Source currency code (EUR, USD, RON)
 * @param toCurrency - Target currency code (EUR, USD, RON)
 * @param exchangeRates - Exchange rates object
 * @returns Converted amount
 */
export function convertCurrency(
  amount: number,
  fromCurrency: string,
  toCurrency: string,
  exchangeRates: ExchangeRates
): number {
  if (fromCurrency === toCurrency) return amount;

  const fromUpper = fromCurrency.toUpperCase();
  const toUpper = toCurrency.toUpperCase();

  // Convert: fromCurrency -> EUR -> toCurrency

  // Step 1: Convert from source currency to EUR
  let amountInEUR = 0;
  if (fromUpper === 'EUR') {
    amountInEUR = amount;
  } else if (fromUpper === 'USD') {
    amountInEUR = amount / exchangeRates.USD;
  } else if (fromUpper === 'RON') {
    amountInEUR = amount / exchangeRates.RON;
  } else {
    // Unknown currency, assume RON
    amountInEUR = amount / exchangeRates.RON;
  }

  // Step 2: Convert from EUR to target currency
  if (toUpper === 'EUR') {
    return amountInEUR;
  } else if (toUpper === 'USD') {
    return amountInEUR * exchangeRates.USD;
  } else if (toUpper === 'RON') {
    return amountInEUR * exchangeRates.RON;
  } else {
    // Unknown currency, assume RON
    return amountInEUR * exchangeRates.RON;
  }
}

/**
 * Format amount as currency using Intl.NumberFormat
 * 
 * @param amount - Amount to format
 * @param currency - Currency code (EUR, USD, RON)
 * @returns Formatted currency string
 */
export function formatAmount(amount: number, currency: string = 'RON'): string {
  const currencyUpper = currency.toUpperCase();
  return new Intl.NumberFormat('ro-RO', {
    style: 'currency',
    currency: currencyUpper,
  }).format(amount);
}

/**
 * Format amount with RON conversion for EUR currency
 * 
 * @param amount - Amount to format
 * @param currency - Currency code (EUR, USD, RON)
 * @param exchangeRates - Exchange rates object
 * @param showRONConversion - Whether to show RON conversion (default: true for EUR)
 * @returns JSX element with formatted amount and optional RON conversion
 */
export function formatAmountWithConversion(
  amount: number,
  currency: string,
  exchangeRates: ExchangeRates,
  showRONConversion: boolean = false
): JSX.Element {
  const currencyUpper = currency.toUpperCase();
  const formatted = formatAmount(amount, currencyUpper);

  // If EUR and showRONConversion is true, also show RON
  if (currencyUpper === 'EUR' && showRONConversion) {
    const ronAmount = convertCurrency(amount, 'EUR', 'RON', exchangeRates);
    const ronRate = exchangeRates.RON;
    return (
      <span>
        {formatted}
        <span className="text-slate-400 text-sm ml-2">
          ({formatAmount(ronAmount, 'RON')} @ {ronRate.toFixed(4)})
        </span>
      </span>
    );
  }

  return <span>{formatted}</span>;
}

/**
 * Format amount with RON conversion for EUR currency (returns string)
 * 
 * @param amount - Amount to format
 * @param currency - Currency code (EUR, USD, RON)
 * @param exchangeRates - Exchange rates object
 * @param showRONConversion - Whether to show RON conversion (default: true for EUR)
 * @returns Formatted string with amount and optional RON conversion
 */
export function formatAmountWithConversionString(
  amount: number,
  currency: string,
  exchangeRates: ExchangeRates,
  showRONConversion: boolean = false
): string {
  const currencyUpper = currency.toUpperCase();
  const formatted = formatAmount(amount, currencyUpper);

  // If EUR and showRONConversion is true, also show RON
  if (currencyUpper === 'EUR' && showRONConversion) {
    const ronAmount = convertCurrency(amount, 'EUR', 'RON', exchangeRates);
    const ronRate = exchangeRates.RON;
    return `${formatted} (${formatAmount(ronAmount, 'RON')} @ ${ronRate.toFixed(4)})`;
  }

  return formatted;
}

