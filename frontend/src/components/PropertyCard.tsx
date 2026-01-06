import { useState } from 'react';
import { api, Property, Renter, Bill } from '../api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { formatDateWithPreferences } from '../lib/utils';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { ExternalLink, Trash2, Pencil, Copy, Settings, MessageCircle } from 'lucide-react';
import PropertyBillsView from './PropertyBillsView';
import RenterDialog from './dialogs/RenterDialog';
import PropertySupplierSettingsDialog from './dialogs/PropertySupplierSettingsDialog';
import { useI18n } from '../lib/i18n';
import { usePreferences } from '../hooks/usePreferences';
import { useScrollPreservation } from '../hooks/useScrollPreservation';
import { convertCurrency, formatAmount } from '../utils/currency';

type PropertyCardProps = {
  token: string | null;
  property: Property;
  renters: Renter[];
  bills: Bill[];
  exchangeRates: { EUR: number; USD: number; RON: number };
  onDelete: (propertyId: string) => void;
  onDataChange: () => void;
  onError: (error: string) => void;
};

export default function PropertyCard({
  token,
  property,
  renters,
  bills,
  exchangeRates,
  onDelete,
  onDataChange,
  onError,
}: PropertyCardProps) {
  const { t, language } = useI18n();
  const { preferences } = usePreferences();
  const { saveScroll, restoreScroll } = useScrollPreservation();
  const [showRenterDialog, setShowRenterDialog] = useState(false);
  const [showSupplierSettings, setShowSupplierSettings] = useState(false);
  const [editingRenter, setEditingRenter] = useState<Renter | null>(null);
  const [renterLink, setRenterLink] = useState<{ token: string; link: string; renter: Renter | null } | null>(null);

  const handleGetRenterLink = async (renterId: string) => {
    if (!token) return;
    try {
      const link = await api.renters.getLink(token, renterId);
      const renter = renters.find(r => r.id === renterId) || null;
      setRenterLink({ token: link.access_token, link: link.link, renter });
    } catch (err) {
      onError(err instanceof Error ? err.message : t('errors.generic'));
    }
  };

  // WhatsApp message template - customize this message in locales/en.json and locales/ro.json under renter.whatsAppMessage
  const getWhatsAppMessage = (link: string): string => {
    return t('renter.whatsAppMessage').replace('{link}', link);
  };

  const getWhatsAppUrl = (): string | null => {
    if (!renterLink || !renterLink.renter) return null;
    
    const userPhone = preferences.phone_number;
    const renterPhone = renterLink.renter.phone;
    
    if (!userPhone || !renterPhone) return null;
    
    // Clean phone number: remove all non-digit characters
    const cleanPhone = renterPhone.replace(/\D/g, '');
    
    const link = `${window.location.origin}/renter/${renterLink.token}`;
    const message = getWhatsAppMessage(link);
    const whatsappUrl = `https://wa.me/${cleanPhone}?text=${encodeURIComponent(message)}`;
    
    return whatsappUrl;
  };

  const handleSendToWhatsApp = () => {
    const whatsappUrl = getWhatsAppUrl();
    if (whatsappUrl) {
      window.open(whatsappUrl, '_blank');
    }
  };

  const handleCopyWhatsAppLink = async () => {
    const whatsappUrl = getWhatsAppUrl();
    if (whatsappUrl) {
      await navigator.clipboard.writeText(whatsappUrl);
    }
  };

  const handleDeleteRenter = async (renterId: string) => {
    if (!token) return;
    if (!confirm(t('renter.confirmDelete'))) {
      return;
    }
    try {
      await api.renters.delete(token, renterId);
      onDataChange();
    } catch (err) {
      onError(err instanceof Error ? err.message : t('errors.generic'));
    }
  };

  const openEditRenter = (renter: Renter) => {
    setEditingRenter(renter);
    setShowRenterDialog(true);
  };

  return (
    <>
      <Card key={property.id} className="bg-slate-950 border-slate-700">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-slate-100">{property.name}</CardTitle>
            <p className="text-sm text-slate-400">{property.address}</p>
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={() => {
                saveScroll();
                setShowSupplierSettings(true);
              }}
              className="bg-slate-700 text-blue-400 hover:bg-slate-600 hover:text-blue-300 border border-slate-600"
              title={t('supplier.manageSuppliers')}
            >
              <Settings className="w-4 h-4" />
            </Button>
            <PropertySupplierSettingsDialog
              token={token}
              property={property}
              open={showSupplierSettings}
              onOpenChange={(open) => {
                if (open) {
                  saveScroll();
                }
                setShowSupplierSettings(open);
              }}
              onSuccess={() => {
                onDataChange();
                // Restore scroll after data change completes (delay to allow async data loading)
                setTimeout(() => {
                  requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                      restoreScroll();
                    });
                  });
                }, 100);
              }}
              onError={onError}
            />
            <RenterDialog
              token={token}
              propertyId={property.id}
              renter={editingRenter}
              open={showRenterDialog}
              onOpenChange={(open) => {
                if (open) {
                  saveScroll();
                }
                setShowRenterDialog(open);
                if (!open) {
                  setEditingRenter(null);
                }
              }}
              onSuccess={() => {
                onDataChange();
                // Restore scroll after data change completes (delay to allow async data loading)
                setTimeout(() => {
                  requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                      restoreScroll();
                    });
                  });
                }, 100);
              }}
              onError={onError}
            />
            <Button
              size="sm"
              onClick={() => onDelete(property.id)}
              className="bg-slate-700 text-red-400 hover:bg-slate-600 hover:text-red-200 border border-slate-600"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="mb-3">
            <span className="text-slate-200 font-medium">{t('renter.renters')}</span>
          </div>
          {renters.length === 0 ? (
            <p className="text-slate-500 text-xs">{t('renter.noRenters')}</p>
          ) : (
            <div className="space-y-1">
              {renters.map((renter) => {
                const rentAmountEUR = renter.rent_amount_eur || 0;
                const rentAmountRON = rentAmountEUR > 0
                  ? convertCurrency(rentAmountEUR, 'EUR', 'RON', exchangeRates)
                  : 0;

                return (
                  <div key={renter.id} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-300 font-medium">{renter.name}</span>
                      {(rentAmountEUR > 0 || renter.rent_day || renter.start_contract_date) && (
                        <span className="text-xs text-slate-400">
                          {rentAmountEUR > 0 && (
                            <>
                              <span>{formatAmount(rentAmountEUR, 'EUR')}</span>
                              <span className="ml-1">({formatAmount(rentAmountRON, 'RON')})</span>
                            </>
                          )}
                          {renter.rent_day && (
                            <span className="ml-2">• {t('renter.dueDay')}: {renter.rent_day}</span>
                          )}
                          {renter.start_contract_date && (
                            <span className="ml-2">• {t('renter.start')}: {formatDateWithPreferences(renter.start_contract_date, preferences.date_format, language)}</span>
                          )}
                        </span>
                      )}
                    </div>
                    <div className="flex gap-1">
                      <Button
                        size="sm"
                        onClick={() => openEditRenter(renter)}
                        className="bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600 h-6 px-2 w-6"
                        title={t('renter.editRenter')}
                      >
                        <Pencil className="w-3 h-3" />
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handleGetRenterLink(renter.id)}
                        className="bg-slate-700 text-emerald-400 hover:bg-slate-600 hover:text-emerald-300 border border-slate-600 h-6 px-2 w-6"
                        title={t('renter.getLink')}
                      >
                        <ExternalLink className="w-3 h-3" />
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handleDeleteRenter(renter.id)}
                        className="bg-slate-700 text-red-400 hover:bg-slate-600 hover:text-red-200 border border-slate-600 h-6 px-2 w-6"
                        title={t('renter.deleteRenter')}
                      >
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
        <CardContent className="pt-0">
          <PropertyBillsView
            token={token}
            propertyId={property.id}
            property={property}
            renters={renters}
            bills={bills}
            onError={onError}
            onBillsChange={onDataChange}
          />
        </CardContent>
      </Card>

      {/* Renter Link Dialog */}
      <Dialog open={!!renterLink} onOpenChange={(open) => !open && setRenterLink(null)}>
        <DialogContent className="bg-slate-800 border-slate-700">
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
                onClick={() => renterLink && navigator.clipboard.writeText(`${window.location.origin}/renter/${renterLink.token}`)}
                variant="outline"
                className="border-slate-600"
              >
                <Copy className="w-4 h-4" />
              </Button>
            </div>
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
                    {t('renter.sendToWhatsApp')}
                  </Button>
                  <Button
                    onClick={handleCopyWhatsAppLink}
                    disabled={!preferences.phone_number || !renterLink.renter?.phone}
                    variant="outline"
                    className="border-slate-600 bg-green-600/20 hover:bg-green-600/30 text-green-400 disabled:opacity-50 disabled:cursor-not-allowed"
                    title={(!preferences.phone_number || !renterLink.renter?.phone) ? t('renter.whatsAppUnavailable') : 'Copy WhatsApp link'}
                  >
                    <Copy className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

