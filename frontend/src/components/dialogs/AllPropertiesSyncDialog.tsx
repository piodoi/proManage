import { useState, useEffect } from 'react';
import { api, Property } from '../../api';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Spinner } from '@/components/ui/spinner';
import { useI18n } from '../../lib/i18n';
import { CheckCircle2, Mail, Users } from 'lucide-react';

type AllPropertiesSyncDialogProps = {
  token: string | null;
  properties: Property[]; // Can be single property or multiple
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onError: (error: string) => void;
};

export default function AllPropertiesSyncDialog({
  token,
  properties,
  open,
  onOpenChange,
  onSuccess,
  onError,
}: AllPropertiesSyncDialogProps) {
  const { t } = useI18n();
  const [refreshRentBills, setRefreshRentBills] = useState(true);
  const [syncEmailBills, setSyncEmailBills] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [totalRentBillsGenerated, setTotalRentBillsGenerated] = useState(0);
  const [totalEmailBillsSynced, setTotalEmailBillsSynced] = useState(0);
  const [propertiesWithRentersCount, setPropertiesWithRentersCount] = useState(0);
  const [totalRentersCount, setTotalRentersCount] = useState(0);

  useEffect(() => {
    // Only reset when dialog is being opened (transitions to open=true)
    if (open && token) {
      loadRenterCounts();
      // Don't reset if already syncing or completed
      if (!syncing && !completed) {
        setRefreshRentBills(true);
        setSyncEmailBills(true);
        setTotalRentBillsGenerated(0);
        setTotalEmailBillsSynced(0);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, token]);

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

  const generateRentBills = async (): Promise<number> => {
    if (!token) return 0;
    
    try {
      // Call backend endpoint to generate all rent bills at once
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
      
      if (result.errors && result.errors.length > 0) {
        console.error('Errors generating rent bills:', result.errors);
      }
      
      return result.bills_created || 0;
    } catch (err) {
      console.error('Failed to generate rent bills:', err);
      return 0;
    }
  };

  const handleSync = async () => {
    if (!refreshRentBills && !syncEmailBills) {
      onError('Please select at least one option');
      return;
    }

    setSyncing(true);
    setCompleted(false);
    let rentCount = 0;
    let emailCount = 0;

    try {
      // Generate rent bills if requested
      if (refreshRentBills) {
        rentCount = await generateRentBills();
        setTotalRentBillsGenerated(rentCount);
      }

      // Sync email bills if requested
      if (syncEmailBills) {
        const result = await api.email.sync(token!);
        emailCount = result.bills_created || 0;
        setTotalEmailBillsSynced(emailCount);
      }

      setCompleted(true);
      onSuccess();
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Sync failed');
    } finally {
      setSyncing(false);
    }
  };

  const handleClose = () => {
    if (!syncing) {
      onOpenChange(false);
      // Reset state after dialog closes
      setTimeout(() => {
        setRefreshRentBills(true);
        setSyncEmailBills(true);
        setCompleted(false);
        setTotalRentBillsGenerated(0);
        setTotalEmailBillsSynced(0);
      }, 300);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-slate-800 border-slate-700 max-w-md">
        <DialogHeader>
          <DialogTitle className="text-slate-100">
            {t('supplier.syncAllProperties')}
          </DialogTitle>
          <DialogDescription className="text-slate-400">
            {properties.length === 1 
              ? t('supplier.syncDescription') 
              : `${t('supplier.syncDescription')} (${properties.length} ${t('property.properties').toLowerCase()})`}
          </DialogDescription>
        </DialogHeader>

        {!completed ? (
          <div className="space-y-4">
            {/* Rent Bills Option */}
            <div className="flex items-start space-x-3 p-3 rounded-lg border border-slate-700 bg-slate-750">
              <Checkbox
                id="refresh-rent"
                checked={refreshRentBills}
                onCheckedChange={(checked) => setRefreshRentBills(checked as boolean)}
                disabled={syncing}
                className="mt-0.5"
              />
              <div className="flex-1">
                <Label
                  htmlFor="refresh-rent"
                  className="text-sm font-medium text-slate-200 cursor-pointer"
                >
                  <div className="flex items-center gap-2">
                    <Users className="w-4 h-4" />
                    {t('supplier.refreshRentBills')}
                  </div>
                </Label>
                <p className="text-xs text-slate-400 mt-1">
                  {t('supplier.refreshRentBillsDesc', {
                    count: propertiesWithRentersCount,
                    renters: totalRentersCount
                  })}
                </p>
              </div>
            </div>

            {/* Email Bills Option */}
            <div className="flex items-start space-x-3 p-3 rounded-lg border border-slate-700 bg-slate-750">
              <Checkbox
                id="sync-email"
                checked={syncEmailBills}
                onCheckedChange={(checked) => setSyncEmailBills(checked as boolean)}
                disabled={syncing}
                className="mt-0.5"
              />
              <div className="flex-1">
                <Label
                  htmlFor="sync-email"
                  className="text-sm font-medium text-slate-200 cursor-pointer"
                >
                  <div className="flex items-center gap-2">
                    <Mail className="w-4 h-4" />
                    {t('supplier.syncEmailBills')}
                  </div>
                </Label>
                <p className="text-xs text-slate-400 mt-1">
                  {t('supplier.syncEmailBillsDesc')}
                </p>
              </div>
            </div>

            {/* Sync Button */}
            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="outline"
                onClick={handleClose}
                disabled={syncing}
                className="bg-slate-700 border-slate-600 text-slate-100 hover:bg-slate-600"
              >
                {t('common.cancel')}
              </Button>
              <Button
                onClick={handleSync}
                disabled={syncing || (!refreshRentBills && !syncEmailBills)}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                {syncing ? (
                  <>
                    <Spinner className="w-4 h-4 mr-2" />
                    {t('supplier.syncing')}
                  </>
                ) : (
                  t('supplier.startSync')
                )}
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-center py-6">
              <CheckCircle2 className="w-16 h-16 text-emerald-500" />
            </div>
            <div className="text-center space-y-3">
              <h3 className="text-lg font-medium text-slate-100">
                {t('supplier.syncComplete')}
              </h3>
              <div className="space-y-2 text-sm">
                {/* Rent Bills Summary */}
                {refreshRentBills && (
                  <div className="flex items-center justify-between px-4 py-2 rounded bg-slate-750 border border-slate-700">
                    <div className="flex items-center gap-2 text-slate-300">
                      <Users className="w-4 h-4" />
                      <span>{t('supplier.refreshRentBills')}</span>
                    </div>
                    <span className={totalRentBillsGenerated > 0 ? "text-emerald-400 font-medium" : "text-slate-400"}>
                      {totalRentBillsGenerated > 0 ? `+${totalRentBillsGenerated}` : '0'}
                    </span>
                  </div>
                )}
                {/* Email Bills Summary */}
                {syncEmailBills && (
                  <div className="flex items-center justify-between px-4 py-2 rounded bg-slate-750 border border-slate-700">
                    <div className="flex items-center gap-2 text-slate-300">
                      <Mail className="w-4 h-4" />
                      <span>{t('supplier.syncEmailBills')}</span>
                    </div>
                    <span className={totalEmailBillsSynced > 0 ? "text-emerald-400 font-medium" : "text-slate-400"}>
                      {totalEmailBillsSynced > 0 ? `+${totalEmailBillsSynced}` : '0'}
                    </span>
                  </div>
                )}
                {/* Total Summary */}
                {(refreshRentBills || syncEmailBills) && (
                  <div className="flex items-center justify-between px-4 py-3 rounded bg-emerald-900/20 border border-emerald-700/50 mt-3">
                    <span className="text-slate-200 font-medium">
                      Total
                    </span>
                    <span className="text-emerald-400 font-bold text-lg">
                      +{totalRentBillsGenerated + totalEmailBillsSynced}
                    </span>
                  </div>
                )}
              </div>
            </div>
            <div className="flex justify-end pt-2">
              <Button
                onClick={handleClose}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                {t('common.close')}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
