/**
 * IBAN validation utility
 * Implements the ISO 13616 standard for IBAN validation using mod-97 algorithm
 */

/**
 * Validates an IBAN using the mod-97 check digit algorithm
 * @param iban - The IBAN string to validate (spaces will be removed)
 * @returns true if the IBAN is valid, false otherwise
 */
export function validateIban(iban: string): boolean {
  if (!iban) {
    return false;
  }

  // Remove spaces and convert to uppercase
  const cleaned = iban.replace(/\s+/g, '').toUpperCase();

  // Basic format check: must start with 2 letters, then 2 digits, then alphanumeric
  if (!/^[A-Z]{2}\d{2}[A-Z0-9]+$/.test(cleaned)) {
    return false;
  }

  // IBAN length must be between 15 and 34 characters
  if (cleaned.length < 15 || cleaned.length > 34) {
    return false;
  }

  // Move first 4 characters (country code and check digits) to the end
  const rearranged = cleaned.slice(4) + cleaned.slice(0, 4);

  // Convert letters to numbers (A=10, B=11, ..., Z=35)
  const numericString = rearranged
    .split('')
    .map(char => {
      if (char >= '0' && char <= '9') {
        return char;
      } else {
        return (char.charCodeAt(0) - 55).toString();
      }
    })
    .join('');

  // Calculate mod-97
  // Process in chunks to handle large numbers in JavaScript
  let remainder = 0;
  for (let i = 0; i < numericString.length; i++) {
    remainder = (remainder * 10 + parseInt(numericString[i])) % 97;
  }

  // Valid IBAN should have remainder of 1
  return remainder === 1;
}

/**
 * Formats an IBAN by adding spaces every 4 characters for better readability
 * @param iban - The IBAN string to format
 * @returns Formatted IBAN with spaces
 */
export function formatIban(iban: string): string {
  if (!iban) {
    return '';
  }

  const cleaned = iban.replace(/\s+/g, '').toUpperCase();
  return cleaned.replace(/(.{4})/g, '$1 ').trim();
}

