import { useState, useEffect } from 'react';
import { api, Supplier, UserSupplierCredential } from '../api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Lock, Pencil, Trash2 } from 'lucide-react';
import { useI18n } from '../lib/i18n';

type SupplierCredentialsSettingsProps = {
  token: string | null;
  onError?: (error: string) => void;
};

export default function SupplierCredentialsSettings({ token, onError }: SupplierCredentialsSettingsProps) {
  const { t } = useI18n();
  const [assignedSuppliers, setAssignedSuppliers] = useState<Supplier[]>([]);
  const [credentials, setCredentials] = useState<UserSupplierCredential[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editingCredential, setEditingCredential] = useState<UserSupplierCredential | null>(null);
  const [formData, setFormData] = useState<Record<string, { username: string; password: string }>>({});

  useEffect(() => {
    if (token) {
      loadData();
    }
  }, [token]);

  const loadData = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [suppliers, credentialList] = await Promise.all([
        api.suppliers.list(token, true), // Only get assigned suppliers
        api.supplierCredentials.list(token),
      ]);
      setAssignedSuppliers(suppliers);
      setCredentials(credentialList);
    } catch (err) {
      if (onError) {
        onError(err instanceof Error ? err.message : t('supplier.loadError'));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (credential: UserSupplierCredential) => {
    setEditingCredential(credential);
    // Initialize form data for this specific credential (don't show existing passwords)
    setFormData(prev => ({
      ...prev,
      [credential.id]: { username: '', password: '' }
    }));
  };

  const handleCancel = () => {
    if (editingCredential) {
      // Remove form data for the credential being cancelled
      setFormData(prev => {
        const updated = { ...prev };
        delete updated[editingCredential.id];
        return updated;
      });
    }
    setEditingCredential(null);
  };

  const handleSaveWithCredential = async (credential: UserSupplierCredential) => {
    if (!token) {
      console.error('[SupplierCredentials] Save failed: missing token');
      return;
    }

    if (!credential || !credential.id) {
      console.error('[SupplierCredentials] Save failed: invalid credential', credential);
      if (onError) {
        onError('Invalid credential ID');
      }
      return;
    }

    setSaving(true);
    const credentialFormData = formData[credential.id] || { username: '', password: '' };

    // Build update payload - only include fields that have values
    const updateData: { username?: string; password?: string } = {};
    if (credentialFormData.username && credentialFormData.username.trim()) {
      updateData.username = credentialFormData.username.trim();
    }
    if (credentialFormData.password && credentialFormData.password.trim()) {
      updateData.password = credentialFormData.password.trim();
    }

    // If both fields are empty, show error
    if (!updateData.username && !updateData.password) {
      setSaving(false);
      if (onError) {
        onError('Please enter at least a username or password');
      }
      return;
    }

    try {
      await api.supplierCredentials.update(token, credential.id, updateData);
      
      // Remove form data for this credential after successful save
      setFormData(prev => {
        const updated = { ...prev };
        delete updated[credential.id];
        return updated;
      });
      setEditingCredential(null);
      await loadData();
      if (onError) {
        onError('');
      }
    } catch (err) {
      console.error('[SupplierCredentials] Save error', err);
      if (onError) {
        onError(err instanceof Error ? err.message : t('supplier.saveCredentialsError'));
      }
    } finally {
      setSaving(false);
    }
  };

  const handleCreate = async (supplierId: string) => {
    if (!token) {
      console.error('[SupplierCredentials] Create failed: missing token');
      return;
    }
    
    if (!editingCredential) {
      console.error('[SupplierCredentials] Create failed: missing editingCredential');
      return;
    }

    setSaving(true);
    // Use supplier_id as key for new credentials being created
    const supplierFormData = formData[supplierId] || formData[editingCredential.supplier_id] || { username: '', password: '' };

    // Build create payload
    const createData: { supplier_id: string; username?: string; password?: string } = {
      supplier_id: supplierId,
    };
    
    if (supplierFormData.username && supplierFormData.username.trim()) {
      createData.username = supplierFormData.username.trim();
    }
    if (supplierFormData.password && supplierFormData.password.trim()) {
      createData.password = supplierFormData.password.trim();
    }

    // If both fields are empty, show error
    if (!createData.username && !createData.password) {
      setSaving(false);
      if (onError) {
        onError('Please enter at least a username or password');
      }
      return;
    }

    try {
      await api.supplierCredentials.create(token, createData);
      
      // Remove form data for this supplier after successful create
      setFormData(prev => {
        const updated = { ...prev };
        delete updated[supplierId];
        if (editingCredential.supplier_id) {
          delete updated[editingCredential.supplier_id];
        }
        return updated;
      });
      setEditingCredential(null);
      await loadData();
      if (onError) {
        onError('');
      }
    } catch (err) {
      console.error('[SupplierCredentials] Create error', err);
      if (onError) {
        onError(err instanceof Error ? err.message : t('supplier.saveCredentialsError'));
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (credentialId: string) => {
    if (!token) return;
    if (!confirm(t('supplier.deleteCredentialConfirm'))) {
      return;
    }

    try {
      await api.supplierCredentials.delete(token, credentialId);
      await loadData();
      if (onError) {
        onError('');
      }
    } catch (err) {
      if (onError) {
        onError(err instanceof Error ? err.message : t('supplier.deleteCredentialError'));
      }
    }
  };

  const getCredentialForSupplier = (supplierId: string) => {
    return credentials.find(c => c.supplier_id === supplierId);
  };

  if (loading) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="pt-6">
          <div className="text-slate-400 text-center py-8">{t('common.loading')}</div>
        </CardContent>
      </Card>
    );
  }

  if (assignedSuppliers.length === 0) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100 flex items-center gap-2">
            <Lock className="w-5 h-5" />
            {t('supplier.manageCredentials')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-slate-400 text-center py-8">
            {t('supplier.noAssignedSuppliers')}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-slate-800 border-slate-700">
      <CardHeader>
        <CardTitle className="text-slate-100 flex items-center gap-2">
          <Lock className="w-5 h-5" />
          {t('supplier.manageCredentials')}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="border border-slate-600 rounded-md overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-700 border-slate-600">
                <TableHead className="text-slate-200">{t('common.actions')}</TableHead>
                <TableHead className="text-slate-200">{t('supplier.supplierName')}</TableHead>
                <TableHead className="text-slate-200">{t('bill.billType')}</TableHead>
                <TableHead className="text-slate-200">{t('supplier.apiSupport')}</TableHead>
                <TableHead className="text-slate-200">{t('supplier.credentials')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {assignedSuppliers.map(supplier => {
                const credential = getCredentialForSupplier(supplier.id);
                // Only consider editing if both exist and IDs match (explicit check to avoid undefined === undefined)
                const isEditing = !!(editingCredential && credential && editingCredential.id && credential.id && editingCredential.id === credential.id);
                // Only consider creating if editingCredential exists, matches supplier, and no credential exists
                const isCreating = !!(editingCredential && !credential && editingCredential.supplier_id === supplier.id);

                return (
                  <TableRow key={supplier.id} className="bg-slate-800 border-slate-600">
                    {/* Actions Column */}
                    <TableCell>
                      {isEditing || isCreating ? (
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              
                              // Re-compute state inside handler to avoid stale closures
                              const currentCredential = getCredentialForSupplier(supplier.id);
                              const actuallyEditing = !!(editingCredential && currentCredential && editingCredential.id && currentCredential.id && editingCredential.id === currentCredential.id);
                              const actuallyCreating = !!(editingCredential && !currentCredential && editingCredential.supplier_id === supplier.id);
                              
                              if (actuallyEditing && currentCredential && currentCredential.id) {
                                // Pass the credential directly to avoid stale closure
                                handleSaveWithCredential(currentCredential);
                              } else if (actuallyCreating && editingCredential) {
                                handleCreate(supplier.id);
                              } else {
                                console.error('[SupplierCredentials] Invalid save state', { 
                                  isEditing, 
                                  actuallyEditing,
                                  isCreating, 
                                  actuallyCreating,
                                  currentCredential, 
                                  editingCredential, 
                                  supplierId: supplier.id 
                                });
                                if (onError) {
                                  onError('Cannot save: Invalid state. Please refresh and try again.');
                                }
                              }
                            }}
                            disabled={saving}
                            className="bg-emerald-600 hover:bg-emerald-700 h-7 text-xs disabled:opacity-50"
                          >
                            {saving ? t('common.saving') || 'Saving...' : t('common.save')}
                          </Button>
                          <Button
                            size="sm"
                            onClick={handleCancel}
                            variant="outline"
                            className="bg-slate-600 text-slate-300 hover:bg-slate-500 h-7 text-xs"
                          >
                            {t('common.cancel')}
                          </Button>
                        </div>
                      ) : credential ? (
                        <Button
                          size="sm"
                          onClick={() => handleEdit(credential)}
                          className="bg-slate-700 text-blue-400 hover:bg-slate-600 hover:text-blue-300 border border-slate-600 h-8"
                        >
                          <Pencil className="w-3 h-3 mr-1" />
                          {t('common.edit')}
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          onClick={() => {
                            const newCredential = { id: '', supplier, user_id: '', supplier_id: supplier.id, has_credentials: false, created_at: '', updated_at: '' };
                            setEditingCredential(newCredential);
                            // Initialize form data for this supplier
                            setFormData(prev => ({
                              ...prev,
                              [supplier.id]: { username: '', password: '' }
                            }));
                          }}
                          className="bg-slate-700 text-blue-400 hover:bg-slate-600 hover:text-blue-300 border border-slate-600 h-8"
                        >
                          <Lock className="w-3 h-3 mr-1" />
                          {t('supplier.setCredentials')}
                        </Button>
                      )}
                    </TableCell>

                    {/* Supplier Name */}
                    <TableCell className="text-slate-300 font-medium">{supplier.name}</TableCell>

                    {/* Bill Type */}
                    <TableCell className="text-slate-400 capitalize">{t(`bill.${supplier.bill_type}`)}</TableCell>

                    {/* Has API */}
                    <TableCell className="text-slate-400">
                      {supplier.has_api ? (
                        <span className="text-emerald-400">🔌 {t('supplier.available')}</span>
                      ) : (
                        <span className="text-slate-500">{t('supplier.notAvailable')}</span>
                      )}
                    </TableCell>

                    {/* Credentials Status / Input Fields */}
                    <TableCell>
                      {isEditing || isCreating ? (
                        <div className="flex gap-2">
                          <Input
                            value={formData[credential?.id || supplier.id]?.username || ''}
                            onChange={(e) => {
                              const key = credential?.id || supplier.id;
                              setFormData(prev => ({
                                ...prev,
                                [key]: { ...(prev[key] || { username: '', password: '' }), username: e.target.value }
                              }));
                            }}
                            placeholder={t('supplier.enterUsername')}
                            className="bg-slate-700 border-slate-600 text-slate-100 h-8 text-sm flex-1"
                          />
                          <Input
                            type="password"
                            value={formData[credential?.id || supplier.id]?.password || ''}
                            onChange={(e) => {
                              const key = credential?.id || supplier.id;
                              setFormData(prev => ({
                                ...prev,
                                [key]: { ...(prev[key] || { username: '', password: '' }), password: e.target.value }
                              }));
                            }}
                            placeholder={credential?.has_credentials ? t('supplier.newPasswordPlaceholder') : t('supplier.enterPassword')}
                            className="bg-slate-700 border-slate-600 text-slate-100 h-8 text-sm flex-1"
                          />
                        </div>
                      ) : credential ? (
                        <div className="flex items-center gap-2">
                          <span className="text-emerald-400">✓ {t('supplier.saved')}</span>
                          <Button
                            size="sm"
                            onClick={() => handleDelete(credential.id)}
                            variant="ghost"
                            className="text-red-400 hover:text-red-300 hover:bg-slate-600 h-6 w-6 p-0"
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </div>
                      ) : (
                        <span className="text-slate-500">{t('supplier.notSet')}</span>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
