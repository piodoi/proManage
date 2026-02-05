import { useState, useEffect } from 'react';
import { Renter, Bill, getRenterBillPdfUrl } from '../../api';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Copy, MessageCircle, ExternalLink } from 'lucide-react';
import { useI18n } from '../../lib/i18n';
import { usePreferences } from '../../hooks/usePreferences';
import { formatDateWithPreferences } from '../../lib/utils';
import { formatAmount } from '../../utils/currency';

type RenterAccessLinkDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  renterLink: { token: string; link: string; renter: Renter | null } | null;
  pendingBills: Bill[];
};

export default function RenterAccessLinkDialog({
  open,
  onOpenChange,
  renterLink,
  pendingBills,
}: RenterAccessLinkDialogProps) {
  const { t, language } = useI18n();
  const { preferences } = usePreferences();
  const [selectedBillIds, setSelectedBillIds] = useState<Set<string>>(new Set());

  // Pre-select all non-rent bills when dialog opens
  useEffect(() => {
    if (open && pendingBills.length > 0) {
      const nonRentBillIds = pendingBills
        .filter(bill => bill.bill_type !== 'rent')
        .map(bill => bill.id);
      setSelectedBillIds(new Set(nonRentBillIds));
    } else if (!open) {
      setSelectedBillIds(new Set());
    }
  }, [open, pendingBills]);

  const toggleBillSelection = (billId: string) => {
    setSelectedBillIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(billId)) {
        newSet.delete(billId);
      } else {
        newSet.add(billId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    setSelectedBillIds(new Set(pendingBills.map(bill => bill.id)));
  };

  const handleSelectNone = () => {
    setSelectedBillIds(new Set());
  };

  const handleRowClick = (e: React.MouseEvent, billId: string) => {
    // Don't toggle if clicking on the checkbox itself
    const target = e.target as HTMLElement;
    if (target.closest('[role="checkbox"]')) {
      return;
    }
    toggleBillSelection(billId);
  };

  // WhatsApp message template
  const getWhatsAppMessage = (link: string, selectedBills: Bill[], token: string): string => {
    if (selectedBills.length === 0) {
      return t('renter.whatsAppMessage').replace('{link}', link);
    }
    
    const billsInfo = selectedBills.map(bill => {
      const supplierName = bill.description || t('bill.other');
      const billNo = bill.bill_number || "";
      const amount = formatAmount(bill.amount, bill.currency || 'RON');
      const pdfUrl = bill.has_pdf ? ` - ${getRenterBillPdfUrl(token, bill.id)}` : '';
      return `* ${supplierName}  : ${amount} - ${billNo}${pdfUrl}`;
    }).join('\n');
    
    return t('renter.whatsAppMessageWithBills')
      .replace('{bills}', billsInfo)
      .replace('{link}', link);
  };

  // Get text message for copying (without encoding)
  const getTextMessage = (): string => {
    if (!renterLink) return '';
    const link = `${window.location.origin}/renter/${renterLink.token}`;
    const selectedBills = pendingBills.filter(bill => selectedBillIds.has(bill.id));
    return getWhatsAppMessage(link, selectedBills, renterLink.token);
  };

  const getWhatsAppUrl = (): string | null => {
    if (!renterLink || !renterLink.renter) return null;
    
    const userPhone = preferences.phone_number;
    const renterPhone = renterLink.renter.phone;
    
    if (!userPhone || !renterPhone) return null;
    
    const cleanPhone = renterPhone.replace(/\D/g, '');
    const link = `${window.location.origin}/renter/${renterLink.token}`;
    const selectedBills = pendingBills.filter(bill => selectedBillIds.has(bill.id));
    const message = getWhatsAppMessage(link, selectedBills, renterLink.token);
    
    return `https://wa.me/${cleanPhone}?text=${encodeURIComponent(message)}`;
  };

  const handleSendToWhatsApp = () => {
    const whatsappUrl = getWhatsAppUrl();
    if (whatsappUrl) {
      window.open(whatsappUrl, '_blank');
    }
  };

  const handleCopyMessage = async () => {
    const message = getTextMessage();
    if (message) {
      await navigator.clipboard.writeText(message);
    }
  };

  const handleCopyLink = () => {
    if (renterLink) {
      navigator.clipboard.writeText(`${window.location.origin}/renter/${renterLink.token}`);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-slate-800 border-slate-700 max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-slate-100">{t('renter.accessLinkTitle')}</DialogTitle>
          <DialogDescription className="text-slate-400 sr-only">
            {t('renter.accessLinkTitle')}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <p className="text-slate-400 text-sm">
            {t('renter.accessLinkDescription')}
          </p>
          <div className="flex gap-2">
            <Input
              readOnly
              value={renterLink ? `${window.location.origin}/renter/${renterLink.token}` : ''}
              className="bg-slate-700 border-slate-600 text-slate-100"
            />
            <Button
              onClick={handleCopyLink}
              variant="outline"
              className="border-slate-600"
              title={t('common.copy')}
            >
              <Copy className="w-4 h-4" />
            </Button>
            <Button
              onClick={() => renterLink && window.open(`/renter/${renterLink.token}`, '_blank')}
              variant="outline"
              className="border-slate-600"
              title={t('common.open')}
            >
              <ExternalLink className="w-4 h-4" />
            </Button>
          </div>
          
          {/* Pending Bills Section */}
          {pendingBills.length > 0 && (
            <div className="border border-slate-600 rounded-lg p-3 bg-slate-700/50">
              <div className="flex items-center justify-between mb-2">
                <p className="text-slate-300 text-sm font-medium">
                  {t('renter.pendingBillsTitle')} ({pendingBills.length})
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleSelectAll}
                    className="text-xs h-7 px-2 border-slate-500"
                  >
                    {t('common.selectAll')}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleSelectNone}
                    className="text-xs h-7 px-2 border-slate-500"
                  >
                    {t('common.none')}
                  </Button>
                </div>
              </div>
              <p className="text-slate-400 text-xs mb-3">
                {t('renter.pendingBillsDescription')}
              </p>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {pendingBills.map((bill) => (
                  <div
                    key={bill.id}
                    className="flex items-center gap-3 p-2 rounded bg-slate-700 hover:bg-slate-600/50 cursor-pointer transition-colors"
                    onClick={(e) => handleRowClick(e, bill.id)}
                  >
                    <Checkbox
                      id={`bill-${bill.id}`}
                      checked={selectedBillIds.has(bill.id)}
                      onCheckedChange={() => toggleBillSelection(bill.id)}
                      className="border-slate-500 data-[state=checked]:bg-green-600 data-[state=checked]:border-green-600"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0 flex-wrap">
                          <span className="text-slate-200 text-sm truncate">
                            {bill.description || t('bill.other')}
                          </span>
                          {bill.has_pdf && (
                            <span title={t('bill.pdfAvailable')} className="text-red-500 text-xs font-bold bg-slate-100 flex-shrink-0">.PDF.</span>
                          )}
                          <span className={`text-xs px-1.5 py-0.5 rounded ${bill.status === 'overdue' ? 'text-red-400 bg-red-900/30' : 'text-amber-400 bg-amber-900/30'}`}>
                            {t(`bill.status.${bill.status}`)}
                          </span>
                          {bill.due_date && (
                            <span className="text-xs text-slate-400">{formatDateWithPreferences(bill.due_date, preferences.date_format, language)}</span>
                          )}
                        </div>
                        <span className="text-slate-300 text-sm font-medium whitespace-nowrap">
                          {formatAmount(bill.amount, bill.currency || 'RON')}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <p className={`text-xs mt-2 ${selectedBillIds.size > 0 ? 'text-green-400' : 'text-slate-500'}`}>
                {selectedBillIds.size > 0
                  ? t('renter.billsSelectedCount', { count: selectedBillIds.size })
                  : t('renter.billsSelectedCount', { count: 0 })
                }
              </p>
            </div>
          )}
          
          {renterLink && renterLink.renter && (
            <div className="pt-2 space-y-2">
              <div className="flex gap-2">
                <Button
                  onClick={handleSendToWhatsApp}
                  disabled={!preferences.phone_number || !renterLink.renter?.phone}
                  variant="outline"
                  className="flex-1 border-slate-600 bg-green-600/20 hover:bg-green-600/30 text-green-400 disabled:opacity-50 disabled:cursor-not-allowed"
                  title={(!preferences.phone_number || !renterLink.renter?.phone) ? t('renter.whatsAppUnavailable') : t('renter.sendToWhatsApp')}
                >
                  <MessageCircle className="w-4 h-4 mr-2" />
                  {selectedBillIds.size > 0
                    ? t('renter.sendToWhatsAppWithBills', { count: selectedBillIds.size })
                    : t('renter.sendToWhatsApp')
                  }
                </Button>
                <Button
                  onClick={handleCopyMessage}
                  variant="outline"
                  className="border-slate-600 bg-green-600/20 hover:bg-green-600/30 text-green-400"
                  title={t('common.copy')}
                >
                  <Copy className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
