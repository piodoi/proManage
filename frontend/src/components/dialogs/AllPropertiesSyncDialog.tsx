import { useState, useEffect, useRef } from 'react';
import { api, Property, PropertySupplier, Renter } from '../../api';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Spinner } from '@/components/ui/spinner';
import { CheckCircle2, XCircle, Clock, AlertCircle } from 'lucide-react';
import { useI18n } from '../../lib/i18n';
import { usePreferences } from '../../hooks/usePreferences';

type SupplierProgress = {
  supplier_name: string;
  contract_id?: string;
  status: 'starting' | 'processing' | 'completed' | 'error';
  bills_found: number;
  bills_created: number;
  error?: string;
  properties_affected?: string[];
};

type DiscoveredBill = {
  id: string;
  property_id: string;
  property_name: string;
  supplier_name: string;
  bill_number?: string;
  amount: number;
  due_date: string;
  iban?: string;
  contract_id?: string;
  description: string;
  bill_data?: any;
};

type AllPropertiesSyncDialogProps = {
  token: string | null;
  properties: Property[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onError: (error: string) => void;
};

type Stage = 'options' | 'suppliers' | 'scraping' | 'bills';

export default function AllPropertiesSyncDialog({
  token,
  properties,
  open,
  onOpenChange,
  onSuccess,
  onError,
}: AllPropertiesSyncDialogProps) {
  const { t } = useI18n();
  const { preferences } = usePreferences();
  const [stage, setStage] = useState<Stage>('options');
  const [refreshRentBills, setRefreshRentBills] = useState(false);
  const [allPropertySuppliers, setAllPropertySuppliers] = useState<Map<string, PropertySupplier[]>>(new Map());
  const [selectedSupplierKeys, setSelectedSupplierKeys] = useState<Set<string>>(new Set());
  const [syncing, setSyncing] = useState(false);
  const [progress, setProgress] = useState<SupplierProgress[]>([]);
  const [discoveredBills, setDiscoveredBills] = useState<DiscoveredBill[]>([]);
  const [selectedBillIds, setSelectedBillIds] = useState<Set<string>>(new Set());
  const [syncId, setSyncId] = useState<string | null>(null);
  const [savingBills, setSavingBills] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const progressMapRef = useRef<Map<string, SupplierProgress>>(new Map());
  const discoveredBillsRef = useRef<DiscoveredBill[]>([]);

  // Load all property suppliers when dialog opens
  useEffect(() => {
    if (open && token) {
      loadAllPropertySuppliers();
      setStage('options');
      setRefreshRentBills(false);
      setSelectedSupplierKeys(new Set());
      setProgress([]);
      setDiscoveredBills([]);
      setSelectedBillIds(new Set());
      setSyncing(false);
      setSavingBills(false);
      progressMapRef.current.clear();
      discoveredBillsRef.current = [];
    }
  }, [open, token, properties]);

  const loadAllPropertySuppliers = async () => {
    if (!token) return;
    try {
      const suppliersMap = new Map<string, PropertySupplier[]>();
      
      for (const property of properties) {
        try {
          const suppliers = await api.suppliers.listForProperty(token, property.id);
          suppliersMap.set(property.id, suppliers);
        } catch (err) {
          console.error(`Failed to load suppliers for property ${property.id}:`, err);
        }
      }
      
      setAllPropertySuppliers(suppliersMap);
      
      // Group suppliers by supplier_id + contract_id to sync only once
      const supplierGroups = new Map<string, { supplier_id: string; contract_id?: string; supplier_name: string; properties: Property[] }>();
      
      suppliersMap.forEach((suppliers, propertyId) => {
        const property = properties.find(p => p.id === propertyId);
        if (!property) return;
        
        suppliers.forEach(ps => {
          if (ps.has_credentials) {
            const key = `${ps.supplier.id}_${ps.contract_id || 'no_contract'}`;
            if (!supplierGroups.has(key)) {
              supplierGroups.set(key, {
                supplier_id: ps.supplier.id,
                contract_id: ps.contract_id || undefined,
                supplier_name: ps.supplier.name,
                properties: []
              });
            }
            supplierGroups.get(key)!.properties.push(property);
          }
        });
      });
      
      // Auto-select all supplier groups
      setSelectedSupplierKeys(new Set(supplierGroups.keys()));
    } catch (err) {
      console.error('Failed to load property suppliers:', err);
      onError(err instanceof Error ? err.message : 'Failed to load suppliers');
    }
  };

  const getSupplierGroups = () => {
    const groups = new Map<string, { supplier_id: string; contract_id?: string; supplier_name: string; properties: Property[] }>();
    
    allPropertySuppliers.forEach((suppliers, propertyId) => {
      const property = properties.find(p => p.id === propertyId);
      if (!property) return;
      
      suppliers.forEach(ps => {
        if (ps.has_credentials) {
          const key = `${ps.supplier.id}_${ps.contract_id || 'no_contract'}`;
          if (!groups.has(key)) {
            groups.set(key, {
              supplier_id: ps.supplier.id,
              contract_id: ps.contract_id || undefined,
              supplier_name: ps.supplier.name,
              properties: []
            });
          }
          groups.get(key)!.properties.push(property);
        }
      });
    });
    
    return Array.from(groups.entries());
  };

  const supplierGroups = getSupplierGroups();

  const handleSelectAllSuppliers = () => {
    if (selectedSupplierKeys.size === supplierGroups.length) {
      setSelectedSupplierKeys(new Set());
    } else {
      setSelectedSupplierKeys(new Set(supplierGroups.map(([key]) => key)));
    }
  };

  const handleSupplierToggle = (key: string) => {
    const newSet = new Set(selectedSupplierKeys);
    if (newSet.has(key)) {
      newSet.delete(key);
    } else {
      newSet.add(key);
    }
    setSelectedSupplierKeys(newSet);
  };

  const handleStartSync = async () => {
    if (selectedSupplierKeys.size === 0) {
      onError('Please select at least one supplier');
      return;
    }

    // If refresh rent bills is checked, generate rent bills first
    if (refreshRentBills) {
      try {
        await generateRentBills();
      } catch (err) {
        onError(err instanceof Error ? err.message : 'Failed to generate rent bills');
        return;
      }
    }

    setStage('scraping');
    startScraping();
  };

  const generateRentBills = async () => {
    if (!token) return;
    
    const warningDays = preferences.rent_warning_days || 5;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    // Calculate due date: end of current month (or next month if we're past the warning period)
    const dueDate = new Date(today.getFullYear(), today.getMonth() + 1, 0); // Last day of current month
    dueDate.setHours(0, 0, 0, 0);
    
    // If we're too close to the end of the month, use next month's end
    const daysUntilEndOfMonth = dueDate.getDate() - today.getDate();
    if (daysUntilEndOfMonth < warningDays) {
      dueDate.setMonth(dueDate.getMonth() + 1);
      dueDate.setDate(0); // Last day of next month
    }
    
    // Calculate bill date: due_date - warning_days, but no less than 1st of the month
    const billDate = new Date(dueDate);
    billDate.setDate(billDate.getDate() - warningDays);
    
    // Ensure bill date is at least the 1st of the month
    if (billDate.getDate() < 1) {
      billDate.setDate(1);
    }
    
    // Use the month number as the bill number (from the due date month)
    const monthNumber = dueDate.getMonth() + 1;
    const billNumber = monthNumber.toString();
    
    // Get all renters for all properties
    const allRenters: Array<{ renter: Renter; property: Property }> = [];
    for (const property of properties) {
      try {
        const renters = await api.renters.list(token, property.id);
        renters.forEach(renter => {
          if (renter.rent_amount_eur && renter.rent_amount_eur > 0) {
            allRenters.push({ renter, property });
          }
        });
      } catch (err) {
        console.error(`Failed to load renters for property ${property.id}:`, err);
      }
    }
    
    // Get all existing bills once
    const existingBills = await api.bills.list(token);
    
    // Check existing bills and create/update
    for (const { renter, property } of allRenters) {
      try {
        // Find existing rent bill with same bill_number (month number)
        const existingRentBill = existingBills.find(
          bill => 
            bill.property_id === property.id &&
            bill.renter_id === renter.id &&
            bill.bill_type === 'rent' &&
            bill.bill_number === billNumber
        );
        
        const billData: any = {
          property_id: property.id,
          renter_id: renter.id,
          bill_type: 'rent' as const,
          description: t('bill.rent'),
          amount: renter.rent_amount_eur || 0,
          currency: preferences.rent_currency || 'EUR',
          due_date: dueDate.toISOString().split('T')[0],
          bill_date: billDate.toISOString().split('T')[0],
          bill_number: billNumber,
          status: 'pending' as const,
        };
        
        // Calculate status based on due date
        const dueDateObj = new Date(dueDate);
        dueDateObj.setHours(0, 0, 0, 0);
        if (dueDateObj < today) {
          billData.status = 'overdue';
        }
        
        if (existingRentBill) {
          // Update existing bill
          await api.bills.update(token, existingRentBill.id, billData);
        } else {
          // Create new bill
          await api.bills.create(token, billData);
        }
      } catch (err) {
        console.error(`Failed to create/update rent bill for renter ${renter.id}:`, err);
        throw err; // Re-throw to show error in UI
      }
    }
  };

  const startScraping = () => {
    if (!token || selectedSupplierKeys.size === 0) return;

    setSyncing(true);
    setProgress([]);
    progressMapRef.current.clear();
    discoveredBillsRef.current = [];
    const newSyncId = crypto.randomUUID();
    setSyncId(newSyncId);

    // Build sync request for all properties
    const selectedGroups = supplierGroups.filter(([key]) => selectedSupplierKeys.has(key));
    const syncData = {
      sync_id: newSyncId,
      supplier_groups: selectedGroups.map(([key, group]) => ({
        supplier_id: group.supplier_id,
        contract_id: group.contract_id,
        property_ids: group.properties.map(p => p.id),
      })),
      discover_only: true,
    };

    const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const abortController = new AbortController();

    fetch(`${apiBaseUrl}/suppliers/sync-all`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify(syncData),
      signal: abortController.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) {
          throw new Error('No response body');
        }

        let buffer = '';
        let currentEvent = '';
        let currentData = '';

        const readStream = async (): Promise<void> => {
          while (true) {
            const { done, value } = await reader.read();
            
            if (done) {
              break;
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (let i = 0; i < lines.length; i++) {
              const line = lines[i];

              if (line.startsWith('event: ')) {
                currentEvent = line.substring(7).trim();
              } else if (line.startsWith('data: ')) {
                currentData = line.substring(6);
                if (i === lines.length - 1 || lines[i + 1] === '' || lines[i + 1].startsWith('event: ')) {
                  try {
                    const eventData = JSON.parse(currentData);
                    handleSSEEvent(currentEvent || 'message', eventData);
                    currentEvent = '';
                    currentData = '';
                  } catch (e) {
                    console.error('Failed to parse SSE data:', e, currentData);
                  }
                } else {
                  currentData += '\n' + lines[i + 1].substring(6);
                  i++;
                }
              } else if (line === '' && currentEvent && currentData) {
                try {
                  const eventData = JSON.parse(currentData);
                  handleSSEEvent(currentEvent, eventData);
                  currentEvent = '';
                  currentData = '';
                } catch (e) {
                  console.error('Failed to parse SSE data:', e, currentData);
                }
              }
            }
          }
        };

        await readStream();
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setSyncing(false);
          const errorMsg = err instanceof Error ? err.message : 'Failed to sync supplier bills';
          onError(errorMsg);
        }
      });

    abortControllerRef.current = abortController;
  };

  const handleSSEEvent = (eventType: string, data: any) => {
    if (eventType === 'start') {
      setSyncing(true);
    } else if (eventType === 'progress') {
      const supplierProgress: SupplierProgress = {
        supplier_name: data.supplier_name,
        contract_id: data.contract_id,
        status: data.status,
        bills_found: data.bills_found || 0,
        bills_created: data.bills_created || 0,
        error: data.error,
        properties_affected: data.properties_affected || [],
      };

      const progressKey = `${data.supplier_name}_${data.contract_id || 'no_contract'}`;
      progressMapRef.current.set(progressKey, supplierProgress);
      setProgress(Array.from(progressMapRef.current.values()));

      if (data.bills && Array.isArray(data.bills)) {
        data.bills.forEach((bill: any) => {
          const property = properties.find(p => p.id === bill.property_id);
          const discoveredBill: DiscoveredBill = {
            id: crypto.randomUUID(),
            property_id: bill.property_id,
            property_name: property?.name || bill.property_id,
            supplier_name: data.supplier_name,
            bill_number: bill.bill_number || undefined,
            amount: bill.amount || 0,
            due_date: bill.due_date,
            iban: bill.iban || undefined,
            contract_id: bill.contract_id || undefined,
            description: bill.description || data.supplier_name,
            bill_data: { ...bill, property_id: bill.property_id },
          };
          discoveredBillsRef.current.push(discoveredBill);
        });
      }
    } else if (eventType === 'complete') {
      setSyncing(false);
      const filteredBills = discoveredBillsRef.current;
      setDiscoveredBills(filteredBills);
      setSelectedBillIds(new Set(filteredBills.map(b => b.id)));
      setStage('bills');
    } else if (eventType === 'error') {
      setSyncing(false);
      onError(data.error || 'Sync failed');
    } else if (eventType === 'cancelled') {
      setSyncing(false);
      setProgress((prev) =>
        prev.map((p) =>
          p.status === 'processing' || p.status === 'starting'
            ? { ...p, status: 'error' as const, error: 'Cancelled' }
            : p
        )
      );
      onOpenChange(false);
    }
  };

  const handleCancel = async () => {
    if (syncId && token) {
      try {
        const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        await fetch(`${apiBaseUrl}/suppliers/sync-all/cancel?sync_id=${syncId}`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
      } catch (err) {
        console.error('Failed to cancel sync:', err);
      }
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setSyncing(false);
    onOpenChange(false);
  };

  const handleSelectAllBills = () => {
    if (selectedBillIds.size === discoveredBills.length) {
      setSelectedBillIds(new Set());
    } else {
      setSelectedBillIds(new Set(discoveredBills.map(b => b.id)));
    }
  };

  const handleBillToggle = (billId: string) => {
    const newSet = new Set(selectedBillIds);
    if (newSet.has(billId)) {
      newSet.delete(billId);
    } else {
      newSet.add(billId);
    }
    setSelectedBillIds(newSet);
  };

  const handleSaveBills = async () => {
    if (!token || selectedBillIds.size === 0) {
      onError('Please select at least one bill to save');
      return;
    }

    setSavingBills(true);
    try {
      const billsToSave = discoveredBills
        .filter(b => selectedBillIds.has(b.id))
        .map(b => {
          if (b.bill_data) {
            return b.bill_data;
          }
          
          return {
            property_id: b.property_id,
            renter_id: null,
            bill_type: 'utilities',
            description: b.description,
            amount: b.amount,
            due_date: b.due_date,
            iban: b.iban || null,
            bill_number: b.bill_number || null,
            extraction_pattern_id: null,
            contract_id: b.contract_id || null,
            status: 'pending',
          };
        });
      
      const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      
      const response = await fetch(`${apiBaseUrl}/suppliers/sync-all/save-bills`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ bills: billsToSave }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || 'Failed to save bills');
      }

      onOpenChange(false);
      onSuccess();
    } catch (err) {
      setSavingBills(false);
      onError(err instanceof Error ? err.message : 'Failed to save bills');
    }
  };

  const handleClose = () => {
    if (syncing) {
      handleCancel();
    }
    onOpenChange(false);
  };

  const getStatusIcon = (status: SupplierProgress['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-emerald-400" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-400" />;
      case 'processing':
        return <Spinner className="w-5 h-5 text-blue-400" />;
      default:
        return <Clock className="w-5 h-5 text-slate-400" />;
    }
  };

  const getStatusText = (status: SupplierProgress['status']) => {
    switch (status) {
      case 'completed':
        return t('supplier.completed');
      case 'error':
        return t('supplier.error');
      case 'processing':
        return t('supplier.processing');
      case 'starting':
        return t('supplier.starting');
      default:
        return t('common.loading');
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString();
    } catch {
      return dateString;
    }
  };

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat('ro-RO', {
      style: 'currency',
      currency: 'RON',
    }).format(amount);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-slate-800 border-slate-700 max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-slate-100">
            {stage === 'options' && t('supplier.syncAllProperties')}
            {stage === 'suppliers' && t('supplier.selectSuppliers')}
            {stage === 'scraping' && t('supplier.syncProgress')}
            {stage === 'bills' && t('supplier.selectBills')}
          </DialogTitle>
          <DialogDescription className="text-slate-400 sr-only">
            {stage === 'options' && t('supplier.syncAllProperties')}
            {stage === 'suppliers' && t('supplier.selectSuppliers')}
            {stage === 'scraping' && t('supplier.syncProgress')}
            {stage === 'bills' && t('supplier.selectBills')}
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col flex-1 min-h-0 space-y-4">
          {/* Stage 0: Options */}
          {stage === 'options' && (
            <div className="flex flex-col flex-1 min-h-0 space-y-4">
              <div className="flex items-center space-x-2 p-3 bg-slate-700/50 rounded-lg border border-slate-600">
                <Checkbox
                  id="refresh-rent-bills"
                  checked={refreshRentBills}
                  onCheckedChange={(checked) => setRefreshRentBills(checked === true)}
                />
                <Label htmlFor="refresh-rent-bills" className="text-slate-300 cursor-pointer">
                  {t('supplier.refreshRentBills')}
                </Label>
              </div>
              <p className="text-sm text-slate-400">
                {t('supplier.refreshRentBillsDescription')}
              </p>
              <div className="flex justify-end pt-2 border-t border-slate-700">
                <Button
                  onClick={() => setStage('suppliers')}
                  className="bg-emerald-600 hover:bg-emerald-700"
                >
                  {t('common.next')}
                </Button>
              </div>
            </div>
          )}

          {/* Stage 1: Supplier Selection */}
          {stage === 'suppliers' && (
            <div className="flex flex-col flex-1 min-h-0 space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-300 font-medium">{t('supplier.selectSuppliersToSync')}</p>
                {supplierGroups.length > 0 && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleSelectAllSuppliers}
                    className="text-xs"
                  >
                    {selectedSupplierKeys.size === supplierGroups.length
                      ? t('supplier.deselectAll')
                      : t('supplier.selectAll')}
                  </Button>
                )}
              </div>

              <div className="flex-1 overflow-y-auto border border-slate-600 rounded-lg bg-slate-700/50 p-4 space-y-2">
                {supplierGroups.length === 0 ? (
                  <p className="text-sm text-slate-400 text-center py-4">
                    {t('supplier.noSuppliers')}
                  </p>
                ) : (
                  supplierGroups.map(([key, group]) => (
                    <div
                      key={key}
                      className="flex items-center space-x-3 p-3 bg-slate-700 rounded-lg border border-slate-600"
                    >
                      <Checkbox
                        checked={selectedSupplierKeys.has(key)}
                        onCheckedChange={() => handleSupplierToggle(key)}
                      />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-slate-100">{group.supplier_name}</p>
                        {group.contract_id && (
                          <p className="text-xs text-slate-400 mt-1">
                            {t('supplier.contractId')}: {group.contract_id}
                          </p>
                        )}
                        <p className="text-xs text-slate-400 mt-1">
                          {t('supplier.propertiesCount', { count: group.properties.length })}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="flex justify-end pt-2 border-t border-slate-700 space-x-2">
                <Button
                  onClick={() => setStage('options')}
                  variant="outline"
                >
                  {t('common.back')}
                </Button>
                <Button
                  onClick={handleStartSync}
                  disabled={selectedSupplierKeys.size === 0}
                  className="bg-emerald-600 hover:bg-emerald-700"
                >
                  {t('supplier.syncBills')}
                </Button>
              </div>
            </div>
          )}

          {/* Stage 2: Scraping Progress */}
          {stage === 'scraping' && (
            <div className="flex flex-col flex-1 min-h-0">
              {syncing && progress.length === 0 && (
                <div className="flex flex-col items-center justify-center py-8 space-y-4">
                  <Spinner className="w-8 h-8 text-slate-400" />
                  <p className="text-sm text-slate-400">{t('supplier.starting')}</p>
                </div>
              )}

              {progress.length > 0 && (
                <div className="flex-1 overflow-y-auto border border-slate-600 rounded-lg bg-slate-700/50 p-4 space-y-3">
                  {progress.map((item, index) => (
                    <div
                      key={`${item.supplier_name}_${item.contract_id || 'no_contract'}_${index}`}
                      className="bg-slate-700 rounded-lg p-4 border border-slate-600"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center space-x-3 flex-1">
                          {getStatusIcon(item.status)}
                          <div className="flex-1">
                            <p className="text-sm font-medium text-slate-100">
                              {item.supplier_name}
                              {item.contract_id && (
                                <span className="text-xs text-slate-400 ml-2">({item.contract_id})</span>
                              )}
                            </p>
                            <div className="flex items-center space-x-4 mt-1">
                              <span className="text-xs text-slate-400">
                                {getStatusText(item.status)}
                              </span>
                              {item.status === 'completed' && (
                                <span className="text-xs text-slate-400">
                                  {t('supplier.found')} {item.bills_found}
                                </span>
                              )}
                              {item.status === 'processing' && item.bills_found > 0 && (
                                <span className="text-xs text-slate-400">
                                  {t('supplier.found')} {item.bills_found} {t('bill.bills')}
                                </span>
                              )}
                            </div>
                            {item.properties_affected && item.properties_affected.length > 0 && (
                              <p className="text-xs text-slate-400 mt-1">
                                {t('supplier.properties')}: {item.properties_affected.length}
                              </p>
                            )}
                            {item.error && (
                              <div className="mt-2 flex items-start space-x-2">
                                <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                                <p className="text-xs text-red-400">{item.error}</p>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {syncing && (
                <div className="flex justify-end pt-2 border-t border-slate-700">
                  <Button
                    onClick={handleCancel}
                    variant="outline"
                    className="bg-red-600 hover:bg-red-700 text-white border-red-700"
                  >
                    {t('common.cancel')}
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* Stage 3: Bill Selection */}
          {stage === 'bills' && (
            <div className="flex flex-col flex-1 min-h-0 space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-300 font-medium">
                  {t('supplier.selectBillsToSave')} ({discoveredBills.length})
                </p>
                {discoveredBills.length > 0 && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleSelectAllBills}
                    className="text-xs"
                  >
                    {selectedBillIds.size === discoveredBills.length
                      ? t('supplier.deselectAll')
                      : t('supplier.selectAll')}
                  </Button>
                )}
              </div>

              {discoveredBills.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8 space-y-4">
                  <p className="text-sm text-slate-400">{t('supplier.noBillsDiscovered')}</p>
                </div>
              ) : (
                <div className="flex-1 overflow-y-auto border border-slate-600 rounded-lg bg-slate-700/50 p-4 space-y-2">
                  {discoveredBills.map((bill) => (
                    <div
                      key={bill.id}
                      className="flex items-start space-x-3 p-3 bg-slate-700 rounded-lg border border-slate-600"
                    >
                      <Checkbox
                        checked={selectedBillIds.has(bill.id)}
                        onCheckedChange={() => handleBillToggle(bill.id)}
                        className="mt-1"
                      />
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium text-slate-100">{bill.description}</p>
                            <p className="text-xs text-slate-400 mt-1">{bill.property_name}</p>
                          </div>
                          <p className="text-sm font-semibold text-slate-100">
                            {formatAmount(bill.amount)}
                          </p>
                        </div>
                        <div className="flex items-center space-x-4 mt-1 text-xs text-slate-400">
                          {bill.bill_number && (
                            <span>{t('bill.billNumber')}: {bill.bill_number}</span>
                          )}
                          <span>{t('bill.dueDate')}: {formatDate(bill.due_date)}</span>
                          {bill.contract_id && (
                            <span>{t('supplier.contractId')}: {bill.contract_id}</span>
                          )}
                        </div>
                        {bill.iban && (
                          <p className="text-xs text-slate-400 mt-1">IBAN: {bill.iban}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex justify-end pt-2 border-t border-slate-700 space-x-2">
                <Button
                  onClick={() => setStage('suppliers')}
                  variant="outline"
                  disabled={savingBills}
                >
                  {t('common.back')}
                </Button>
                <Button
                  onClick={handleSaveBills}
                  disabled={selectedBillIds.size === 0 || savingBills}
                  className="bg-emerald-600 hover:bg-emerald-700"
                >
                  {savingBills ? t('common.loading') : t('supplier.saveBills')}
                </Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

