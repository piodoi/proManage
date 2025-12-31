import { useState, useEffect } from 'react';
import { useAuth } from '../App';
import { api, User, Supplier, SupplierCreate, SupplierUpdate } from '../api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { LogOut, Plus, Pencil, Trash2, Users, FileText, Building2, Settings, ChevronLeft, ChevronRight, RefreshCw, Wrench, Package } from 'lucide-react';
import { Pagination, PaginationContent, PaginationItem } from '@/components/ui/pagination';
import BillParserPage from './BillParserPage';
import LandlordView from '../components/LandlordView';
import SettingsView from '../components/SettingsView';
import { useI18n } from '../lib/i18n';
import { LanguageSelector } from '../components/LanguageSelector';

export default function AdminDashboard() {
  const { user, token, logout } = useAuth();
  const { t } = useI18n();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [editUser, setEditUser] = useState<User | null>(null);
  const [formData, setFormData] = useState({ email: '', name: '', role: 'landlord' as 'admin' | 'landlord', password: '' });
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalUsers, setTotalUsers] = useState(0);
  const [showBillParser, setShowBillParser] = useState(false);
  const [showRefreshDialog, setShowRefreshDialog] = useState(false);
  const [refreshingPatterns, setRefreshingPatterns] = useState(false);
  const [forceRefresh, setForceRefresh] = useState(false);
  const [refreshResults, setRefreshResults] = useState<Array<{ action: string; pattern_name: string; file_name: string; supplier?: string; error?: string }>>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loadingSuppliers, setLoadingSuppliers] = useState(false);
  const [showSupplierCreate, setShowSupplierCreate] = useState(false);
  const [editSupplier, setEditSupplier] = useState<Supplier | null>(null);
  const [deleteSupplier, setDeleteSupplier] = useState<Supplier | null>(null);
  const [supplierProperties, setSupplierProperties] = useState<Array<{ property_id: string; property_name: string; property_address: string; property_supplier_id: string }>>([]);
  const [supplierForm, setSupplierForm] = useState<SupplierCreate>({
    name: '',
    has_api: false,
    bill_type: 'utilities',
    extraction_pattern_supplier: undefined,
  });

  useEffect(() => {
    loadUsers();
    if (token) {
      loadSuppliers();
    }
  }, [token, currentPage]);

  const loadUsers = async () => {
    if (!token) return;
    try {
      const data = await api.admin.listUsers(token, currentPage, 50);
      setUsers(data.users);
      setTotalPages(data.total_pages);
      setTotalUsers(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!token) return;
    if (!formData.password) {
      setError(t('admin.passwordRequired'));
      return;
    }
    try {
      await api.admin.createUser(token, formData);
      setShowCreate(false);
      setFormData({ email: '', name: '', role: 'landlord', password: '' });
      loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create user');
    }
  };

  const handleUpdate = async () => {
    if (!token || !editUser) return;
    try {
      // Only send password if it was changed
      const updateData: { email?: string; name?: string; role?: 'admin' | 'landlord'; password?: string } = {
        email: formData.email,
        name: formData.name,
        role: formData.role,
      };
      if (formData.password) {
        updateData.password = formData.password;
      }
      await api.admin.updateUser(token, editUser.id, updateData);
      setEditUser(null);
      setFormData({ email: '', name: '', role: 'landlord', password: '' });
      loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update user');
    }
  };

  const handleDelete = async (id: string) => {
    if (!token || !confirm(t('admin.deleteUserConfirm'))) return;
    try {
      await api.admin.deleteUser(token, id);
      loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete user');
    }
  };

  const handleSubscription = async (userId: string, tier: number) => {
    if (!token) return;
    try {
      await api.admin.updateSubscription(token, userId, tier);
      loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update subscription');
    }
  };

  const openEdit = (user: User) => {
    setEditUser(user);
    setFormData({ email: user.email, name: user.name, role: user.role, password: '' });
  };

  const loadSuppliers = async () => {
    if (!token) return;
    setLoadingSuppliers(true);
    try {
      const data = await api.admin.suppliers.list(token);
      setSuppliers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load suppliers');
    } finally {
      setLoadingSuppliers(false);
    }
  };

  const handleSupplierCreate = async () => {
    if (!token) return;
    try {
      await api.admin.suppliers.create(token, supplierForm);
      setShowSupplierCreate(false);
      setSupplierForm({ name: '', has_api: false, bill_type: 'utilities', extraction_pattern_supplier: undefined });
      loadSuppliers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create supplier');
    }
  };

  const handleSupplierUpdate = async () => {
    if (!token || !editSupplier) return;
    try {
      const updateData: SupplierUpdate = {
        name: supplierForm.name || undefined,
        has_api: supplierForm.has_api,
        bill_type: supplierForm.bill_type,
        extraction_pattern_supplier: supplierForm.extraction_pattern_supplier || undefined,
      };
      await api.admin.suppliers.update(token, editSupplier.id, updateData);
      setEditSupplier(null);
      setSupplierForm({ name: '', has_api: false, bill_type: 'utilities', extraction_pattern_supplier: undefined });
      loadSuppliers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update supplier');
    }
  };

  const handleSupplierDelete = async (removeReferences: boolean = false) => {
    if (!token || !deleteSupplier) return;
    try {
      await api.admin.suppliers.delete(token, deleteSupplier.id, removeReferences);
      setDeleteSupplier(null);
      setSupplierProperties([]);
      loadSuppliers();
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : 'Failed to delete supplier';
      // Check if error contains properties list - in this case we need to parse it from the error response
      // The backend returns a structured error, but FastAPI converts it to a string
      // We'll need to handle this differently - the error should already be caught and properties loaded
      setError(errMsg);
    }
  };

  const openSupplierEdit = (supplier: Supplier) => {
    setEditSupplier(supplier);
    setSupplierForm({
      name: supplier.name,
      has_api: supplier.has_api,
      bill_type: supplier.bill_type,
      extraction_pattern_supplier: supplier.extraction_pattern_supplier || undefined,
    });
  };

  const openSupplierDelete = async (supplier: Supplier) => {
    if (!token) return;
    setDeleteSupplier(supplier);
    setSupplierProperties([]);
    try {
      const props = await api.admin.suppliers.getProperties(token, supplier.id);
      setSupplierProperties(props);
    } catch (err) {
      // Ignore error, properties list might be empty
      setSupplierProperties([]);
    }
  };


  if (showBillParser) {
    return (
      <div className="min-h-screen bg-slate-900">
        <header className="bg-slate-800 border-b border-slate-700 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileText className="w-6 h-6 text-emerald-500" />
              <h1 className="text-xl font-semibold text-slate-100">{t('admin.dashboard')}</h1>
            </div>
            <div className="flex items-center gap-2">
              <LanguageSelector />
              <Button onClick={logout} variant="ghost" className="text-slate-400 hover:text-slate-100">
                <LogOut className="w-4 h-4 mr-2" />
                {t('app.logout')}
              </Button>
            </div>
          </div>
        </header>
        <main className="p-6">
          <BillParserPage onBack={() => setShowBillParser(false)} />
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900">
      <header className="bg-slate-800 border-b border-slate-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Users className="w-6 h-6 text-emerald-500" />
            <div>
              <h1 className="text-xl font-semibold text-slate-100">{t('admin.dashboard')}</h1>
              {user && <p className="text-sm text-slate-400">{user.name}</p>}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <LanguageSelector />
            <Button onClick={logout} variant="ghost" className="text-slate-400 hover:text-slate-100">
              <LogOut className="w-4 h-4 mr-2" />
              {t('app.logout')}
            </Button>
          </div>
        </div>
      </header>

      <main className="p-6">
        {error && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded text-red-200">
            {error}
            <button onClick={() => setError('')} className="ml-2 text-red-400 hover:text-red-200">x</button>
          </div>
        )}

        <Tabs defaultValue="property" className="space-y-4">
          <TabsList className="bg-slate-800 border border-slate-700">
            <TabsTrigger value="property" className="data-[state=active]:bg-slate-700">
              <Building2 className="w-4 h-4 mr-2" />
              {t('property.properties')}
            </TabsTrigger>
            <TabsTrigger value="admin" className="data-[state=active]:bg-slate-700">
              <Users className="w-4 h-4 mr-2" />
              {t('admin.users')}
            </TabsTrigger>
            <TabsTrigger value="settings" className="data-[state=active]:bg-slate-700">
              <Settings className="w-4 h-4 mr-2" />
              {t('settings.settings')}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="property" className="space-y-4">
            <LandlordView token={token} onError={setError} hideSettings />
          </TabsContent>

          <TabsContent value="admin" className="space-y-4">
            {/* Housekeeping Section */}
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-slate-100 flex items-center gap-2">
                  <Wrench className="w-5 h-5" />
                  {t('admin.housekeeping')}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h3 className="text-slate-200 mb-2">{t('admin.billExtractionPatterns')}</h3>
                  <p className="text-slate-400 text-sm mb-4">
                    {t('admin.refreshPatternsDesc')}
                  </p>
                  <div className="flex items-center gap-4 mb-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={forceRefresh}
                        onChange={(e) => setForceRefresh(e.target.checked)}
                        className="w-4 h-4 rounded bg-slate-700 border-slate-600 text-emerald-600 focus:ring-emerald-500"
                      />
                      <span className="text-slate-300 text-sm">{t('admin.forceRefresh')}</span>
                    </label>
                  </div>
                  <Button
                    onClick={async () => {
                      if (!token) return;
                      setRefreshingPatterns(true);
                      setRefreshResults([]);
                      setShowRefreshDialog(true);
                      try {
                        const result = await api.admin.refreshPatterns(token, forceRefresh);
                        setRefreshResults(result.results);
                      } catch (err) {
                        setError(err instanceof Error ? err.message : t('errors.generic'));
                        setShowRefreshDialog(false);
                      } finally {
                        setRefreshingPatterns(false);
                      }
                    }}
                    disabled={refreshingPatterns}
                    className="bg-emerald-600 text-white hover:bg-emerald-700"
                  >
                    <RefreshCw className={`w-4 h-4 mr-2 ${refreshingPatterns ? 'animate-spin' : ''}`} />
                    {refreshingPatterns ? t('admin.refreshing') : t('admin.refreshBillPatterns')}
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Suppliers Management Section */}
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-slate-100 flex items-center gap-2">
                  <Package className="w-5 h-5" />
                  {t('admin.suppliersManagement')}
                </CardTitle>
                <Dialog open={showSupplierCreate} onOpenChange={setShowSupplierCreate}>
                  <DialogTrigger asChild>
                    <Button className="bg-emerald-600 hover:bg-emerald-700">
                      <Plus className="w-4 h-4 mr-2" />
                      {t('admin.createSupplier')}
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="bg-slate-800 border-slate-700 max-w-md">
                    <DialogHeader>
                      <DialogTitle className="text-slate-100">{t('admin.createSupplier')}</DialogTitle>
                      <DialogDescription className="text-slate-400 sr-only">
                        {t('admin.createSupplier')}
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                      <div>
                        <Label className="text-slate-300">{t('common.name')} *</Label>
                        <Input
                          value={supplierForm.name}
                          onChange={(e) => setSupplierForm({ ...supplierForm, name: e.target.value })}
                          className="bg-slate-700 border-slate-600 text-slate-100"
                          required
                        />
                      </div>
                      <div>
                        <Label className="text-slate-300">{t('bill.billType')} *</Label>
                        <Select 
                          value={supplierForm.bill_type} 
                          onValueChange={(v) => setSupplierForm({ ...supplierForm, bill_type: v as 'rent' | 'utilities' | 'ebloc' | 'other' })}
                        >
                          <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-slate-700 border-slate-600">
                            <SelectItem value="utilities">{t('bill.utilities')}</SelectItem>
                            <SelectItem value="rent">{t('bill.rent')}</SelectItem>
                            <SelectItem value="ebloc">{t('bill.ebloc')}</SelectItem>
                            <SelectItem value="other">{t('bill.other')}</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label className="text-slate-300">{t('admin.extractionPatternSupplier')}</Label>
                        <Input
                          value={supplierForm.extraction_pattern_supplier || ''}
                          onChange={(e) => setSupplierForm({ ...supplierForm, extraction_pattern_supplier: e.target.value || undefined })}
                          className="bg-slate-700 border-slate-600 text-slate-100"
                          placeholder={t('admin.extractionPatternSupplierPlaceholder')}
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={supplierForm.has_api}
                          onChange={(e) => setSupplierForm({ ...supplierForm, has_api: e.target.checked })}
                          className="w-4 h-4 rounded bg-slate-700 border-slate-600 text-emerald-600 focus:ring-emerald-500"
                        />
                        <Label className="text-slate-300">{t('admin.hasApiIntegration')}</Label>
                      </div>
                      <DialogFooter>
                        <Button onClick={() => setShowSupplierCreate(false)} variant="outline" className="bg-slate-700 text-slate-100 hover:bg-slate-600">
                          {t('common.cancel')}
                        </Button>
                        <Button onClick={handleSupplierCreate} className="bg-emerald-600 hover:bg-emerald-700">
                          {t('common.add')}
                        </Button>
                      </DialogFooter>
                    </div>
                  </DialogContent>
                </Dialog>
              </CardHeader>
              <CardContent>
                {loadingSuppliers ? (
                  <div className="text-slate-400 text-center py-4">{t('admin.loadingSuppliers')}</div>
                ) : suppliers.length === 0 ? (
                  <div className="text-slate-400 text-center py-4">{t('admin.noSuppliersFound')}</div>
                ) : (
                  <div className={suppliers.length > 10 ? "max-h-96 overflow-y-auto" : ""}>
                    <Table>
                      <TableHeader>
                        <TableRow className="border-slate-700">
                          <TableHead className="text-slate-300">{t('common.name')}</TableHead>
                          <TableHead className="text-slate-300">{t('bill.billType')}</TableHead>
                          <TableHead className="text-slate-300">{t('supplier.hasApi')}</TableHead>
                          <TableHead className="text-slate-300">{t('admin.extractionPatterns')}</TableHead>
                          <TableHead className="text-slate-300">{t('common.actions')}</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {suppliers.map((supplier) => (
                          <TableRow key={supplier.id} className="border-slate-700">
                            <TableCell className="text-slate-100">{supplier.name}</TableCell>
                            <TableCell className="text-slate-300 capitalize">{supplier.bill_type}</TableCell>
                            <TableCell className="text-slate-300">
                              {supplier.has_api ? t('common.yes') : t('common.no')}
                            </TableCell>
                            <TableCell className="text-slate-300 text-sm">
                              {supplier.extraction_pattern_supplier || '-'}
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => openSupplierEdit(supplier)}
                                  className="text-slate-400 hover:text-slate-100"
                                >
                                  <Pencil className="w-4 h-4" />
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => openSupplierDelete(supplier)}
                                  className="text-red-400 hover:text-red-300"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Edit Supplier Dialog */}
            <Dialog open={!!editSupplier} onOpenChange={(open) => !open && setEditSupplier(null)}>
              <DialogContent className="bg-slate-800 border-slate-700 max-w-md">
                <DialogHeader>
                  <DialogTitle className="text-slate-100">{t('admin.editSupplier')}</DialogTitle>
                  <DialogDescription className="text-slate-400 sr-only">
                    {t('admin.editSupplier')}
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label className="text-slate-300">{t('common.name')} *</Label>
                    <Input
                      value={supplierForm.name}
                      onChange={(e) => setSupplierForm({ ...supplierForm, name: e.target.value })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                      required
                    />
                  </div>
                  <div>
                    <Label className="text-slate-300">{t('bill.billType')} *</Label>
                    <Select 
                      value={supplierForm.bill_type} 
                      onValueChange={(v) => setSupplierForm({ ...supplierForm, bill_type: v as 'rent' | 'utilities' | 'ebloc' | 'other' })}
                    >
                      <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-700 border-slate-600">
                        <SelectItem value="utilities">{t('bill.utilities')}</SelectItem>
                        <SelectItem value="rent">{t('bill.rent')}</SelectItem>
                        <SelectItem value="ebloc">{t('bill.ebloc')}</SelectItem>
                        <SelectItem value="other">{t('bill.other')}</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-slate-300">{t('admin.extractionPatternSupplier')}</Label>
                    <Input
                      value={supplierForm.extraction_pattern_supplier || ''}
                      onChange={(e) => setSupplierForm({ ...supplierForm, extraction_pattern_supplier: e.target.value || undefined })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                      placeholder={t('admin.extractionPatternSupplierPlaceholder')}
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={supplierForm.has_api}
                      onChange={(e) => setSupplierForm({ ...supplierForm, has_api: e.target.checked })}
                      className="w-4 h-4 rounded bg-slate-700 border-slate-600 text-emerald-600 focus:ring-emerald-500"
                    />
                    <Label className="text-slate-300">{t('admin.hasApiIntegration')}</Label>
                  </div>
                  <DialogFooter>
                    <Button onClick={() => setEditSupplier(null)} variant="outline" className="bg-slate-700 text-slate-100 hover:bg-slate-600">
                      {t('common.cancel')}
                    </Button>
                    <Button onClick={handleSupplierUpdate} className="bg-emerald-600 hover:bg-emerald-700">
                      {t('common.save')}
                    </Button>
                  </DialogFooter>
                </div>
              </DialogContent>
            </Dialog>

            {/* Delete Supplier Confirmation Dialog */}
            <Dialog open={!!deleteSupplier} onOpenChange={(open) => !open && setDeleteSupplier(null)}>
              <DialogContent className="bg-slate-800 border-slate-700 max-w-md">
                <DialogHeader>
                  <DialogTitle className="text-slate-100">{t('admin.deleteSupplier')}</DialogTitle>
                  <DialogDescription className="text-slate-400 sr-only">
                    {t('admin.deleteSupplier')}
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <p className="text-slate-300">
                    {t('admin.supplierDeleteConfirm')} <strong className="text-slate-100">{deleteSupplier?.name}</strong>?
                  </p>
                  {supplierProperties.length > 0 && (
                    <div>
                      <p className="text-slate-300 mb-2">
                        {t('admin.supplierConnectedTo', { count: supplierProperties.length })}
                      </p>
                      <div className="max-h-48 overflow-y-auto bg-slate-700/50 rounded p-3 space-y-1">
                        {supplierProperties.map((prop) => (
                          <div key={prop.property_id} className="text-slate-200 text-sm">
                            • {prop.property_name} - {prop.property_address}
                          </div>
                        ))}
                      </div>
                      <p className="text-slate-400 text-sm mt-2">
                        {t('admin.removeReferences')}
                      </p>
                    </div>
                  )}
                  <DialogFooter className="flex-col gap-2 sm:flex-row">
                    <Button 
                      onClick={() => setDeleteSupplier(null)} 
                      variant="outline" 
                      className="bg-slate-700 text-slate-100 hover:bg-slate-600 w-full sm:w-auto"
                    >
                      {t('common.cancel')}
                    </Button>
                    {supplierProperties.length > 0 && (
                      <Button 
                        onClick={() => handleSupplierDelete(false)} 
                        className="bg-yellow-600 hover:bg-yellow-700 w-full sm:w-auto"
                      >
                        {t('admin.deleteSupplierOnly')}
                      </Button>
                    )}
                    <Button 
                      onClick={() => handleSupplierDelete(true)} 
                      className="bg-red-600 hover:bg-red-700 w-full sm:w-auto"
                    >
                      {supplierProperties.length > 0 ? t('admin.deleteSupplierAndReferences') : t('common.delete')}
                    </Button>
                  </DialogFooter>
                </div>
              </DialogContent>
            </Dialog>

            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-slate-100 flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  {t('admin.billParser')}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-400 text-sm mb-4">
                  {t('admin.billParserDesc')}
                </p>
                <Button onClick={() => setShowBillParser(true)} className="bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600">
                  <FileText className="w-4 h-4 mr-2" />
                  {t('admin.openBillParser')}
                </Button>
              </CardContent>
            </Card>
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-slate-100">{t('admin.userManagement')}</CardTitle>
                <Dialog open={showCreate} onOpenChange={setShowCreate}>
                  <DialogTrigger asChild>
                    <Button className="bg-emerald-600 hover:bg-emerald-700">
                      <Plus className="w-4 h-4 mr-2" />
                      {t('admin.createUser')}
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="bg-slate-800 border-slate-700">
                    <DialogHeader>
                      <DialogTitle className="text-slate-100">{t('admin.createUser')}</DialogTitle>
                      <DialogDescription className="text-slate-400 sr-only">
                        {t('admin.createUser')}
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                      <div>
                        <Label className="text-slate-300">{t('common.email')}</Label>
                        <Input
                          value={formData.email}
                          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                          className="bg-slate-700 border-slate-600 text-slate-100"
                        />
                      </div>
                      <div>
                        <Label className="text-slate-300">{t('common.password')} *</Label>
                        <Input
                          type="password"
                          value={formData.password}
                          onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                          className="bg-slate-700 border-slate-600 text-slate-100"
                          required
                        />
                      </div>
                      <div>
                        <Label className="text-slate-300">{t('common.name')}</Label>
                        <Input
                          value={formData.name}
                          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                          className="bg-slate-700 border-slate-600 text-slate-100"
                        />
                      </div>
                      <div>
                        <Label className="text-slate-300">{t('admin.role')}</Label>
                        <Select value={formData.role} onValueChange={(v) => setFormData({ ...formData, role: v as 'admin' | 'landlord' })}>
                          <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-slate-700 border-slate-600">
                            <SelectItem value="landlord">{t('admin.landlord')}</SelectItem>
                            <SelectItem value="admin">Admin</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <Button onClick={handleCreate} className="w-full bg-emerald-600 hover:bg-emerald-700">
                        {t('common.add')}
                      </Button>
                    </div>
                  </DialogContent>
                </Dialog>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="text-slate-400 text-center py-8">{t('common.loading')}</div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow className="border-slate-700">
                        <TableHead className="text-slate-400">{t('common.name')}</TableHead>
                        <TableHead className="text-slate-400">{t('common.email')}</TableHead>
                        <TableHead className="text-slate-400">{t('common.password')}</TableHead>
                        <TableHead className="text-slate-400">{t('admin.role')}</TableHead>
                        <TableHead className="text-slate-400">{t('admin.subscription')}</TableHead>
                        <TableHead className="text-slate-400">{t('common.actions')}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {users.map((user) => (
                        <TableRow key={user.id} className="border-slate-700">
                          <TableCell className="text-slate-200">{user.name}</TableCell>
                          <TableCell className="text-slate-300">{user.email}</TableCell>
                          <TableCell className="text-slate-300">
                            {user.password_hash ? '••••••••' : 'OAuth'}
                          </TableCell>
                          <TableCell>
                            <span className={`px-2 py-1 rounded text-xs ${user.role === 'admin' ? 'bg-purple-900 text-purple-200' : 'bg-blue-900 text-blue-200'}`}>
                              {user.role}
                            </span>
                          </TableCell>
                          <TableCell>
                            {user.role === 'landlord' && (
                              <Select
                                value={((user.subscription_tier ?? 0) > 0 ? '1' : '0')}
                                onValueChange={(v) => handleSubscription(user.id, parseInt(v, 10))}
                              >
                                <SelectTrigger className="w-20 h-8 bg-slate-700 border-slate-600 text-slate-100">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent className="bg-slate-700 border-slate-600">
                                  <SelectItem value="0">{t('admin.off')}</SelectItem>
                                  <SelectItem value="1">{t('admin.on')}</SelectItem>
                                </SelectContent>
                              </Select>
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => openEdit(user)}
                                className="text-slate-400 hover:text-slate-100"
                              >
                                <Pencil className="w-4 h-4" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleDelete(user.id)}
                                className="text-red-400 hover:text-red-200"
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
                {totalPages > 1 && (
                  <div className="mt-4 flex items-center justify-between">
                    <p className="text-sm text-slate-400">
                      {t('admin.showingUsers', { 
                        from: ((currentPage - 1) * 50) + 1, 
                        to: Math.min(currentPage * 50, totalUsers), 
                        total: totalUsers 
                      })}
                    </p>
                    <Pagination>
                      <PaginationContent>
                        <PaginationItem>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => currentPage > 1 && setCurrentPage(currentPage - 1)}
                            disabled={currentPage === 1}
                            className="text-slate-400 hover:text-slate-100"
                          >
                            <ChevronLeft className="h-4 w-4 mr-1" />
                            {t('admin.previous')}
                          </Button>
                        </PaginationItem>
                        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                          let pageNum;
                          if (totalPages <= 5) {
                            pageNum = i + 1;
                          } else if (currentPage <= 3) {
                            pageNum = i + 1;
                          } else if (currentPage >= totalPages - 2) {
                            pageNum = totalPages - 4 + i;
                          } else {
                            pageNum = currentPage - 2 + i;
                          }
                          return (
                            <PaginationItem key={pageNum}>
                              <Button
                                variant={currentPage === pageNum ? "outline" : "ghost"}
                                size="sm"
                                onClick={() => setCurrentPage(pageNum)}
                                className={currentPage === pageNum ? 'bg-slate-700 text-slate-100 border-slate-600' : 'text-slate-400 hover:text-slate-100'}
                              >
                                {pageNum}
                              </Button>
                            </PaginationItem>
                          );
                        })}
                        <PaginationItem>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => currentPage < totalPages && setCurrentPage(currentPage + 1)}
                            disabled={currentPage === totalPages}
                            className="text-slate-400 hover:text-slate-100"
                          >
                            {t('admin.next')}
                            <ChevronRight className="h-4 w-4 ml-1" />
                          </Button>
                        </PaginationItem>
                      </PaginationContent>
                    </Pagination>
                  </div>
                )}
              </CardContent>
            </Card>

            <Dialog open={!!editUser} onOpenChange={(open) => !open && setEditUser(null)}>
              <DialogContent className="bg-slate-800 border-slate-700">
                <DialogHeader>
                  <DialogTitle className="text-slate-100">{t('admin.editUser')}</DialogTitle>
                  <DialogDescription className="text-slate-400 sr-only">
                    {t('admin.editUser')}
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label className="text-slate-300">{t('common.email')}</Label>
                    <Input
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                    />
                  </div>
                  <div>
                    <Label className="text-slate-300">{t('common.password')}</Label>
                    <Input
                      type="password"
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                      placeholder={t('common.password')}
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      {t('common.password')}
                    </p>
                  </div>
                  <div>
                    <Label className="text-slate-300">{t('common.name')}</Label>
                    <Input
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                    />
                  </div>
                  <div>
                    <Label className="text-slate-300">{t('admin.role')}</Label>
                    <Select value={formData.role} onValueChange={(v) => setFormData({ ...formData, role: v as 'admin' | 'landlord' })}>
                      <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-700 border-slate-600">
                        <SelectItem value="landlord">{t('admin.landlord')}</SelectItem>
                        <SelectItem value="admin">Admin</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <Button onClick={handleUpdate} className="w-full bg-emerald-600 hover:bg-emerald-700">
                    {t('admin.update')}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </TabsContent>

          <TabsContent value="settings" className="space-y-4">
            <SettingsView token={token} onError={setError} />
          </TabsContent>
        </Tabs>
      </main>

      {/* Refresh Patterns Dialog */}
      <Dialog open={showRefreshDialog} onOpenChange={setShowRefreshDialog}>
        <DialogContent className="bg-slate-800 border-slate-700 max-w-2xl">
          <DialogHeader>
            <DialogTitle className="text-slate-100 flex items-center gap-2">
              <RefreshCw className="w-5 h-5" />
              {t('admin.refreshBillPatternsTitle')}
            </DialogTitle>
            <DialogDescription className="text-slate-400 sr-only">
              {t('admin.refreshBillPatternsTitle')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 text-slate-300">
            {refreshingPatterns ? (
              <div className="text-center py-4">
                <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2 text-emerald-500" />
                <p>{t('admin.refreshingPatterns')}</p>
              </div>
            ) : refreshResults.length === 0 ? (
              <p className="text-slate-400">{t('admin.noPatternsUpdated')}</p>
            ) : (
              <div className="space-y-2">
                <p className="text-slate-200 font-medium">
                  {t('admin.updatedPatterns', { count: refreshResults.filter(r => r.action === 'created' || r.action === 'updated').length })}
                </p>
                <div className="max-h-96 overflow-y-auto space-y-2">
                  {refreshResults.map((result, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded border ${
                        result.action === 'error'
                          ? 'bg-red-900/30 border-red-700 text-red-200'
                          : result.action === 'created'
                          ? 'bg-emerald-900/30 border-emerald-700 text-emerald-200'
                          : 'bg-blue-900/30 border-blue-700 text-blue-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="font-medium">
                            {result.action === 'created' ? t('admin.created') : result.action === 'updated' ? t('admin.updated') : t('admin.error')}
                          </span>
                          <span className="ml-2">{result.pattern_name}</span>
                          {result.supplier && (
                            <span className="text-slate-400 ml-2">({result.supplier})</span>
                          )}
                        </div>
                        <span className="text-xs text-slate-400">{result.file_name}</span>
                      </div>
                      {result.error && (
                        <div className="mt-1 text-xs text-red-300">{result.error}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button
              onClick={() => {
                setShowRefreshDialog(false);
                setRefreshResults([]);
              }}
              disabled={refreshingPatterns}
              className="bg-slate-700 text-slate-100 hover:bg-slate-600"
            >
              OK
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
