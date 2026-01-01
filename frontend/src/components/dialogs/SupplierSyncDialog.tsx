import { useState, useEffect, useRef } from 'react';
import { api, Property, PropertySupplier } from '../../api';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { Spinner } from '@/components/ui/spinner';
import { CheckCircle2, XCircle, Clock, AlertCircle } from 'lucide-react';
import { useI18n } from '../../lib/i18n';

type SupplierProgress = {
  supplier_name: string;
  status: 'starting' | 'processing' | 'completed' | 'error';
  bills_found: number;
  bills_created: number;
  error?: string;
};

type DiscoveredBill = {
  id: string; // Temporary ID for selection
  supplier_name: string;
  bill_number?: string;
  amount: number;
  due_date: string;
  iban?: string;
  contract_id?: string;
  description: string;
  // Full bill data from backend
  bill_data?: any;
};

type SupplierSyncDialogProps = {
  token: string | null;
  property: Property;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onError: (error: string) => void;
};

type Stage = 'suppliers' | 'scraping' | 'bills';

export default function SupplierSyncDialog({
  token,
  property,
  open,
  onOpenChange,
  onSuccess,
  onError,
}: SupplierSyncDialogProps) {
  const { t } = useI18n();
  const [stage, setStage] = useState<Stage>('suppliers');
  const [propertySuppliers, setPropertySuppliers] = useState<PropertySupplier[]>([]);
  const [selectedSupplierIds, setSelectedSupplierIds] = useState<Set<string>>(new Set());
  const [syncing, setSyncing] = useState(false);
  const [progress, setProgress] = useState<SupplierProgress[]>([]);
  const [discoveredBills, setDiscoveredBills] = useState<DiscoveredBill[]>([]);
  const [selectedBillIds, setSelectedBillIds] = useState<Set<string>>(new Set());
  const [syncId, setSyncId] = useState<string | null>(null);
  const [savingBills, setSavingBills] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const progressMapRef = useRef<Map<string, SupplierProgress>>(new Map());
  const discoveredBillsRef = useRef<DiscoveredBill[]>([]);

  // Load property suppliers when dialog opens
  useEffect(() => {
    if (open && token) {
      loadPropertySuppliers();
      // Reset state
      setStage('suppliers');
      setSelectedSupplierIds(new Set());
      setProgress([]);
      setDiscoveredBills([]);
      setSelectedBillIds(new Set());
      setSyncing(false);
      setSavingBills(false);
      progressMapRef.current.clear();
      discoveredBillsRef.current = [];
    }
  }, [open, token, property.id]);

  const loadPropertySuppliers = async () => {
    if (!token) return;
    try {
      const suppliers = await api.suppliers.listForProperty(token, property.id);
      setPropertySuppliers(suppliers);
    } catch (err) {
      console.error('Failed to load property suppliers:', err);
      onError(err instanceof Error ? err.message : 'Failed to load suppliers');
    }
  };

  const eligibleSuppliers = propertySuppliers.filter(ps => ps.has_credentials);
  const ineligibleSuppliers = propertySuppliers.filter(ps => !ps.has_credentials);

  const handleSelectAllSuppliers = () => {
    if (selectedSupplierIds.size === eligibleSuppliers.length) {
      setSelectedSupplierIds(new Set());
    } else {
      setSelectedSupplierIds(new Set(eligibleSuppliers.map(ps => ps.id)));
    }
  };

  const handleSupplierToggle = (supplierId: string) => {
    const newSet = new Set(selectedSupplierIds);
    if (newSet.has(supplierId)) {
      newSet.delete(supplierId);
    } else {
      newSet.add(supplierId);
    }
    setSelectedSupplierIds(newSet);
  };

  const handleStartSync = () => {
    if (selectedSupplierIds.size === 0) {
      onError('Please select at least one supplier');
      return;
    }
    setStage('scraping');
    startScraping();
  };

  const startScraping = () => {
    if (!token || selectedSupplierIds.size === 0) return;

    setSyncing(true);
    setProgress([]);
    progressMapRef.current.clear();
    discoveredBillsRef.current = [];
    const newSyncId = crypto.randomUUID();
    setSyncId(newSyncId);

    const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const selectedIds = Array.from(selectedSupplierIds);
    const url = `${apiBaseUrl}/suppliers/sync/${property.id}?sync_id=${newSyncId}&supplier_ids=${encodeURIComponent(selectedIds.join(','))}&discover_only=true`;

    const abortController = new AbortController();

    fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'text/event-stream',
      },
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
        status: data.status,
        bills_found: data.bills_found || 0,
        bills_created: data.bills_created || 0,
        error: data.error,
      };

      progressMapRef.current.set(data.supplier_name, supplierProgress);
      setProgress(Array.from(progressMapRef.current.values()));

      // Collect discovered bills
      if (data.bills && Array.isArray(data.bills)) {
        data.bills.forEach((bill: any) => {
          const discoveredBill: DiscoveredBill = {
            id: crypto.randomUUID(),
            supplier_name: data.supplier_name,
            bill_number: bill.bill_number || undefined,
            amount: bill.amount || 0,
            due_date: bill.due_date,
            iban: bill.iban || undefined,
            contract_id: bill.contract_id || undefined,
            description: bill.description || data.supplier_name,
            bill_data: bill, // Store full bill data
          };
          discoveredBillsRef.current.push(discoveredBill);
        });
      }
    } else if (eventType === 'complete') {
      setSyncing(false);
      // Move to bills selection stage
      // Filter bills based on supplier contract_id
      const filteredBills = filterBillsByContractId(discoveredBillsRef.current);
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
    }
  };

  const handleCancel = async () => {
    if (syncId && token) {
      try {
        const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        await fetch(`${apiBaseUrl}/suppliers/sync/${property.id}/cancel?sync_id=${syncId}`, {
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
          // Use the full bill_data if available, otherwise construct from display data
          if (b.bill_data) {
            return b.bill_data;
          }
          
          // Fallback: construct bill data from display fields
          return {
            property_id: property.id,
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
      
      const response = await fetch(`${apiBaseUrl}/suppliers/sync/${property.id}/save-bills`, {
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

  const filterBillsByContractId = (bills: DiscoveredBill[]): DiscoveredBill[] => {
    // Create a map of supplier names to their contract_ids
    const supplierContractMap = new Map<string, string | null>();
    propertySuppliers.forEach(ps => {
      if (selectedSupplierIds.has(ps.id)) {
        supplierContractMap.set(ps.supplier.name, ps.contract_id || null);
      }
    });

    // Remove duplicates first (same supplier, bill_number, amount, due_date)
    const seen = new Set<string>();
    const uniqueBills = bills.filter(bill => {
      const key = `${bill.supplier_name}|${bill.bill_number || ''}|${bill.amount}|${bill.due_date}`;
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });

    // Filter bills: if supplier has contract_id, only show bills with matching contract_id
    // If supplier has no contract_id, show all bills from that supplier
    return uniqueBills.filter(bill => {
      const supplierContractId = supplierContractMap.get(bill.supplier_name);
      
      // If supplier has no contract_id configured, show all bills
      if (supplierContractId === null || supplierContractId === '') {
        return true;
      }
      
      // If supplier has contract_id, only show bills with matching contract_id
      // Allow bills with no contract_id if supplier has no filter (shouldn't happen, but be safe)
      return bill.contract_id === supplierContractId;
    });
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
            {stage === 'suppliers' && t('supplier.selectSuppliers')}
            {stage === 'scraping' && t('supplier.syncProgress')}
            {stage === 'bills' && t('supplier.selectBills')}
          </DialogTitle>
          <DialogDescription className="text-slate-400 sr-only">
            {stage === 'suppliers' && t('supplier.selectSuppliers')}
            {stage === 'scraping' && t('supplier.syncProgress')}
            {stage === 'bills' && t('supplier.selectBills')}
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col flex-1 min-h-0 space-y-4">
          <div>
            <p className="text-sm text-slate-300 font-medium mb-1">{t('property.properties')}:</p>
            <p className="text-sm text-slate-100 font-semibold">{property.name}</p>
            {property.address && (
              <p className="text-xs text-slate-400 mt-1">{property.address}</p>
            )}
          </div>

          {/* Stage 1: Supplier Selection */}
          {stage === 'suppliers' && (
            <div className="flex flex-col flex-1 min-h-0 space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-300 font-medium">{t('supplier.selectSuppliersToSync')}</p>
                {eligibleSuppliers.length > 0 && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleSelectAllSuppliers}
                    className="text-xs"
                  >
                    {selectedSupplierIds.size === eligibleSuppliers.length
                      ? t('supplier.deselectAll')
                      : t('supplier.selectAll')}
                  </Button>
                )}
              </div>

              <div className="flex-1 overflow-y-auto border border-slate-600 rounded-lg bg-slate-700/50 p-4 space-y-2">
                {eligibleSuppliers.length === 0 && ineligibleSuppliers.length === 0 && (
                  <p className="text-sm text-slate-400 text-center py-4">
                    {t('supplier.noSuppliers')}
                  </p>
                )}

                {eligibleSuppliers.map((ps) => (
                  <div
                    key={ps.id}
                    className="flex items-center space-x-3 p-3 bg-slate-700 rounded-lg border border-slate-600"
                  >
                    <Checkbox
                      checked={selectedSupplierIds.has(ps.id)}
                      onCheckedChange={() => handleSupplierToggle(ps.id)}
                    />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-slate-100">{ps.supplier.name}</p>
                      {ps.contract_id && (
                        <p className="text-xs text-slate-400 mt-1">
                          {t('supplier.contractId')}: {ps.contract_id}
                        </p>
                      )}
                    </div>
                  </div>
                ))}

                {ineligibleSuppliers.length > 0 && (
                  <>
                    <div className="border-t border-slate-600 my-3"></div>
                    <p className="text-xs text-slate-400 font-medium mb-2">
                      {t('supplier.notEligible')}:
                    </p>
                    {ineligibleSuppliers.map((ps) => (
                      <div
                        key={ps.id}
                        className="flex items-center space-x-3 p-3 bg-slate-800/50 rounded-lg border border-slate-700 opacity-60"
                      >
                        <Checkbox disabled />
                        <div className="flex-1">
                          <p className="text-sm font-medium text-slate-400">{ps.supplier.name}</p>
                          <p className="text-xs text-red-400 mt-1">
                            {t('supplier.credentialsMissing')}
                          </p>
                        </div>
                      </div>
                    ))}
                  </>
                )}
              </div>

              <div className="flex justify-end pt-2 border-t border-slate-700">
                <Button
                  onClick={handleStartSync}
                  disabled={selectedSupplierIds.size === 0}
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
                      key={item.supplier_name || index}
                      className="bg-slate-700 rounded-lg p-4 border border-slate-600"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center space-x-3 flex-1">
                          {getStatusIcon(item.status)}
                          <div className="flex-1">
                            <p className="text-sm font-medium text-slate-100">
                              {item.supplier_name}
                            </p>
                            <div className="flex items-center space-x-4 mt-1">
                              <span className="text-xs text-slate-400">
                                {getStatusText(item.status)}
                              </span>
                              {item.status === 'completed' && (
                                <>
                                  <span className="text-xs text-slate-400">
                                    {t('supplier.found')} {item.bills_found}
                                  </span>
                                </>
                              )}
                              {item.status === 'processing' && item.bills_found > 0 && (
                                <span className="text-xs text-slate-400">
                                  {t('supplier.found')} {item.bills_found} {t('bill.bills')}
                                </span>
                              )}
                            </div>
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
                          <p className="text-sm font-medium text-slate-100">{bill.description}</p>
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
