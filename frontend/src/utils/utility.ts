export interface PaymentLimitInfo {
  acceptsLessPrice: boolean;
  acceptsMorePrice: boolean;
  maxValue?: number;
  minValue?: number;
}

export interface PaymentField {
  name: string;
  type: string;
  required: boolean;
  label?: string;
  validation?: Record<string, any>;
}

export interface SupplierMatch {
  uid: string;
  name: string;
  module: string;
  paymentLimit: PaymentLimitInfo;
  paymentFields: PaymentField[];
}

export interface PaymentFieldsData {
  barcode?: string;
  invoiceNumber?: string;
  invoiceCustomerCode?: string;
  [key: string]: string | undefined;
}

export interface UtilityData {
  supplierName?: string;
  customerName?: string;
  invoiceNumber?: string;
  dueDate?: string;
  additionalInfo?: Record<string, any>;
}

export interface BalanceRequest {
  supplierUid: string;
  productUid: string;
  paymentFields: PaymentFieldsData;
  transactionId?: string;
  partnerTransactionId?: string;
  terminalType?: string;
}

export interface BalanceResponse {
  balance: number;
  currency: string;
  utilityData?: UtilityData;
  success: boolean;
  message?: string;
}

export interface PaymentRequest {
  supplierUid: string;
  productUid: string;
  paymentFields: PaymentFieldsData;
  amount?: number;
  transactionId?: string;
  partnerTransactionId?: string;
  terminalType?: string;
}

export type TransactionStatus = 'pending' | 'completed' | 'failed' | 'cancelled';

export interface TransactionResponse {
  transactionId: string;
  status: TransactionStatus;
  amount: number;
  currency: string;
  timestamp: string;
  receiptData?: Record<string, any>;
  success: boolean;
  message?: string;
}

export interface SupplierInfo {
  uid: string;
  name: string;
  category?: string;
  logoUrl?: string;
  description?: string;
}

export interface ProductInfo {
  uid: string;
  name: string;
  supplierUid: string;
  description?: string;
  price?: number;
}
