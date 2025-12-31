import { useState, useEffect } from 'react';
import { api, Property } from '../../api';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
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

type SupplierSyncDialogProps = {
  token: string | null;
  property: Property;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onError: (error: string) => void;
};

export default function SupplierSyncDialog({
  token,
  property,
  open,
  onOpenChange,
  onSuccess,
  onError,
}: SupplierSyncDialogProps) {
  const { t } = useI18n();
  const [syncing, setSyncing] = useState(false);
  const [progress, setProgress] = useState<SupplierProgress[]>([]);
  const [totalBillsCreated, setTotalBillsCreated] = useState(0);
  const [errors, setErrors] = useState<string[]>([]);

  useEffect(() => {
    if (open && token && !syncing) {
      // Reset state
      setSyncing(true);
      setProgress([]);
      setTotalBillsCreated(0);
      setErrors([]);

      // Start sync
      api.suppliers.sync(token, property.id)
        .then((result) => {
          setSyncing(false);
          
          if (result.status === 'no_suppliers') {
            onError(result.message || 'No suppliers with credentials configured');
            onOpenChange(false);
            return;
          }

          // Update progress from result
          if (result.progress && Array.isArray(result.progress)) {
            setProgress(result.progress);
          }

          if (result.bills_created !== undefined) {
            setTotalBillsCreated(result.bills_created);
          }

          if (result.errors && result.errors.length > 0) {
            setErrors(result.errors);
          }

          // Call success callback after a short delay to show the results
          setTimeout(() => {
            onOpenChange(false);
            onSuccess();
            if (result.bills_created > 0 || (result.errors && result.errors.length > 0)) {
              const message = result.bills_created > 0 
                ? `Successfully synced ${result.bills_created} bill(s) from suppliers`
                : 'Sync completed with errors';
              onError(message);
            }
          }, 2000);
        })
        .catch((err) => {
          setSyncing(false);
          onError(err instanceof Error ? err.message : 'Failed to sync supplier bills');
        });
    }
  }, [open, token, property.id, syncing, onOpenChange, onSuccess, onError]);

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

  return (
    <Dialog open={open} onOpenChange={(open) => {
      if (!open && !syncing) {
        onOpenChange(false);
      }
    }}>
      <DialogContent className="bg-slate-800 border-slate-700 max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-slate-100">{t('supplier.syncProgress')}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <p className="text-sm text-slate-300 font-medium mb-1">{t('property.properties')}:</p>
            <p className="text-sm text-slate-100 font-semibold">{property.name}</p>
            {property.address && (
              <p className="text-xs text-slate-400 mt-1">{property.address}</p>
            )}
          </div>

          {syncing && progress.length === 0 && (
            <div className="flex flex-col items-center justify-center py-8 space-y-4">
              <Spinner className="w-8 h-8 text-slate-400" />
              <p className="text-sm text-slate-400">{t('supplier.starting')}</p>
            </div>
          )}

          {progress.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm text-slate-300 font-medium">{t('supplier.supplierProgress')}</p>
                {!syncing && (
                  <p className="text-sm text-slate-100 font-semibold">
                    {t('supplier.totalBillsCreated')} {totalBillsCreated}
                  </p>
                )}
              </div>

              {progress.map((item, index) => (
                <div
                  key={index}
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
                              <span className="text-xs text-emerald-400">
                                {t('supplier.created')} {item.bills_created}
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

          {errors.length > 0 && (
            <div className="bg-red-900/20 border border-red-700 rounded-lg p-4">
              <p className="text-sm font-medium text-red-400 mb-2">{t('errors.generic')}:</p>
              <ul className="space-y-1">
                {errors.map((error, index) => (
                  <li key={index} className="text-xs text-red-300">{error}</li>
                ))}
              </ul>
            </div>
          )}

          {!syncing && progress.length > 0 && (
            <div className="flex justify-end pt-2">
              <Button
                onClick={() => {
                  onOpenChange(false);
                  onSuccess();
                }}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                {t('common.close')}
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

