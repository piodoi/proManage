import React, { useState, useEffect, useMemo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2, CheckCircle2, AlertCircle, ChevronRight, ArrowLeft, Search, Receipt } from 'lucide-react';
import { useUtilityPayment } from '../../hooks/useUtilityPayment';
import { useI18n } from '../../lib/i18n';
import { getSuppliersAPI } from '../../api';
import {
  SupplierMatch,
  SupplierInfo,
  BalanceResponse,
  TransactionResponse,
  PaymentFieldsData,
} from '../../utils/utility';

interface BillInfo {
  description?: string;
  amount?: number;
  currency?: string;
  due_date?: string;
  bill_type?: string;
}

interface UtilityPaymentDialogProps {
  open: boolean;
  onClose: () => void;
  billBarcode?: string;
  billId?: string;
  billInfo?: BillInfo;
  onSuccess?: (transaction: TransactionResponse) => void;
  mode: 'landlord' | 'renter';
  renterToken?: string;
  detectedBarcodes?: string[];
}

const steps = ['utility.step.identify', 'utility.step.verify', 'utility.step.confirm'];

export function UtilityPaymentDialog({
  open,
  onClose,
  billBarcode,
  billId,
  billInfo,
  onSuccess,
  mode,
  renterToken,
  detectedBarcodes = [],
}: UtilityPaymentDialogProps) {
  const { t } = useI18n();
  const { matchBarcode, getBalance, payBill, loading, error, clearError } = useUtilityPayment(renterToken);

  const [activeStep, setActiveStep] = useState(0);
  const [allSuppliers, setAllSuppliers] = useState<SupplierInfo[]>([]);
  const [matchedSuppliers, setMatchedSuppliers] = useState<SupplierMatch[]>([]);
  const [selectedSupplierUid, setSelectedSupplierUid] = useState<string>('');
  const [supplierSearch, setSupplierSearch] = useState('');
  const [balance, setBalance] = useState<BalanceResponse | null>(null);
  const [transaction, setTransaction] = useState<TransactionResponse | null>(null);
  const [loadingSuppliers, setLoadingSuppliers] = useState(false);
  const [barcodeMatchFailed, setBarcodeMatchFailed] = useState(false);
  
  const [paymentFields, setPaymentFields] = useState<PaymentFieldsData>({
    barcode: billBarcode || '',
  });

  const loadSuppliers = async (candidateBarcode?: string) => {
    setLoadingSuppliers(true);
    setBarcodeMatchFailed(false);
    setMatchedSuppliers([]);
    setAllSuppliers([]);
    setSelectedSupplierUid('');
    
    try {
      const barcode = (candidateBarcode ?? paymentFields.barcode ?? '').trim();

      // First try to match barcode if available
      if (barcode) {
        try {
          const matches = await matchBarcode(barcode);
          if (matches && matches.length > 0) {
            setMatchedSuppliers(matches);
            // Auto-select if only one match
            if (matches.length === 1) {
              setSelectedSupplierUid(matches[0].uid);
            }
            setLoadingSuppliers(false);
            return;
          }
        } catch (err) {
          // Barcode match failed, will load all suppliers
          setBarcodeMatchFailed(true);
        }
      }
      
      // Load all suppliers as fallback
      const suppliers = await getSuppliersAPI(renterToken);
      setAllSuppliers(suppliers);
      
      // Try to pre-select supplier based on bill description (case-insensitive)
      if (billInfo?.description && suppliers.length > 0) {
        const descLower = billInfo.description.toLowerCase();
        const matchedByDescription = suppliers.find(s =>
          descLower.includes(s.name.toLowerCase()) ||
          s.name.toLowerCase().includes(descLower)
        );
        if (matchedByDescription) {
          setSelectedSupplierUid(matchedByDescription.uid);
          setSupplierSearch(billInfo.description);
        }
      }
    } catch (err) {
      console.error('Failed to load suppliers:', err);
    } finally {
      setLoadingSuppliers(false);
    }
  };

  useEffect(() => {
    if (!open) {
      return;
    }

    const initialBarcode = billBarcode || '';
    setActiveStep(0);
    setAllSuppliers([]);
    setMatchedSuppliers([]);
    setSelectedSupplierUid('');
    setSupplierSearch('');
    setBalance(null);
    setTransaction(null);
    setBarcodeMatchFailed(false);
    setPaymentFields({ barcode: initialBarcode });
    clearError();
    void loadSuppliers(initialBarcode);
  }, [open, billBarcode, renterToken]);

  const handleRetryBarcodeMatch = async () => {
    setActiveStep(0);
    setBalance(null);
    setTransaction(null);
    await loadSuppliers(paymentFields.barcode);
  };

  // Filter suppliers based on search
  const filteredSuppliers = useMemo(() => {
    const searchLower = supplierSearch.toLowerCase();
    
    // If we have matched suppliers from barcode, use those
    if (matchedSuppliers.length > 0) {
      return matchedSuppliers.filter(s => 
        s.name.toLowerCase().includes(searchLower)
      );
    }
    
    // Otherwise use all suppliers
    return allSuppliers.filter(s => 
      s.name.toLowerCase().includes(searchLower) ||
      (s.category && s.category.toLowerCase().includes(searchLower))
    );
  }, [matchedSuppliers, allSuppliers, supplierSearch]);

  // Get selected supplier details
  const selectedSupplier = useMemo(() => {
    if (!selectedSupplierUid) return null;
    
    // Check matched suppliers first
    const matched = matchedSuppliers.find(s => s.uid === selectedSupplierUid);
    if (matched) return matched;
    
    // Then check all suppliers
    const supplier = allSuppliers.find(s => s.uid === selectedSupplierUid);
    return supplier;
  }, [selectedSupplierUid, matchedSuppliers, allSuppliers]);

  const handleGetBalance = async () => {
    if (!selectedSupplierUid) return;

    try {
      // Get the matched supplier for module info
      const matchedSupplier = matchedSuppliers.find(s => s.uid === selectedSupplierUid);
      const productUid = matchedSupplier?.productUid || matchedSupplier?.module || selectedSupplierUid;
      
      const balanceResponse = await getBalance(
        selectedSupplierUid,
        productUid,
        paymentFields
      );
      
      setBalance(balanceResponse);
      setActiveStep(1);
    } catch (err) {
      console.error('Balance fetch failed:', err);
    }
  };

  const handlePayment = async () => {
    if (!selectedSupplierUid || !balance) return;

    try {
      const matchedSupplier = matchedSuppliers.find(s => s.uid === selectedSupplierUid);
      const productUid = matchedSupplier?.productUid || matchedSupplier?.module || selectedSupplierUid;
      
      const transactionResponse = await payBill({
        supplierUid: selectedSupplierUid,
        productUid: productUid,
        paymentFields: paymentFields,
        amount: balance.balance,
        billId,
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
    setAllSuppliers([]);
    setMatchedSuppliers([]);
    setSelectedSupplierUid('');
    setSupplierSearch('');
    setBalance(null);
    setTransaction(null);
    setBarcodeMatchFailed(false);
    setPaymentFields({ barcode: billBarcode || '' });
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

  // Bill info card
  const BillInfoCard = () => (
    <Card className="border-slate-600 bg-slate-700/50 mb-4">
      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-2">
          <Receipt className="w-4 h-4 text-slate-400" />
          <span className="text-sm font-medium text-slate-300">{t('utility.billToPay')}</span>
        </div>
        <div className="space-y-1">
          {billInfo?.description && (
            <p className="text-slate-100 font-medium">{billInfo.description}</p>
          )}
          {billInfo?.amount && (
            <p className="text-lg font-bold text-blue-400">
              {billInfo.amount.toFixed(2)} {billInfo.currency || 'RON'}
            </p>
          )}
          {billInfo?.due_date && (
            <p className="text-xs text-slate-400">
              {t('bill.dueDate')}: {new Date(billInfo.due_date).toLocaleDateString()}
            </p>
          )}
          {paymentFields.barcode && (
            <p className="text-xs text-slate-500 font-mono mt-2">
              {t('utility.barcode')}: {paymentFields.barcode}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );

  const renderStepContent = () => {
    switch (activeStep) {
      case 0:
        // Step 1: Supplier selection
        return (
          <div className="space-y-4">
            <BillInfoCard />

            <div className="space-y-3">
              <Label className="text-slate-300">{t('utility.barcode')}</Label>
              <div className="flex gap-2">
                <Input
                  value={paymentFields.barcode || ''}
                  onChange={(e) => setPaymentFields(prev => ({ ...prev, barcode: e.target.value }))}
                  placeholder={t('utility.barcodePlaceholder')}
                  className="bg-slate-700 border-slate-600 text-slate-100 font-mono"
                />
                <Button
                  type="button"
                  onClick={() => void handleRetryBarcodeMatch()}
                  disabled={loadingSuppliers || !(paymentFields.barcode || '').trim()}
                  className="bg-slate-700 hover:bg-slate-600"
                >
                  <Search className="w-4 h-4 mr-2" />
                  {t('utility.tryBarcode')}
                </Button>
              </div>
              <p className="text-xs text-slate-400">{t('utility.editBarcodeHint')}</p>
              {detectedBarcodes.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs uppercase tracking-wide text-slate-500">{t('utility.detectedBarcodes')}</p>
                  <div className="flex flex-wrap gap-2">
                    {detectedBarcodes.map((barcode) => (
                      <Button
                        key={barcode}
                        type="button"
                        variant="outline"
                        onClick={() => setPaymentFields(prev => ({ ...prev, barcode }))}
                        className="max-w-full border-slate-600 bg-slate-700 text-slate-200 hover:bg-slate-600"
                      >
                        <span className="truncate font-mono text-xs">{barcode}</span>
                      </Button>
                    ))}
                  </div>
                </div>
              )}
            </div>
            
            {barcodeMatchFailed && (
              <Alert className="bg-amber-900/30 border-amber-600">
                <AlertCircle className="h-4 w-4 text-amber-500" />
                <AlertDescription className="text-amber-200">
                  {t('utility.barcodeNoMatch')}
                </AlertDescription>
              </Alert>
            )}
            
            <div>
              <Label className="text-slate-300">{t('utility.selectSupplier')}</Label>
              
              {/* Search input */}
              <div className="relative mt-2 mb-2">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  value={supplierSearch}
                  onChange={(e) => setSupplierSearch(e.target.value)}
                  placeholder={t('utility.searchSupplier')}
                  className="bg-slate-700 border-slate-600 text-slate-100 pl-10"
                />
              </div>
              
              {loadingSuppliers ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-400" />
                  <span className="ml-2 text-slate-400">{t('utility.loadingSuppliers')}</span>
                </div>
              ) : (
                <Select value={selectedSupplierUid} onValueChange={setSelectedSupplierUid}>
                  <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                    <SelectValue placeholder={t('utility.selectSupplierPlaceholder')} />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-600 max-h-60">
                    {filteredSuppliers.length === 0 ? (
                      <div className="p-4 text-center text-slate-400">
                        {t('utility.noSuppliersFound')}
                      </div>
                    ) : (
                      filteredSuppliers.map((supplier) => (
                        <SelectItem 
                          key={supplier.uid} 
                          value={supplier.uid}
                          className="text-slate-100 focus:bg-slate-700"
                        >
                          <div className="flex flex-col">
                            <span>{supplier.name}</span>
                            {'category' in supplier && supplier.category && (
                              <span className="text-xs text-slate-400">{supplier.category}</span>
                            )}
                          </div>
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
              )}
              
              {matchedSuppliers.length > 0 && (
                <p className="text-xs text-emerald-400 mt-2">
                  ✓ {t('utility.barcodeMatched', { count: matchedSuppliers.length })}
                </p>
              )}
            </div>
          </div>
        );

      case 1:
        // Step 2: Display balance and confirm payment
        return (
          <div className="space-y-4">
            {balance && (
              <>
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
              onClick={handleGetBalance}
              disabled={loading || !selectedSupplierUid || loadingSuppliers}
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

      case 1:
        return (
          <>
            <Button 
              variant="outline" 
              onClick={() => setActiveStep(0)} 
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
