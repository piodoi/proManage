import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../App';
import { api, User, Supplier, SupplierCreate, SupplierUpdate, BillType, BILL_TYPES } from '../api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import HeaderBar from '@/components/HeaderBar';
import Footer from '@/components/Footer';
import { Plus, Pencil, Trash2, Users, FileText, Building2, Settings, ChevronLeft, ChevronRight, Package, FolderSearch, Crown, Bell, Settings2 } from 'lucide-react';
import { Pagination, PaginationContent, PaginationItem } from '@/components/ui/pagination';
import LandlordView from '../components/LandlordView';
import SettingsView from '../components/SettingsView';
import SummaryView from '../components/SummaryView';
import TextPatternView from '../components/TextPatternView';
import NotificationsView from '../components/NotificationsView';
import HelpManualView from '../components/HelpManualView';
import EnvVariablesView from '../components/EnvVariablesView';
import UserPatternDialog from '../components/dialogs/UserPatternDialog';
import { useI18n } from '../lib/i18n';

export default function Dashboard() {
  const { user, token } = useAuth();
  const { t } = useI18n();
  const [error, setError] = useState('');
  const isAdmin = user?.role === 'admin';

  // Admin state
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editUser, setEditUser] = useState<User | null>(null);
  const [formData, setFormData] = useState({ email: '', name: '', role: 'landlord' as 'admin' | 'landlord', password: '', subscription_tier: 0 });
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalUsers, setTotalUsers] = useState(0);
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

  // Notification count state
  const [notificationCount, setNotificationCount] = useState(0);

  // Session-based tab memory
  const [activeTab, setActiveTab] = useState(() => {
    const saved = sessionStorage.getItem('dashboard-active-tab');
    return saved || 'summary';
  });

  // Load notification count on mount
  const loadNotificationCount = useCallback(async () => {
    if (!token) return;
    try {
      const { count } = await api.paymentNotifications.count(token);
      setNotificationCount(count);
    } catch (err) {
      console.error('Failed to load notification count:', err);
    }
  }, [token]);

  useEffect(() => {
    loadNotificationCount();
    // Refresh count every 60 seconds
    const interval = setInterval(loadNotificationCount, 60000);
    return () => clearInterval(interval);
  }, [loadNotificationCount]);

  useEffect(() => {
    if (activeTab) {
      sessionStorage.setItem('dashboard-active-tab', activeTab);
    }
  }, [activeTab]);

  useEffect(() => {
    if (isAdmin && token) {
      loadUsers();
      loadSuppliers();
    }
  }, [token, currentPage, isAdmin]);

  const loadUsers = async () => {
    if (!token || !isAdmin) return;
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
      setFormData({ email: '', name: '', role: 'landlord', password: '', subscription_tier: 0 });
      loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create user');
    }
  };

  const handleUpdate = async () => {
    if (!token || !editUser) return;
    try {
      const updateData: { email?: string; name?: string; role?: 'admin' | 'landlord'; password?: string; subscription_tier?: number } = {
        email: formData.email,
        name: formData.name,
        role: formData.role,
        subscription_tier: formData.subscription_tier,
      };
      if (formData.password) {
        updateData.password = formData.password;
      }
      await api.admin.updateUser(token, editUser.id, updateData);
      setEditUser(null);
      setFormData({ email: '', name: '', role: 'landlord', password: '', subscription_tier: 0 });
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
    setFormData({ email: user.email, name: user.name, role: user.role, password: '', subscription_tier: user.subscription_tier ?? 0 });
  };

  const loadSuppliers = async () => {
    if (!token || !isAdmin) return;
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
      setSupplierProperties([]);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col">
      <HeaderBar />

      <main className="flex-1 p-2 sm:p-3 bg-slate-900">
        <div className="w-full">
        {error && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded text-red-200">
            {error}
            <button onClick={() => setError('')} className="ml-2 text-red-400 hover:text-red-200">x</button>
          </div>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="bg-slate-800 border-b border-slate-700 rounded-none rounded-t-lg h-auto p-0 gap-0 w-full flex flex-wrap justify-start">
            <TabsTrigger value="summary" className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-2 sm:px-4 py-2 border-b-2 border-transparent text-xs sm:text-sm">
              <FileText className="w-4 h-4 mr-1 sm:mr-2" />
              {t('summary.summary')}
            </TabsTrigger>
            <TabsTrigger value="property" className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-2 sm:px-4 py-2 border-b-2 border-transparent text-xs sm:text-sm">
              <Building2 className="w-4 h-4 mr-1 sm:mr-2" />
              {t('property.properties')}
            </TabsTrigger>
            <TabsTrigger value="settings" className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-2 sm:px-4 py-2 border-b-2 border-transparent text-xs sm:text-sm">
              <Settings className="w-4 h-4 mr-1 sm:mr-2" />
              {t('settings.settings')}
            </TabsTrigger>
            <TabsTrigger value="subscription" className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-2 sm:px-4 py-2 border-b-2 border-transparent text-xs sm:text-sm">
              <Crown className="w-4 h-4 mr-1 sm:mr-2" />
              {t('settings.subscriptions')}
            </TabsTrigger>
            <TabsTrigger value="notifications" className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-2 sm:px-4 py-2 border-b-2 border-transparent relative text-xs sm:text-sm">
              <Bell className="w-4 h-4 mr-1 sm:mr-2" />
              {t('notifications.title')}
              {notificationCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
                  {notificationCount > 9 ? '9+' : notificationCount}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="tools" className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-2 sm:px-4 py-2 border-b-2 border-transparent text-xs sm:text-sm">
              <FileText className="w-4 h-4 mr-1 sm:mr-2" />
              {t('tools.tools')}
            </TabsTrigger>
            {isAdmin && (
              <TabsTrigger value="admin" className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-2 sm:px-4 py-2 border-b-2 border-transparent text-xs sm:text-sm">
                <Users className="w-4 h-4 mr-1 sm:mr-2" />
                {t('admin.adminTab')}
              </TabsTrigger>
            )}
          </TabsList>

          <div className="bg-slate-800 border border-t-0 border-slate-700 rounded-b-lg">
            <TabsContent value="summary" className="m-0 p-3 space-y-3">
              <SummaryView />
            </TabsContent>

            <TabsContent value="property" className="m-0 p-3 space-y-3">
              <LandlordView token={token} onError={setError} hideSettings onNavigateToSubscription={() => setActiveTab('subscription')} />
            </TabsContent>

            <TabsContent value="settings" className="m-0 p-3 space-y-3">
              <SettingsView token={token} user={user} onError={setError} onNavigateToSubscription={() => setActiveTab('subscription')} />
            </TabsContent>

            <TabsContent value="subscription" className="m-0 p-3 space-y-3">
              <SettingsView token={token} user={user} onError={setError} forceTab="subscription" hideTabBar />
            </TabsContent>

            <TabsContent value="notifications" className="m-0 p-3 space-y-3">
              <NotificationsView onCountChange={setNotificationCount} />
            </TabsContent>

            <TabsContent value="tools" className="m-0 p-3 space-y-3">
              <TextPatternView />
            </TabsContent>

            <TabsContent value="help" className="m-0 p-3 space-y-3">
              <HelpManualView />
            </TabsContent>

            {isAdmin && (
              <TabsContent value="admin" className="m-0 p-3 space-y-0">
                <AdminTabsContent
                  token={token}
                  users={users}
                  loading={loading}
                  suppliers={suppliers}
                  loadingSuppliers={loadingSuppliers}
                  showCreate={showCreate}
                  setShowCreate={setShowCreate}
                  editUser={editUser}
                  setEditUser={setEditUser}
                  formData={formData}
                  setFormData={setFormData}
                  currentPage={currentPage}
                  setCurrentPage={setCurrentPage}
                  totalPages={totalPages}
                  totalUsers={totalUsers}
                  handleCreate={handleCreate}
                  handleUpdate={handleUpdate}
                  handleDelete={handleDelete}
                  handleSubscription={handleSubscription}
                  openEdit={openEdit}
                  showSupplierCreate={showSupplierCreate}
                  setShowSupplierCreate={setShowSupplierCreate}
                  editSupplier={editSupplier}
                  setEditSupplier={setEditSupplier}
                  deleteSupplier={deleteSupplier}
                  setDeleteSupplier={setDeleteSupplier}
                  supplierProperties={supplierProperties}
                  supplierForm={supplierForm}
                  setSupplierForm={setSupplierForm}
                  handleSupplierCreate={handleSupplierCreate}
                  handleSupplierUpdate={handleSupplierUpdate}
                  handleSupplierDelete={handleSupplierDelete}
                  openSupplierEdit={openSupplierEdit}
                  openSupplierDelete={openSupplierDelete}
                />
              </TabsContent>
            )}
          </div>
        </Tabs>
        </div>
      </main>
      <Footer />
    </div>
  );
}

// Admin tabs content component
function AdminTabsContent({
  token,
  users,
  loading,
  suppliers,
  loadingSuppliers,
  showCreate,
  setShowCreate,
  editUser,
  setEditUser,
  formData,
  setFormData,
  currentPage,
  setCurrentPage,
  totalPages,
  totalUsers,
  handleCreate,
  handleUpdate,
  handleDelete,
  handleSubscription,
  openEdit,
  showSupplierCreate,
  setShowSupplierCreate,
  editSupplier,
  setEditSupplier,
  deleteSupplier,
  setDeleteSupplier,
  supplierProperties,
  supplierForm,
  setSupplierForm,
  handleSupplierCreate,
  handleSupplierUpdate,
  handleSupplierDelete,
  openSupplierEdit,
  openSupplierDelete,
}: any) {
  const { t } = useI18n();
  const [adminActiveTab, setAdminActiveTab] = useState(() => {
    const saved = sessionStorage.getItem('admin-active-tab');
    // Default to suppliers if housekeeping was previously saved
    return saved && saved !== 'housekeeping' ? saved : 'suppliers';
  });
  const [showUserPatternDialog, setShowUserPatternDialog] = useState(false);
  const [userPatternError, setUserPatternError] = useState('');

  useEffect(() => {
    if (adminActiveTab) {
      sessionStorage.setItem('admin-active-tab', adminActiveTab);
    }
  }, [adminActiveTab]);

  const handleUserPatternSuccess = () => {
    // Refresh suppliers list after creating a supplier from user pattern
    // Note: loadSuppliers is passed from parent component
    setUserPatternError('');
  };

  return (
    <div className="space-y-0">
      <Tabs value={adminActiveTab} onValueChange={setAdminActiveTab} className="w-full">
        <TabsList className="bg-slate-800 border-b border-slate-700 rounded-none rounded-t-lg h-auto p-0 gap-0 w-full justify-start">
          <TabsTrigger value="suppliers" className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-4 py-2 border-b-2 border-transparent">
            <Package className="w-4 h-4 mr-2" />
            {t('admin.suppliersManagement')}
          </TabsTrigger>
          <TabsTrigger value="users" className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-4 py-2 border-b-2 border-transparent">
            <Users className="w-4 h-4 mr-2" />
            {t('admin.userManagement')}
          </TabsTrigger>
          <TabsTrigger value="env" className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-4 py-2 border-b-2 border-transparent">
            <Settings2 className="w-4 h-4 mr-2" />
            {t('admin.envVariables') || 'ENV Variables'}
          </TabsTrigger>
        </TabsList>

        <div className="bg-slate-800 border border-t-0 border-slate-700 rounded-b-lg">
          <TabsContent value="suppliers" className="m-0 p-6 space-y-4">
            <Card className="bg-slate-800 border-0 shadow-none">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-slate-100 flex items-center gap-2">
                  <Package className="w-5 h-5" />
                  {t('admin.suppliersManagement')}
                </CardTitle>
                <div className="flex gap-2">
                  <Button 
                    variant="outline" 
                    className="bg-slate-700 text-slate-100 hover:bg-slate-600 border-slate-600"
                    onClick={() => setShowUserPatternDialog(true)}
                  >
                    <FolderSearch className="w-4 h-4 mr-2" />
                    {t('admin.userPatterns.addFromUserPattern')}
                  </Button>
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
                          onValueChange={(v) => setSupplierForm({ ...supplierForm, bill_type: v as BillType })}
                        >
                          <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-slate-700 border-slate-600">
                            {BILL_TYPES.map(type => (
                              <SelectItem key={type} value={type}>{t(`bill.${type}`)}</SelectItem>
                            ))}
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
                </div>
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
                        {suppliers.map((supplier: Supplier) => (
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
                      onValueChange={(v) => setSupplierForm({ ...supplierForm, bill_type: v as BillType })}
                    >
                      <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-700 border-slate-600">
                        {BILL_TYPES.map(type => (
                          <SelectItem key={type} value={type}>{t(`bill.${type}`)}</SelectItem>
                        ))}
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
                        {supplierProperties.map((prop: any) => (
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
          </TabsContent>

          <TabsContent value="users" className="m-0 p-6 space-y-4">
            <Card className="bg-slate-800 border-0 shadow-none">
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
                      {users.map((user: User) => (
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
                            <Input
                              type="number"
                              min="0"
                              value={user.subscription_tier ?? 0}
                              onChange={(e) => handleSubscription(user.id, parseInt(e.target.value, 10) || 0)}
                              className="w-16 h-8 bg-slate-700 border-slate-600 text-slate-100 text-center"
                            />
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
                  <div>
                    <Label className="text-slate-300">{t('admin.subscription')} ({t('admin.tier')})</Label>
                    <Input
                      type="number"
                      min="0"
                      value={formData.subscription_tier}
                      onChange={(e) => setFormData({ ...formData, subscription_tier: parseInt(e.target.value, 10) || 0 })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                      placeholder="0 = free, 1+ = paid tier"
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      0 = {t('settings.freeTier')}, 1+ = {t('admin.paidTierProperties')}
                    </p>
                  </div>
                  <Button onClick={handleUpdate} className="w-full bg-emerald-600 hover:bg-emerald-700">
                    {t('admin.update')}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </TabsContent>

          <TabsContent value="env" className="m-0 p-6 space-y-4">
            <EnvVariablesView />
          </TabsContent>
        </div>
      </Tabs>

      {/* User Pattern Dialog */}
      <UserPatternDialog
        token={token}
        open={showUserPatternDialog}
        onOpenChange={setShowUserPatternDialog}
        onSuccess={handleUserPatternSuccess}
        onError={(error) => setUserPatternError(error)}
      />
      {userPatternError && (
        <div className="fixed bottom-4 right-4 bg-red-900/90 text-red-100 px-4 py-2 rounded-lg shadow-lg">
          {userPatternError}
        </div>
      )}
    </div>
  );
}

