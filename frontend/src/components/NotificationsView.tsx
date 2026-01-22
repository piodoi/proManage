import { useState, useEffect, useCallback, useMemo } from 'react';
import { api, PaymentNotificationWithDetails, Property } from '../api';
import { useAuth } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Bell, CheckCircle, XCircle, Clock, Building2, User, FileText, MessageSquare, Trash2 } from 'lucide-react';
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
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('pending');
  const [selectedNotification, setSelectedNotification] = useState<PaymentNotificationWithDetails | null>(null);
  const [actionType, setActionType] = useState<'confirm' | 'reject' | null>(null);
  const [landlordNote, setLandlordNote] = useState('');
  const [processing, setProcessing] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [selectedPropertyFilter, setSelectedPropertyFilter] = useState<string>('all');
  const [selectedNotificationIds, setSelectedNotificationIds] = useState<Set<string>>(new Set());

  // Load properties for filter dropdown
  useEffect(() => {
    const loadProperties = async () => {
      if (!token) return;
      try {
        const data = await api.properties.list(token);
        setProperties(data);
      } catch (err) {
        console.error('Failed to load properties:', err);
      }
    };
    loadProperties();
  }, [token]);

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
      
      // Clear selection when reloading
      setSelectedNotificationIds(new Set());
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

  // Filter notifications by property
  const filteredNotifications = useMemo(() => {
    if (selectedPropertyFilter === 'all') {
      return notifications;
    }
    return notifications.filter(n => n.property?.id === selectedPropertyFilter);
  }, [notifications, selectedPropertyFilter]);

  // Get unique properties from notifications for the filter
  const notificationProperties = useMemo(() => {
    const propertyMap = new Map<string, { id: string; name: string }>();
    notifications.forEach(n => {
      if (n.property) {
        propertyMap.set(n.property.id, { id: n.property.id, name: n.property.name });
      }
    });
    return Array.from(propertyMap.values());
  }, [notifications]);

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

  const handleClearAll = async () => {
    if (!token) return;
    
    setClearing(true);
    try {
      const status = activeTab === 'all' ? undefined : activeTab;
      const propertyId = selectedPropertyFilter !== 'all' ? selectedPropertyFilter : undefined;
      await api.paymentNotifications.clearAll(token, status, propertyId);
      
      setShowClearConfirm(false);
      loadNotifications();
      
      // Refresh pending count
      if (onCountChange) {
        const { count } = await api.paymentNotifications.count(token);
        onCountChange(count);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.generic'));
    } finally {
      setClearing(false);
    }
  };

  const handleClearSelected = async () => {
    if (!token || selectedNotificationIds.size === 0) return;
    
    setClearing(true);
    try {
      await api.paymentNotifications.clearSelected(token, Array.from(selectedNotificationIds));
      
      setSelectedNotificationIds(new Set());
      loadNotifications();
      
      // Refresh pending count
      if (onCountChange) {
        const { count } = await api.paymentNotifications.count(token);
        onCountChange(count);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.generic'));
    } finally {
      setClearing(false);
    }
  };

  const toggleNotificationSelection = (notificationId: string) => {
    setSelectedNotificationIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(notificationId)) {
        newSet.delete(notificationId);
      } else {
        newSet.add(notificationId);
      }
      return newSet;
    });
  };

  const toggleSelectAll = () => {
    if (selectedNotificationIds.size === filteredNotifications.length) {
      // Deselect all
      setSelectedNotificationIds(new Set());
    } else {
      // Select all filtered notifications
      setSelectedNotificationIds(new Set(filteredNotifications.map(n => n.notification.id)));
    }
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
            <div className="flex flex-col gap-4 mb-4">
              <div className="flex items-center justify-between">
                <TabsList className="bg-slate-700">
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
              </div>
              
              {/* Filter and action row */}
              <div className="flex items-center justify-between gap-4">
                {/* Property filter */}
                <div className="flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-slate-400" />
                  <Select
                    value={selectedPropertyFilter}
                    onValueChange={setSelectedPropertyFilter}
                  >
                    <SelectTrigger className="w-48 bg-slate-700 border-slate-600 text-slate-200">
                      <SelectValue placeholder={t('notifications.filterByProperty') || 'Filter by property'} />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-600">
                      <SelectItem value="all" className="text-slate-200 hover:bg-slate-700">
                        {t('notifications.allProperties') || 'All Properties'}
                      </SelectItem>
                      {notificationProperties.map((prop) => (
                        <SelectItem
                          key={prop.id}
                          value={prop.id}
                          className="text-slate-200 hover:bg-slate-700"
                        >
                          {prop.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                {/* Action buttons */}
                <div className="flex items-center gap-2">
                  {selectedNotificationIds.size > 0 && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleClearSelected}
                      disabled={clearing}
                      className="border-red-600 text-red-400 hover:bg-red-900/50"
                    >
                      <Trash2 className="w-4 h-4 mr-1" />
                      {t('notifications.clearSelected') || 'Clear Selected'} ({selectedNotificationIds.size})
                    </Button>
                  )}
                  {filteredNotifications.length > 0 && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowClearConfirm(true)}
                      className="border-red-600 text-red-400 hover:bg-red-900/50"
                    >
                      <Trash2 className="w-4 h-4 mr-1" />
                      {t('notifications.clearAll')}
                      {selectedPropertyFilter !== 'all' && ` (${filteredNotifications.length})`}
                    </Button>
                  )}
                </div>
              </div>
            </div>

            <TabsContent value={activeTab} className="mt-0">
              {loading ? (
                <div className="text-slate-400 text-center py-8">{t('common.loading')}</div>
              ) : filteredNotifications.length === 0 ? (
                <div className="text-slate-400 text-center py-8">{t('notifications.noNotifications')}</div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow className="border-slate-700">
                      <TableHead className="text-slate-400 w-10">
                        <Checkbox
                          checked={selectedNotificationIds.size === filteredNotifications.length && filteredNotifications.length > 0}
                          onCheckedChange={toggleSelectAll}
                          className="border-slate-500 data-[state=checked]:bg-emerald-600 data-[state=checked]:border-emerald-600"
                        />
                      </TableHead>
                      <TableHead className="text-slate-400">{t('notifications.notificationDate')}</TableHead>
                      <TableHead className="text-slate-400">{t('notifications.property')}</TableHead>
                      <TableHead className="text-slate-400">{t('notifications.notes')}</TableHead>
                      <TableHead className="text-slate-400">{t('notifications.renter')}</TableHead>
                      <TableHead className="text-slate-400">{t('notifications.bill')}</TableHead>
                      <TableHead className="text-slate-400">{t('notifications.amount')}</TableHead>
                      <TableHead className="text-slate-400">{t('notifications.status')}</TableHead>
                      <TableHead className="text-slate-400">{t('notifications.actions')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredNotifications.map((item) => {
                      // Check if this is a contract expiry notification (no bill, amount = 0)
                      const isContractExpiry = !item.notification.bill_id || item.notification.amount === 0;
                      const hasNotes = item.notification.renter_note || item.notification.landlord_note;
                      const isSelected = selectedNotificationIds.has(item.notification.id);
                      
                      return (
                        <TableRow key={item.notification.id} className={`border-slate-700 ${isSelected ? 'bg-slate-700/50' : ''}`}>
                          <TableCell>
                            <Checkbox
                              checked={isSelected}
                              onCheckedChange={() => toggleNotificationSelection(item.notification.id)}
                              className="border-slate-500 data-[state=checked]:bg-emerald-600 data-[state=checked]:border-emerald-600"
                            />
                          </TableCell>
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
                            {hasNotes ? (
                              <div className="flex flex-col gap-1 max-w-xs">
                                {/* Show renter note if present */}
                                {item.notification.renter_note && (
                                  <div className="text-xs text-amber-400 flex items-start gap-1">
                                    <MessageSquare className="w-3 h-3 mt-0.5 flex-shrink-0" />
                                    <span className="break-words">{item.notification.renter_note}</span>
                                  </div>
                                )}
                                {/* Show landlord note if present */}
                                {item.notification.landlord_note && (
                                  <div className="text-xs text-blue-400 flex items-start gap-1">
                                    <MessageSquare className="w-3 h-3 mt-0.5 flex-shrink-0" />
                                    <span className="break-words">{item.notification.landlord_note}</span>
                                  </div>
                                )}
                              </div>
                            ) : (
                              <span className="text-slate-500">-</span>
                            )}
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
                              {isContractExpiry ? t('common.none') : (item.bill?.description || '-')}
                            </div>
                          </TableCell>
                          <TableCell className={isContractExpiry ? "text-slate-500" : "text-emerald-400 font-medium"}>
                            {isContractExpiry ? t('common.none') : `${item.notification.amount.toFixed(2)} ${item.notification.currency}`}
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
                      );
                    })}
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

      {/* Clear All Confirmation Dialog */}
      <Dialog open={showClearConfirm} onOpenChange={setShowClearConfirm}>
        <DialogContent className="bg-slate-800 border-slate-700 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-slate-100">
              {t('notifications.clearAll')}
            </DialogTitle>
            <DialogDescription className="text-slate-400">
              {selectedPropertyFilter !== 'all' 
                ? (t('notifications.clearAllForPropertyConfirm') || `This will delete all ${activeTab !== 'all' ? activeTab : ''} notifications for the selected property.`)
                : t('notifications.clearAllConfirm')
              }
            </DialogDescription>
          </DialogHeader>
          
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowClearConfirm(false)}
              className="border-slate-600 text-slate-300 hover:bg-slate-700"
            >
              {t('common.cancel')}
            </Button>
            <Button
              onClick={handleClearAll}
              disabled={clearing}
              className="bg-red-600 hover:bg-red-700"
            >
              {clearing ? t('notifications.clearing') : t('notifications.clearAll')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
