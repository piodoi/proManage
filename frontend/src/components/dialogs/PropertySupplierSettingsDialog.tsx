import { useState, useEffect } from 'react';
import { api, Property, Supplier, PropertySupplier } from '../../api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Trash2, Lock } from 'lucide-react';

type PropertySupplierSettingsDialogProps = {
  token: string | null;
  property: Property;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onError: (error: string) => void;
};

export default function PropertySupplierSettingsDialog({
  token,
  property,
  open,
  onOpenChange,
  onSuccess,
  onError,
}: PropertySupplierSettingsDialogProps) {
  const [allSuppliers, setAllSuppliers] = useState<Supplier[]>([]);
  const [propertySuppliers, setPropertySuppliers] = useState<PropertySupplier[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSupplierId, setSelectedSupplierId] = useState<string>('');
  const [editingSupplier, setEditingSupplier] = useState<PropertySupplier | null>(null);
  const [credentials, setCredentials] = useState({ username: '', password: '' });

  // Load suppliers and property suppliers when dialog opens
  useEffect(() => {
    if (open && token) {
      loadData();
    } else if (!open) {
      // Reset state when dialog closes
      setEditingSupplier(null);
      setCredentials({ username: '', password: '' });
      setSelectedSupplierId('');
    }
  }, [open, token, property.id]);

  const loadData = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [suppliers, propertySuppliersList] = await Promise.all([
        api.suppliers.list(token),
        api.suppliers.listForProperty(token, property.id),
      ]);
      setAllSuppliers(suppliers);
      setPropertySuppliers(propertySuppliersList);
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed to load suppliers');
    } finally {
      setLoading(false);
    }
  };

  const handleAddSupplier = async () => {
    if (!token || !selectedSupplierId) {
      onError('Please select a supplier');
      return;
    }

    try {
      await api.suppliers.addToProperty(token, property.id, {
        supplier_id: selectedSupplierId,
      });
      await loadData();
      setSelectedSupplierId('');
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed to add supplier');
    }
  };

  const handleSaveCredentials = async () => {
    if (!token || !editingSupplier) return;

    try {
      await api.suppliers.updateForProperty(
        token,
        property.id,
        editingSupplier.id,
        {
          username: credentials.username || undefined,
          password: credentials.password || undefined,
        }
      );
      setEditingSupplier(null);
      setCredentials({ username: '', password: '' });
      await loadData();
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed to save credentials');
    }
  };

  const handleEditCredentials = (ps: PropertySupplier) => {
    setEditingSupplier(ps);
    setCredentials({ username: '', password: '' }); // Don't show existing passwords
  };

  const handleDeleteSupplier = async (propertySupplierId: string) => {
    if (!token) return;
    if (!confirm('Are you sure you want to remove this supplier from the property?')) {
      return;
    }

    try {
      await api.suppliers.removeFromProperty(token, property.id, propertySupplierId);
      await loadData();
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed to remove supplier');
    }
  };

  const getPropertySupplierForSupplier = (supplierId: string) => {
    return propertySuppliers.find(ps => ps.supplier_id === supplierId);
  };

  const availableSuppliers = allSuppliers.filter(s => 
    !propertySuppliers.some(ps => ps.supplier_id === s.id)
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-slate-800 border-slate-700 max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-slate-100">
            Bill Suppliers - {property.name}
          </DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="text-slate-400 text-center py-8">Loading...</div>
        ) : (
          <div className="space-y-6">
            {/* Add Supplier Section */}
            <div className="space-y-2">
              <Label className="text-slate-300">Add Supplier to Property</Label>
              <div className="flex gap-2">
                <Select value={selectedSupplierId} onValueChange={setSelectedSupplierId}>
                  <SelectTrigger className="flex-1 bg-slate-700 border-slate-600 text-slate-100">
                    <SelectValue placeholder="Select a supplier" />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-700 border-slate-600">
                    {availableSuppliers.map(supplier => (
                      <SelectItem key={supplier.id} value={supplier.id}>
                        {supplier.name} {supplier.has_api && '🔌'}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  onClick={handleAddSupplier}
                  disabled={!selectedSupplierId}
                  className="bg-emerald-600 hover:bg-emerald-700"
                >
                  <Plus className="w-4 h-4 mr-1" />
                  Add
                </Button>
              </div>
            </div>

            {/* Property Suppliers List */}
            {propertySuppliers.length > 0 && (
              <div className="space-y-2">
                <Label className="text-slate-300">Configured Suppliers for this Property</Label>
                <div className="border border-slate-600 rounded-md overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-slate-700 border-slate-600">
                        <TableHead className="text-slate-200">Supplier</TableHead>
                        <TableHead className="text-slate-200">Type</TableHead>
                        <TableHead className="text-slate-200">API Support</TableHead>
                        <TableHead className="text-slate-200">Credentials</TableHead>
                        <TableHead className="text-slate-200">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {propertySuppliers.map(ps => (
                        <TableRow key={ps.id} className="bg-slate-800 border-slate-600">
                          <TableCell className="text-slate-300">{ps.supplier.name}</TableCell>
                          <TableCell className="text-slate-400 capitalize">{ps.supplier.bill_type}</TableCell>
                          <TableCell className="text-slate-400">
                            {ps.supplier.has_api ? (
                              <span className="text-emerald-400">🔌 Available</span>
                            ) : (
                              <span className="text-slate-500">Not available</span>
                            )}
                          </TableCell>
                          <TableCell className="text-slate-400">
                            {ps.has_credentials ? (
                              <span className="text-emerald-400">✓ Saved</span>
                            ) : (
                              <span className="text-slate-500">Not set</span>
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                onClick={() => handleEditCredentials(ps)}
                                className="bg-slate-700 text-blue-400 hover:bg-slate-600 hover:text-blue-300 border border-slate-600 h-8 px-3"
                              >
                                <Lock className="w-3 h-3 mr-1" />
                                {ps.has_credentials ? 'Update' : 'Set'} Credentials
                              </Button>
                              <Button
                                size="sm"
                                onClick={() => handleDeleteSupplier(ps.id)}
                                className="bg-slate-700 text-red-400 hover:bg-slate-600 hover:text-red-300 border border-slate-600 h-8 px-3"
                              >
                                <Trash2 className="w-3 h-3" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}

            {/* Credentials Dialog */}
            {editingSupplier && (
              <div className="space-y-4 border-t border-slate-600 pt-4">
                <div>
                  <Label className="text-slate-300">
                    Credentials for {editingSupplier.supplier.name}
                  </Label>
                  <p className="text-xs text-slate-500 mt-1">
                    {editingSupplier.supplier.has_api
                      ? 'Enter your login credentials to enable automatic bill fetching'
                      : 'Save credentials for manual use'}
                  </p>
                </div>
                <div className="space-y-3">
                  <div>
                    <Label className="text-slate-300">Username</Label>
                    <Input
                      value={credentials.username}
                      onChange={(e) => setCredentials({ ...credentials, username: e.target.value })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                      placeholder="Enter username"
                    />
                  </div>
                  <div>
                    <Label className="text-slate-300">Password</Label>
                    <Input
                      type="password"
                      value={credentials.password}
                      onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                      placeholder={editingSupplier.has_credentials ? 'Enter new password (leave blank to keep existing)' : 'Enter password'}
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={handleSaveCredentials}
                      className="bg-emerald-600 hover:bg-emerald-700"
                    >
                      Save Credentials
                    </Button>
                    <Button
                      onClick={() => {
                        setEditingSupplier(null);
                        setCredentials({ username: '', password: '' });
                      }}
                      variant="outline"
                      className="bg-slate-700 text-slate-300 hover:bg-slate-600"
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* All Suppliers Table */}
            <div className="space-y-2 border-t border-slate-600 pt-4">
              <Label className="text-slate-300">All Supported Suppliers</Label>
              <div className="border border-slate-600 rounded-md overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-slate-700 border-slate-600">
                      <TableHead className="text-slate-200">Supplier</TableHead>
                      <TableHead className="text-slate-200">Type</TableHead>
                      <TableHead className="text-slate-200">API Support</TableHead>
                      <TableHead className="text-slate-200">Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {allSuppliers.map(supplier => {
                      const ps = getPropertySupplierForSupplier(supplier.id);
                      return (
                        <TableRow key={supplier.id} className="bg-slate-800 border-slate-600">
                          <TableCell className="text-slate-300">{supplier.name}</TableCell>
                          <TableCell className="text-slate-400 capitalize">{supplier.bill_type}</TableCell>
                          <TableCell className="text-slate-400">
                            {supplier.has_api ? (
                              <span className="text-emerald-400">🔌 Available</span>
                            ) : (
                              <span className="text-slate-500">Not available</span>
                            )}
                          </TableCell>
                          <TableCell className="text-slate-400">
                            {ps ? (
                              <span className="text-emerald-400">✓ Added</span>
                            ) : (
                              <span className="text-slate-500">Not added</span>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

