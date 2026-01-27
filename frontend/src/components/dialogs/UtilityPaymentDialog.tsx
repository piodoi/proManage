import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Loader2, CheckCircle2, AlertCircle, ChevronRight, ArrowLeft } from 'lucide-react';
import { useUtilityPayment } from '../../hooks/useUtilityPayment';
import { useI18n } from '../../lib/i18n';
import {
  SupplierMatch,
  BalanceResponse,
  TransactionResponse,
  PaymentFieldsData,
} from '../../utils/utility';

interface UtilityPaymentDialogProps {
  open: boolean;
  onClose: () => void;
  billBarcode?: string;
  billInvoiceNumber?: string;
  billCustomerCode?: string;
  onSuccess?: (transaction: TransactionResponse) => void;
  mode: 'landlord' | 'renter';
}

const steps = ['utility.step.identify', 'utility.step.verify', 'utility.step.confirm'];

export function UtilityPaymentDialog({
  open,
  onClose,
  billBarcode,
  billInvoiceNumber,
  billCustomerCode,
  onSuccess,
  mode,
}: UtilityPaymentDialogProps) {
  const { t } = useI18n();
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

  // Step indicator component
  const StepIndicator = () => (
    <div className="flex items-center justify-center mb-6">
      {steps.map((step, index) => (
        <React.Fragment key={step}>
          <div className="flex flex-col items-center">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                index < activeStep
                  ? 'bg-emerald-600 text-white'
                  : index === activeStep
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-600 text-slate-400'
              }`}
            >
              {index < activeStep ? (
                <CheckCircle2 className="w-5 h-5" />
              ) : (
                index + 1
              )}
            </div>
            <span className={`text-xs mt-1 ${
              index <= activeStep ? 'text-slate-200' : 'text-slate-500'
            }`}>
              {t(step)}
            </span>
          </div>
          {index < steps.length - 1 && (
            <div
              className={`w-12 h-0.5 mx-2 ${
                index < activeStep ? 'bg-emerald-600' : 'bg-slate-600'
              }`}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );

  const renderStepContent = () => {
    switch (activeStep) {
      case 0:
        // Step 1: Barcode input and supplier matching
        return (
          <div className="space-y-4">
            <p className="text-sm text-slate-400">
              {t('utility.enterBarcode')}
            </p>
            <div>
              <Label className="text-slate-300">{t('utility.barcode')}</Label>
              <Input
                value={paymentFields.barcode || ''}
                onChange={(e) =>
                  setPaymentFields({ ...paymentFields, barcode: e.target.value })
                }
                disabled={loading}
                className="bg-slate-700 border-slate-600 text-slate-100"
                placeholder={t('utility.barcodePlaceholder')}
              />
            </div>
            <div>
              <Label className="text-slate-300">{t('utility.invoiceNumber')} ({t('common.optional')})</Label>
              <Input
                value={paymentFields.invoiceNumber || ''}
                onChange={(e) =>
                  setPaymentFields({ ...paymentFields, invoiceNumber: e.target.value })
                }
                disabled={loading}
                className="bg-slate-700 border-slate-600 text-slate-100"
              />
            </div>
            <div>
              <Label className="text-slate-300">{t('utility.customerCode')} ({t('common.optional')})</Label>
              <Input
                value={paymentFields.invoiceCustomerCode || ''}
                onChange={(e) =>
                  setPaymentFields({ ...paymentFields, invoiceCustomerCode: e.target.value })
                }
                disabled={loading}
                className="bg-slate-700 border-slate-600 text-slate-100"
              />
            </div>
          </div>
        );

      case 1:
        // Step 2: Supplier selection and balance fetch
        return (
          <div className="space-y-4">
            {suppliers.length > 1 ? (
              <>
                <p className="text-sm text-slate-400">
                  {t('utility.multipleSuppliers')}
                </p>
                {suppliers.map((supplier) => (
                  <Card
                    key={supplier.uid}
                    className={`cursor-pointer transition-colors ${
                      selectedSupplier?.uid === supplier.uid
                        ? 'border-2 border-blue-500 bg-slate-700'
                        : 'border-slate-600 bg-slate-800 hover:bg-slate-700'
                    }`}
                    onClick={() => setSelectedSupplier(supplier)}
                  >
                    <CardContent className="p-4">
                      <p className="font-medium text-slate-100">{supplier.name}</p>
                      <p className="text-sm text-slate-400">{supplier.module}</p>
                    </CardContent>
                  </Card>
                ))}
              </>
            ) : selectedSupplier ? (
              <div className="space-y-4">
                <p className="text-sm text-slate-400">
                  {t('utility.supplierIdentified')}
                </p>
                <Card className="border-emerald-500 bg-emerald-900/30">
                  <CardContent className="p-4">
                    <p className="font-medium text-lg text-slate-100">{selectedSupplier.name}</p>
                  </CardContent>
                </Card>
                {loading && (
                  <p className="text-sm text-slate-400 flex items-center">
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    {t('utility.fetchingBalance')}
                  </p>
                )}
              </div>
            ) : (
              <Alert className="bg-amber-900/30 border-amber-600">
                <AlertCircle className="h-4 w-4 text-amber-500" />
                <AlertDescription className="text-amber-200">
                  {t('utility.noSupplierMatch')}
                </AlertDescription>
              </Alert>
            )}
          </div>
        );

      case 2:
        // Step 3: Display balance and confirm payment
        return (
          <div className="space-y-4">
            {balance && (
              <>
                <p className="text-sm text-slate-400">
                  {t('utility.confirmPayment')}
                </p>
                <Card className="border-slate-600 bg-slate-800">
                  <CardContent className="p-4 space-y-4">
                    <div>
                      <p className="text-xs text-slate-500 uppercase tracking-wide">
                        {t('utility.supplier')}
                      </p>
                      <p className="text-lg font-medium text-slate-100">
                        {selectedSupplier?.name}
                      </p>
                    </div>

                    {balance.utilityData && (
                      <>
                        {balance.utilityData.customerName && (
                          <div>
                            <p className="text-xs text-slate-500 uppercase tracking-wide">
                              {t('utility.customerName')}
                            </p>
                            <p className="text-slate-200">
                              {balance.utilityData.customerName}
                            </p>
                          </div>
                        )}
                        {balance.utilityData.invoiceNumber && (
                          <div>
                            <p className="text-xs text-slate-500 uppercase tracking-wide">
                              {t('utility.invoiceNumber')}
                            </p>
                            <p className="text-slate-200">
                              {balance.utilityData.invoiceNumber}
                            </p>
                          </div>
                        )}
                        {balance.utilityData.dueDate && (
                          <div>
                            <p className="text-xs text-slate-500 uppercase tracking-wide">
                              {t('utility.dueDate')}
                            </p>
                            <p className="text-slate-200">
                              {balance.utilityData.dueDate}
                            </p>
                          </div>
                        )}
                      </>
                    )}

                    <Separator className="bg-slate-600" />

                    <div>
                      <p className="text-xs text-slate-500 uppercase tracking-wide">
                        {t('utility.amountToPay')}
                      </p>
                      <p className="text-3xl font-bold text-blue-400">
                        {balance.balance.toFixed(2)} {balance.currency}
                      </p>
                    </div>
                  </CardContent>
                </Card>

                <Alert className="bg-blue-900/30 border-blue-600">
                  <AlertCircle className="h-4 w-4 text-blue-400" />
                  <AlertDescription className="text-blue-200">
                    {mode === 'landlord'
                      ? t('utility.landlordPaymentNote')
                      : t('utility.renterPaymentNote')}
                  </AlertDescription>
                </Alert>
              </>
            )}

            {transaction && (
              <Alert className="bg-emerald-900/30 border-emerald-600">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                <AlertDescription className="text-emerald-200">
                  {t('utility.paymentSuccess')} {t('utility.transactionId')}: {transaction.transactionId}
                </AlertDescription>
              </Alert>
            )}
          </div>
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
            <Button variant="outline" onClick={handleClose} className="border-slate-600 text-slate-300 hover:bg-slate-700">
              {t('common.cancel')}
            </Button>
            <Button
              onClick={handleMatchBarcode}
              disabled={loading || !paymentFields.barcode}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <ChevronRight className="w-4 h-4 mr-2" />
              )}
              {t('utility.findSupplier')}
            </Button>
          </>
        );

      case 1:
        return (
          <>
            <Button variant="outline" onClick={() => setActiveStep(0)} className="border-slate-600 text-slate-300 hover:bg-slate-700">
              <ArrowLeft className="w-4 h-4 mr-2" />
              {t('common.back')}
            </Button>
            <Button
              onClick={() => handleGetBalance()}
              disabled={loading || !selectedSupplier}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <ChevronRight className="w-4 h-4 mr-2" />
              )}
              {t('utility.getBalance')}
            </Button>
          </>
        );

      case 2:
        return (
          <>
            <Button 
              variant="outline" 
              onClick={() => setActiveStep(1)} 
              disabled={loading || !!transaction}
              className="border-slate-600 text-slate-300 hover:bg-slate-700"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              {t('common.back')}
            </Button>
            <Button
              onClick={handlePayment}
              disabled={loading || !!transaction}
              className={transaction ? 'bg-emerald-600' : 'bg-blue-600 hover:bg-blue-700'}
            >
              {loading ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : transaction ? (
                <CheckCircle2 className="w-4 h-4 mr-2" />
              ) : null}
              {transaction ? t('utility.paid') : t('utility.confirmPaymentBtn')}
            </Button>
          </>
        );

      default:
        return null;
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && handleClose()}>
      <DialogContent className="bg-slate-800 border-slate-700 max-w-md">
        <DialogHeader>
          <DialogTitle className="text-slate-100">{t('utility.payOnline')}</DialogTitle>
          <DialogDescription className="text-slate-400">
            {t('utility.payOnlineDescription')}
          </DialogDescription>
        </DialogHeader>

        <StepIndicator />

        {error && (
          <Alert className="bg-red-900/30 border-red-600">
            <AlertCircle className="h-4 w-4 text-red-400" />
            <AlertDescription className="text-red-200">
              {error}
            </AlertDescription>
          </Alert>
        )}

        {renderStepContent()}

        <DialogFooter className="flex gap-2 mt-4">
          {getActionButtons()}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
