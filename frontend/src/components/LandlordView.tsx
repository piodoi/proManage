import { useState, useEffect } from 'react';
import { api, Property, Renter, Bill, SubscriptionStatus } from '../api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Building2, Users, Settings, Copy, ExternalLink, Trash2, Pencil } from 'lucide-react';
import { Spinner } from '@/components/ui/spinner';
import PropertyBillsView from './PropertyBillsView';
import SettingsView from './SettingsView';

type LandlordViewProps = {
  token: string | null;
  onError?: (error: string) => void;
  hideSettings?: boolean;
};

export default function LandlordView({ token, onError, hideSettings = false }: LandlordViewProps) {
  const [properties, setProperties] = useState<Property[]>([]);
  const [renters, setRenters] = useState<Record<string, Renter[]>>({});
  const [bills, setBills] = useState<Bill[]>([]);
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showPropertyForm, setShowPropertyForm] = useState(false);
  const [showRenterForm, setShowRenterForm] = useState<string | null>(null);
  const [showEmailConfig, setShowEmailConfig] = useState(false);
  const [showEblocConfig, setShowEblocConfig] = useState<string | null>(null);
  const [showEblocDiscover, setShowEblocDiscover] = useState(false);
  const [eblocDiscoveredProperties, setEblocDiscoveredProperties] = useState<Array<{ page_id: string; name: string; address: string; url: string }>>([]);
  const [eblocDiscovering, setEblocDiscovering] = useState(false);
  const [eblocImporting, setEblocImporting] = useState(false);
  const [propertyForm, setPropertyForm] = useState({ name: '', address: '' });
  const [renterForm, setRenterForm] = useState({ name: '', rent_date: '', rent_amount: '', rent_currency: 'EUR' as 'EUR' | 'RON' | 'USD', email: '', phone: '' });
  const [editingRenter, setEditingRenter] = useState<Renter | null>(null);
  const [exchangeRates, setExchangeRates] = useState<{ EUR: number; USD: number; RON: number }>({ EUR: 1, USD: 1, RON: 4.97 });
  const [emailForm, setEmailForm] = useState({ config_type: 'forwarding' as 'direct' | 'forwarding', forwarding_email: '' });
  const [eblocForm, setEblocForm] = useState({ username: '', password: '', selectedPropertyId: '' });
  const [renterLink, setRenterLink] = useState<{ token: string; link: string } | null>(null);

  useEffect(() => {
    loadData();
    loadExchangeRates();
  }, [token]);

  // Load exchange rates
  const loadExchangeRates = async () => {
    try {
      // Use exchangerate-api.com (free, no API key needed for basic usage)
      const response = await fetch('https://api.exchangerate-api.com/v4/latest/EUR');
      if (!response.ok) throw new Error('Failed to fetch exchange rates');
      const data = await response.json();
      setExchangeRates({
        EUR: 1,
        USD: data.rates?.USD || 1.1,
        RON: data.rates?.RON || 4.97, // EUR to RON rate
      });
      console.log('[LandlordView] Exchange rates loaded:', { EUR: 1, USD: data.rates?.USD || 1.1, RON: data.rates?.RON || 4.97 });
    } catch (err) {
      console.error('[LandlordView] Failed to load exchange rates:', err);
      // Fallback to approximate rates
      setExchangeRates({ EUR: 1, USD: 1.1, RON: 4.97 });
    }
  };

  // Get rent bill info for a renter
  const getRenterRentInfo = (renter: Renter): { amount: number; due_date: string; currency: 'EUR' | 'RON' | 'USD' } | null => {
    console.log('[LandlordView] getRenterRentInfo called for renter:', renter.id, {
      renter_unit_id: renter.unit_id,
      total_bills: bills.length,
      bills_for_unit: bills.filter(b => b.unit_id === renter.unit_id),
      bills_details: bills.filter(b => b.unit_id === renter.unit_id).map(b => ({
        id: b.id,
        unit_id: b.unit_id,
        bill_type: b.bill_type,
        amount: b.amount,
        due_date: b.due_date
      }))
    });
    
    // Find rent bills for this renter's unit
    const rentBills = bills.filter(b => b.unit_id === renter.unit_id && b.bill_type === 'rent');
    console.log('[LandlordView] Rent bills found:', rentBills.length, rentBills);
    
    if (rentBills.length === 0) {
      // Check if there are any bills for this unit with different bill_type
      const unitBills = bills.filter(b => b.unit_id === renter.unit_id);
      if (unitBills.length > 0) {
        console.log('[LandlordView] No rent bills, but found other bills for unit:', unitBills.map(b => ({ type: b.bill_type, amount: b.amount })));
      }
      return null;
    }

    // Get the most recent rent bill
    const latestRentBill = rentBills.sort((a, b) => 
      new Date(b.due_date).getTime() - new Date(a.due_date).getTime()
    )[0];

    console.log('[LandlordView] Using latest rent bill:', latestRentBill);
    return {
      amount: latestRentBill.amount,
      due_date: latestRentBill.due_date,
      currency: 'EUR' as 'EUR' | 'RON' | 'USD', // Default to EUR, could be stored in bill later
    };
  };

  // Sync form when editing renter changes
  useEffect(() => {
    if (editingRenter) {
      console.log('[LandlordView] Populating form for renter:', editingRenter.id, { 
        renter: { 
          name: editingRenter.name, 
          email: editingRenter.email, 
          phone: editingRenter.phone,
          rent_date: editingRenter.rent_date,
          rent_amount_eur: editingRenter.rent_amount_eur
        }
      });
      
      // Format date properly for date input (YYYY-MM-DD)
      let formattedDate = '';
      if (editingRenter.rent_date) {
        try {
          const date = new Date(editingRenter.rent_date);
          if (!isNaN(date.getTime())) {
            formattedDate = date.toISOString().split('T')[0];
          }
        } catch (e) {
          console.error('[LandlordView] Error formatting date:', e, editingRenter.rent_date);
        }
      }
      
      // Format amount as string for number input
      const formattedAmount = editingRenter.rent_amount_eur ? editingRenter.rent_amount_eur.toString() : '';
      
      console.log('[LandlordView] Setting form values:', {
        name: editingRenter.name || '',
        rent_date: formattedDate,
        rent_amount: formattedAmount,
        rent_currency: 'EUR', // Default to EUR for now
        email: editingRenter.email || '',
        phone: editingRenter.phone || ''
      });
      
      setRenterForm({ 
        name: editingRenter.name || '', 
        rent_date: formattedDate,
        rent_amount: formattedAmount,
        rent_currency: 'EUR', // Default to EUR for now
        email: editingRenter.email || '', 
        phone: editingRenter.phone || '' 
      });
    } else {
      // Reset form when not editing
      setRenterForm({ name: '', rent_date: '', rent_amount: '', rent_currency: 'EUR', email: '', phone: '' });
    }
  }, [editingRenter]);

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
      
      console.log('[LandlordView] Loading renters...');
      for (const prop of propsData) {
        const rentersData = await api.renters.list(token, prop.id);
        console.log(`[LandlordView] Property ${prop.name}: ${rentersData.length} renters`);
        setRenters((prev) => ({ ...prev, [prop.id]: rentersData }));
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


  const handleCreateRenter = async (propertyId: string) => {
    if (!token) return;
    if (!renterForm.name || !renterForm.rent_amount) {
      handleError(new Error('Name and rent amount are required'));
      return;
    }
    try {
      // Default date to 1st of current month if not provided
      const rentDate = renterForm.rent_date || new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0];
      
      // Convert amount to EUR if needed (for now, assume input is in selected currency)
      // TODO: Implement proper currency conversion
      const rentAmountEUR = parseFloat(renterForm.rent_amount);
      
      // Create renter with all info including rent details
      await api.renters.create(token, propertyId, {
        name: renterForm.name,
        email: renterForm.email || undefined,
        phone: renterForm.phone || undefined,
        rent_date: rentDate,
        rent_amount_eur: rentAmountEUR,
      });
      
      setShowRenterForm(null);
      setEditingRenter(null);
      setRenterForm({ name: '', rent_date: '', rent_amount: '', rent_currency: 'EUR', email: '', phone: '' });
      await loadData();
    } catch (err) {
      handleError(err);
    }
  };

  const handleUpdateRenter = async (renterId: string) => {
    if (!token || !editingRenter) return;
    if (!renterForm.name || !renterForm.rent_amount) {
      handleError(new Error('Name and rent amount are required'));
      return;
    }
    try {
      // Default date to 1st of current month if not provided
      const rentDate = renterForm.rent_date || new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0];
      
      // Convert amount to EUR if needed (for now, assume input is in selected currency)
      // TODO: Implement proper currency conversion
      const rentAmountEUR = parseFloat(renterForm.rent_amount);
      
      await api.renters.update(token, renterId, {
        name: renterForm.name,
        email: renterForm.email || undefined,
        phone: renterForm.phone || undefined,
        rent_date: rentDate,
        rent_amount_eur: rentAmountEUR,
      });
      setEditingRenter(null);
      setShowRenterForm(null);
      setRenterForm({ name: '', rent_date: '', rent_amount: '', rent_currency: 'EUR', email: '', phone: '' });
      await loadData();
    } catch (err) {
      handleError(err);
    }
  };

  const handleDeleteRenter = async (renterId: string) => {
    if (!token) return;
    if (!confirm('Are you sure you want to delete this renter? This will also delete all associated bills.')) {
      return;
    }
    try {
      await api.renters.delete(token, renterId);
      await loadData();
    } catch (err) {
      handleError(err);
    }
  };

  const openEditRenter = (renter: Renter) => {
    // Find the unit this renter belongs to first
    let targetUnitId: string | null = null;
    for (const [unitId, unitRenters] of Object.entries(renters)) {
      if (unitRenters.some(r => r.id === renter.id)) {
        targetUnitId = unitId;
        break;
      }
    }
    
    if (targetUnitId) {
      setEditingRenter(renter);
      setShowRenterForm(targetUnitId);
      // Form will be populated by useEffect when editingRenter changes
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

  return (
    <>
      {error && (
        <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded text-red-200">
          {error}
          <button onClick={() => setError('')} className="ml-2 text-red-400 hover:text-red-200">x</button>
        </div>
      )}

      {hideSettings ? (
        <div className="space-y-4">
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
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-slate-200 font-medium">Renters</span>
                    <Dialog open={showRenterForm === property.id && (editingRenter === null || renters[property.id]?.some(r => r.id === editingRenter.id))} onOpenChange={(open) => {
                      if (!open) {
                        setShowRenterForm(null);
                        setEditingRenter(null);
                        // Form will be reset by useEffect when editingRenter becomes null
                      } else {
                        setShowRenterForm(property.id);
                      }
                    }}>
                      <DialogTrigger asChild>
                        <Button size="sm" variant="ghost" className="text-slate-400 hover:text-slate-100">
                          <Users className="w-4 h-4 mr-1" />
                          Add Renter
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="bg-slate-800 border-slate-700" key={`renter-dialog-${editingRenter?.id || 'new'}`}>
                        <DialogHeader>
                          <DialogTitle className="text-slate-100">
                            {editingRenter ? 'Edit Renter' : 'Add Renter'}
                          </DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4">
                          <div>
                            <Label className="text-slate-300">Name *</Label>
                            <Input
                              key={`name-${editingRenter?.id || 'new'}`}
                              value={renterForm.name}
                              onChange={(e) => setRenterForm({ ...renterForm, name: e.target.value })}
                              className="bg-slate-700 border-slate-600 text-slate-100"
                              placeholder="Renter name"
                              required
                            />
                          </div>
                          <div>
                            <Label className="text-slate-300">Rent Date (Due Date)</Label>
                            <Input
                              key={`rent_date-${editingRenter?.id || 'new'}`}
                              type="date"
                              value={renterForm.rent_date}
                              onChange={(e) => setRenterForm({ ...renterForm, rent_date: e.target.value })}
                              className="bg-slate-700 border-slate-600 text-slate-100"
                            />
                            <p className="text-xs text-slate-500 mt-1">
                              Defaults to 1st of current month if not filled
                            </p>
                          </div>
                          <div>
                            <Label className="text-slate-300">Rent Amount *</Label>
                            <div className="flex gap-2 items-center">
                              <Input
                                key={`rent_amount-${editingRenter?.id || 'new'}`}
                                type="number"
                                step="0.01"
                                value={renterForm.rent_amount}
                                onChange={(e) => setRenterForm({ ...renterForm, rent_amount: e.target.value })}
                                className="bg-slate-700 border-slate-600 text-slate-100 w-32 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                                placeholder="0.00"
                                required
                              />
                              <Select 
                                key={`rent_currency-${editingRenter?.id || 'new'}`}
                                value={renterForm.rent_currency} 
                                onValueChange={(v) => setRenterForm({ ...renterForm, rent_currency: v as 'EUR' | 'RON' | 'USD' })}
                              >
                                <SelectTrigger className="w-20 h-10 bg-slate-700 border-slate-600 text-slate-100">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent className="bg-slate-700 border-slate-600">
                                  <SelectItem value="EUR">EUR</SelectItem>
                                  <SelectItem value="RON">RON</SelectItem>
                                  <SelectItem value="USD">USD</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                            <p className="text-xs text-slate-500 mt-1">
                              Will be converted to RON automatically if needed
                            </p>
                          </div>
                          <div>
                            <Label className="text-slate-300">Phone (optional)</Label>
                            <Input
                              key={`phone-${editingRenter?.id || 'new'}`}
                              type="tel"
                              value={renterForm.phone}
                              onChange={(e) => setRenterForm({ ...renterForm, phone: e.target.value })}
                              className="bg-slate-700 border-slate-600 text-slate-100"
                              placeholder="+40 123 456 789"
                            />
                          </div>
                          <div>
                            <Label className="text-slate-300">Email (optional)</Label>
                            <Input
                              key={`email-${editingRenter?.id || 'new'}`}
                              type="email"
                              value={renterForm.email}
                              onChange={(e) => setRenterForm({ ...renterForm, email: e.target.value })}
                              className="bg-slate-700 border-slate-600 text-slate-100"
                              placeholder="renter@example.com"
                            />
                          </div>
                          <Button 
                            onClick={() => editingRenter ? handleUpdateRenter(editingRenter.id) : handleCreateRenter(property.id)} 
                            className="w-full bg-emerald-600 hover:bg-emerald-700"
                            disabled={!renterForm.name || !renterForm.rent_amount}
                          >
                            {editingRenter ? 'Update Renter' : 'Add Renter'}
                          </Button>
                        </div>
                      </DialogContent>
                    </Dialog>
                  </div>
                  {(renters[property.id] || []).length === 0 ? (
                    <p className="text-slate-500 text-xs">No renters yet</p>
                  ) : (
                    <div className="space-y-1">
                      {(renters[property.id] || []).map((renter) => {
                        const rentAmountEUR = renter.rent_amount_eur || 0;
                        // Convert to RON using live exchange rates
                        const rentAmountRON = rentAmountEUR > 0 
                          ? (rentAmountEUR * exchangeRates.RON).toFixed(2)
                          : '0.00';
                        
                        return (
                        <div key={renter.id} className="flex items-center justify-between text-sm">
                          <div className="flex items-center gap-2">
                            <span className="text-slate-300 font-medium">{renter.name}</span>
                            {(rentAmountEUR > 0 || renter.rent_date) && (
                              <span className="text-xs text-slate-400">
                                {rentAmountEUR > 0 && (
                                  <>
                                    <span>{rentAmountEUR.toFixed(2)} EUR</span>
                                    <span className="ml-1">({rentAmountRON} RON)</span>
                                  </>
                                )}
                                {renter.rent_date && (
                                  <span className="ml-2">• Due: {new Date(renter.rent_date).toLocaleDateString()}</span>
                                )}
                              </span>
                            )}
                          </div>
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => openEditRenter(renter)}
                              className="text-slate-400 hover:text-slate-200 h-6 px-2"
                              title="Edit renter"
                            >
                              <Pencil className="w-3 h-3" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleGetRenterLink(renter.id)}
                              className="text-emerald-400 hover:text-emerald-300 h-6 px-2"
                              title="Get renter link"
                            >
                              <ExternalLink className="w-3 h-3" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleDeleteRenter(renter.id)}
                              className="text-red-400 hover:text-red-200 h-6 px-2"
                              title="Delete renter"
                            >
                              <Trash2 className="w-3 h-3" />
                            </Button>
                          </div>
                        </div>
                      );
                      })}
                    </div>
                  )}
                </CardContent>
                
                {/* Bills Section for this Property */}
                <CardContent className="pt-0">
                  <PropertyBillsView
                    token={token}
                    propertyId={property.id}
                    renters={renters[property.id] || []}
                    bills={bills}
                    onError={setError}
                    onBillsChange={loadData}
                  />
                </CardContent>
              </Card>
            ))
          )}
        </div>
      ) : (
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
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-slate-200 font-medium">Renters</span>
                      <Dialog open={showRenterForm === property.id && (editingRenter === null || renters[property.id]?.some(r => r.id === editingRenter.id))} onOpenChange={(open) => {
                        if (!open) {
                          setShowRenterForm(null);
                          setEditingRenter(null);
                          // Form will be reset by useEffect when editingRenter becomes null
                        } else {
                          setShowRenterForm(property.id);
                        }
                      }}>
                        <DialogTrigger asChild>
                          <Button size="sm" variant="ghost" className="text-slate-400 hover:text-slate-100">
                            <Users className="w-4 h-4 mr-1" />
                            Add Renter
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="bg-slate-800 border-slate-700" key={`renter-dialog-${editingRenter?.id || 'new'}`}>
                          <DialogHeader>
                            <DialogTitle className="text-slate-100">
                              {editingRenter ? 'Edit Renter' : 'Add Renter'}
                            </DialogTitle>
                          </DialogHeader>
                          <div className="space-y-4">
                            <div>
                              <Label className="text-slate-300">Name *</Label>
                              <Input
                                key={`name-${editingRenter?.id || 'new'}`}
                                value={renterForm.name}
                                onChange={(e) => setRenterForm({ ...renterForm, name: e.target.value })}
                                className="bg-slate-700 border-slate-600 text-slate-100"
                                placeholder="Renter name"
                                required
                              />
                            </div>
                            <div>
                              <Label className="text-slate-300">Rent Date (Due Date)</Label>
                              <Input
                                key={`rent_date-${editingRenter?.id || 'new'}`}
                                type="date"
                                value={renterForm.rent_date}
                                onChange={(e) => setRenterForm({ ...renterForm, rent_date: e.target.value })}
                                className="bg-slate-700 border-slate-600 text-slate-100"
                              />
                              <p className="text-xs text-slate-500 mt-1">
                                Defaults to 1st of current month if not filled
                              </p>
                            </div>
                            <div>
                              <Label className="text-slate-300">Rent Amount *</Label>
                              <div className="flex gap-2 items-center">
                                <Input
                                  key={`rent_amount-${editingRenter?.id || 'new'}`}
                                  type="number"
                                  step="0.01"
                                  value={renterForm.rent_amount}
                                  onChange={(e) => setRenterForm({ ...renterForm, rent_amount: e.target.value })}
                                  className="bg-slate-700 border-slate-600 text-slate-100 w-32 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                                  placeholder="0.00"
                                  required
                                />
                                <Select 
                                  key={`rent_currency-${editingRenter?.id || 'new'}`}
                                  value={renterForm.rent_currency} 
                                  onValueChange={(v) => setRenterForm({ ...renterForm, rent_currency: v as 'EUR' | 'RON' | 'USD' })}
                                >
                                  <SelectTrigger className="w-20 h-10 bg-slate-700 border-slate-600 text-slate-100">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent className="bg-slate-700 border-slate-600">
                                    <SelectItem value="EUR">EUR</SelectItem>
                                    <SelectItem value="RON">RON</SelectItem>
                                    <SelectItem value="USD">USD</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                              <p className="text-xs text-slate-500 mt-1">
                                Will be converted to RON automatically if needed
                              </p>
                            </div>
                            <div>
                              <Label className="text-slate-300">Phone (optional)</Label>
                              <Input
                                key={`phone-${editingRenter?.id || 'new'}`}
                                type="tel"
                                value={renterForm.phone}
                                onChange={(e) => setRenterForm({ ...renterForm, phone: e.target.value })}
                                className="bg-slate-700 border-slate-600 text-slate-100"
                                placeholder="+40 123 456 789"
                              />
                            </div>
                            <div>
                              <Label className="text-slate-300">Email (optional)</Label>
                              <Input
                                key={`email-${editingRenter?.id || 'new'}`}
                                type="email"
                                value={renterForm.email}
                                onChange={(e) => setRenterForm({ ...renterForm, email: e.target.value })}
                                className="bg-slate-700 border-slate-600 text-slate-100"
                                placeholder="renter@example.com"
                              />
                            </div>
                            <Button 
                              onClick={() => editingRenter ? handleUpdateRenter(editingRenter.id) : handleCreateRenter(property.id)} 
                              className="w-full bg-emerald-600 hover:bg-emerald-700"
                              disabled={!renterForm.name || !renterForm.rent_amount}
                            >
                              {editingRenter ? 'Update Renter' : 'Add Renter'}
                            </Button>
                          </div>
                        </DialogContent>
                      </Dialog>
                    </div>
                    {(renters[property.id] || []).length === 0 ? (
                      <p className="text-slate-500 text-xs">No renters yet</p>
                    ) : (
                      <div className="space-y-1">
                        {(renters[property.id] || []).map((renter) => {
                          const rentAmountEUR = renter.rent_amount_eur || 0;
                          // Convert to RON using live exchange rates
                          const rentAmountRON = rentAmountEUR > 0 
                            ? (rentAmountEUR * exchangeRates.RON).toFixed(2)
                            : '0.00';
                          
                          return (
                          <div key={renter.id} className="flex items-center justify-between text-sm">
                            <div className="flex items-center gap-2">
                              <span className="text-slate-300 font-medium">{renter.name}</span>
                              {(rentAmountEUR > 0 || renter.rent_date) && (
                                <span className="text-xs text-slate-400">
                                  {rentAmountEUR > 0 && (
                                    <>
                                      <span>{rentAmountEUR.toFixed(2)} EUR</span>
                                      <span className="ml-1">({rentAmountRON} RON)</span>
                                    </>
                                  )}
                                  {renter.rent_date && (
                                    <span className="ml-2">• Due: {new Date(renter.rent_date).toLocaleDateString()}</span>
                                  )}
                                </span>
                              )}
                            </div>
                            <div className="flex gap-1">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => openEditRenter(renter)}
                                className="text-slate-400 hover:text-slate-200 h-6 px-2"
                                title="Edit renter"
                              >
                                <Pencil className="w-3 h-3" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleGetRenterLink(renter.id)}
                                className="text-emerald-400 hover:text-emerald-300 h-6 px-2"
                                title="Get renter link"
                              >
                                <ExternalLink className="w-3 h-3" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleDeleteRenter(renter.id)}
                                className="text-red-400 hover:text-red-200 h-6 px-2"
                                title="Delete renter"
                              >
                                <Trash2 className="w-3 h-3" />
                              </Button>
                            </div>
                          </div>
                        );
                        })}
                      </div>
                    )}
                  </CardContent>
                  
                  <CardContent className="pt-0">
                    <PropertyBillsView
                      token={token}
                      propertyId={property.id}
                      renters={renters[property.id] || []}
                      bills={bills}
                      onError={setError}
                      onBillsChange={loadData}
                    />
                  </CardContent>
                </Card>
              ))
            )}
          </TabsContent>

          <TabsContent value="settings" className="space-y-4">
            <SettingsView token={token} onError={onError} />
          </TabsContent>
        </Tabs>
      )}

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



