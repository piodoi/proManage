import { formatDateWithPreferences } from '../lib/utils';

export type SupplierProgressStatus = 'starting' | 'processing' | 'completed' | 'error';

// Re-export the main date formatting utility for backward compatibility
export const formatDate = (dateString: string, dateFormat?: string, language?: string) => {
  return formatDateWithPreferences(dateString, dateFormat, language);
};

export const formatAmount = (amount: number) => {
  return new Intl.NumberFormat('ro-RO', {
    style: 'currency',
    currency: 'RON',
  }).format(amount);
};

