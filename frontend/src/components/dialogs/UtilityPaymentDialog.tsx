import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Typography,
  Box,
  CircularProgress,
  Alert,
  Stepper,
  Step,
  StepLabel,
  Paper,
  Divider,
} from '@mui/material';
import { useUtilityPayment } from '../hooks/useUtilityPayment';
import {
  SupplierMatch,
  BalanceResponse,
  TransactionResponse,
  PaymentFieldsData,
} from '../types/utility';

interface UtilityPaymentDialogProps {
  open: boolean;
  onClose: () => void;
  billBarcode?: string;
  billInvoiceNumber?: string;
  billCustomerCode?: string;
  onSuccess?: (transaction: TransactionResponse) => void;
  mode: 'landlord' | 'renter';
}

const steps = ['Identify Supplier', 'Verify Amount', 'Confirm Payment'];

export function UtilityPaymentDialog({
  open,
  onClose,
  billBarcode,
  billInvoiceNumber,
  billCustomerCode,
  onSuccess,
  mode,
}: UtilityPaymentDialogProps) {
  const { matchBarcode, getBalance, payBill, loading, error, clearError } = useUtilityPayment();

  const [activeStep, setActiveStep] = useState(0);
  const [suppliers, setSuppliers] = useState<SupplierMatch[]>([]);
  const [selectedSupplier, setSelectedSupplier] = useState<SupplierMatch | null>(null);
  const [balance, setBalance] = useState<BalanceResponse | null>(null);
  const [transaction, setTransaction] = useState<TransactionResponse | null>(null);
  
  const [paymentFields, setPaymentFields] = useState<PaymentFieldsData>({
    barcode: billBarcode || '',
    invoiceNumber: billInvoiceNumber || '',
    invoiceCustomerCode: billCustomerCode || '',
  });

  // Step 1: Match barcode on mount
  useEffect(() => {
    if (open && billBarcode && activeStep === 0) {
      handleMatchBarcode();
    }
  }, [open, billBarcode]);

  const handleMatchBarcode = async () => {
    if (!paymentFields.barcode) {
      return;
    }

    try {
      const matches = await matchBarcode(paymentFields.barcode);
      setSuppliers(matches);

      if (matches.length === 1) {
        // Auto-select if only one match
        setSelectedSupplier(matches[0]);
        setActiveStep(1);
        // Auto-fetch balance
        handleGetBalance(matches[0]);
      } else if (matches.length > 1) {
        setActiveStep(1);
      }
    } catch (err) {
      console.error('Barcode match failed:', err);
    }
  };

  const handleGetBalance = async (supplier?: SupplierMatch) => {
    const targetSupplier = supplier || selectedSupplier;
    if (!targetSupplier) return;

    try {
      // Assume first product for simplicity - adjust based on API response
      const productUid = targetSupplier.module; // or fetch products separately
      
      const balanceResponse = await getBalance(
        targetSupplier.uid,
        productUid,
        paymentFields
      );
      
      setBalance(balanceResponse);
      setActiveStep(2);
    } catch (err) {
      console.error('Balance fetch failed:', err);
    }
  };

  const handlePayment = async () => {
    if (!selectedSupplier || !balance) return;

    try {
      const productUid = selectedSupplier.module;
      
      const transactionResponse = await payBill({
        supplierUid: selectedSupplier.uid,
        productUid: productUid,
        paymentFields: paymentFields,
        amount: balance.balance,
        terminalType: 'terminal',
      });

      setTransaction(transactionResponse);

      if (transactionResponse.success && onSuccess) {
        onSuccess(transactionResponse);
      }
    } catch (err) {
      console.error('Payment failed:', err);
    }
  };

  const handleClose = () => {
    // Reset state
    setActiveStep(0);
    setSuppliers([]);
    setSelectedSupplier(null);
    setBalance(null);
    setTransaction(null);
    clearError();
    onClose();
  };

  const renderStepContent = () => {
    switch (activeStep) {
      case 0:
        // Step 1: Barcode input and supplier matching
        return (
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Enter the barcode from your utility bill to identify the supplier.
            </Typography>
            <TextField
              fullWidth
              label="Barcode"
              value={paymentFields.barcode || ''}
              onChange={(e) =>
                setPaymentFields({ ...paymentFields, barcode: e.target.value })
              }
              disabled={loading}
              sx={{ mb: 2 }}
            />
            <TextField
              fullWidth
              label="Invoice Number (optional)"
              value={paymentFields.invoiceNumber || ''}
              onChange={(e) =>
                setPaymentFields({ ...paymentFields, invoiceNumber: e.target.value })
              }
              disabled={loading}
              sx={{ mb: 2 }}
            />
            <TextField
              fullWidth
              label="Customer Code (optional)"
              value={paymentFields.invoiceCustomerCode || ''}
              onChange={(e) =>
                setPaymentFields({ ...paymentFields, invoiceCustomerCode: e.target.value })
              }
              disabled={loading}
            />
          </Box>
        );

      case 1:
        // Step 2: Supplier selection and balance fetch
        return (
          <Box>
            {suppliers.length > 1 ? (
              <>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Multiple suppliers matched. Please select one:
                </Typography>
                {suppliers.map((supplier) => (
                  <Paper
                    key={supplier.uid}
                    sx={{
                      p: 2,
                      mb: 1,
                      cursor: 'pointer',
                      border: selectedSupplier?.uid === supplier.uid ? 2 : 1,
                      borderColor: selectedSupplier?.uid === supplier.uid ? 'primary.main' : 'divider',
                    }}
                    onClick={() => setSelectedSupplier(supplier)}
                  >
                    <Typography variant="subtitle1">{supplier.name}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {supplier.module}
                    </Typography>
                  </Paper>
                ))}
              </>
            ) : selectedSupplier ? (
              <Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  Supplier identified:
                </Typography>
                <Paper sx={{ p: 2, mb: 2, bgcolor: 'success.light' }}>
                  <Typography variant="h6">{selectedSupplier.name}</Typography>
                </Paper>
                <Typography variant="body2" color="text.secondary">
                  Fetching bill amount...
                </Typography>
              </Box>
            ) : (
              <Alert severity="warning">No suppliers matched this barcode.</Alert>
            )}
          </Box>
        );

      case 2:
        // Step 3: Display balance and confirm payment
        return (
          <Box>
            {balance && (
              <>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Please confirm the payment details:
                </Typography>
                <Paper sx={{ p: 2, mb: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Supplier
                  </Typography>
                  <Typography variant="h6" sx={{ mb: 2 }}>
                    {selectedSupplier?.name}
                  </Typography>

                  {balance.utilityData && (
                    <>
                      {balance.utilityData.customerName && (
                        <>
                          <Typography variant="subtitle2" color="text.secondary">
                            Customer Name
                          </Typography>
                          <Typography variant="body1" sx={{ mb: 1 }}>
                            {balance.utilityData.customerName}
                          </Typography>
                        </>
                      )}
                      {balance.utilityData.invoiceNumber && (
                        <>
                          <Typography variant="subtitle2" color="text.secondary">
                            Invoice Number
                          </Typography>
                          <Typography variant="body1" sx={{ mb: 1 }}>
                            {balance.utilityData.invoiceNumber}
                          </Typography>
                        </>
                      )}
                      {balance.utilityData.dueDate && (
                        <>
                          <Typography variant="subtitle2" color="text.secondary">
                            Due Date
                          </Typography>
                          <Typography variant="body1" sx={{ mb: 1 }}>
                            {balance.utilityData.dueDate}
                          </Typography>
                        </>
                      )}
                    </>
                  )}

                  <Divider sx={{ my: 2 }} />

                  <Typography variant="subtitle2" color="text.secondary">
                    Amount to Pay
                  </Typography>
                  <Typography variant="h4" color="primary">
                    {balance.balance.toFixed(2)} {balance.currency}
                  </Typography>
                </Paper>

                <Alert severity="info">
                  {mode === 'landlord'
                    ? 'As landlord, this payment will be charged to your account.'
                    : 'This payment will be processed immediately.'}
                </Alert>
              </>
            )}

            {transaction && (
              <Alert severity="success" sx={{ mt: 2 }}>
                Payment successful! Transaction ID: {transaction.transactionId}
              </Alert>
            )}
          </Box>
        );

      default:
        return null;
    }
  };

  const getActionButtons = () => {
    switch (activeStep) {
      case 0:
        return (
          <>
            <Button onClick={handleClose}>Cancel</Button>
            <Button
              variant="contained"
              onClick={handleMatchBarcode}
              disabled={loading || !paymentFields.barcode}
            >
              {loading ? <CircularProgress size={24} /> : 'Find Supplier'}
            </Button>
          </>
        );

      case 1:
        return (
          <>
            <Button onClick={() => setActiveStep(0)}>Back</Button>
            <Button
              variant="contained"
              onClick={() => handleGetBalance()}
              disabled={loading || !selectedSupplier}
            >
              {loading ? <CircularProgress size={24} /> : 'Get Balance'}
            </Button>
          </>
        );

      case 2:
        return (
          <>
            <Button onClick={() => setActiveStep(1)} disabled={loading || !!transaction}>
              Back
            </Button>
            <Button
              variant="contained"
              color="primary"
              onClick={handlePayment}
              disabled={loading || !!transaction}
            >
              {loading ? <CircularProgress size={24} /> : transaction ? 'Paid' : 'Confirm Payment'}
            </Button>
          </>
        );

      default:
        return null;
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Pay Utility Bill Online</DialogTitle>
      <DialogContent>
        <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={clearError}>
            {error}
          </Alert>
        )}

        {renderStepContent()}
      </DialogContent>
      <DialogActions>{getActionButtons()}</DialogActions>
    </Dialog>
  );
}
