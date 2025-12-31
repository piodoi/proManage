import { useState } from 'react';
import { api, Bill, Renter, ExtractionResult, Property } from '../api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Receipt, Settings, Pencil, Trash2 } from 'lucide-react';
import AddressWarningDialog from './dialogs/AddressWarningDialog';
import PatternSelectionDialog from './dialogs/PatternSelectionDialog';
import SupplierSyncDialog from './dialogs/SupplierSyncDialog';
import { useI18n } from '../lib/i18n';

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
  const { t } = useI18n();
  const [showBillForm, setShowBillForm] = useState(false);
  const [editingBill, setEditingBill] = useState<Bill | null>(null);
  const [billForm, setBillForm] = useState({
    renter_id: 'all',  // 'all' means "all/property", specific renter ID otherwise
    bill_type: 'other' as 'rent' | 'utilities' | 'ebloc' | 'other',
    amount: '',
    due_date: new Date().toISOString().split('T')[0], // Default to today
  });
  const [parsingPdf, setParsingPdf] = useState(false);
  const [pdfResult, setPdfResult] = useState<ExtractionResult | null>(null);
  const [showAddressWarning, setShowAddressWarning] = useState(false);
  const [showPatternSelection, setShowPatternSelection] = useState(false);
  const [showContractSelector, setShowContractSelector] = useState(false);
  const [multipleContracts, setMultipleContracts] = useState<Record<string, { supplier_name: string; contracts: Array<{ contract_id: string; address?: string }> }>>({});
  const [selectedContracts, setSelectedContracts] = useState<Record<string, string>>({});
  const [showSyncDialog, setShowSyncDialog] = useState(false);

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

  const createBillFromPdf = async (result: ExtractionResult, patternId?: string, supplier?: string) => {
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
      
      // Use supplier from matched pattern, or provided supplier, or fallback
      // Priority: provided supplier > matched_pattern_supplier > 'PDF'
      // Note: We don't use matched_pattern_name as it's the pattern name, not the supplier
      const billSupplier = supplier || result.matched_pattern_supplier || 'PDF';
      const extractionPatternId = patternId || result.matched_pattern_id;
      
      // Description should just be the supplier name 
      
      const billData = {
        property_id: propertyId,
        renter_id: 'all', // Default to all/property
        bill_type: extractionPatternId ? 'utilities' : 'other',
        description: billSupplier,
        amount: result.amount || 0,
        due_date: dueDate,
        iban: result.iban,
        bill_number: result.bill_number,
        extraction_pattern_id: extractionPatternId,
        contract_id: result.contract_id,
      };
      
      await api.billParser.createFromPdf(token, billData);
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

  const handleSaveBill = async () => {
    if (!token) return;
    if (!billForm.amount) {
      handleError(new Error(t('bill.amountRequired')));
      return;
    }
    try {
      const billData = {
        property_id: propertyId,
        renter_id: billForm.renter_id === 'all' ? undefined : billForm.renter_id,  // 'all' becomes undefined (all renters)
        bill_type: billForm.bill_type,
        description: t(`bill.${billForm.bill_type}`),
        amount: parseFloat(billForm.amount),
        due_date: billForm.due_date ? new Date(billForm.due_date).toISOString() : new Date().toISOString(),
      };

      if (editingBill) {
        await api.bills.update(token, editingBill.id, billData);
      } else {
        await api.bills.create(token, billData);
      }
      
      setShowBillForm(false);
      setEditingBill(null);
      setBillForm({ renter_id: 'all', bill_type: 'other', amount: '', due_date: new Date().toISOString().split('T')[0] });
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
      amount: bill.amount.toString(),
      due_date: formattedDueDate || new Date().toISOString().split('T')[0],
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
            {property && (
              <SupplierSyncDialog
                token={token}
                property={property}
                open={showSyncDialog}
                onOpenChange={setShowSyncDialog}
                onSuccess={() => {
                  if (onBillsChange) {
                    onBillsChange();
                  }
                }}
                onError={(error) => {
                  if (onError) {
                    onError(error);
                  }
                }}
              />
            )}
            <Button
              size="sm"
              onClick={() => {
                if (property) {
                  setShowSyncDialog(true);
                } else {
                  // Fallback: if property not provided, show error
                  if (onError) {
                    onError(t('errors.generic'));
                  }
                }
              }}
              className="bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600"
            >
              <Settings className="w-4 h-4 mr-1" />
              {t('bill.syncBills')}
            </Button>
            <Dialog open={showBillForm} onOpenChange={(open) => {
              setShowBillForm(open);
              if (!open) {
                setEditingBill(null);
                setBillForm({ renter_id: 'all', bill_type: 'other', amount: '', due_date: new Date().toISOString().split('T')[0] });
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
                  <div>
                    <Label className="text-slate-300">{t('common.amount')} (RON) *</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={billForm.amount}
                      onChange={(e) => setBillForm({ ...billForm, amount: e.target.value })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                      placeholder="0.00"
                      required
                    />
                  </div>
                  <div>
                    <Label className="text-slate-300">{t('bill.dueDate')}</Label>
                    <Input
                      type="date"
                      value={billForm.due_date}
                      onChange={(e) => setBillForm({ ...billForm, due_date: e.target.value })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                    />
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
              <TableHead className="text-slate-400">{t('common.amount')}</TableHead>
              <TableHead className="text-slate-400">{t('bill.dueDate')}</TableHead>
              <TableHead className="text-slate-400">{t('common.status')}</TableHead>
              <TableHead className="text-slate-400">{t('common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {propertyBills.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-slate-500 text-center py-4">
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
                    <TableCell className="text-slate-200">{bill.amount.toFixed(2)} RON</TableCell>
                    <TableCell className="text-slate-300">{new Date(bill.due_date).toLocaleDateString()}</TableCell>
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
      <Dialog open={showContractSelector} onOpenChange={setShowContractSelector}>
        <DialogContent className="bg-slate-800 border-slate-700 max-w-2xl">
          <DialogHeader>
            <DialogTitle className="text-slate-200">{t('supplier.selectContracts')}</DialogTitle>
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
