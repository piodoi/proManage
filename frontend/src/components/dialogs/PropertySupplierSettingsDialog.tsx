import { useState, useEffect } from 'react';
import { api, Property, Supplier, PropertySupplier } from '../../api';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Trash2 } from 'lucide-react';
import { useI18n } from '../../lib/i18n';

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
  const { t } = useI18n();
  const [allSuppliers, setAllSuppliers] = useState<Supplier[]>([]);
  const [propertySuppliers, setPropertySuppliers] = useState<PropertySupplier[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSupplierId, setSelectedSupplierId] = useState<string>('');

  // Load suppliers and property suppliers when dialog opens
  useEffect(() => {
    if (open && token) {
      loadData();
    } else if (!open) {
      // Reset state when dialog closes
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
      onError(err instanceof Error ? err.message : t('supplier.loadError'));
    } finally {
      setLoading(false);
    }
  };

  const handleAddSupplier = async () => {
    if (!token || !selectedSupplierId) {
      onError(t('supplier.selectSupplier'));
      return;
    }

    try {
      await api.suppliers.addToProperty(token, property.id, {
        supplier_id: selectedSupplierId,
      });
      await loadData();
      setSelectedSupplierId('');
      onSuccess();
    } catch (err) {
      onError(err instanceof Error ? err.message : t('supplier.addError'));
    }
  };

  const handleDeleteSupplier = async (propertySupplierId: string) => {
    if (!token) return;
    if (!confirm(t('supplier.removeConfirm'))) {
      return;
    }

    try {
      await api.suppliers.removeFromProperty(token, property.id, propertySupplierId);
      await loadData();
      onSuccess();
    } catch (err) {
      onError(err instanceof Error ? err.message : t('supplier.removeError'));
    }
  };

  const availableSuppliers = allSuppliers.filter(s => 
    !propertySuppliers.some(ps => ps.supplier_id === s.id)
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-slate-800 border-slate-700 max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-slate-100">
            {t('supplier.billSuppliers')} - {property.name}
          </DialogTitle>
          <DialogDescription className="text-slate-400 sr-only">
            {t('supplier.billSuppliers')} - {property.name}
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="text-slate-400 text-center py-8">{t('common.loading')}</div>
        ) : (
          <div className="space-y-6">
            {/* Add Supplier Section */}
            <div className="space-y-2">
              <Label className="text-slate-300">{t('supplier.addSupplierToProperty')}</Label>
              <p className="text-xs text-slate-500">
                {t('supplier.credentialsManagedInSettings')}
              </p>
              <div className="flex gap-2">
                <Select value={selectedSupplierId} onValueChange={setSelectedSupplierId}>
                  <SelectTrigger className="flex-1 bg-slate-700 border-slate-600 text-slate-100">
                    <SelectValue placeholder={t('supplier.selectSupplier')} />
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
                  {t('common.add')}
                </Button>
              </div>
            </div>

            {/* Property Suppliers List */}
            {propertySuppliers.length > 0 && (
              <div className="space-y-2">
                <Label className="text-slate-300">{t('supplier.configuredSuppliers')}</Label>
                <div className="border border-slate-600 rounded-md overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-slate-700 border-slate-600">
                        <TableHead className="text-slate-200">{t('supplier.supplierName')}</TableHead>
                        <TableHead className="text-slate-200">{t('bill.billType')}</TableHead>
                        <TableHead className="text-slate-200">{t('supplier.apiSupport')}</TableHead>
                        <TableHead className="text-slate-200">{t('supplier.credentials')}</TableHead>
                        <TableHead className="text-slate-200">{t('common.actions')}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {propertySuppliers.map(ps => (
                        <TableRow key={ps.id} className="bg-slate-800 border-slate-600">
                          <TableCell className="text-slate-300">{ps.supplier.name}</TableCell>
                          <TableCell className="text-slate-400 capitalize">{t(`bill.${ps.supplier.bill_type}`)}</TableCell>
                          <TableCell className="text-slate-400">
                            {ps.supplier.has_api ? (
                              <span className="text-emerald-400">🔌 {t('supplier.available')}</span>
                            ) : (
                              <span className="text-slate-500">{t('supplier.notAvailable')}</span>
                            )}
                          </TableCell>
                          <TableCell className="text-slate-400">
                            {ps.has_credentials ? (
                              <span className="text-emerald-400">✓ {t('supplier.saved')}</span>
                            ) : (
                              <span className="text-slate-500">{t('supplier.notSet')}</span>
                            )}
                          </TableCell>
                          <TableCell>
                            <Button
                              size="sm"
                              onClick={() => handleDeleteSupplier(ps.id)}
                              className="bg-slate-700 text-red-400 hover:bg-slate-600 hover:text-red-300 border border-slate-600 h-8 px-3"
                            >
                              <Trash2 className="w-3 h-3" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
