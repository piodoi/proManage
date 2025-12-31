import { useState, useEffect } from 'react';
import { api, Property, Renter, Bill, SubscriptionStatus } from '../api';
import { useAuth } from '../App';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Building2, Settings } from 'lucide-react';
import SettingsView from './SettingsView';
import PropertyCard from './PropertyCard';
import PropertyDialog from './dialogs/PropertyDialog';
import EblocImportDialog from './dialogs/EblocImportDialog';
import { useI18n } from '../lib/i18n';

type LandlordViewProps = {
  token: string | null;
  onError?: (error: string) => void;
  hideSettings?: boolean;
};

export default function LandlordView({ token, onError, hideSettings = false }: LandlordViewProps) {
  const { user } = useAuth();
  const { t } = useI18n();
  const [properties, setProperties] = useState<Property[]>([]);
  const [renters, setRenters] = useState<Record<string, Renter[]>>({});
  const [bills, setBills] = useState<Bill[]>([]);
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showPropertyForm, setShowPropertyForm] = useState(false);
  const [showEblocDiscover, setShowEblocDiscover] = useState(false);
  const [exchangeRates, setExchangeRates] = useState<{ EUR: number; USD: number; RON: number }>({ EUR: 1, USD: 1, RON: 4.97 });

  useEffect(() => {
    loadData();
    loadExchangeRates();
  }, [token]);

  const loadExchangeRates = async () => {
    try {
      const response = await fetch('https://api.exchangerate-api.com/v4/latest/EUR');
      if (!response.ok) throw new Error('Failed to fetch exchange rates');
      const data = await response.json();
      setExchangeRates({
        EUR: 1,
        USD: data.rates?.USD || 1.1,
        RON: data.rates?.RON || 4.97,
      });
    } catch (err) {
      console.error('[LandlordView] Failed to load exchange rates:', err);
      setExchangeRates({ EUR: 1, USD: 1.1, RON: 4.97 });
    }
  };

  const handleError = (err: unknown) => {
    const message = err instanceof Error ? err.message : t('errors.generic');
    setError(message);
    if (onError) {
      onError(message);
    }
  };

  const loadData = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [propsData, billsData, subData] = await Promise.all([
        api.properties.list(token),
        api.bills.list(token),
        api.subscription.status(token),
      ]);

      setProperties(propsData);
      setBills(billsData);
      setSubscription(subData);

      for (const prop of propsData) {
        const rentersData = await api.renters.list(token, prop.id);
        setRenters((prev) => ({ ...prev, [prop.id]: rentersData }));
      }
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteProperty = async (propertyId: string) => {
    if (!token) return;
    if (!confirm(t('property.confirmDelete'))) {
      return;
    }
    try {
      await api.properties.delete(token, propertyId);
      loadData();
    } catch (err) {
      handleError(err);
    }
  };


  return (
    <>
      {error && !error.includes('E-bloc') && (
        <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded text-red-200">
          {error}
          <button onClick={() => setError('')} className="ml-2 text-red-400 hover:text-red-200">x</button>
        </div>
      )}

      {hideSettings ? (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-medium text-slate-100">{t('property.properties')}</h2>
            <div className="flex gap-2">
              <EblocImportDialog
                token={token}
                open={showEblocDiscover}
                onOpenChange={setShowEblocDiscover}
                onSuccess={loadData}
                onError={setError}
              />
              <PropertyDialog
                token={token}
                open={showPropertyForm}
                onOpenChange={setShowPropertyForm}
                onSuccess={loadData}
                onError={setError}
                canAddProperty={user?.role === 'admin' || (subscription ? subscription.can_add_property : false)}
              />
            </div>
          </div>

          {loading ? (
            <div className="text-slate-400 text-center py-8">{t('common.loading')}</div>
          ) : properties.length === 0 ? (
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="py-8 text-center text-slate-400">
                {t('property.noProperties')}
              </CardContent>
            </Card>
          ) : (
            properties.map((property) => (
              <PropertyCard
                key={property.id}
                token={token}
                property={property}
                renters={renters[property.id] || []}
                bills={bills}
                exchangeRates={exchangeRates}
                onDelete={handleDeleteProperty}
                onDataChange={loadData}
                onError={setError}
              />
            ))
          )}
        </div>
      ) : (
        <Tabs defaultValue="properties" className="space-y-4">
          <TabsList className="bg-slate-800 border border-slate-700">
            <TabsTrigger value="properties" className="data-[state=active]:bg-slate-700">
              <Building2 className="w-4 h-4 mr-2" />
              {t('property.properties')}
            </TabsTrigger>
            <TabsTrigger value="settings" className="data-[state=active]:bg-slate-700">
              <Settings className="w-4 h-4 mr-2" />
              {t('settings.settings')}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="properties" className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-medium text-slate-100">{t('property.properties')}</h2>
              <div className="flex gap-2">
                <EblocImportDialog
                  token={token}
                  open={showEblocDiscover}
                  onOpenChange={setShowEblocDiscover}
                  onSuccess={loadData}
                  onError={setError}
                />
                <PropertyDialog
                  token={token}
                  open={showPropertyForm}
                  onOpenChange={setShowPropertyForm}
                  onSuccess={loadData}
                  onError={setError}
                  canAddProperty={user?.role === 'admin' || (subscription ? subscription.can_add_property : false)}
                />
              </div>
            </div>

            {loading ? (
              <div className="text-slate-400 text-center py-8">{t('common.loading')}</div>
            ) : properties.length === 0 ? (
              <Card className="bg-slate-800 border-slate-700">
                <CardContent className="py-8 text-center text-slate-400">
                  {t('property.noProperties')}
                </CardContent>
              </Card>
            ) : (
              properties.map((property) => (
                <PropertyCard
                  key={property.id}
                  token={token}
                  property={property}
                  renters={renters[property.id] || []}
                  bills={bills}
                  exchangeRates={exchangeRates}
                  onDelete={handleDeleteProperty}
                  onDataChange={loadData}
                  onError={setError}
                />
              ))
            )}
          </TabsContent>

          <TabsContent value="settings" className="space-y-4">
            <SettingsView token={token} onError={onError} />
          </TabsContent>
        </Tabs>
      )}

    </>
  );
}
