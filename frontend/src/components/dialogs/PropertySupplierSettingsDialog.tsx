import { useState, useEffect, useRef } from 'react';
import { api, Property, Supplier, PropertySupplier } from '../../api';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
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
  const [contractId, setContractId] = useState<string>('');
  const [directDebit, setDirectDebit] = useState<boolean>(false);
  const prevOpenRef = useRef(open);

  // Load suppliers and property suppliers when dialog opens
  useEffect(() => {
    if (open && token) {
      loadData();
    } else if (!open) {
      // Reset state when dialog closes
      setSelectedSupplierId('');
      setContractId('');
      setDirectDebit(false);
    }
  }, [open, token, property.id]);

  // Notify parent when dialog closes (only on transition from open to closed)
  useEffect(() => {
    // Only call onSuccess when dialog transitions from open (true) to closed (false)
    if (prevOpenRef.current === true && open === false) {
      // Use a small delay to ensure this runs after the dialog has fully closed
      const timer = setTimeout(() => {
        onSuccess();
      }, 100);
      
      // Update ref for next render
      prevOpenRef.current = open;
      
      return () => clearTimeout(timer);
    }
    // Update ref on every render to track previous value
    prevOpenRef.current = open;
  }, [open, onSuccess]);

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
      const response = await api.suppliers.addToProperty(token, property.id, {
        supplier_id: selectedSupplierId,
        contract_id: contractId.trim() || undefined,
        direct_debit: directDebit,
      });
      await loadData();
      // Reset selection but keep dialog open so user can add more
      // Don't call onSuccess() here - it will be called when dialog closes
      setSelectedSupplierId('');
      setContractId('');
      setDirectDebit(false);
      // Show message if provided (e.g., when duplicate exists with same settings)
      if ((response as any).message) {
        // Use onError to show the message, but it's informational, not an error
        onError((response as any).message);
      }
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
      // Don't call onSuccess() here - it will be called when dialog closes
    } catch (err) {
      onError(err instanceof Error ? err.message : t('supplier.removeError'));
    }
  };

  // Show all suppliers - allow adding same supplier multiple times with different contract IDs
  const availableSuppliers = allSuppliers;

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
              <p className="text-xs text-slate-500">
                {t('supplier.credentialsManagedInSettings')}
              </p>
              <div className="space-y-3">
                <div className="flex flex-col sm:flex-row gap-2 sm:gap-2 sm:items-end">
                  <div className="flex-1 min-w-0">
                    <Label className="text-slate-300 text-sm mb-1 block">{t('supplier.addSupplierToProperty')}</Label>
                    <Select value={selectedSupplierId} onValueChange={setSelectedSupplierId}>
                      <SelectTrigger className="w-full bg-slate-700 border-slate-600 text-slate-100">
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
                  </div>
                  <div className="flex-1 min-w-0">
                    <Label className="text-slate-300 text-sm mb-1 block">{t('supplier.contractId') || 'Contract ID'}</Label>
                    <Input
                      type="text"
                      value={contractId}
                      onChange={(e) => setContractId(e.target.value)}
                      placeholder={t('supplier.contractIdPlaceholder') || 'Contract ID (optional)'}
                      className="w-full bg-slate-700 border-slate-600 text-slate-100 placeholder:text-slate-500"
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <Label className="text-slate-300 text-sm mb-1 block text-center">{t('supplier.directDebit') || 'Direct debit'}</Label>
                    <div className="flex items-center justify-center h-10">
                      <Checkbox
                        id="direct-debit"
                        checked={directDebit}
                        onCheckedChange={(checked) => setDirectDebit(checked === true)}
                        className="bg-slate-700 border-slate-600"
                      />
                    </div>
                  </div>
                  <Button
                    onClick={handleAddSupplier}
                    disabled={!selectedSupplierId}
                    className="bg-emerald-600 hover:bg-emerald-700 sm:flex-shrink-0"
                  >
                    <Plus className="w-4 h-4 mr-1" />
                    {t('common.add')}
                  </Button>
                </div>
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
                        <TableHead className="text-slate-200">{t('supplier.contractId') || 'Contract ID'}</TableHead>
                        <TableHead className="text-slate-200">{t('supplier.directDebit') || 'Direct debit'}</TableHead>
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
                          <TableCell className="text-slate-400">{ps.contract_id || <span className="text-slate-500">—</span>}</TableCell>
                          <TableCell className="text-slate-400">
                            {ps.direct_debit ? (
                              <span className="text-emerald-400">✓ {t('common.yes') || 'Yes'}</span>
                            ) : (
                              <span className="text-slate-500">{t('common.no') || 'No'}</span>
                            )}
                          </TableCell>
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
