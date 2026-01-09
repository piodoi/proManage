import { useState, useEffect } from 'react';
import { api, Bill, Renter, ExtractionResult, Property } from '../api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Receipt, Settings, Pencil, Trash2 } from 'lucide-react';
import AddressWarningDialog from './dialogs/AddressWarningDialog';
import PatternSelectionDialog from './dialogs/PatternSelectionDialog';
import { useI18n } from '../lib/i18n';
import { usePreferences } from '../hooks/usePreferences';
import { formatDateWithPreferences } from '../lib/utils';

type PropertyBillsViewProps = {
  token: string | null;
  propertyId: string;
  property?: Property;  // Optional property object for sync dialog
  renters: Renter[];
  bills: Bill[];
  onError?: (error: string) => void;
  onBillsChange?: () => void;
};

export default function PropertyBillsView({ 
  token, 
  propertyId,
  property,
  renters, 
  bills, 
  onError,
  onBillsChange 
}: PropertyBillsViewProps) {
  const { t, language } = useI18n();
  const { preferences } = usePreferences();
  const [showBillForm, setShowBillForm] = useState(false);
  const [editingBill, setEditingBill] = useState<Bill | null>(null);
  const [billForm, setBillForm] = useState({
    renter_id: 'all',  // 'all' means "all/property", specific renter ID otherwise
    bill_type: 'other' as 'rent' | 'utilities' | 'ebloc' | 'other',
    description: '',
    amount: '',
    currency: preferences.bill_currency || 'RON',
    due_date: new Date().toISOString().split('T')[0], // Default to today
    status: 'pending' as 'pending' | 'paid' | 'overdue',
    bill_number: '',
  });

  // Update currency when preferences change
  useEffect(() => {
    if (!editingBill && preferences.bill_currency) {
      setBillForm(prev => ({ ...prev, currency: preferences.bill_currency || 'RON' }));
    }
  }, [preferences.bill_currency, editingBill]);

  // Calculate status based on due_date for add variant
  const calculateStatus = (dueDate: string): 'pending' | 'paid' | 'overdue' => {
    if (!dueDate) return 'pending';
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const due = new Date(dueDate);
    due.setHours(0, 0, 0, 0);
    if (due < today) {
      return 'overdue';
    }
    return 'pending';
  };

  // Update status when due_date changes (only for add variant)
  useEffect(() => {
    if (!editingBill && billForm.due_date) {
      const calculatedStatus = calculateStatus(billForm.due_date);
      setBillForm(prev => ({ ...prev, status: calculatedStatus }));
    }
  }, [billForm.due_date, editingBill]);

  // Helper to get month name based on current language
  const getMonthName = (monthIndex: number): string => {
    const monthNamesEn = ['January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December'];
    const monthNamesRo = ['Ianuarie', 'Februarie', 'Martie', 'Aprilie', 'Mai', 'Iunie',
                          'Iulie', 'August', 'Septembrie', 'Octombrie', 'Noiembrie', 'Decembrie'];
    return language === 'ro' ? monthNamesRo[monthIndex] : monthNamesEn[monthIndex];
  };

  // Update description when bill type changes to rent (prefill with month and year)
  useEffect(() => {
    if (!editingBill && billForm.bill_type === 'rent') {
      const today = new Date();
      const nextMonth = new Date(today.getFullYear(), today.getMonth() + 1, 1);
      const monthName = getMonthName(nextMonth.getMonth());
      const year = nextMonth.getFullYear();
      setBillForm(prev => ({ ...prev, description: `${monthName} ${year}` }));
    } else if (!editingBill && billForm.bill_type !== 'rent' && !billForm.description) {
      // For non-rent bills, clear description if it was auto-filled
      setBillForm(prev => ({ ...prev, description: '' }));
    }
  }, [billForm.bill_type, editingBill, language]);

  // Prefill renter if only one renter exists
  useEffect(() => {
    if (!editingBill && renters.length === 1 && billForm.renter_id === 'all') {
      setBillForm(prev => ({ ...prev, renter_id: renters[0].id }));
    }
  }, [renters, editingBill, billForm.renter_id]);
  const [parsingPdf, setParsingPdf] = useState(false);
  const [pdfResult, setPdfResult] = useState<ExtractionResult | null>(null);
  const [showAddressWarning, setShowAddressWarning] = useState(false);
  const [showPatternSelection, setShowPatternSelection] = useState(false);
  const [duplicateConflict, setDuplicateConflict] = useState<{
    billNumber: string;
    existingAmount: number;
    newAmount: number;
    billData: any;
  } | null>(null);
  const [showContractSelector, setShowContractSelector] = useState(false);
  const [multipleContracts, setMultipleContracts] = useState<Record<string, { supplier_name: string; contracts: Array<{ contract_id: string; address?: string }> }>>({});
  const [selectedContracts, setSelectedContracts] = useState<Record<string, string>>({});

  const handleError = (err: unknown) => {
    console.error('[PropertyBillsView] Error:', err);
    let message = t('errors.generic');
    if (err instanceof Error) {
      message = err.message;
    } else if (typeof err === 'string') {
      message = err;
    } else if (err && typeof err === 'object' && 'detail' in err) {
      message = String((err as any).detail);
    }
    if (onError) {
      onError(message);
    }
  };

  const createBillFromPdf = async (result: ExtractionResult, patternId?: string, supplier?: string, forceUpdate?: boolean) => {
    if (!token || !result) return;
    
    try {
      // Parse due date - try to convert from various formats
      // Only use default if due_date is truly not available (null, undefined, or empty string)
      let dueDate: string;
      if (result.due_date && result.due_date.trim()) {
        dueDate = result.due_date.trim();
        // If it's in DD/MM/YYYY or DD.MM.YYYY format, convert to YYYY-MM-DD
        if (dueDate.includes('/') || dueDate.includes('.')) {
          const parts = dueDate.split(/[\/\.]/);
          if (parts.length === 3) {
            // Assume DD/MM/YYYY or DD.MM.YYYY format
            dueDate = `${parts[2]}-${parts[1].padStart(2, '0')}-${parts[0].padStart(2, '0')}`;
          }
        }
      } else {
        // Only default to today if no due_date was extracted
        dueDate = new Date().toISOString().split('T')[0];
      }
      
      // Use pattern name as description, supplier name for supplier matching
      const extractionPatternId = patternId || result.matched_pattern_id;
      
      // Send matched_pattern_name and matched_pattern_bill_type - backend will use these
      const billData: any = {
        property_id: propertyId,
        renter_id: 'all', // Default to all/property
        amount: result.amount || 0,
        currency: preferences.bill_currency || 'RON',
        due_date: dueDate,
        iban: result.iban,
        bill_number: result.bill_number,
        extraction_pattern_id: extractionPatternId,
        contract_id: result.contract_id,
        // Pass pattern info for backend to resolve description and bill_type
        matched_pattern_name: result.matched_pattern_name,
        matched_pattern_supplier: supplier || result.matched_pattern_supplier,
        matched_pattern_bill_type: (result as any).matched_pattern_bill_type,
      };
      
      if (forceUpdate) {
        billData.force_update = true;
      }
      
      const response = await api.billParser.createFromPdf(token, billData);
      
      // Handle duplicate detection response
      if (response.duplicate) {
        if (response.action === 'skipped') {
          // Same bill_number and amount - just show info message
          handleError(new Error(response.message || t('bill.duplicateSkipped')));
        } else if (response.action === 'conflict') {
          // Different amount - show conflict dialog
          setDuplicateConflict({
            billNumber: response.bill_number,
            existingAmount: response.existing_amount,
            newAmount: response.new_amount,
            billData: { ...billData, result, patternId, supplier },
          });
          return; // Don't close dialogs yet - waiting for user decision
        } else if (response.action === 'updated') {
          // Successfully updated
          setDuplicateConflict(null);
        }
      }
      
      setPdfResult(null);
      setShowAddressWarning(false);
      setShowPatternSelection(false);
      if (onBillsChange) {
        onBillsChange();
      }
    } catch (err) {
      handleError(err);
    }
  };
  
  const handleDuplicateUpdate = async () => {
    if (!duplicateConflict) return;
    const { billData } = duplicateConflict;
    await createBillFromPdf(billData.result, billData.patternId, billData.supplier, true);
    setDuplicateConflict(null);
  };
  
  const handleDuplicateSkip = () => {
    setDuplicateConflict(null);
    setPdfResult(null);
    setShowAddressWarning(false);
    setShowPatternSelection(false);
  };

  const handleSaveBill = async () => {
    if (!token) return;
    if (!billForm.amount) {
      handleError(new Error(t('bill.amountRequired')));
      return;
    }
    try {
      const billData: any = {
        bill_type: billForm.bill_type,
        description: billForm.description || t(`bill.${billForm.bill_type}`),
        amount: parseFloat(billForm.amount),
        currency: billForm.currency || preferences.bill_currency || 'RON',
        due_date: billForm.due_date ? new Date(billForm.due_date).toISOString() : new Date().toISOString(),
        status: billForm.status,
        bill_number: billForm.bill_number || undefined,
      };

      // For create, include property_id and renter_id
      // For update, include renter_id (null for all/property, or specific renter_id)
      if (editingBill) {
        // When updating, explicitly set renter_id to null if 'all', or to the renter_id if specific
        billData.renter_id = billForm.renter_id === 'all' ? null : billForm.renter_id;
        await api.bills.update(token, editingBill.id, billData);
      } else {
        // When creating, property_id is required, and renter_id can be undefined (which becomes null)
        billData.property_id = propertyId;
        billData.renter_id = billForm.renter_id === 'all' ? undefined : billForm.renter_id;
        await api.bills.create(token, billData);
      }
      
      setShowBillForm(false);
      setEditingBill(null);
      const defaultRenterId = renters.length === 1 ? renters[0].id : 'all';
      setBillForm({ renter_id: defaultRenterId, bill_type: 'other', description: '', amount: '', currency: preferences.bill_currency || 'RON', due_date: new Date().toISOString().split('T')[0], status: 'pending', bill_number: '' });
      if (onBillsChange) {
        onBillsChange();
      }
    } catch (err) {
      handleError(err);
    }
  };

  const handleEditBill = (bill: Bill) => {
    setEditingBill(bill);
    // Format due_date for date input (YYYY-MM-DD)
    let formattedDueDate = '';
    if (bill.due_date) {
      try {
        const date = new Date(bill.due_date);
        if (!isNaN(date.getTime())) {
          formattedDueDate = date.toISOString().split('T')[0];
        }
      } catch (e) {
        console.error('[PropertyBillsView] Error formatting due_date:', e);
      }
    }
    setBillForm({
      renter_id: bill.renter_id || 'all',
      bill_type: bill.bill_type,
      description: bill.description || '',
      amount: bill.amount.toString(),
      currency: bill.currency || preferences.bill_currency || 'RON',
      due_date: formattedDueDate || new Date().toISOString().split('T')[0],
      status: bill.status || 'pending',
      bill_number: bill.bill_number || '',
    });
    setShowBillForm(true);
  };

  const handleDeleteBill = async (billId: string) => {
    if (!token) return;
    if (!confirm(t('bill.confirmDelete'))) {
      return;
    }
    try {
      await api.bills.delete(token, billId);
      if (onBillsChange) {
        onBillsChange();
      }
    } catch (err) {
      handleError(err);
    }
  };

  // Filter bills for this property
  const propertyBills = bills.filter(bill => bill.property_id === propertyId);

  return (
    <>
    <Card className="bg-slate-800 border-slate-700">
      <CardHeader>
        <div className="flex justify-between items-center">
          <CardTitle className="text-slate-100 flex items-center gap-2">
            <Receipt className="w-5 h-5" />
            {t('bill.bills')}
          </CardTitle>
          <div className="flex gap-2">
            <input
              type="file"
              accept=".pdf"
              id={`pdf-upload-${propertyId}`}
              style={{ display: 'none' }}
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file || !token) return;
                setParsingPdf(true);
                try {
                  const result = await api.billParser.parse(token, file, propertyId);
                  setPdfResult(result);
                  
                  // Show supplier message if present (info message, not blocking)
                  if (result.supplier_message && onError) {
                    // Use onError as a general message handler - supplier messages are informational
                    onError(result.supplier_message);
                  }
                  
                  // Check if pattern was matched
                  if (!result.matched_pattern_id) {
                    // No pattern matched - show pattern selection dialog
                    setShowPatternSelection(true);
                  } else {
                    // Pattern matched - check if address matches
                    if (!result.address_matches && result.address_warning) {
                      setShowAddressWarning(true);
                    } else {
                      // Address matches or no address extracted, proceed to create bill
                      await createBillFromPdf(result);
                    }
                  }
                } catch (err) {
                  handleError(err);
                } finally {
                  setParsingPdf(false);
                  // Reset file input
                  const input = e.target as HTMLInputElement;
                  if (input) input.value = '';
                }
              }}
            />
            <Button
              size="sm"
              onClick={() => document.getElementById(`pdf-upload-${propertyId}`)?.click()}
              disabled={parsingPdf}
              className="bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600"
            >
              <Receipt className="w-4 h-4 mr-1" />
              {parsingPdf ? t('common.loading') : t('bill.uploadPdf')}
            </Button>
            <Dialog open={showBillForm} onOpenChange={(open) => {
              setShowBillForm(open);
              if (!open) {
                setEditingBill(null);
                const defaultRenterId = renters.length === 1 ? renters[0].id : 'all';
                setBillForm({ renter_id: defaultRenterId, bill_type: 'other', description: '', amount: '', currency: preferences.bill_currency || 'RON', due_date: new Date().toISOString().split('T')[0], status: 'pending', bill_number: '' });
              }
            }}>
              <DialogTrigger asChild>
                <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700">
                  <Plus className="w-4 h-4 mr-1" />
                  {t('bill.addBill')}
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-slate-800 border-slate-700">
                <DialogHeader>
                  <DialogTitle className="text-slate-100">{editingBill ? t('bill.editBill') : t('bill.addBill')}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label className="text-slate-300">{t('renter.renters')}</Label>
                    <Select value={billForm.renter_id} onValueChange={(v) => setBillForm({ ...billForm, renter_id: v })}>
                      <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                        <SelectValue placeholder={t('renter.renters')} />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-700 border-slate-600">
                        <SelectItem value="all">{t('bill.allRenters')}</SelectItem>
                        {renters.map((renter) => (
                          <SelectItem key={renter.id} value={renter.id}>{renter.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-slate-500 mt-1">
                      {t('bill.allRenters')}
                    </p>
                  </div>
                  <div>
                    <Label className="text-slate-300">{t('bill.billType')} *</Label>
                    <Select value={billForm.bill_type} onValueChange={(v) => setBillForm({ ...billForm, bill_type: v as 'rent' | 'utilities' | 'ebloc' | 'other' })}>
                      <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                        <SelectValue placeholder={t('bill.billType')} />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-700 border-slate-600">
                        <SelectItem value="rent">{t('bill.rent')}</SelectItem>
                        <SelectItem value="utilities">{t('bill.utilities')}</SelectItem>
                        <SelectItem value="ebloc">{t('bill.ebloc')}</SelectItem>
                        <SelectItem value="other">{t('bill.other')}</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-slate-300">{t('common.amount')} *</Label>
                      <div className="flex gap-2">
                        <Input
                          type="number"
                          step="0.01"
                          value={billForm.amount}
                          onChange={(e) => setBillForm({ ...billForm, amount: e.target.value })}
                          className="bg-slate-700 border-slate-600 text-slate-100 flex-1"
                          placeholder="0.00"
                          required
                        />
                        <Select
                          value={billForm.currency || 'RON'}
                          onValueChange={(value) => setBillForm({ ...billForm, currency: value })}
                        >
                          <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100 w-24">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-slate-700 border-slate-600">
                            <SelectItem value="EUR">EUR</SelectItem>
                            <SelectItem value="RON">RON</SelectItem>
                            <SelectItem value="USD">USD</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div>
                      <Label className="text-slate-300">{t('bill.billNumber')}</Label>
                      <Input
                        type="text"
                        value={billForm.bill_number}
                        onChange={(e) => setBillForm({ ...billForm, bill_number: e.target.value })}
                        className="bg-slate-700 border-slate-600 text-slate-100"
                        placeholder={billForm.bill_type === 'rent' ? '01' : ''}
                      />
                    </div>
                  </div>
                  <div>
                    <Label className="text-slate-300">{t('common.description')}</Label>
                    <Input
                      type="text"
                      value={billForm.description}
                      onChange={(e) => setBillForm({ ...billForm, description: e.target.value })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                      placeholder={billForm.bill_type === 'rent' ? 'January 2026' : t('common.description')}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-slate-300">{t('bill.dueDate')}</Label>
                      <Input
                        type="date"
                        value={billForm.due_date}
                        onChange={(e) => setBillForm({ ...billForm, due_date: e.target.value })}
                        className="bg-slate-700 border-slate-600 text-slate-100"
                      />
                    </div>
                    <div>
                      <Label className="text-slate-300">{t('common.status')}</Label>
                      <Select
                        value={billForm.status}
                        onValueChange={(value) => setBillForm({ ...billForm, status: value as 'pending' | 'paid' | 'overdue' })}
                        disabled={!editingBill} // Disable for add variant (calculated automatically)
                      >
                        <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-slate-700 border-slate-600">
                          <SelectItem value="pending">{t('bill.status.pending')}</SelectItem>
                          <SelectItem value="paid">{t('bill.status.paid')}</SelectItem>
                          <SelectItem value="overdue">{t('bill.status.overdue')}</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <Button onClick={handleSaveBill} className="w-full bg-emerald-600 hover:bg-emerald-700" disabled={!billForm.amount}>
                    {editingBill ? t('bill.editBill') : t('bill.addBill')}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow className="border-slate-700">
              <TableHead className="text-slate-400">{t('renter.renters')}</TableHead>
              <TableHead className="text-slate-400">{t('common.description')}</TableHead>
              <TableHead className="text-slate-400">{t('bill.billType')}</TableHead>
              <TableHead className="text-slate-400">{t('bill.billNumber')}</TableHead>
              <TableHead className="text-slate-400">{t('common.amount')}</TableHead>
              <TableHead className="text-slate-400">{t('bill.dueDate')}</TableHead>
              <TableHead className="text-slate-400">{t('common.status')}</TableHead>
              <TableHead className="text-slate-400">{t('common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {propertyBills.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-slate-500 text-center py-4">
                  {t('bill.noBills')}
                </TableCell>
              </TableRow>
            ) : (
              propertyBills.map((bill) => {
                const renter = bill.renter_id ? renters.find(r => r.id === bill.renter_id) : null;
                return (
                  <TableRow key={bill.id} className="border-slate-700">
                    <TableCell className="text-slate-300">{renter ? renter.name : t('bill.allProperty')}</TableCell>
                    <TableCell className="text-slate-200">{bill.description}</TableCell>
                    <TableCell className="text-slate-300">{t(`bill.${bill.bill_type}`)}</TableCell>
                    <TableCell className="text-slate-300">{bill.bill_number || '-'}</TableCell>
                    <TableCell className="text-slate-200">{bill.amount.toFixed(2)} {bill.currency || 'RON'}</TableCell>
                    <TableCell className="text-slate-300">{formatDateWithPreferences(bill.due_date, preferences.date_format, language)}</TableCell>
                    <TableCell>
                      <span className={`px-2 py-1 rounded text-xs ${
                        bill.status === 'paid' ? 'bg-green-900 text-green-200' :
                        bill.status === 'overdue' ? 'bg-red-900 text-red-200' :
                        'bg-amber-900 text-amber-200'
                      }`}>
                        {t(`bill.status.${bill.status}`)}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          onClick={() => handleEditBill(bill)}
                          className="bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600 h-6 px-2 w-6"
                          title={t('bill.editBill')}
                        >
                          <Pencil className="w-3 h-3" />
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handleDeleteBill(bill.id)}
                          className="bg-slate-700 text-red-400 hover:bg-slate-600 hover:text-red-200 border border-slate-600 h-6 px-2 w-6"
                          title={t('bill.deleteBill')}
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
        </CardContent>
      </Card>
      <AddressWarningDialog
        open={showAddressWarning}
        onOpenChange={setShowAddressWarning}
        pdfResult={pdfResult}
        onCancel={() => {
          setShowAddressWarning(false);
          setPdfResult(null);
        }}
        onConfirm={() => {
          if (pdfResult) {
            createBillFromPdf(pdfResult);
          }
        }}
      />
      <PatternSelectionDialog
        open={showPatternSelection}
        onOpenChange={setShowPatternSelection}
        pdfResult={pdfResult}
        token={token}
        onCancel={() => {
          setShowPatternSelection(false);
          setPdfResult(null);
        }}
        onConfirm={(patternId, supplier) => {
          if (pdfResult) {
            // Check address after pattern selection
            if (!pdfResult.address_matches && pdfResult.address_warning) {
              // Update pdfResult with selected pattern info for address warning
              const updatedResult = { ...pdfResult, matched_pattern_id: patternId, matched_pattern_supplier: supplier };
              setPdfResult(updatedResult);
              setShowPatternSelection(false);
              setShowAddressWarning(true);
            } else {
              createBillFromPdf(pdfResult, patternId, supplier);
            }
          }
        }}
      />
      {/* Duplicate Bill Conflict Dialog */}
      <Dialog open={!!duplicateConflict} onOpenChange={(open) => !open && setDuplicateConflict(null)}>
        <DialogContent className="bg-slate-800 border-slate-700">
          <DialogHeader>
            <DialogTitle className="text-slate-200">{t('bill.duplicateBillFound')}</DialogTitle>
            <DialogDescription className="text-slate-400">
              {t('bill.duplicateBillDescription', { billNumber: duplicateConflict?.billNumber })}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="bg-slate-750 border border-slate-700 rounded-lg p-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">{t('bill.existingAmount')}:</span>
                <span className="text-slate-200 font-medium">{duplicateConflict?.existingAmount?.toFixed(2)} {preferences.bill_currency || 'RON'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">{t('bill.newAmount')}:</span>
                <span className="text-emerald-400 font-medium">{duplicateConflict?.newAmount?.toFixed(2)} {preferences.bill_currency || 'RON'}</span>
              </div>
            </div>
            <p className="text-sm text-slate-400">
              {t('bill.duplicateDecision')}
            </p>
            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                onClick={handleDuplicateSkip}
                className="bg-slate-700 border-slate-600 text-slate-100 hover:bg-slate-600"
              >
                {t('bill.skipBill')}
              </Button>
              <Button
                onClick={handleDuplicateUpdate}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                {t('bill.updateBill')}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
      <Dialog open={showContractSelector} onOpenChange={setShowContractSelector}>
        <DialogContent className="bg-slate-800 border-slate-700 max-w-2xl">
          <DialogHeader>
            <DialogTitle className="text-slate-200">{t('supplier.selectContracts')}</DialogTitle>
            <DialogDescription className="text-slate-400 sr-only">
              {t('supplier.selectContracts')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <p className="text-slate-300 text-sm">
              {t('supplier.multipleContractsFound')}
            </p>
            {Object.entries(multipleContracts).map(([supplierId, info]) => (
              <div key={supplierId} className="space-y-2">
                <Label className="text-slate-300 font-medium">{info.supplier_name}</Label>
                <Select
                  value={selectedContracts[supplierId] || ''}
                  onValueChange={(value) => {
                    setSelectedContracts({ ...selectedContracts, [supplierId]: value });
                  }}
                >
                  <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-200">
                    <SelectValue placeholder={t('supplier.selectContract')} />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-700 border-slate-600">
                    {info.contracts.map((contract) => (
                      <SelectItem key={contract.contract_id} value={contract.contract_id} className="text-slate-200">
                        {contract.contract_id} {contract.address ? `- ${contract.address}` : ''}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ))}
            <div className="flex gap-2 justify-end mt-6">
              <Button
                onClick={() => {
                  setShowContractSelector(false);
                  setMultipleContracts({});
                  setSelectedContracts({});
                }}
                className="bg-slate-700 text-slate-200 hover:bg-slate-600"
              >
                {t('common.cancel')}
              </Button>
              <Button
                onClick={async () => {
                  if (!token) return;
                  // Update property suppliers with selected contract_ids
                  try {
                    const propertySuppliers = await api.suppliers.listForProperty(token, propertyId);
                    for (const [supplierId, contractId] of Object.entries(selectedContracts)) {
                      const propertySupplier = propertySuppliers.find(ps => ps.supplier_id === supplierId);
                      if (propertySupplier) {
                        await api.suppliers.updateForProperty(token, propertyId, propertySupplier.id, {
                          contract_id: contractId
                        });
                      }
                    }
                    setShowContractSelector(false);
                    setMultipleContracts({});
                    setSelectedContracts({});
                    if (onBillsChange) {
                      onBillsChange();
                    }
                    if (onError) {
                      onError(t('supplier.contractSelectionsSaved'));
                    }
                  } catch (err) {
                    handleError(err);
                  }
                }}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                {t('common.save')}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
