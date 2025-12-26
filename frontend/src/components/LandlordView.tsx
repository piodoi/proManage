import { useState, useEffect } from 'react';
import { api, Property, Unit, Renter, Bill, SubscriptionStatus } from '../api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Building2, Users, Receipt, Mail, Settings, Copy, ExternalLink, Trash2 } from 'lucide-react';
import { Spinner } from '@/components/ui/spinner';

type LandlordViewProps = {
  token: string | null;
  onError?: (error: string) => void;
};

export default function LandlordView({ token, onError }: LandlordViewProps) {
  const [properties, setProperties] = useState<Property[]>([]);
  const [units, setUnits] = useState<Record<string, Unit[]>>({});
  const [renters, setRenters] = useState<Record<string, Renter[]>>({});
  const [bills, setBills] = useState<Bill[]>([]);
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showPropertyForm, setShowPropertyForm] = useState(false);
  const [showUnitForm, setShowUnitForm] = useState<string | null>(null);
  const [showRenterForm, setShowRenterForm] = useState<string | null>(null);
  const [showBillForm, setShowBillForm] = useState(false);
  const [showEmailConfig, setShowEmailConfig] = useState(false);
  const [showEblocConfig, setShowEblocConfig] = useState<string | null>(null);
  const [showEblocDiscover, setShowEblocDiscover] = useState(false);
  const [eblocDiscoveredProperties, setEblocDiscoveredProperties] = useState<Array<{ page_id: string; name: string; address: string; url: string }>>([]);
  const [eblocDiscovering, setEblocDiscovering] = useState(false);
  const [eblocImporting, setEblocImporting] = useState(false);
  const [propertyForm, setPropertyForm] = useState({ name: '', address: '' });
  const [unitForm, setUnitForm] = useState({ unit_number: '' });
  const [renterForm, setRenterForm] = useState({ name: '', email: '', phone: '' });
  const [billForm, setBillForm] = useState({
    property_id: '',
    unit_id: '',
    bill_type: 'rent' as 'rent' | 'utilities' | 'ebloc' | 'other',
    description: '',
    amount: '',
    due_date: '',
    iban: '',
    bill_number: '',
  });
  const [emailForm, setEmailForm] = useState({ config_type: 'forwarding' as 'direct' | 'forwarding', forwarding_email: '' });
  const [eblocForm, setEblocForm] = useState({ username: '', password: '', selectedPropertyId: '' });
  const [renterLink, setRenterLink] = useState<{ token: string; link: string } | null>(null);

  useEffect(() => {
    loadData();
  }, [token]);

  const handleError = (err: unknown) => {
    const message = err instanceof Error ? err.message : 'An error occurred';
    setError(message);
    if (onError) {
      onError(message);
    }
  };

  const loadData = async () => {
    if (!token) {
      console.log('[LandlordView] No token, skipping loadData');
      return;
    }
    console.log('[LandlordView] Loading data...');
    setLoading(true);
    try {
      console.log('[LandlordView] Fetching properties, bills, and subscription...');
      const [propsData, billsData, subData] = await Promise.all([
        api.properties.list(token),
        api.bills.list(token),
        api.subscription.status(token),
      ]);
      console.log('[LandlordView] Data fetched:', { 
        properties: propsData.length, 
        bills: billsData.length,
        subscription: subData 
      });
      
      setProperties(propsData);
      setBills(billsData);
      setSubscription(subData);
      
      console.log('[LandlordView] Loading units and renters...');
      for (const prop of propsData) {
        const unitsData = await api.units.list(token, prop.id);
        console.log(`[LandlordView] Property ${prop.name}: ${unitsData.length} units`);
        setUnits((prev) => ({ ...prev, [prop.id]: unitsData }));
        for (const unit of unitsData) {
          const rentersData = await api.renters.list(token, unit.id);
          setRenters((prev) => ({ ...prev, [unit.id]: rentersData }));
        }
      }
      console.log('[LandlordView] Data loaded successfully');
    } catch (err) {
      console.error('[LandlordView] Error loading data:', err);
      handleError(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProperty = async () => {
    if (!token) return;
    try {
      await api.properties.create(token, propertyForm);
      setShowPropertyForm(false);
      setPropertyForm({ name: '', address: '' });
      loadData();
    } catch (err) {
      handleError(err);
    }
  };

  const handleDeleteProperty = async (propertyId: string) => {
    if (!token) return;
    if (!confirm('Are you sure you want to delete this property? This will also delete all units, renters, and bills associated with it.')) {
      return;
    }
    try {
      await api.properties.delete(token, propertyId);
      loadData();
    } catch (err) {
      handleError(err);
    }
  };

  const handleCreateUnit = async (propertyId: string) => {
    if (!token) return;
    try {
      await api.units.create(token, propertyId, unitForm);
      setShowUnitForm(null);
      setUnitForm({ unit_number: '' });
      loadData();
    } catch (err) {
      handleError(err);
    }
  };

  const handleCreateRenter = async (unitId: string) => {
    if (!token) return;
    try {
      await api.renters.create(token, unitId, renterForm);
      setShowRenterForm(null);
      setRenterForm({ name: '', email: '', phone: '' });
      loadData();
    } catch (err) {
      handleError(err);
    }
  };

  const handleCreateBill = async () => {
    if (!token) return;
    try {
      await api.bills.create(token, {
        ...billForm,
        amount: parseFloat(billForm.amount),
        due_date: new Date(billForm.due_date).toISOString(),
      });
      setShowBillForm(false);
      setBillForm({ property_id: '', unit_id: '', bill_type: 'rent', description: '', amount: '', due_date: '', iban: '', bill_number: '' });
      loadData();
    } catch (err) {
      handleError(err);
    }
  };

  const handleConfigureEmail = async () => {
    if (!token) return;
    try {
      await api.email.configure(token, emailForm);
      setShowEmailConfig(false);
      setError('');
    } catch (err) {
      handleError(err);
    }
  };

  const handleDiscoverEbloc = async () => {
    if (!token) {
      console.error('[E-Bloc] No token available');
      return;
    }
    if (!eblocForm.username || !eblocForm.password) {
      console.error('[E-Bloc] Missing username or password');
      setError('Please enter both username and password');
      return;
    }
    
    console.log('[E-Bloc] Starting discovery...', { username: eblocForm.username });
    setEblocDiscovering(true);
    setError('');
    setEblocDiscoveredProperties([]);
    
    try {
      console.log('[E-Bloc] Calling discover API...');
      const result = await api.ebloc.discover(token, { username: eblocForm.username, password: eblocForm.password });
      console.log('[E-Bloc] Discovery result:', JSON.stringify(result, null, 2));
      
      if (result && result.properties && Array.isArray(result.properties)) {
        console.log(`[E-Bloc] Found ${result.properties.length} properties:`, result.properties);
        if (result.properties.length > 0) {
          // Ensure all properties have url field
          const propertiesWithUrl = result.properties.map(p => ({
            ...p,
            url: p.url || `https://www.e-bloc.ro/index.php?page=${p.page_id}`
          }));
          setEblocDiscoveredProperties(propertiesWithUrl);
          setEblocForm({ ...eblocForm, selectedPropertyId: propertiesWithUrl[0].page_id });
          console.log('[E-Bloc] Selected first property:', propertiesWithUrl[0].page_id);
          setError(''); // Clear any previous errors
        } else {
          console.warn('[E-Bloc] No properties found in e-bloc account');
          setError('No properties found in your e-bloc account. Please check your credentials.');
          setEblocDiscoveredProperties([]);
        }
      } else {
        console.error('[E-Bloc] Unexpected response format:', result);
        const errorMsg = (result as any)?.detail || (result as any)?.message || `Unexpected response: ${JSON.stringify(result)}`;
        setError(errorMsg);
        setEblocDiscoveredProperties([]);
      }
    } catch (err) {
      console.error('[E-Bloc] Discovery error:', err);
      if (err instanceof Error) {
        console.error('[E-Bloc] Error message:', err.message);
        console.error('[E-Bloc] Error stack:', err.stack);
      }
      const errorMessage = err instanceof Error ? err.message : 'Failed to discover properties. Please check your credentials and try again.';
      setError(errorMessage);
      setEblocDiscoveredProperties([]);
    } finally {
      setEblocDiscovering(false);
    }
  };

  const handleConfigureEbloc = async (propertyId?: string) => {
    if (!token) {
      console.error('[E-Bloc] No token available');
      return;
    }
    
    const eblocPageId = eblocForm.selectedPropertyId;
    if (!eblocPageId) {
      console.error('[E-Bloc] No e-bloc property selected');
      setError('Please select a property to import');
      return;
    }
    
    // Find the selected property data
    const selectedProperty = eblocDiscoveredProperties.find(p => p.page_id === eblocPageId);
    if (!selectedProperty) {
      setError('Selected property not found');
      return;
    }
    
    console.log('[E-Bloc] Configuring/importing property (instant)...', { propertyId, eblocPageId, selectedProperty });
    setEblocImporting(true);
    setError('');
    
    try {
      const result = await api.ebloc.configure(token, {
        property_id: propertyId || undefined,
        username: eblocForm.username,
        password: eblocForm.password,
        ebloc_page_id: eblocPageId,
        ebloc_property_name: selectedProperty.name,
        ebloc_property_address: selectedProperty.address,
        ebloc_property_url: selectedProperty.url
      });
      
      console.log('[E-Bloc] Configure result:', result);
      
      setShowEblocConfig(null);
      setShowEblocDiscover(false);
      setEblocForm({ username: '', password: '', selectedPropertyId: '' });
      setEblocDiscoveredProperties([]);
      
      // Reload data to show new property if one was created
      console.log('[E-Bloc] Reloading data...');
      await loadData();
      console.log('[E-Bloc] Data reloaded successfully');
    } catch (err) {
      console.error('[E-Bloc] Configure error:', err);
      handleError(err);
    } finally {
      setEblocImporting(false);
    }
  };

  const handleImportEblocProperties = async () => {
    if (!token) {
      console.error('[E-Bloc] No token available');
      return;
    }
    if (eblocDiscoveredProperties.length === 0) {
      console.error('[E-Bloc] No properties to import');
      return;
    }
    
    console.log(`[E-Bloc] Importing ${eblocDiscoveredProperties.length} properties (instant)...`);
    setEblocImporting(true);
    setError('');
    
    try {
      // Import all discovered properties using instant import
      for (let i = 0; i < eblocDiscoveredProperties.length; i++) {
        const eblocProp = eblocDiscoveredProperties[i];
        console.log(`[E-Bloc] Importing property ${i + 1}/${eblocDiscoveredProperties.length}:`, eblocProp);
        
        const result = await api.ebloc.configure(token, {
          username: eblocForm.username,
          password: eblocForm.password,
          ebloc_page_id: eblocProp.page_id,
          ebloc_property_name: eblocProp.name,
          ebloc_property_address: eblocProp.address,
          ebloc_property_url: eblocProp.url
        });
        
        console.log(`[E-Bloc] Property ${i + 1} imported:`, result);
      }
      
      console.log('[E-Bloc] All properties imported, reloading data...');
      setShowEblocDiscover(false);
      setEblocForm({ username: '', password: '', selectedPropertyId: '' });
      setEblocDiscoveredProperties([]);
      await loadData();
      console.log('[E-Bloc] Import complete');
    } catch (err) {
      console.error('[E-Bloc] Import error:', err);
      handleError(err);
    } finally {
      setEblocImporting(false);
    }
  };

  const handleGetRenterLink = async (renterId: string) => {
    if (!token) return;
    try {
      const link = await api.renters.getLink(token, renterId);
      setRenterLink({ token: link.access_token, link: link.link });
    } catch (err) {
      handleError(err);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const allUnits = Object.values(units).flat();

  return (
    <>
      {error && (
        <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded text-red-200">
          {error}
          <button onClick={() => setError('')} className="ml-2 text-red-400 hover:text-red-200">x</button>
        </div>
      )}

      <Tabs defaultValue="properties" className="space-y-4">
        <TabsList className="bg-slate-800 border border-slate-700">
          <TabsTrigger value="properties" className="data-[state=active]:bg-slate-700">
            <Building2 className="w-4 h-4 mr-2" />
            Properties
          </TabsTrigger>
          <TabsTrigger value="settings" className="data-[state=active]:bg-slate-700">
            <Settings className="w-4 h-4 mr-2" />
            Settings
          </TabsTrigger>
        </TabsList>

        <TabsContent value="properties" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-medium text-slate-100">Properties</h2>
            <div className="flex gap-2">
              <Dialog open={showEblocDiscover} onOpenChange={setShowEblocDiscover}>
                <DialogTrigger asChild>
                  <Button variant="outline" className="border-slate-600 text-slate-300 hover:bg-slate-700">
                    <Building2 className="w-4 h-4 mr-2" />
                    Import from E-Bloc
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-slate-800 border-slate-700 max-w-2xl">
                  <DialogHeader>
                    <DialogTitle className="text-slate-100">Import Properties from E-Bloc.ro</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4">
                    <p className="text-sm text-slate-400">
                      Connect your e-bloc.ro account to discover and import properties. This will also import outstanding balances and payment receipts.
                    </p>
                    {error && eblocDiscoveredProperties.length === 0 && (
                      <div className="p-3 bg-red-900/50 border border-red-700 rounded text-red-200 text-sm">
                        {error}
                      </div>
                    )}
                    <div>
                      <Label className="text-slate-300">E-Bloc Username</Label>
                      <Input
                        value={eblocForm.username}
                        onChange={(e) => setEblocForm({ ...eblocForm, username: e.target.value })}
                        className="bg-slate-700 border-slate-600 text-slate-100"
                        placeholder="your-email@example.com"
                        disabled={eblocDiscovering || eblocImporting}
                      />
                    </div>
                    <div>
                      <Label className="text-slate-300">E-Bloc Password</Label>
                      <Input
                        type="password"
                        value={eblocForm.password}
                        onChange={(e) => setEblocForm({ ...eblocForm, password: e.target.value })}
                        className="bg-slate-700 border-slate-600 text-slate-100"
                        disabled={eblocDiscovering || eblocImporting}
                      />
                    </div>
                    {eblocDiscoveredProperties.length === 0 ? (
                      <Button 
                        onClick={handleDiscoverEbloc} 
                        className="w-full bg-emerald-600 hover:bg-emerald-700"
                        disabled={eblocDiscovering || !eblocForm.username || !eblocForm.password}
                      >
                        {eblocDiscovering ? (
                          <>
                            <Spinner className="w-4 h-4 mr-2" />
                            Discovering...
                          </>
                        ) : (
                          'Discover Properties'
                        )}
                      </Button>
                    ) : (
                      <div className="space-y-4">
                        <div>
                          <Label className="text-slate-300">Select Property to Import</Label>
                          <Select
                            value={eblocForm.selectedPropertyId}
                            onValueChange={(v) => {
                              console.log('[E-Bloc] Property selected:', v);
                              setEblocForm({ ...eblocForm, selectedPropertyId: v });
                            }}
                            disabled={eblocImporting}
                          >
                            <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                              <SelectValue placeholder="Select property" />
                            </SelectTrigger>
                            <SelectContent className="bg-slate-700 border-slate-600">
                              {eblocDiscoveredProperties.map((prop) => (
                                <SelectItem key={prop.page_id} value={prop.page_id} data-url={prop.url}>
                                  {prop.name} - {prop.address}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            onClick={() => handleConfigureEbloc()}
                            className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                            disabled={eblocImporting || !eblocForm.selectedPropertyId}
                          >
                            {eblocImporting ? (
                              <>
                                <Spinner className="w-4 h-4 mr-2" />
                                Importing...
                              </>
                            ) : (
                              'Import Selected'
                            )}
                          </Button>
                          {eblocDiscoveredProperties.length > 1 && (
                            <Button
                              onClick={handleImportEblocProperties}
                              variant="outline"
                              className="flex-1 border-slate-600 text-slate-300"
                              disabled={eblocImporting}
                            >
                              {eblocImporting ? (
                                <>
                                  <Spinner className="w-4 h-4 mr-2" />
                                  Importing...
                                </>
                              ) : (
                                `Import All (${eblocDiscoveredProperties.length})`
                              )}
                            </Button>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </DialogContent>
              </Dialog>
              <Dialog open={showPropertyForm} onOpenChange={setShowPropertyForm}>
                <DialogTrigger asChild>
                  <Button
                    className="bg-emerald-600 hover:bg-emerald-700"
                    disabled={subscription ? !subscription.can_add_property : false}
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Add Property
                  </Button>
                </DialogTrigger>
              <DialogContent className="bg-slate-800 border-slate-700">
                <DialogHeader>
                  <DialogTitle className="text-slate-100">Add Property</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label className="text-slate-300">Name</Label>
                    <Input
                      value={propertyForm.name}
                      onChange={(e) => setPropertyForm({ ...propertyForm, name: e.target.value })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                      placeholder="My Apartment Building"
                    />
                  </div>
                  <div>
                    <Label className="text-slate-300">Address</Label>
                    <Input
                      value={propertyForm.address}
                      onChange={(e) => setPropertyForm({ ...propertyForm, address: e.target.value })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                      placeholder="123 Main St, City"
                    />
                  </div>
                  <Button onClick={handleCreateProperty} className="w-full bg-emerald-600 hover:bg-emerald-700">
                    Create Property
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
            </div>
          </div>

          {loading ? (
            <div className="text-slate-400 text-center py-8">Loading...</div>
          ) : properties.length === 0 ? (
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="py-8 text-center text-slate-400">
                No properties yet. Add your first property to get started.
              </CardContent>
            </Card>
          ) : (
            properties.map((property) => (
              <Card key={property.id} className="bg-slate-800 border-slate-700">
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="text-slate-100">{property.name}</CardTitle>
                    <p className="text-sm text-slate-400">{property.address}</p>
                  </div>
                  <div className="flex gap-2">
                    <Dialog open={showUnitForm === property.id} onOpenChange={(open) => setShowUnitForm(open ? property.id : null)}>
                      <DialogTrigger asChild>
                        <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700">
                          <Plus className="w-4 h-4 mr-1" />
                          Add Unit
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="bg-slate-800 border-slate-700">
                        <DialogHeader>
                          <DialogTitle className="text-slate-100">Add Unit</DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4">
                          <div>
                            <Label className="text-slate-300">Unit Number</Label>
                            <Input
                              value={unitForm.unit_number}
                              onChange={(e) => setUnitForm({ unit_number: e.target.value })}
                              className="bg-slate-700 border-slate-600 text-slate-100"
                              placeholder="Apt 101"
                            />
                          </div>
                          <Button onClick={() => handleCreateUnit(property.id)} className="w-full bg-emerald-600 hover:bg-emerald-700">
                            Add Unit
                          </Button>
                        </div>
                      </DialogContent>
                    </Dialog>
                    <Dialog open={showEblocConfig === property.id} onOpenChange={(open) => setShowEblocConfig(open ? property.id : null)}>
                      <DialogTrigger asChild>
                        <Button variant="outline" size="sm" className="border-slate-600 text-slate-300">
                          Sync E-Bloc
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="bg-slate-800 border-slate-700">
                        <DialogHeader>
                          <DialogTitle className="text-slate-100">Sync E-Bloc.ro</DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4">
                          <p className="text-sm text-slate-400">
                            Sync outstanding balances and payment receipts from your e-bloc.ro account.
                          </p>
                          <Button
                            onClick={async () => {
                              if (!token) return;
                              try {
                                const result = await api.ebloc.sync(token, property.id);
                                setShowEblocConfig(null);
                                loadData();
                                if (result.bills_created > 0 || result.payments_created > 0) {
                                  setError('');
                                  // Show success message
                                  alert(`Synced successfully! Created ${result.bills_created} bills and ${result.payments_created} payments.`);
                                }
                              } catch (err) {
                                handleError(err);
                              }
                            }}
                            className="w-full bg-emerald-600 hover:bg-emerald-700"
                          >
                            Sync Now
                          </Button>
                        </div>
                      </DialogContent>
                    </Dialog>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteProperty(property.id)}
                      className="text-red-400 hover:text-red-200 hover:bg-red-900/20"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  {(units[property.id] || []).length === 0 ? (
                    <p className="text-slate-500 text-sm">No units yet</p>
                  ) : (
                    <div className="space-y-3">
                      {(units[property.id] || []).map((unit) => (
                        <div key={unit.id} className="bg-slate-700/50 rounded p-3">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-slate-200 font-medium">{unit.unit_number}</span>
                            <Dialog open={showRenterForm === unit.id} onOpenChange={(open) => setShowRenterForm(open ? unit.id : null)}>
                              <DialogTrigger asChild>
                                <Button size="sm" variant="ghost" className="text-slate-400 hover:text-slate-100">
                                  <Users className="w-4 h-4 mr-1" />
                                  Add Renter
                                </Button>
                              </DialogTrigger>
                              <DialogContent className="bg-slate-800 border-slate-700">
                                <DialogHeader>
                                  <DialogTitle className="text-slate-100">Add Renter</DialogTitle>
                                </DialogHeader>
                                <div className="space-y-4">
                                  <div>
                                    <Label className="text-slate-300">Name</Label>
                                    <Input
                                      value={renterForm.name}
                                      onChange={(e) => setRenterForm({ ...renterForm, name: e.target.value })}
                                      className="bg-slate-700 border-slate-600 text-slate-100"
                                    />
                                  </div>
                                  <div>
                                    <Label className="text-slate-300">Email (optional)</Label>
                                    <Input
                                      value={renterForm.email}
                                      onChange={(e) => setRenterForm({ ...renterForm, email: e.target.value })}
                                      className="bg-slate-700 border-slate-600 text-slate-100"
                                    />
                                  </div>
                                  <div>
                                    <Label className="text-slate-300">Phone (optional)</Label>
                                    <Input
                                      value={renterForm.phone}
                                      onChange={(e) => setRenterForm({ ...renterForm, phone: e.target.value })}
                                      className="bg-slate-700 border-slate-600 text-slate-100"
                                    />
                                  </div>
                                  <Button onClick={() => handleCreateRenter(unit.id)} className="w-full bg-emerald-600 hover:bg-emerald-700">
                                    Add Renter
                                  </Button>
                                </div>
                              </DialogContent>
                            </Dialog>
                          </div>
                          {(renters[unit.id] || []).length === 0 ? (
                            <p className="text-slate-500 text-xs">No renters</p>
                          ) : (
                            <div className="space-y-1">
                              {(renters[unit.id] || []).map((renter) => (
                                <div key={renter.id} className="flex items-center justify-between text-sm">
                                  <span className="text-slate-300">{renter.name}</span>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => handleGetRenterLink(renter.id)}
                                    className="text-emerald-400 hover:text-emerald-300 h-6 px-2"
                                  >
                                    <ExternalLink className="w-3 h-3 mr-1" />
                                    Get Link
                                  </Button>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
                
                {/* Bills Section for this Property */}
                <CardContent className="pt-0">
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
                            id={`pdf-upload-${property.id}`}
                            style={{ display: 'none' }}
                            onChange={async (e) => {
                              const file = e.target.files?.[0];
                              if (!file || !token) return;
                              try {
                                // TODO: Implement PDF upload endpoint
                                console.log('[Bills] PDF upload for property:', property.id, file.name);
                                setError('PDF upload functionality coming soon');
                              } catch (err) {
                                handleError(err);
                              }
                            }}
                          />
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => document.getElementById(`pdf-upload-${property.id}`)?.click()}
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
                                console.log('[Bills] Sync utilities for property:', property.id);
                                setError('Utilities sync functionality coming soon');
                              } catch (err) {
                                handleError(err);
                              }
                            }}
                            className="border-slate-600 text-slate-300"
                          >
                            <Settings className="w-4 h-4 mr-1" />
                            Sync Utilities
                          </Button>
                          <Dialog open={showBillForm && billForm.property_id === property.id} onOpenChange={(open) => {
                            if (!open) {
                              setShowBillForm(false);
                              setBillForm({ ...billForm, property_id: '' });
                            } else {
                              setBillForm({ ...billForm, property_id: property.id });
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
                                <DialogTitle className="text-slate-100">Add Bill</DialogTitle>
                              </DialogHeader>
                              <div className="space-y-4">
                                <div>
                                  <Label className="text-slate-300">Unit</Label>
                                  <Select value={billForm.unit_id} onValueChange={(v) => setBillForm({ ...billForm, unit_id: v })}>
                                    <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                                      <SelectValue placeholder="Select unit" />
                                    </SelectTrigger>
                                    <SelectContent className="bg-slate-700 border-slate-600">
                                      {(units[property.id] || []).map((unit) => (
                                        <SelectItem key={unit.id} value={unit.id}>{unit.unit_number}</SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                </div>
                                <div>
                                  <Label className="text-slate-300">Type</Label>
                                  <Select value={billForm.bill_type} onValueChange={(v) => setBillForm({ ...billForm, bill_type: v as typeof billForm.bill_type })}>
                                    <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                                      <SelectValue />
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
                                  <Label className="text-slate-300">Description</Label>
                                  <Input
                                    value={billForm.description}
                                    onChange={(e) => setBillForm({ ...billForm, description: e.target.value })}
                                    className="bg-slate-700 border-slate-600 text-slate-100"
                                  />
                                </div>
                                <div>
                                  <Label className="text-slate-300">Amount</Label>
                                  <Input
                                    type="number"
                                    value={billForm.amount}
                                    onChange={(e) => setBillForm({ ...billForm, amount: e.target.value })}
                                    className="bg-slate-700 border-slate-600 text-slate-100"
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
                                <div>
                                  <Label className="text-slate-300">IBAN (for bank transfer)</Label>
                                  <Input
                                    value={billForm.iban}
                                    onChange={(e) => setBillForm({ ...billForm, iban: e.target.value })}
                                    className="bg-slate-700 border-slate-600 text-slate-100"
                                    placeholder="RO49AAAA1B31007593840000"
                                  />
                                </div>
                                <div>
                                  <Label className="text-slate-300">Bill Number</Label>
                                  <Input
                                    value={billForm.bill_number}
                                    onChange={(e) => setBillForm({ ...billForm, bill_number: e.target.value })}
                                    className="bg-slate-700 border-slate-600 text-slate-100"
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
                            <TableHead className="text-slate-400">Unit</TableHead>
                            <TableHead className="text-slate-400">Description</TableHead>
                            <TableHead className="text-slate-400">Type</TableHead>
                            <TableHead className="text-slate-400">Amount</TableHead>
                            <TableHead className="text-slate-400">Due Date</TableHead>
                            <TableHead className="text-slate-400">Status</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(() => {
                            // Get all units for this property
                            const propertyUnits = units[property.id] || [];
                            const propertyUnitIds = new Set(propertyUnits.map(u => u.id));
                            // Filter bills for units in this property
                            const propertyBills = bills.filter(bill => propertyUnitIds.has(bill.unit_id));
                            
                            if (propertyBills.length === 0) {
                              return (
                                <TableRow>
                                  <TableCell colSpan={6} className="text-slate-500 text-center py-4">
                                    No bills yet for this property
                                  </TableCell>
                                </TableRow>
                              );
                            }
                            
                            return propertyBills.map((bill) => {
                              const unit = propertyUnits.find(u => u.id === bill.unit_id);
                              return (
                                <TableRow key={bill.id} className="border-slate-700">
                                  <TableCell className="text-slate-300">{unit?.unit_number || 'Unknown'}</TableCell>
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
                            });
                          })()}
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>

        <TabsContent value="bills" className="space-y-4" style={{ display: 'none' }}>
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-medium text-slate-100">Bills</h2>
            <Dialog open={showBillForm} onOpenChange={setShowBillForm}>
              <DialogTrigger asChild>
                <Button className="bg-emerald-600 hover:bg-emerald-700">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Bill
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-slate-800 border-slate-700">
                <DialogHeader>
                  <DialogTitle className="text-slate-100">Add Bill</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label className="text-slate-300">Unit</Label>
                    <Select value={billForm.unit_id} onValueChange={(v) => setBillForm({ ...billForm, unit_id: v })}>
                      <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                        <SelectValue placeholder="Select unit" />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-700 border-slate-600">
                        {allUnits.map((unit) => (
                          <SelectItem key={unit.id} value={unit.id}>{unit.unit_number}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-slate-300">Type</Label>
                    <Select value={billForm.bill_type} onValueChange={(v) => setBillForm({ ...billForm, bill_type: v as typeof billForm.bill_type })}>
                      <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                        <SelectValue />
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
                    <Label className="text-slate-300">Description</Label>
                    <Input
                      value={billForm.description}
                      onChange={(e) => setBillForm({ ...billForm, description: e.target.value })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                    />
                  </div>
                  <div>
                    <Label className="text-slate-300">Amount</Label>
                    <Input
                      type="number"
                      value={billForm.amount}
                      onChange={(e) => setBillForm({ ...billForm, amount: e.target.value })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
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
                  <div>
                    <Label className="text-slate-300">IBAN (for bank transfer)</Label>
                    <Input
                      value={billForm.iban}
                      onChange={(e) => setBillForm({ ...billForm, iban: e.target.value })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                      placeholder="RO49AAAA1B31007593840000"
                    />
                  </div>
                  <div>
                    <Label className="text-slate-300">Bill Number</Label>
                    <Input
                      value={billForm.bill_number}
                      onChange={(e) => setBillForm({ ...billForm, bill_number: e.target.value })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                    />
                  </div>
                  <Button onClick={handleCreateBill} className="w-full bg-emerald-600 hover:bg-emerald-700">
                    Create Bill
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>

          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="border-slate-700">
                    <TableHead className="text-slate-400">Description</TableHead>
                    <TableHead className="text-slate-400">Type</TableHead>
                    <TableHead className="text-slate-400">Amount</TableHead>
                    <TableHead className="text-slate-400">Due Date</TableHead>
                    <TableHead className="text-slate-400">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {bills.map((bill) => (
                    <TableRow key={bill.id} className="border-slate-700">
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
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings" className="space-y-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100 flex items-center gap-2">
                <Mail className="w-5 h-5" />
                Email Bill Import
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-slate-400 text-sm">
                Configure email access to automatically import bills. You can either grant direct access to your Gmail
                or set up email forwarding to a dedicated address.
              </p>
              <Dialog open={showEmailConfig} onOpenChange={setShowEmailConfig}>
                <DialogTrigger asChild>
                  <Button variant="outline" className="border-slate-600 text-slate-300">
                    Configure Email
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-slate-800 border-slate-700">
                  <DialogHeader>
                    <DialogTitle className="text-slate-100">Email Configuration</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div>
                      <Label className="text-slate-300">Access Type</Label>
                      <Select value={emailForm.config_type} onValueChange={(v) => setEmailForm({ ...emailForm, config_type: v as 'direct' | 'forwarding' })}>
                        <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-slate-700 border-slate-600">
                          <SelectItem value="direct">Direct Gmail Access</SelectItem>
                          <SelectItem value="forwarding">Email Forwarding</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    {emailForm.config_type === 'forwarding' && (
                      <div>
                        <Label className="text-slate-300">Forwarding Email</Label>
                        <Input
                          value={emailForm.forwarding_email}
                          onChange={(e) => setEmailForm({ ...emailForm, forwarding_email: e.target.value })}
                          className="bg-slate-700 border-slate-600 text-slate-100"
                          placeholder="bills@promanage.local"
                        />
                        <p className="text-xs text-slate-500 mt-1">
                          Forward your utility bills to this address for automatic processing
                        </p>
                      </div>
                    )}
                    {emailForm.config_type === 'direct' && (
                      <p className="text-sm text-slate-400">
                        Direct Gmail access requires OAuth configuration. Contact support to enable this feature.
                      </p>
                    )}
                    <Button onClick={handleConfigureEmail} className="w-full bg-emerald-600 hover:bg-emerald-700">
                      Save Configuration
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </CardContent>
          </Card>

          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100">Subscription Status</CardTitle>
            </CardHeader>
            <CardContent>
              {subscription && (
                <div className="space-y-2">
                  <p className="text-slate-300">
                    Status: <span className={subscription.status === 'active' ? 'text-green-400' : 'text-amber-400'}>
                      {subscription.status}
                    </span>
                  </p>
                  <p className="text-slate-300">Properties: {subscription.property_count}</p>
                  {subscription.expires && (
                    <p className="text-slate-300">Expires: {new Date(subscription.expires).toLocaleDateString()}</p>
                  )}
                  {!subscription.can_add_property && (
                    <p className="text-amber-400 text-sm mt-2">
                      Upgrade to add more properties. Contact admin for subscription.
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={!!renterLink} onOpenChange={(open) => !open && setRenterLink(null)}>
        <DialogContent className="bg-slate-800 border-slate-700">
          <DialogHeader>
            <DialogTitle className="text-slate-100">Renter Access Link</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-slate-400 text-sm">
              Share this link with your renter. They can use it to view and pay their bills without logging in.
            </p>
            <div className="flex gap-2">
              <Input
                readOnly
                value={`${window.location.origin}/renter/${renterLink?.token}`}
                className="bg-slate-700 border-slate-600 text-slate-100"
              />
              <Button
                onClick={() => copyToClipboard(`${window.location.origin}/renter/${renterLink?.token}`)}
                variant="outline"
                className="border-slate-600"
              >
                <Copy className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

