import { useState } from 'react';
import { api, Bill, Renter } from '../api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Receipt, Settings } from 'lucide-react';

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
  const [billForm, setBillForm] = useState({
    renter_id: '',  // Empty string means "all/property"
    description: '',
    amount: '',
  });

  const handleError = (err: unknown) => {
    const message = err instanceof Error ? err.message : 'An error occurred';
    if (onError) {
      onError(message);
    }
  };

  const handleCreateBill = async () => {
    if (!token) return;
    if (!billForm.description || !billForm.amount) {
      handleError(new Error('Please fill in description and amount'));
      return;
    }
    try {
      await api.bills.create(token, {
        property_id: propertyId,
        renter_id: billForm.renter_id || undefined,  // Empty string becomes undefined (all renters)
        bill_type: 'other',
        description: billForm.description,
        amount: parseFloat(billForm.amount),
        due_date: new Date().toISOString(), // Default to today
      });
      setShowBillForm(false);
      setBillForm({ renter_id: '', description: '', amount: '' });
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
                try {
                  // TODO: Implement PDF upload endpoint
                  console.log('[Bills] PDF upload for property:', propertyId, file.name);
                  if (onError) {
                    onError('PDF upload functionality coming soon');
                  }
                } catch (err) {
                  handleError(err);
                }
              }}
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => document.getElementById(`pdf-upload-${propertyId}`)?.click()}
              className="border-slate-600 text-slate-300"
            >
              <Receipt className="w-4 h-4 mr-1" />
              Upload PDF
            </Button>
            <Button
              variant="outline"
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
              className="border-slate-600 text-slate-300"
            >
              <Settings className="w-4 h-4 mr-1" />
              Sync Utilities
            </Button>
            <Dialog open={showBillForm} onOpenChange={setShowBillForm}>
              <DialogTrigger asChild>
                <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700">
                  <Plus className="w-4 h-4 mr-1" />
                  Add Bill
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-slate-800 border-slate-700">
                <DialogHeader>
                  <DialogTitle className="text-slate-100">Add Bill</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label className="text-slate-300">Renter</Label>
                    <Select value={billForm.renter_id} onValueChange={(v) => setBillForm({ ...billForm, renter_id: v })}>
                      <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                        <SelectValue placeholder="Select renter" />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-700 border-slate-600">
                        <SelectItem value="">All / Property</SelectItem>
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
                    <Label className="text-slate-300">What is this bill for?</Label>
                    <Input
                      value={billForm.description}
                      onChange={(e) => setBillForm({ ...billForm, description: e.target.value })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                      placeholder="e.g., Utilities, Maintenance, etc."
                    />
                  </div>
                  <div>
                    <Label className="text-slate-300">Amount (RON)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={billForm.amount}
                      onChange={(e) => setBillForm({ ...billForm, amount: e.target.value })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                      placeholder="0.00"
                    />
                  </div>
                  <Button onClick={handleCreateBill} className="w-full bg-emerald-600 hover:bg-emerald-700">
                    Create Bill
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
            </TableRow>
          </TableHeader>
          <TableBody>
            {propertyBills.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-slate-500 text-center py-4">
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
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
