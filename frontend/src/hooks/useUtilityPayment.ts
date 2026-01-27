import { useState } from 'react';
import {
  SupplierMatch,
  BalanceRequest,
  BalanceResponse,
  PaymentRequest,
  TransactionResponse,
  PaymentFieldsData,
} from '../utils/utility';
import {
  matchBarcodeAPI,
  getUtilityBalanceAPI,
  payUtilityBillAPI,
} from '../api';

export interface UseUtilityPaymentReturn {
  matchBarcode: (barcode: string) => Promise<SupplierMatch[]>;
  getBalance: (
    supplierUid: string,
    productUid: string,
    fields: PaymentFieldsData
  ) => Promise<BalanceResponse>;
  payBill: (paymentData: PaymentRequest) => Promise<TransactionResponse>;
  loading: boolean;
  error: string | null;
  clearError: () => void;
}

export function useUtilityPayment(): UseUtilityPaymentReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = () => setError(null);

  const matchBarcode = async (barcode: string): Promise<SupplierMatch[]> => {
    setLoading(true);
    setError(null);
    try {
      const suppliers = await matchBarcodeAPI(barcode);
      return suppliers;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to match barcode';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const getBalance = async (
    supplierUid: string,
    productUid: string,
    fields: PaymentFieldsData
  ): Promise<BalanceResponse> => {
    setLoading(true);
    setError(null);
    try {
      const request: BalanceRequest = {
        supplierUid,
        productUid,
        paymentFields: fields,
        terminalType: 'terminal',
      };
      const balance = await getUtilityBalanceAPI(request);
      return balance;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get balance';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const payBill = async (paymentData: PaymentRequest): Promise<TransactionResponse> => {
    setLoading(true);
    setError(null);
    try {
      const transaction = await payUtilityBillAPI(paymentData);
      return transaction;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Payment failed';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return {
    matchBarcode,
    getBalance,
    payBill,
    loading,
    error,
    clearError,
  };
}
