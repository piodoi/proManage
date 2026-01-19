import { useState, useEffect, useCallback } from 'react';
import { api, PaymentNotificationWithDetails } from '../api';
import { useAuth } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Bell, CheckCircle, XCircle, Clock, Building2, User, FileText, MessageSquare } from 'lucide-react';
import { useI18n } from '../lib/i18n';
import { formatDateWithPreferences } from '../lib/utils';
import { usePreferences } from '../hooks/usePreferences';

type NotificationsViewProps = {
  onCountChange?: (count: number) => void;
};

export default function NotificationsView({ onCountChange }: NotificationsViewProps) {
  const { token } = useAuth();
  const { t, language } = useI18n();
  const { preferences } = usePreferences();
  const [notifications, setNotifications] = useState<PaymentNotificationWithDetails[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('pending');
  const [selectedNotification, setSelectedNotification] = useState<PaymentNotificationWithDetails | null>(null);
  const [actionType, setActionType] = useState<'confirm' | 'reject' | null>(null);
  const [landlordNote, setLandlordNote] = useState('');
  const [processing, setProcessing] = useState(false);

  const loadNotifications = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const status = activeTab === 'all' ? undefined : activeTab;
      const data = await api.paymentNotifications.list(token, status);
      setNotifications(data);
      
      // Update count for pending notifications
      if (activeTab === 'pending' && onCountChange) {
        onCountChange(data.length);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.generic'));
    } finally {
      setLoading(false);
    }
  }, [token, activeTab, onCountChange, t]);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  // Also load pending count on mount
  useEffect(() => {
    const loadPendingCount = async () => {
      if (!token || !onCountChange) return;
      try {
        const { count } = await api.paymentNotifications.count(token);
        onCountChange(count);
      } catch (err) {
        console.error('Failed to load notification count:', err);
      }
    };
    loadPendingCount();
  }, [token, onCountChange]);

  const handleAction = async () => {
    if (!token || !selectedNotification || !actionType) return;
    
    setProcessing(true);
    try {
      if (actionType === 'confirm') {
        await api.paymentNotifications.confirm(token, selectedNotification.notification.id, landlordNote || undefined);
      } else {
        await api.paymentNotifications.reject(token, selectedNotification.notification.id, landlordNote || undefined);
      }
      
      setSelectedNotification(null);
      setActionType(null);
      setLandlordNote('');
      loadNotifications();
      
      // Refresh pending count
      if (onCountChange) {
        const { count } = await api.paymentNotifications.count(token);
        onCountChange(count);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.generic'));
    } finally {
      setProcessing(false);
    }
  };

  const openActionDialog = (notification: PaymentNotificationWithDetails, action: 'confirm' | 'reject') => {
    setSelectedNotification(notification);
    setActionType(action);
    setLandlordNote('');
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return (
          <span className="flex items-center gap-1 px-2 py-1 rounded text-xs bg-amber-900 text-amber-200">
            <Clock className="w-3 h-3" />
            {t('common.pending')}
          </span>
        );
      case 'confirmed':
        return (
          <span className="flex items-center gap-1 px-2 py-1 rounded text-xs bg-green-900 text-green-200">
            <CheckCircle className="w-3 h-3" />
            {t('common.confirmed')}
          </span>
        );
      case 'rejected':
        return (
          <span className="flex items-center gap-1 px-2 py-1 rounded text-xs bg-red-900 text-red-200">
            <XCircle className="w-3 h-3" />
            {t('common.rejected')}
          </span>
        );
      default:
        return null;
    }
  };

  const formatDate = (dateStr: string) => {
    return formatDateWithPreferences(dateStr, preferences.date_format || 'DD/MM/YYYY', language);
  };

  return (
    <div className="space-y-4">
      {error && (
        <div className="p-3 bg-red-900/50 border border-red-700 rounded text-red-200">
          {error}
          <button onClick={() => setError('')} className="ml-2 text-red-400 hover:text-red-200">x</button>
        </div>
      )}

      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100 flex items-center gap-2">
            <Bell className="w-5 h-5" />
            {t('notifications.paymentNotifications')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="bg-slate-700 mb-4">
              <TabsTrigger value="pending" className="data-[state=active]:bg-slate-600">
                {t('notifications.pendingPayments')}
              </TabsTrigger>
              <TabsTrigger value="confirmed" className="data-[state=active]:bg-slate-600">
                {t('notifications.confirmedPayments')}
              </TabsTrigger>
              <TabsTrigger value="rejected" className="data-[state=active]:bg-slate-600">
                {t('notifications.rejectedPayments')}
              </TabsTrigger>
              <TabsTrigger value="all" className="data-[state=active]:bg-slate-600">
                {t('notifications.allNotifications')}
              </TabsTrigger>
            </TabsList>

            <TabsContent value={activeTab} className="mt-0">
              {loading ? (
                <div className="text-slate-400 text-center py-8">{t('common.loading')}</div>
              ) : notifications.length === 0 ? (
                <div className="text-slate-400 text-center py-8">{t('notifications.noNotifications')}</div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow className="border-slate-700">
                      <TableHead className="text-slate-400">{t('notifications.notificationDate')}</TableHead>
                      <TableHead className="text-slate-400">{t('notifications.property')}</TableHead>
                      <TableHead className="text-slate-400">{t('notifications.renter')}</TableHead>
                      <TableHead className="text-slate-400">{t('notifications.bill')}</TableHead>
                      <TableHead className="text-slate-400">{t('notifications.amount')}</TableHead>
                      <TableHead className="text-slate-400">{t('notifications.status')}</TableHead>
                      <TableHead className="text-slate-400">{t('notifications.actions')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {notifications.map((item) => (
                      <TableRow key={item.notification.id} className="border-slate-700">
                        <TableCell className="text-slate-300">
                          {formatDate(item.notification.created_at)}
                        </TableCell>
                        <TableCell className="text-slate-200">
                          <div className="flex items-center gap-1">
                            <Building2 className="w-4 h-4 text-slate-400" />
                            {item.property?.name || '-'}
                          </div>
                        </TableCell>
                        <TableCell className="text-slate-200">
                          <div className="flex items-center gap-1">
                            <User className="w-4 h-4 text-slate-400" />
                            {item.renter?.name || '-'}
                          </div>
                        </TableCell>
                        <TableCell className="text-slate-200">
                          <div className="flex items-center gap-1">
                            <FileText className="w-4 h-4 text-slate-400" />
                            {item.bill?.description || '-'}
                          </div>
                        </TableCell>
                        <TableCell className="text-emerald-400 font-medium">
                          {item.notification.amount.toFixed(2)} {item.notification.currency}
                        </TableCell>
                        <TableCell>
                          {getStatusBadge(item.notification.status)}
                        </TableCell>
                        <TableCell>
                          {item.notification.status === 'pending' ? (
                            <div className="flex items-center gap-2">
                              <Button
                                size="sm"
                                onClick={() => openActionDialog(item, 'confirm')}
                                className="bg-emerald-600 hover:bg-emerald-700"
                              >
                                <CheckCircle className="w-4 h-4 mr-1" />
                                {t('common.confirm')}
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => openActionDialog(item, 'reject')}
                                className="border-red-600 text-red-400 hover:bg-red-900/50"
                              >
                                <XCircle className="w-4 h-4 mr-1" />
                                {t('common.reject')}
                              </Button>
                            </div>
                          ) : (
                            <span className="text-slate-500 text-sm">
                              {item.notification.confirmed_at && formatDate(item.notification.confirmed_at)}
                            </span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Action Confirmation Dialog */}
      <Dialog open={!!selectedNotification && !!actionType} onOpenChange={(open) => {
        if (!open) {
          setSelectedNotification(null);
          setActionType(null);
          setLandlordNote('');
        }
      }}>
        <DialogContent className="bg-slate-800 border-slate-700 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-slate-100">
              {actionType === 'confirm' ? t('notifications.confirmPayment') : t('notifications.rejectPayment')}
            </DialogTitle>
            <DialogDescription className="text-slate-400">
              {actionType === 'confirm' 
                ? t('notifications.confirmPaymentQuestion')
                : t('notifications.rejectPaymentQuestion')
              }
            </DialogDescription>
          </DialogHeader>
          
          {selectedNotification && (
            <div className="space-y-4">
              {/* Notification Details */}
              <div className="bg-slate-900 rounded-lg p-4 space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-400">{t('notifications.renter')}:</span>
                  <span className="text-slate-200">{selectedNotification.renter?.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">{t('notifications.bill')}:</span>
                  <span className="text-slate-200">{selectedNotification.bill?.description}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">{t('notifications.amount')}:</span>
                  <span className="text-emerald-400 font-medium">
                    {selectedNotification.notification.amount.toFixed(2)} {selectedNotification.notification.currency}
                  </span>
                </div>
                {selectedNotification.notification.renter_note && (
                  <div className="pt-2 border-t border-slate-700">
                    <div className="flex items-center gap-1 text-slate-400 text-sm mb-1">
                      <MessageSquare className="w-3 h-3" />
                      {t('notifications.renterNote')}:
                    </div>
                    <p className="text-slate-300 text-sm bg-slate-800 rounded p-2">
                      {selectedNotification.notification.renter_note}
                    </p>
                  </div>
                )}
              </div>

              {/* Landlord Note */}
              <div className="space-y-2">
                <label className="text-slate-400 text-sm">{t('notifications.landlordNote')}</label>
                <Textarea
                  value={landlordNote}
                  onChange={(e) => setLandlordNote(e.target.value)}
                  placeholder={t('notifications.landlordNotePlaceholder')}
                  className="bg-slate-900 border-slate-600 text-slate-200 placeholder:text-slate-500"
                  rows={2}
                />
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setSelectedNotification(null);
                setActionType(null);
                setLandlordNote('');
              }}
              className="border-slate-600 text-slate-300 hover:bg-slate-700"
            >
              {t('common.cancel')}
            </Button>
            <Button
              onClick={handleAction}
              disabled={processing}
              className={actionType === 'confirm' 
                ? 'bg-emerald-600 hover:bg-emerald-700' 
                : 'bg-red-600 hover:bg-red-700'
              }
            >
              {processing 
                ? (actionType === 'confirm' ? t('notifications.confirming') : t('notifications.rejecting'))
                : (actionType === 'confirm' ? t('common.confirm') : t('common.reject'))
              }
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
