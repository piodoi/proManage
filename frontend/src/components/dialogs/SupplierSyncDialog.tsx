import { useState, useEffect, useRef } from 'react';
import { api, Property } from '../../api';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
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
  const [syncId, setSyncId] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const progressMapRef = useRef<Map<string, SupplierProgress>>(new Map());

  useEffect(() => {
    if (open && token && !syncing) {
      // Reset state
      setSyncing(true);
      setProgress([]);
      setTotalBillsCreated(0);
      progressMapRef.current.clear();
      const newSyncId = crypto.randomUUID();
      setSyncId(newSyncId);

      // Get API base URL
      const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const url = `${apiBaseUrl}/suppliers/sync/${property.id}?sync_id=${newSyncId}`;

      // Use fetch to read SSE stream manually (EventSource doesn't support POST or custom headers)
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
                  // Check if this is the last line of the event (next line is empty or new event)
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
                    // Multi-line data, accumulate
                    currentData += '\n' + lines[i + 1].substring(6);
                    i++; // Skip next line as we've processed it
                  }
                } else if (line === '' && currentEvent && currentData) {
                  // Empty line indicates end of event
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

      // Cleanup function
      return () => {
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
          abortControllerRef.current = null;
        }
      };
    } else if (!open && abortControllerRef.current) {
      // Abort any ongoing requests when dialog closes
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      setSyncing(false);
    }
  }, [open, token, property.id]);

  const handleSSEEvent = (eventType: string, data: any) => {
    if (eventType === 'start') {
      setSyncing(true);
    } else if (eventType === 'progress') {
      // Update progress for this supplier
      const supplierProgress: SupplierProgress = {
        supplier_name: data.supplier_name,
        status: data.status,
        bills_found: data.bills_found || 0,
        bills_created: data.bills_created || 0,
        error: data.error,
      };

      progressMapRef.current.set(data.supplier_name, supplierProgress);
      setProgress(Array.from(progressMapRef.current.values()));

      // Update total bills created
      if (data.bills_created) {
        setTotalBillsCreated((prev) => {
          const currentSupplierPrevious = progressMapRef.current.get(data.supplier_name);
          const previousCreated = currentSupplierPrevious?.bills_created || 0;
          return prev + (data.bills_created - previousCreated);
        });
      }
    } else if (eventType === 'complete') {
      setSyncing(false);
      if (data.bills_created !== undefined) {
        setTotalBillsCreated(data.bills_created);
      }
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

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-slate-800 border-slate-700 max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-slate-100">{t('supplier.syncProgress')}</DialogTitle>
          <DialogDescription className="text-slate-400 sr-only">
            {t('supplier.syncProgress')}
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

          {syncing && progress.length === 0 && (
            <div className="flex flex-col items-center justify-center py-8 space-y-4">
              <Spinner className="w-8 h-8 text-slate-400" />
              <p className="text-sm text-slate-400">{t('supplier.starting')}</p>
            </div>
          )}

          {progress.length > 0 && (
            <div className="flex flex-col flex-1 min-h-0">
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm text-slate-300 font-medium">{t('supplier.supplierProgress')}</p>
                {!syncing && (
                  <p className="text-sm text-slate-100 font-semibold">
                    {t('supplier.totalBillsCreated')} {totalBillsCreated}
                  </p>
                )}
              </div>

              {/* Scrolling progress box */}
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
            </div>
          )}

          {!syncing && progress.length > 0 && (
            <div className="flex justify-end pt-2 border-t border-slate-700">
              <Button
                onClick={() => {
                  onOpenChange(false);
                  if (totalBillsCreated > 0 || progress.some((p) => p.status === 'completed')) {
                    onSuccess();
                  }
                }}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                {t('common.close')}
              </Button>
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
      </DialogContent>
    </Dialog>
  );
}
