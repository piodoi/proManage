/**
 * Currency configuration based on feature flags
 * 
 * In US_BUILD mode:
 * - Default currency is USD
 * - No RON/EUR conversions shown
 * - US locale available
 * 
 * In standard mode (non-US):
 * - Default currency is RON
 * - EUR to RON conversions shown
 * - EN/RO locales available
 */

import { featureFlags } from './featureFlags';

export type CurrencyCode = 'USD' | 'EUR' | 'RON';

interface CurrencyConfig {
  /** The primary/default currency for this build */
  defaultCurrency: CurrencyCode;
  /** The local currency (what amounts are converted TO for display) */
  localCurrency: CurrencyCode;
  /** Whether to show conversion to local currency */
  showLocalConversion: boolean;
  /** Available currencies for selection */
  availableCurrencies: CurrencyCode[];
  /** Currency symbol for the local currency */
  localCurrencySymbol: string;
}

const US_CONFIG: CurrencyConfig = {
  defaultCurrency: 'USD',
  localCurrency: 'USD',
  showLocalConversion: false,
  availableCurrencies: ['USD', 'EUR'],  // USD primary, EUR optional for international
  localCurrencySymbol: '$',
};

const STANDARD_CONFIG: CurrencyConfig = {
  defaultCurrency: 'RON',
  localCurrency: 'RON',
  showLocalConversion: true,
  availableCurrencies: ['EUR', 'USD', 'RON'],
  localCurrencySymbol: 'RON',
};

/**
 * Get the currency configuration based on the current build mode
 */
export function getCurrencyConfig(): CurrencyConfig {
  return featureFlags.usBuild ? US_CONFIG : STANDARD_CONFIG;
}

/**
 * Get the default currency for the current build
 */
export function getDefaultCurrency(): CurrencyCode {
  return getCurrencyConfig().defaultCurrency;
}

/**
 * Get the local currency for display conversions
 */
export function getLocalCurrency(): CurrencyCode {
  return getCurrencyConfig().localCurrency;
}

/**
 * Check if we should show local currency conversion
 */
export function shouldShowLocalConversion(): boolean {
  return getCurrencyConfig().showLocalConversion;
}

/**
 * Get available currencies for selection dropdowns
 */
export function getAvailableCurrencies(): CurrencyCode[] {
  return getCurrencyConfig().availableCurrencies;
}

/**
 * Check if a currency is the local currency
 */
export function isLocalCurrency(currency: string): boolean {
  return currency.toUpperCase() === getCurrencyConfig().localCurrency;
}

/**
 * Check if we're in US build mode
 */
export function isUSBuild(): boolean {
  return featureFlags.usBuild;
}
