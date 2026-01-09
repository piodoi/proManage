import { useState, useEffect, useRef } from 'react';
import { api, Property } from '../../api';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Spinner } from '@/components/ui/spinner';
import { useI18n } from '../../lib/i18n';
import { usePreferences } from '../../hooks/usePreferences';
import DiscoveredBillItem, { type DiscoveredBill } from '../supplierSync/DiscoveredBillItem';
import { CheckCircle2, Mail, Users } from 'lucide-react';

type AllPropertiesSyncDialogProps = {
  token: string | null;
  properties: Property[]; // Can be single property or multiple
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onError: (error: string) => void;
};

type Stage = 'selection' | 'syncing' | 'bills';

export default function AllPropertiesSyncDialog({
  token,
  properties,
  open,
  onOpenChange,
  onSuccess,
  onError,
}: AllPropertiesSyncDialogProps) {
  const { t } = useI18n();
  usePreferences(); // Initialize preferences context
  const [stage, setStage] = useState<Stage>('selection');
  const [refreshRentBills, setRefreshRentBills] = useState(true);
  const [syncEmailBills, setSyncEmailBills] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [discoveredBills, setDiscoveredBills] = useState<DiscoveredBill[]>([]);
  const [selectedBillIds, setSelectedBillIds] = useState<Set<string>>(new Set());
  const [processedEmailIds, setProcessedEmailIds] = useState<Set<string>>(new Set());
  const [savingBills, setSavingBills] = useState(false);
  const [totalRentBillsGenerated, setTotalRentBillsGenerated] = useState(0);
  const [propertiesWithRentersCount, setPropertiesWithRentersCount] = useState(0);
  const [totalRentersCount, setTotalRentersCount] = useState(0);
  const [syncProgress, setSyncProgress] = useState<string>('');
  const discoveredBillsRef = useRef<DiscoveredBill[]>([]);

  // Load counts when dialog opens
  useEffect(() => {
    if (open && token) {
      loadRenterCounts();
      setStage('selection');
      setRefreshRentBills(true);
      setSyncEmailBills(true);
      setDiscoveredBills([]);
      setSelectedBillIds(new Set());
      setProcessedEmailIds(new Set());
      setSyncing(false);
      setSavingBills(false);
      setTotalRentBillsGenerated(0);
      setSyncProgress('');
      discoveredBillsRef.current = [];
    }
  }, [open, token, properties]);

  const loadRenterCounts = async () => {
    if (!token) return;
    
    let propertiesWithRenters = 0;
    let totalRenters = 0;
    
    for (const property of properties) {
      try {
        const renters = await api.renters.list(token, property.id);
        const rentersWithAmount = renters.filter(r => r.rent_amount_eur && r.rent_amount_eur > 0);
        if (rentersWithAmount.length > 0) {
          propertiesWithRenters++;
          totalRenters += rentersWithAmount.length;
        }
      } catch (err) {
        console.error(`Failed to load renters for property ${property.id}:`, err);
      }
    }
    
    setPropertiesWithRentersCount(propertiesWithRenters);
    setTotalRentersCount(totalRenters);
  };

  const generateRentBills = async (): Promise<{ count: number; bills: DiscoveredBill[] }> => {
    if (!token) return { count: 0, bills: [] };
    
    try {
      setSyncProgress(t('supplier.generatingRentBills'));
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/rent/generate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`Failed to generate rent bills: ${response.statusText}`);
      }
      
      const result = await response.json();
      const count = result.bills_created || 0;
      
      // Convert backend bills to DiscoveredBill format
      const rentBills: DiscoveredBill[] = (result.created_bills || []).map((bill: any) => ({
        id: bill.id,
        supplier_name: 'Rent',
        bill_number: bill.bill_number,
        amount: bill.amount || 0,
        due_date: bill.due_date,
        iban: bill.iban,
        description: `${bill.description} - ${bill.renter_name}`,
        property_id: bill.property_id,
        property_name: bill.property_name,
        address_confidence: 100,
        match_reason: 'rent_bill',
        bill_data: bill,
        source: 'rent',
        supplier: 'Rent',
      }));
      
      return { count, bills: rentBills };
    } catch (err) {
      console.error('Failed to generate rent bills:', err);
      return { count: 0, bills: [] };
    }
  };

  const handleStartSync = async () => {
    if (!refreshRentBills && !syncEmailBills) {
      onError(t('supplier.selectAtLeastOne'));
      return;
    }

    setStage('syncing');
    setSyncing(true);
    const allDiscoveredBills: DiscoveredBill[] = [];

    try {
      // Generate rent bills if requested
      if (refreshRentBills) {
        const { count, bills: rentBills } = await generateRentBills();
        setTotalRentBillsGenerated(count);
        allDiscoveredBills.push(...rentBills);
      }

      // Sync email bills if requested - discover only, don't create yet
      if (syncEmailBills) {
        setSyncProgress(t('supplier.fetchingEmailBills'));
        const result = await api.email.sync(token!);
        
        if (result.status === 'success') {
          // Process email bills (even if empty array)
          const emailBills: DiscoveredBill[] = (result.discovered_bills || []).map((bill: any) => ({
            id: bill.id || crypto.randomUUID(),
            supplier_name: bill.supplier_name || bill.pattern_name || 'Unknown',
            bill_number: bill.bill_number,
            amount: bill.amount || 0,
            due_date: bill.due_date,
            iban: bill.iban,
            contract_id: bill.contract_id,
            description: bill.description || bill.pattern_name || bill.supplier_name,
            property_id: bill.property_id,
            property_name: bill.property_name,
            address_confidence: bill.address_confidence,
            match_reason: bill.match_reason,
            bill_data: bill,
            source: 'email',
            supplier: bill.supplier || bill.pattern_name,
            email_id: bill.email_id,
          }));
          
          // Collect email_ids for deletion later
          const newEmailIds = new Set(processedEmailIds);
          emailBills.forEach((bill) => {
            if (bill.email_id) {
              newEmailIds.add(bill.email_id);
            }
          });
          setProcessedEmailIds(newEmailIds);
          
          allDiscoveredBills.push(...emailBills);
        } else {
          onError(result.message || 'Failed to sync email bills');
        }
      }

      // Set all discovered bills (rent + email)
      discoveredBillsRef.current = allDiscoveredBills;
      setDiscoveredBills(allDiscoveredBills);
      
      // Pre-select only email bills (rent bills are already saved)
      const emailBillIds = allDiscoveredBills.filter(b => b.source === 'email').map(b => b.id);
      setSelectedBillIds(new Set(emailBillIds));

      // Move to bills stage (even if no bills found)
      setSyncing(false);
      setStage('bills');
    } catch (err) {
      setSyncing(false);
      onError(err instanceof Error ? err.message : 'Sync failed');
      setStage('bills'); // Still show bills stage even on error
    }
  };

  const handleSelectAllBills = () => {
    const emailBills = discoveredBills.filter(b => b.source === 'email');
    if (selectedBillIds.size === emailBills.length) {
      setSelectedBillIds(new Set());
    } else {
      setSelectedBillIds(new Set(emailBills.map(b => b.id)));
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

  const handlePropertyChange = (billId: string, propertyId: string) => {
    const property = properties.find(p => p.id === propertyId);
    if (!property) return;
    
    const updatedBills = discoveredBills.map(bill => {
      if (bill.id === billId) {
        return {
          ...bill,
          property_id: propertyId,
          property_name: property.name,
          bill_data: {
            ...bill.bill_data,
            property_id: propertyId,
          }
        };
      }
      return bill;
    });
    
    setDiscoveredBills(updatedBills);
    discoveredBillsRef.current = updatedBills;
  };

  const handleSaveBills = async () => {
    if (!token || selectedBillIds.size === 0) {
      onError(t('supplier.selectBillsToSave'));
      return;
    }

    setSavingBills(true);
    try {
      // Only save email bills (rent bills are already saved by the backend)
      const billsToSave = discoveredBills
        .filter(b => selectedBillIds.has(b.id) && b.source === 'email')
        .map(b => {
          if (b.bill_data) {
            return {
              ...b.bill_data,
              property_id: b.property_id, // Use potentially updated property_id
            };
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
            source: b.source || null,
            supplier: b.supplier || null,
          };
        });
      
      if (billsToSave.length > 0) {
        const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const response = await fetch(`${API_URL}/suppliers/sync-all/save-bills`, {
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
      }

      // Close dialog and delete emails in background
      handleCloseAndCleanup();
      onSuccess();
    } catch (err) {
      setSavingBills(false);
      onError(err instanceof Error ? err.message : 'Failed to save bills');
    }
  };

  const handleCloseAndCleanup = () => {
    // Close dialog immediately
    onOpenChange(false);
    
    // Delete processed emails in background (fire-and-forget)
    if (processedEmailIds.size > 0 && token) {
      const emailIdsToDelete = Array.from(processedEmailIds);
      console.log(`[Email Delete] Deleting ${emailIdsToDelete.length} emails in background`);
      
      api.email.delete(token, emailIdsToDelete)
        .then(() => {
          console.log(`[Email Delete] ✓ Successfully deleted ${emailIdsToDelete.length} emails`);
        })
        .catch((err) => {
          console.error('[Email Delete] ✗ Failed to delete emails:', err);
        });
    }
  };

  const handleClose = () => {
    if (syncing) {
      return; // Don't allow closing while syncing
    }
    handleCloseAndCleanup();
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-slate-800 border-slate-700 max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-slate-100">
            {stage === 'selection' && t('supplier.syncAllProperties')}
            {stage === 'syncing' && t('supplier.syncProgress')}
            {stage === 'bills' && t('supplier.selectBills')}
          </DialogTitle>
          <DialogDescription className="text-slate-400 sr-only">
            {stage === 'selection' && t('supplier.syncAllProperties')}
            {stage === 'syncing' && t('supplier.syncProgress')}
            {stage === 'bills' && t('supplier.selectBills')}
          </DialogDescription>
        </DialogHeader>
        
        <div className="flex flex-col flex-1 min-h-0 space-y-4">
          {/* Stage 1: Selection */}
          {stage === 'selection' && (
            <div className="flex flex-col flex-1 min-h-0 space-y-4">
              <p className="text-sm text-slate-300">{t('supplier.syncDescription')}</p>
              
              <div className="flex-1 overflow-y-auto border border-slate-600 rounded-lg bg-slate-700/50 p-4 space-y-2">
                {/* Rent Bills Option */}
                <div className="flex items-center space-x-3 p-3 bg-slate-700 rounded-lg border border-slate-600">
                  <Checkbox
                    id="refresh-rent-bills"
                    checked={refreshRentBills}
                    onCheckedChange={(checked) => setRefreshRentBills(checked === true)}
                  />
                  <div className="flex-1">
                    <Label htmlFor="refresh-rent-bills" className="text-sm font-medium text-slate-100 cursor-pointer">
                      <div className="flex items-center gap-2">
                        <Users className="w-4 h-4" />
                        {t('supplier.refreshRentBills')}
                      </div>
                    </Label>
                    <div className="flex items-center gap-4 mt-1 text-xs text-slate-400">
                      <span>
                        {t('supplier.properties')}: <span className="text-slate-300">{propertiesWithRentersCount}</span>
                      </span>
                      <span>
                        {t('supplier.renters')}: <span className="text-slate-300">{totalRentersCount}</span>
                      </span>
                    </div>
                  </div>
                </div>

                {/* Email Bills Option */}
                <div className="flex items-center space-x-3 p-3 bg-slate-700 rounded-lg border border-slate-600">
                  <Checkbox
                    id="sync-email-bills"
                    checked={syncEmailBills}
                    onCheckedChange={(checked) => setSyncEmailBills(checked === true)}
                  />
                  <div className="flex-1">
                    <Label htmlFor="sync-email-bills" className="text-sm font-medium text-slate-100 cursor-pointer">
                      <div className="flex items-center gap-2">
                        <Mail className="w-4 h-4" />
                        {t('supplier.syncEmailBills')}
                      </div>
                    </Label>
                    <div className="text-xs text-slate-400 mt-1">
                      {t('supplier.syncEmailBillsDesc')}
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex justify-end pt-2 border-t border-slate-700 gap-2">
                <Button
                  variant="outline"
                  onClick={handleClose}
                  className="bg-slate-700 border-slate-600 text-slate-100 hover:bg-slate-600"
                >
                  {t('common.cancel')}
                </Button>
                <Button
                  onClick={handleStartSync}
                  disabled={!refreshRentBills && !syncEmailBills}
                  className="bg-emerald-600 hover:bg-emerald-700"
                >
                  {t('supplier.startSync')}
                </Button>
              </div>
            </div>
          )}

          {/* Stage 2: Syncing Progress */}
          {stage === 'syncing' && (
            <div className="flex flex-col items-center justify-center py-8 space-y-4">
              <Spinner className="w-8 h-8 text-emerald-500" />
              <p className="text-sm text-slate-300">{syncProgress || t('common.syncing')}</p>
              {totalRentBillsGenerated > 0 && (
                <p className="text-xs text-slate-400">
                  {t('supplier.rentBillsGenerated')}: {totalRentBillsGenerated}
                </p>
              )}
            </div>
          )}

          {/* Stage 3: Bill Selection */}
          {stage === 'bills' && (
            <div className="flex flex-col flex-1 min-h-0 space-y-4">

              {/* Bills list */}
              {discoveredBills.length > 0 ? (
                <>
                  {/* Rent bills section (already saved, read-only display) */}
                  {discoveredBills.filter(b => b.source === 'rent').length > 0 && (
                    <div className="space-y-2">
                      <p className="text-sm text-slate-300 font-medium flex items-center gap-2">
                        <Users className="w-4 h-4" />
                        {t('supplier.rentBillsGenerated', { count: totalRentBillsGenerated })}
                      </p>
                      <div className="border border-slate-600 rounded-lg bg-slate-700/30 p-3 space-y-2 max-h-40 overflow-y-auto">
                        {discoveredBills.filter(b => b.source === 'rent').map((bill) => (
                          <div key={bill.id} className="flex items-center justify-between p-2 bg-slate-700 rounded text-sm">
                            <div className="flex items-center gap-2">
                              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                              <span className="text-slate-100">{bill.description}</span>
                              <span className="text-slate-400">- {bill.property_name}</span>
                            </div>
                            <span className="font-semibold text-slate-100">{bill.amount} {bill.bill_data?.currency || 'EUR'}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Email bills section (need confirmation) */}
                  {discoveredBills.filter(b => b.source === 'email').length > 0 && (
                    <>
                      <div className="flex items-center justify-between">
                        <p className="text-sm text-slate-300 font-medium flex items-center gap-2">
                          <Mail className="w-4 h-4" />
                          {t('supplier.selectBillsToSave')} ({discoveredBills.filter(b => b.source === 'email').length})
                        </p>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleSelectAllBills}
                          className="text-xs"
                        >
                          {selectedBillIds.size === discoveredBills.filter(b => b.source === 'email').length
                            ? t('common.deselectAll')
                            : t('common.selectAll')}
                        </Button>
                      </div>

                      <div className="flex-1 overflow-y-auto border border-slate-600 rounded-lg bg-slate-700/50 p-4 space-y-2">
                        {discoveredBills.filter(b => b.source === 'email').map((bill) => (
                          <DiscoveredBillItem
                            key={bill.id}
                            bill={bill}
                            selected={selectedBillIds.has(bill.id)}
                            onToggle={handleBillToggle}
                            properties={properties}
                            onPropertyChange={handlePropertyChange}
                          />
                        ))}
                      </div>
                    </>
                  )}
                </>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 space-y-4">
                  <CheckCircle2 className="w-12 h-12 text-emerald-500" />
                  <p className="text-sm text-slate-300">
                    {totalRentBillsGenerated > 0 
                      ? t('supplier.syncComplete')
                      : t('supplier.noBillsDiscovered')}
                  </p>
                </div>
              )}

              <div className="flex justify-end pt-2 border-t border-slate-700 space-x-2">
                <Button
                  onClick={() => setStage('selection')}
                  variant="outline"
                  disabled={savingBills}
                  className="bg-slate-700 border-slate-600 text-slate-100 hover:bg-slate-600"
                >
                  {t('common.back')}
                </Button>
                {discoveredBills.filter(b => b.source === 'email').length === 0 ? (
                  <Button
                    onClick={handleClose}
                    className="bg-emerald-600 hover:bg-emerald-700"
                  >
                    {t('common.close')}
                  </Button>
                ) : (
                  <Button
                    onClick={handleSaveBills}
                    disabled={selectedBillIds.size === 0 || savingBills}
                    className="bg-emerald-600 hover:bg-emerald-700"
                  >
                    {savingBills ? (
                      <>
                        <Spinner className="w-4 h-4 mr-2" />
                        {t('common.loading')}
                      </>
                    ) : (
                      t('supplier.saveBills')
                    )}
                  </Button>
                )}
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
