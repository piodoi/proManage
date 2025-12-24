import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../App';
import { api, ExtractionPattern, ExtractionPatternCreate, ExtractionResult } from '../api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Upload, Plus, Pencil, Trash2, FileText, ArrowLeft } from 'lucide-react';

type Props = {
  onBack: () => void;
};

export default function BillParserPage({ onBack }: Props) {
  const { token } = useAuth();
  const [patterns, setPatterns] = useState<ExtractionPattern[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [editPattern, setEditPattern] = useState<ExtractionPattern | null>(null);
  const [extractionResult, setExtractionResult] = useState<ExtractionResult | null>(null);
  const [parsing, setParsing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [formData, setFormData] = useState<ExtractionPatternCreate>({
    name: '',
    bill_type: 'utilities',
    vendor_hint: '',
    iban_pattern: '',
    amount_pattern: '',
    address_pattern: '',
    bill_number_pattern: '',
    priority: 0,
  });

  useEffect(() => {
    loadPatterns();
  }, [token]);

  const loadPatterns = async () => {
    if (!token) return;
    try {
      const data = await api.extractionPatterns.list(token);
      setPatterns(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load patterns');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !token) return;
    setParsing(true);
    setError('');
    try {
      const result = await api.billParser.parse(token, file);
      setExtractionResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to parse PDF');
    } finally {
      setParsing(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleCreate = async () => {
    if (!token) return;
    try {
      await api.extractionPatterns.create(token, formData);
      setShowCreate(false);
      resetForm();
      loadPatterns();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create pattern');
    }
  };

  const handleUpdate = async () => {
    if (!token || !editPattern) return;
    try {
      await api.extractionPatterns.update(token, editPattern.id, formData);
      setEditPattern(null);
      resetForm();
      loadPatterns();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update pattern');
    }
  };

  const handleDelete = async (id: string) => {
    if (!token || !confirm('Delete this pattern?')) return;
    try {
      await api.extractionPatterns.delete(token, id);
      loadPatterns();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete pattern');
    }
  };

  const handleToggleEnabled = async (pattern: ExtractionPattern) => {
    if (!token) return;
    try {
      await api.extractionPatterns.update(token, pattern.id, { enabled: !pattern.enabled });
      loadPatterns();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle pattern');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      bill_type: 'utilities',
      vendor_hint: '',
      iban_pattern: '',
      amount_pattern: '',
      address_pattern: '',
      bill_number_pattern: '',
      priority: 0,
    });
  };

  const openEdit = (pattern: ExtractionPattern) => {
    setEditPattern(pattern);
    setFormData({
      name: pattern.name,
      bill_type: pattern.bill_type,
      vendor_hint: pattern.vendor_hint || '',
      iban_pattern: pattern.iban_pattern || '',
      amount_pattern: pattern.amount_pattern || '',
      address_pattern: pattern.address_pattern || '',
      bill_number_pattern: pattern.bill_number_pattern || '',
      priority: pattern.priority,
    });
  };

  const PatternForm = ({ onSubmit, submitLabel }: { onSubmit: () => void; submitLabel: string }) => (
    <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
      <div>
        <Label className="text-slate-300">Name</Label>
        <Input
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          className="bg-slate-700 border-slate-600 text-slate-100"
          placeholder="e.g., Enel Electric Bill"
        />
      </div>
      <div>
        <Label className="text-slate-300">Bill Type</Label>
        <Select
          value={formData.bill_type}
          onValueChange={(v) => setFormData({ ...formData, bill_type: v as ExtractionPatternCreate['bill_type'] })}
        >
          <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-slate-700 border-slate-600">
            <SelectItem value="utilities">Utilities</SelectItem>
            <SelectItem value="rent">Rent</SelectItem>
            <SelectItem value="ebloc">E-Bloc</SelectItem>
            <SelectItem value="other">Other</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label className="text-slate-300">Vendor Hint (regex to match vendor)</Label>
        <Input
          value={formData.vendor_hint}
          onChange={(e) => setFormData({ ...formData, vendor_hint: e.target.value })}
          className="bg-slate-700 border-slate-600 text-slate-100"
          placeholder="e.g., ENEL|enel energia"
        />
      </div>
      <div>
        <Label className="text-slate-300">IBAN Pattern (regex with capture group)</Label>
        <Input
          value={formData.iban_pattern}
          onChange={(e) => setFormData({ ...formData, iban_pattern: e.target.value })}
          className="bg-slate-700 border-slate-600 text-slate-100"
          placeholder="e.g., IBAN[:\s]*([A-Z]{2}\d{2}[A-Z0-9]+)"
        />
      </div>
      <div>
        <Label className="text-slate-300">Amount Pattern (regex with capture group)</Label>
        <Input
          value={formData.amount_pattern}
          onChange={(e) => setFormData({ ...formData, amount_pattern: e.target.value })}
          className="bg-slate-700 border-slate-600 text-slate-100"
          placeholder="e.g., Total[:\s]*(\d+[.,]\d{2})"
        />
      </div>
      <div>
        <Label className="text-slate-300">Address Pattern (regex with capture group)</Label>
        <Input
          value={formData.address_pattern}
          onChange={(e) => setFormData({ ...formData, address_pattern: e.target.value })}
          className="bg-slate-700 border-slate-600 text-slate-100"
          placeholder="e.g., Loc consum[:\s]*(.+)"
        />
      </div>
      <div>
        <Label className="text-slate-300">Bill Number Pattern (regex with capture group)</Label>
        <Input
          value={formData.bill_number_pattern}
          onChange={(e) => setFormData({ ...formData, bill_number_pattern: e.target.value })}
          className="bg-slate-700 border-slate-600 text-slate-100"
          placeholder="e.g., Nr\. factura[:\s]*([A-Z0-9-]+)"
        />
      </div>
      <div>
        <Label className="text-slate-300">Priority (higher = tried first)</Label>
        <Input
          type="number"
          value={formData.priority}
          onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })}
          className="bg-slate-700 border-slate-600 text-slate-100"
        />
      </div>
      <Button onClick={onSubmit} className="w-full bg-emerald-600 hover:bg-emerald-700">
        {submitLabel}
      </Button>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button onClick={onBack} variant="ghost" className="text-slate-400 hover:text-slate-100">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        <h2 className="text-xl font-semibold text-slate-100">Bill Parser Test/Learn</h2>
      </div>

      {error && (
        <div className="p-3 bg-red-900/50 border border-red-700 rounded text-red-200">
          {error}
          <button onClick={() => setError('')} className="ml-2 text-red-400 hover:text-red-200">x</button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-slate-100 flex items-center gap-2">
              <Upload className="w-5 h-5" />
              Test PDF Extraction
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <Label className="text-slate-300">Upload PDF Bill</Label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  onChange={handleFileUpload}
                  className="block w-full text-slate-300 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-emerald-600 file:text-white hover:file:bg-emerald-700 cursor-pointer"
                />
              </div>
              {parsing && <div className="text-slate-400">Parsing PDF...</div>}
              {extractionResult && (
                <div className="space-y-3">
                  <h4 className="text-slate-200 font-medium">Extraction Results:</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="text-slate-400">IBAN:</div>
                    <div className="text-slate-200">{extractionResult.iban || '-'}</div>
                    <div className="text-slate-400">Amount:</div>
                    <div className="text-slate-200">{extractionResult.amount?.toFixed(2) || '-'}</div>
                    <div className="text-slate-400">Bill Number:</div>
                    <div className="text-slate-200">{extractionResult.bill_number || '-'}</div>
                    <div className="text-slate-400">Address:</div>
                    <div className="text-slate-200">{extractionResult.address || '-'}</div>
                    <div className="text-slate-400">Consumption Location:</div>
                    <div className="text-slate-200">{extractionResult.consumption_location || '-'}</div>
                    <div className="text-slate-400">Matched Pattern:</div>
                    <div className="text-slate-200">{extractionResult.matched_pattern_name || 'Default'}</div>
                  </div>
                  {extractionResult.all_addresses.length > 0 && (
                    <div>
                      <div className="text-slate-400 text-sm mb-1">All Addresses Found:</div>
                      <ul className="text-slate-300 text-sm list-disc list-inside">
                        {extractionResult.all_addresses.map((addr, i) => (
                          <li key={i}>{addr}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <details className="mt-4">
                    <summary className="text-slate-400 cursor-pointer hover:text-slate-200">
                      View Raw Text
                    </summary>
                    <Textarea
                      readOnly
                      value={extractionResult.raw_text || ''}
                      className="mt-2 bg-slate-700 border-slate-600 text-slate-300 h-48 text-xs font-mono"
                    />
                  </details>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-slate-100 flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Extraction Patterns
            </CardTitle>
            <Dialog open={showCreate} onOpenChange={setShowCreate}>
              <DialogTrigger asChild>
                <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700">
                  <Plus className="w-4 h-4 mr-1" />
                  Add Pattern
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-slate-800 border-slate-700 max-w-lg">
                <DialogHeader>
                  <DialogTitle className="text-slate-100">Create Extraction Pattern</DialogTitle>
                </DialogHeader>
                <PatternForm onSubmit={handleCreate} submitLabel="Create" />
              </DialogContent>
            </Dialog>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-slate-400 text-center py-4">Loading...</div>
            ) : patterns.length === 0 ? (
              <div className="text-slate-400 text-center py-4">
                No patterns yet. Add one to customize extraction.
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="border-slate-700">
                    <TableHead className="text-slate-400">Name</TableHead>
                    <TableHead className="text-slate-400">Type</TableHead>
                    <TableHead className="text-slate-400">Priority</TableHead>
                    <TableHead className="text-slate-400">Enabled</TableHead>
                    <TableHead className="text-slate-400">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {patterns.map((pattern) => (
                    <TableRow key={pattern.id} className="border-slate-700">
                      <TableCell className="text-slate-200">{pattern.name}</TableCell>
                      <TableCell className="text-slate-300">{pattern.bill_type}</TableCell>
                      <TableCell className="text-slate-300">{pattern.priority}</TableCell>
                      <TableCell>
                        <Switch
                          checked={pattern.enabled}
                          onCheckedChange={() => handleToggleEnabled(pattern)}
                        />
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => openEdit(pattern)}
                            className="text-slate-400 hover:text-slate-100 h-8 w-8 p-0"
                          >
                            <Pencil className="w-4 h-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDelete(pattern.id)}
                            className="text-red-400 hover:text-red-200 h-8 w-8 p-0"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={!!editPattern} onOpenChange={(open) => !open && setEditPattern(null)}>
        <DialogContent className="bg-slate-800 border-slate-700 max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-slate-100">Edit Extraction Pattern</DialogTitle>
          </DialogHeader>
          <PatternForm onSubmit={handleUpdate} submitLabel="Update" />
        </DialogContent>
      </Dialog>
    </div>
  );
}
