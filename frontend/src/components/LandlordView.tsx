import { useState, useEffect } from 'react';
import { api, Property, Renter, Bill, SubscriptionStatus } from '../api';
import { useAuth } from '../App';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Building2, Settings, List, Grid, RefreshCw } from 'lucide-react';
import SettingsView from './SettingsView';
import PropertyCard from './PropertyCard';
import PropertyDialog from './dialogs/PropertyDialog';
import EblocImportDialog from './dialogs/EblocImportDialog';
import AllPropertiesSyncDialog from './dialogs/AllPropertiesSyncDialog';
import SummaryView from './SummaryView';
import { useI18n } from '../lib/i18n';
import { usePreferences } from '../hooks/usePreferences';
import { useScrollPreservation } from '../hooks/useScrollPreservation';
import { FileText } from 'lucide-react';
import { useExchangeRates } from '../hooks/useExchangeRates';

type LandlordViewProps = {
  token: string | null;
  onError?: (error: string) => void;
  hideSettings?: boolean;
};

export default function LandlordView({ token, onError, hideSettings = false }: LandlordViewProps) {
  const { user } = useAuth();
  const { t } = useI18n();
  const { preferences, setViewMode } = usePreferences();
  const { saveScroll, restoreScroll } = useScrollPreservation();
  const [properties, setProperties] = useState<Property[]>([]);
  const [renters, setRenters] = useState<Record<string, Renter[]>>({});
  const [bills, setBills] = useState<Bill[]>([]);
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showPropertyForm, setShowPropertyForm] = useState(false);
  const [showEblocDiscover, setShowEblocDiscover] = useState(false);
  const [showAllPropertiesSync, setShowAllPropertiesSync] = useState(false);
  const viewMode = (preferences.view_mode as 'list' | 'grid') || 'list';
  const { exchangeRates } = useExchangeRates();

  useEffect(() => {
    loadData();
  }, [token]);

  const handleError = (err: unknown) => {
    const message = err instanceof Error ? err.message : t('errors.generic');
    setError(message);
    if (onError) {
      onError(message);
    }
  };

  const loadData = async (shouldRestoreScroll = false) => {
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
      // Restore scroll position after data loads if requested
      if (shouldRestoreScroll) {
        restoreScroll();
      }
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
            <div className="flex items-center gap-2">
              <Button
                onClick={() => setViewMode(viewMode === 'list' ? 'grid' : 'list')}
                className="bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600"
                title={viewMode === 'list' ? t('property.switchToGrid') : t('property.switchToList')}
              >
                {viewMode === 'list' ? <Grid className="w-4 h-4 mr-2" /> : <List className="w-4 h-4 mr-2" />}
                {viewMode === 'list' ? t('property.gridView') : t('property.listView')}
              </Button>
              <Button
                onClick={() => {
                  saveScroll();
                  setShowAllPropertiesSync(true);
                }}
                className="bg-emerald-600 text-white hover:bg-emerald-700 border border-emerald-700"
                title={t('supplier.syncAllProperties')}
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                {t('supplier.syncBills')}
              </Button>
            </div>
            <h2 className="text-lg font-medium text-slate-100">{t('property.properties')}</h2>
            <div className="flex gap-2">
              <EblocImportDialog
                token={token}
                open={showEblocDiscover}
                onOpenChange={(open) => {
                  if (open) {
                    saveScroll();
                  }
                  setShowEblocDiscover(open);
                }}
                onSuccess={() => loadData(true)}
                onError={setError}
              />
              <PropertyDialog
                token={token}
                open={showPropertyForm}
                onOpenChange={(open) => {
                  if (open) {
                    saveScroll();
                  }
                  setShowPropertyForm(open);
                }}
                onSuccess={() => loadData(true)}
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
          ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-2 gap-4">
              {properties.map((property) => (
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
              ))}
            </div>
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
          <AllPropertiesSyncDialog
            token={token}
            properties={properties}
            open={showAllPropertiesSync}
            onOpenChange={(open) => {
              if (open) {
                saveScroll();
              }
              setShowAllPropertiesSync(open);
            }}
            onSuccess={() => loadData(true)}
            onError={setError}
          />
        </div>
      ) : (
        <Tabs defaultValue="summary" className="space-y-4">
          <TabsList className="bg-slate-800 border border-slate-700">
            <TabsTrigger value="summary" className="data-[state=active]:bg-slate-700">
              <FileText className="w-4 h-4 mr-2" />
              {t('summary.summary')}
            </TabsTrigger>
            <TabsTrigger value="properties" className="data-[state=active]:bg-slate-700">
              <Building2 className="w-4 h-4 mr-2" />
              {t('property.properties')}
            </TabsTrigger>
            <TabsTrigger value="settings" className="data-[state=active]:bg-slate-700">
              <Settings className="w-4 h-4 mr-2" />
              {t('settings.settings')}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="summary" className="space-y-4">
            <SummaryView />
          </TabsContent>

          <TabsContent value="properties" className="space-y-4">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-2">
                <Button
                  onClick={() => setViewMode(viewMode === 'list' ? 'grid' : 'list')}
                  className="bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600"
                  title={viewMode === 'list' ? t('property.switchToGrid') : t('property.switchToList')}
                >
                  {viewMode === 'list' ? <Grid className="w-4 h-4 mr-2" /> : <List className="w-4 h-4 mr-2" />}
                  {viewMode === 'list' ? t('property.gridView') : t('property.listView')}
                </Button>
                <Button
                  onClick={() => {
                    saveScroll();
                    setShowAllPropertiesSync(true);
                  }}
                  className="bg-emerald-600 text-white hover:bg-emerald-700 border border-emerald-700"
                  title={t('supplier.syncAllProperties')}
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  {t('supplier.syncBills')}
                </Button>
              </div>
              <h2 className="text-lg font-medium text-slate-100">{t('property.properties')}</h2>
              <div className="flex gap-2">
                <EblocImportDialog
                  token={token}
                  open={showEblocDiscover}
                  onOpenChange={(open) => {
                    if (open) {
                      saveScroll();
                    }
                    setShowEblocDiscover(open);
                  }}
                  onSuccess={() => loadData(true)}
                  onError={setError}
                />
                <PropertyDialog
                  token={token}
                  open={showPropertyForm}
                  onOpenChange={(open) => {
                    if (open) {
                      saveScroll();
                    }
                    setShowPropertyForm(open);
                  }}
                  onSuccess={() => loadData(true)}
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
            ) : viewMode === 'grid' ? (
              <div className="grid grid-cols-2 gap-4">
                {properties.map((property) => (
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
                ))}
              </div>
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
            <AllPropertiesSyncDialog
              token={token}
              properties={properties}
              open={showAllPropertiesSync}
              onOpenChange={(open) => {
                if (open) {
                  saveScroll();
                }
                setShowAllPropertiesSync(open);
              }}
              onSuccess={() => loadData(true)}
              onError={setError}
            />
          </TabsContent>

          <TabsContent value="settings" className="space-y-4">
            <SettingsView token={token} onError={onError} />
          </TabsContent>
        </Tabs>
      )}

    </>
  );
}
