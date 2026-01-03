import { useState, useEffect, useRef } from 'react';
import { api, Property, PropertySupplier, Renter } from '../../api';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Spinner } from '@/components/ui/spinner';
import { useI18n } from '../../lib/i18n';
import { usePreferences } from '../../hooks/usePreferences';
import SupplierProgressDisplay, { type SupplierProgress } from '../supplierSync/SupplierProgressDisplay';
import DiscoveredBillItem, { type DiscoveredBill } from '../supplierSync/DiscoveredBillItem';

type SupplierGroup = {
  supplier_id: string;
  supplier_name: string;
  properties: Property[];
  property_suppliers: PropertySupplier[]; // All property_suppliers for this supplier
  has_credentials: boolean;
};

type AllPropertiesSyncDialogProps = {
  token: string | null;
  properties: Property[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onError: (error: string) => void;
};

type Stage = 'suppliers' | 'scraping' | 'bills';

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
  const [stage, setStage] = useState<Stage>('suppliers');
  const [refreshRentBills, setRefreshRentBills] = useState(true); // Default on
  const [allPropertySuppliers, setAllPropertySuppliers] = useState<Map<string, PropertySupplier[]>>(new Map());
  const [supplierGroups, setSupplierGroups] = useState<SupplierGroup[]>([]);
  const [selectedSupplierKeys, setSelectedSupplierKeys] = useState<Set<string>>(new Set());
  const [syncing, setSyncing] = useState(false);
  const [progress, setProgress] = useState<SupplierProgress[]>([]);
  const [discoveredBills, setDiscoveredBills] = useState<DiscoveredBill[]>([]);
  const [selectedBillIds, setSelectedBillIds] = useState<Set<string>>(new Set());
  const [syncId, setSyncId] = useState<string | null>(null);
  const [savingBills, setSavingBills] = useState(false);
  const [totalRentBillsGenerated, setTotalRentBillsGenerated] = useState(0);
  const abortControllerRef = useRef<AbortController | null>(null);
  const progressMapRef = useRef<Map<string, SupplierProgress>>(new Map());
  const discoveredBillsRef = useRef<DiscoveredBill[]>([]);

  // Load all property suppliers when dialog opens
  useEffect(() => {
    if (open && token) {
      loadAllPropertySuppliers();
      setStage('suppliers');
      setRefreshRentBills(true); // Default on
      setProgress([]);
      setDiscoveredBills([]);
      setSelectedBillIds(new Set());
      setSyncing(false);
      setSavingBills(false);
      setTotalRentBillsGenerated(0);
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
      
      // Group suppliers by supplier name (or supplier_id if available) - like Manage Supplier Credentials
      const groupsMap = new Map<string, SupplierGroup>();
      
      suppliersMap.forEach((suppliers, propertyId) => {
        const property = properties.find(p => p.id === propertyId);
        if (!property) return;
        
        suppliers.forEach(ps => {
          // Use supplier_id as key (or supplier name if ID not available, but ID should always be available)
          const key = ps.supplier.id || ps.supplier.name;
          if (!groupsMap.has(key)) {
            groupsMap.set(key, {
              supplier_id: ps.supplier.id,
              supplier_name: ps.supplier.name,
              properties: [],
              property_suppliers: [],
              has_credentials: false,
            });
          }
          const group = groupsMap.get(key)!;
          if (!group.properties.find(p => p.id === property.id)) {
            group.properties.push(property);
          }
          group.property_suppliers.push(ps);
          if (ps.has_credentials) {
            group.has_credentials = true;
          }
        });
      });
      
      const groupsArray = Array.from(groupsMap.values());
      setSupplierGroups(groupsArray);
      
      // Auto-select all supplier groups that have credentials by default
      const eligibleKeys = groupsArray
        .filter(g => g.has_credentials)
        .map(g => g.supplier_id || g.supplier_name);
      setSelectedSupplierKeys(new Set(eligibleKeys));
    } catch (err) {
      console.error('Failed to load property suppliers:', err);
      onError(err instanceof Error ? err.message : 'Failed to load suppliers');
    }
  };

  const eligibleSupplierGroups = supplierGroups.filter(g => g.has_credentials);
  const ineligibleSupplierGroups = supplierGroups.filter(g => !g.has_credentials);

  const handleSelectAllSuppliers = () => {
    if (selectedSupplierKeys.size === eligibleSupplierGroups.length) {
      setSelectedSupplierKeys(new Set());
    } else {
      setSelectedSupplierKeys(new Set(eligibleSupplierGroups.map(g => g.supplier_id || g.supplier_name)));
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
        const count = await generateRentBills();
        setTotalRentBillsGenerated(count);
      } catch (err) {
        onError(err instanceof Error ? err.message : 'Failed to generate rent bills');
        return;
      }
    }

    setStage('scraping');
    startScraping();
  };

  const generateRentBills = async (): Promise<number> => {
    if (!token) return 0;
    
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
    let billsGenerated = 0;
    
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
        billsGenerated++;
      } catch (err) {
        console.error(`Failed to create/update rent bill for renter ${renter.id}:`, err);
        throw err; // Re-throw to show error in UI
      }
    }
    
    return billsGenerated;
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
    // For each selected supplier, create groups by supplier_id+contract_id (backend requirement)
    const syncGroups: Array<{ supplier_id: string; contract_id?: string; property_ids: string[] }> = [];
    
    selectedSupplierKeys.forEach(supplierKey => {
      const supplierGroup = supplierGroups.find(g => (g.supplier_id || g.supplier_name) === supplierKey);
      if (!supplierGroup || !supplierGroup.has_credentials) return;
      
      // Group property_suppliers by contract_id for this supplier
      const contractGroups = new Map<string, { contract_id?: string; property_ids: Set<string> }>();
      
      supplierGroup.property_suppliers.forEach(ps => {
        if (!ps.has_credentials) return;
        
        const contractKey = ps.contract_id || 'no_contract';
        if (!contractGroups.has(contractKey)) {
          contractGroups.set(contractKey, {
            contract_id: ps.contract_id || undefined,
            property_ids: new Set(),
          });
        }
        const property = properties.find(p => 
          allPropertySuppliers.get(p.id)?.some(ps2 => ps2.id === ps.id)
        );
        if (property) {
          contractGroups.get(contractKey)!.property_ids.add(property.id);
        }
      });
      
      // Create sync groups for each contract_id
      contractGroups.forEach((contractGroup) => {
        syncGroups.push({
          supplier_id: supplierGroup.supplier_id,
          contract_id: contractGroup.contract_id,
          property_ids: Array.from(contractGroup.property_ids),
        });
      });
    });
    
    const syncData = {
      sync_id: newSyncId,
      supplier_groups: syncGroups,
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


  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-slate-800 border-slate-700 max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-slate-100">
            {stage === 'suppliers' && t('supplier.syncAllProperties')}
            {stage === 'scraping' && t('supplier.syncProgress')}
            {stage === 'bills' && t('supplier.selectBills')}
          </DialogTitle>
          <DialogDescription className="text-slate-400 sr-only">
            {stage === 'suppliers' && t('supplier.syncAllProperties')}
            {stage === 'scraping' && t('supplier.syncProgress')}
            {stage === 'bills' && t('supplier.selectBills')}
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col flex-1 min-h-0 space-y-4">
          {/* Stage 1: Supplier Selection */}
          {stage === 'suppliers' && (
            <div className="flex flex-col flex-1 min-h-0 space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-300 font-medium">{t('supplier.selectSuppliersToSync')}</p>
                {eligibleSupplierGroups.length > 0 && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleSelectAllSuppliers}
                    className="text-xs"
                  >
                    {selectedSupplierKeys.size === eligibleSupplierGroups.length
                      ? t('supplier.deselectAll')
                      : t('supplier.selectAll')}
                  </Button>
                )}
              </div>

              <div className="flex-1 overflow-y-auto border border-slate-600 rounded-lg bg-slate-700/50 p-4 space-y-2">
                {eligibleSupplierGroups.length === 0 && ineligibleSupplierGroups.length === 0 && (
                  <p className="text-sm text-slate-400 text-center py-4">
                    {t('supplier.noSuppliers')}
                  </p>
                )}

                {/* Refresh rent bills checkbox - same style as suppliers */}
                <div className="flex items-center space-x-3 p-3 bg-slate-700 rounded-lg border border-slate-600">
                  <Checkbox
                    id="refresh-rent-bills"
                    checked={refreshRentBills}
                    onCheckedChange={(checked) => setRefreshRentBills(checked === true)}
                  />
                  <div className="flex-1">
                    <Label htmlFor="refresh-rent-bills" className="text-sm font-medium text-slate-100 cursor-pointer">
                      {t('supplier.refreshRentBills')}
                    </Label>
                  </div>
                </div>

                {/* Eligible suppliers */}
                {eligibleSupplierGroups.map((group) => {
                  const key = group.supplier_id || group.supplier_name;
                  return (
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
                        <div className="flex items-center gap-4 mt-1 text-xs text-slate-400">
                          <span>
                            {t('supplier.properties')}: <span className="text-slate-300">{group.properties.length}</span>
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {/* Ineligible suppliers */}
                {ineligibleSupplierGroups.length > 0 && (
                  <>
                    <div className="border-t border-slate-600 my-3"></div>
                    <p className="text-xs text-slate-400 font-medium mb-2">
                      {t('supplier.notEligible')}:
                    </p>
                    {ineligibleSupplierGroups.map((group) => {
                      const key = group.supplier_id || group.supplier_name;
                      return (
                        <div
                          key={key}
                          className="flex items-center space-x-3 p-3 bg-slate-800/50 rounded-lg border border-slate-700 opacity-60"
                        >
                          <Checkbox disabled />
                          <div className="flex-1">
                            <p className="text-sm font-medium text-slate-400">{group.supplier_name}</p>
                            <div className="flex items-center gap-4 mt-1 text-xs text-slate-400">
                              <span>
                                {t('supplier.properties')}: <span className="text-slate-300">{group.properties.length}</span>
                              </span>
                            </div>
                            <p className="text-xs text-red-400 mt-1">
                              {t('supplier.credentialsMissing')}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </>
                )}
              </div>

              {totalRentBillsGenerated > 0 && (
                <div className="text-xs text-slate-400 text-center pt-2 border-t border-slate-700">
                  {t('supplier.rentBillsGenerated')}: {totalRentBillsGenerated}
                </div>
              )}

              <div className="flex justify-end pt-2 border-t border-slate-700">
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
                <SupplierProgressDisplay progress={progress} />
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
                    <DiscoveredBillItem
                      key={bill.id}
                      bill={bill}
                      selected={selectedBillIds.has(bill.id)}
                      onToggle={handleBillToggle}
                    />
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

