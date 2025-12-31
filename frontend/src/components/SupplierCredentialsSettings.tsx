import { useState, useEffect } from 'react';
import { api, Supplier, UserSupplierCredential } from '../api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
  const [editingCredential, setEditingCredential] = useState<UserSupplierCredential | null>(null);
  const [formData, setFormData] = useState({ username: '', password: '' });

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
    setFormData({ username: '', password: '' }); // Don't show existing passwords
  };

  const handleCancel = () => {
    setEditingCredential(null);
    setFormData({ username: '', password: '' });
  };

  const handleSave = async () => {
    if (!token || !editingCredential) return;

    try {
      await api.supplierCredentials.update(token, editingCredential.id, {
        username: formData.username || undefined,
        password: formData.password || undefined,
      });
      setEditingCredential(null);
      setFormData({ username: '', password: '' });
      await loadData();
      if (onError) {
        onError('');
      }
    } catch (err) {
      if (onError) {
        onError(err instanceof Error ? err.message : t('supplier.saveCredentialsError'));
      }
    }
  };

  const handleCreate = async (supplierId: string) => {
    if (!token) return;

    try {
      await api.supplierCredentials.create(token, {
        supplier_id: supplierId,
        username: formData.username || undefined,
        password: formData.password || undefined,
      });
      setFormData({ username: '', password: '' });
      await loadData();
      if (onError) {
        onError('');
      }
    } catch (err) {
      if (onError) {
        onError(err instanceof Error ? err.message : t('supplier.saveCredentialsError'));
      }
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
        <div className="space-y-3">
          {assignedSuppliers.map(supplier => {
            const credential = getCredentialForSupplier(supplier.id);
            const isEditing = editingCredential?.id === credential?.id;
            const isCreating = editingCredential?.supplier_id === supplier.id && !credential;

            return (
              <div
                key={supplier.id}
                className="flex items-center gap-3 p-3 bg-slate-700/50 rounded border border-slate-600"
              >
                {/* Set Credentials Button (first) */}
                <div className="flex-shrink-0">
                  {isEditing || isCreating ? (
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={isEditing ? handleSave : () => handleCreate(supplier.id)}
                        className="bg-emerald-600 hover:bg-emerald-700 h-7 text-xs"
                      >
                        {t('common.save')}
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
                      onClick={() => setEditingCredential({ id: '', supplier, user_id: '', supplier_id: supplier.id, has_credentials: false, created_at: '', updated_at: '' })}
                      className="bg-slate-700 text-blue-400 hover:bg-slate-600 hover:text-blue-300 border border-slate-600 h-8"
                    >
                      <Lock className="w-3 h-3 mr-1" />
                      {t('supplier.setCredentials')}
                    </Button>
                  )}
                </div>

                {/* Supplier Name */}
                <div className="flex-shrink-0 min-w-[150px]">
                  <div className="text-slate-200 font-medium">{supplier.name}</div>
                </div>

                {/* Bill Type */}
                <div className="flex-shrink-0 min-w-[100px]">
                  <div className="text-slate-400 text-sm capitalize">{t(`bill.${supplier.bill_type}`)}</div>
                </div>

                {/* Has API */}
                <div className="flex-shrink-0 min-w-[120px]">
                  {supplier.has_api ? (
                    <span className="text-emerald-400 text-sm">🔌 {t('supplier.available')}</span>
                  ) : (
                    <span className="text-slate-500 text-sm">{t('supplier.notAvailable')}</span>
                  )}
                </div>

                {/* Credentials Status / Input Fields */}
                <div className="flex-1">
                  {isEditing || isCreating ? (
                    <div className="flex gap-2">
                      <Input
                        value={formData.username}
                        onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                        placeholder={t('supplier.enterUsername')}
                        className="bg-slate-700 border-slate-600 text-slate-100 h-8 text-sm flex-1"
                      />
                      <Input
                        type="password"
                        value={formData.password}
                        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                        placeholder={credential?.has_credentials ? t('supplier.newPasswordPlaceholder') : t('supplier.enterPassword')}
                        className="bg-slate-700 border-slate-600 text-slate-100 h-8 text-sm flex-1"
                      />
                    </div>
                  ) : credential ? (
                    <div className="flex items-center gap-2">
                      <span className="text-emerald-400 text-sm">✓ {t('supplier.saved')}</span>
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
                    <span className="text-slate-500 text-sm">{t('supplier.notSet')}</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
