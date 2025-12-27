import { useState } from 'react';
import { api, Bill, Renter, ExtractionResult } from '../api';
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

type PropertyBillsViewProps = {
  token: string | null;
  propertyId: string;
  renters: Renter[];
  bills: Bill[];
  onError?: (error: string) => void;
  onBillsChange?: () => void;
};

export default function PropertyBillsView({ 
  token, 
  propertyId, 
  renters, 
  bills, 
  onError,
  onBillsChange 
}: PropertyBillsViewProps) {
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

  const handleError = (err: unknown) => {
    const message = err instanceof Error ? err.message : 'An error occurred';
    if (onError) {
      onError(message);
    }
  };

  const createBillFromPdf = async (result: ExtractionResult, patternId?: string, supplier?: string) => {
    if (!token || !result) return;
    
    try {
      // Parse due date - try to convert from various formats
      let dueDate = result.due_date || new Date().toISOString().split('T')[0];
      // If it's in DD/MM/YYYY or DD.MM.YYYY format, convert to YYYY-MM-DD
      if (dueDate.includes('/') || dueDate.includes('.')) {
        const parts = dueDate.split(/[\/\.]/);
        if (parts.length === 3) {
          dueDate = `${parts[2]}-${parts[1].padStart(2, '0')}-${parts[0].padStart(2, '0')}`;
        }
      }
      
      // Use supplier from matched pattern, or provided supplier, or fallback
      const billSupplier = supplier || result.matched_pattern_supplier || result.matched_pattern_name || 'PDF';
      const extractionPatternId = patternId || result.matched_pattern_id;
      
      const billData = {
        property_id: propertyId,
        renter_id: 'all', // Default to all/property
        bill_type: extractionPatternId ? 'utilities' : 'other',
        description: result.bill_number 
          ? `Bill from ${billSupplier} - ${result.bill_number}`
          : `Bill from ${billSupplier}`,
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
      handleError(new Error('Please fill in amount'));
      return;
    }
    try {
      const billData = {
        property_id: propertyId,
        renter_id: billForm.renter_id === 'all' ? undefined : billForm.renter_id,  // 'all' becomes undefined (all renters)
        bill_type: billForm.bill_type,
        description: billForm.bill_type === 'rent' ? 'Rent' : billForm.bill_type === 'utilities' ? 'Utilities' : billForm.bill_type === 'ebloc' ? 'E-Bloc' : 'Other',
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
    if (!confirm('Are you sure you want to delete this bill?')) {
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
            Bills
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
              {parsingPdf ? 'Parsing...' : 'Upload PDF'}
            </Button>
            <Button
              size="sm"
              onClick={async () => {
                if (!token) return;
                try {
                  // TODO: Implement utilities sync endpoint
                  console.log('[Bills] Sync utilities for property:', propertyId);
                  if (onError) {
                    onError('Utilities sync functionality coming soon');
                  }
                } catch (err) {
                  handleError(err);
                }
              }}
              className="bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600"
            >
              <Settings className="w-4 h-4 mr-1" />
              Sync Utilities
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
                  Add Bill
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-slate-800 border-slate-700">
                <DialogHeader>
                  <DialogTitle className="text-slate-100">{editingBill ? 'Edit Bill' : 'Add Bill'}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label className="text-slate-300">Renter</Label>
                    <Select value={billForm.renter_id} onValueChange={(v) => setBillForm({ ...billForm, renter_id: v })}>
                      <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                        <SelectValue placeholder="Select renter" />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-700 border-slate-600">
                        <SelectItem value="all">All / Property</SelectItem>
                        {renters.map((renter) => (
                          <SelectItem key={renter.id} value={renter.id}>{renter.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-slate-500 mt-1">
                      Select "All / Property" to apply bill to all renters, or select a specific renter
                    </p>
                  </div>
                  <div>
                    <Label className="text-slate-300">Bill Type *</Label>
                    <Select value={billForm.bill_type} onValueChange={(v) => setBillForm({ ...billForm, bill_type: v as 'rent' | 'utilities' | 'ebloc' | 'other' })}>
                      <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                        <SelectValue placeholder="Select type" />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-700 border-slate-600">
                        <SelectItem value="rent">Rent</SelectItem>
                        <SelectItem value="utilities">Utilities</SelectItem>
                        <SelectItem value="ebloc">E-Bloc</SelectItem>
                        <SelectItem value="other">Other</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-slate-300">Amount (RON) *</Label>
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
                    <Label className="text-slate-300">Due Date</Label>
                    <Input
                      type="date"
                      value={billForm.due_date}
                      onChange={(e) => setBillForm({ ...billForm, due_date: e.target.value })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                    />
                  </div>
                  <Button onClick={handleSaveBill} className="w-full bg-emerald-600 hover:bg-emerald-700" disabled={!billForm.amount}>
                    {editingBill ? 'Update Bill' : 'Create Bill'}
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
              <TableHead className="text-slate-400">Renter</TableHead>
              <TableHead className="text-slate-400">Description</TableHead>
              <TableHead className="text-slate-400">Type</TableHead>
              <TableHead className="text-slate-400">Amount</TableHead>
              <TableHead className="text-slate-400">Due Date</TableHead>
              <TableHead className="text-slate-400">Status</TableHead>
              <TableHead className="text-slate-400">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {propertyBills.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-slate-500 text-center py-4">
                  No bills yet for this property
                </TableCell>
              </TableRow>
            ) : (
              propertyBills.map((bill) => {
                const renter = bill.renter_id ? renters.find(r => r.id === bill.renter_id) : null;
                return (
                  <TableRow key={bill.id} className="border-slate-700">
                    <TableCell className="text-slate-300">{renter ? renter.name : 'All / Property'}</TableCell>
                    <TableCell className="text-slate-200">{bill.description}</TableCell>
                    <TableCell className="text-slate-300">{bill.bill_type}</TableCell>
                    <TableCell className="text-slate-200">{bill.amount.toFixed(2)} RON</TableCell>
                    <TableCell className="text-slate-300">{new Date(bill.due_date).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <span className={`px-2 py-1 rounded text-xs ${
                        bill.status === 'paid' ? 'bg-green-900 text-green-200' :
                        bill.status === 'overdue' ? 'bg-red-900 text-red-200' :
                        'bg-amber-900 text-amber-200'
                      }`}>
                        {bill.status}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          onClick={() => handleEditBill(bill)}
                          className="bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600 h-6 px-2 w-6"
                          title="Edit bill"
                        >
                          <Pencil className="w-3 h-3" />
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handleDeleteBill(bill.id)}
                          className="bg-slate-700 text-red-400 hover:bg-slate-600 hover:text-red-200 border border-slate-600 h-6 px-2 w-6"
                          title="Delete bill"
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
    </>
  );
}
