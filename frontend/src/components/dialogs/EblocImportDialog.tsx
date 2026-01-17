import { useState } from 'react';
import { api, SubscriptionStatus } from '../../api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from '@/components/ui/dialog';
import { Spinner } from '@/components/ui/spinner';
import { Building2, Crown } from 'lucide-react';
import { useI18n } from '../../lib/i18n';

type EblocImportDialogProps = {
  token: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onError: (error: string) => void;
  subscription?: SubscriptionStatus | null;
  onUpgradeClick?: () => void;
};

export default function EblocImportDialog({
  token,
  open,
  onOpenChange,
  onSuccess,
  onError,
  subscription,
  onUpgradeClick,
}: EblocImportDialogProps) {
  const { t } = useI18n();
  const [form, setForm] = useState({ username: '', password: '', selectedPropertyId: '' });
  const [discoveredProperties, setDiscoveredProperties] = useState<Array<{ page_id: string; name: string; address: string; url: string }>>([]);
  const [discovering, setDiscovering] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importSelectedHovered, setImportSelectedHovered] = useState(false);
  const [importAllHovered, setImportAllHovered] = useState(false);
  
  // Calculate how many properties can still be added
  const canAddProperty = subscription?.can_add_property ?? true;
  const remainingSlots = subscription 
    ? subscription.limits.max_properties - subscription.property_count 
    : Infinity;
  
  const importSelectedNeedsUpgrade = !canAddProperty && onUpgradeClick;
  const importAllNeedsUpgrade = discoveredProperties.length > 1 && remainingSlots < discoveredProperties.length && onUpgradeClick;

  const handleDiscover = async () => {
    if (!token) return;
    if (!form.username || !form.password) {
      onError(t('ebloc.enterUsernamePassword'));
      return;
    }

    setDiscovering(true);
    onError('');

    try {
      const result = await api.ebloc.discover(token, { username: form.username, password: form.password });

      if (result && result.properties && Array.isArray(result.properties)) {
        if (result.properties.length > 0) {
          // Credentials are not saved (privacy note)
          setForm(prev => ({ ...prev, password: '' }));

          const propertiesWithUrl = result.properties.map(p => ({
            ...p,
            url: p.url || `https://www.e-bloc.ro/index.php?page=${p.page_id}`,
          }));
          setDiscoveredProperties(propertiesWithUrl);
          setForm(prev => ({ ...prev, selectedPropertyId: propertiesWithUrl[0].page_id }));
          onError('');
        } else {
          onError(t('ebloc.noPropertiesFound'));
          setDiscoveredProperties([]);
        }
      } else {
        const errorMsg = (result as any)?.detail || (result as any)?.message || t('ebloc.unexpectedResponse');
        onError(errorMsg);
        setDiscoveredProperties([]);
      }
    } catch (err) {
      onError(err instanceof Error ? err.message : t('ebloc.failedToDiscover'));
      setDiscoveredProperties([]);
    } finally {
      setDiscovering(false);
    }
  };

  const handleImportSelected = async () => {
    if (!token || !form.selectedPropertyId) return;
    
    // Use already discovered properties - no need to scrape again
    const selectedProp = discoveredProperties.find(p => p.page_id === form.selectedPropertyId);
    if (!selectedProp) {
      onError(t('ebloc.propertyNotFoundInMemory'));
      return;
    }

    setImporting(true);
    onError('');

    try {
      // Just create the property from memory - no need to configure/scrape again
      const newProperty = await api.properties.create(token, {
        name: selectedProp.name,
        address: selectedProp.address || selectedProp.name,
      });
      
      // Auto-setup E-bloc supplier and credentials
      try {
        await api.ebloc.setupSupplierForProperties(token, [newProperty.id]);
      } catch (setupErr) {
        // Log but don't fail the import if setup fails
        console.warn('Failed to auto-setup E-bloc supplier:', setupErr);
      }

      // Remove imported property from discovered list, but keep others in memory
      const remainingProperties = discoveredProperties.filter(p => p.page_id !== form.selectedPropertyId);
      setDiscoveredProperties(remainingProperties);
      
      // Set new selection if there are properties left
      if (remainingProperties.length > 0) {
        setForm(prev => ({ ...prev, selectedPropertyId: remainingProperties[0].page_id }));
      } else {
        // All properties imported, close dialog
        onOpenChange(false);
        setForm({ username: '', password: '', selectedPropertyId: '' });
      }
      
      onSuccess();
    } catch (err) {
      onError(err instanceof Error ? err.message : t('errors.generic'));
    } finally {
      setImporting(false);
    }
  };

  const handleImportAll = async () => {
    if (!token) return;
    if (discoveredProperties.length === 0) return;

    setImporting(true);
    onError('');

    try {
      // Import all properties from memory - no need to scrape again
      const importedPropertyIds: string[] = [];
      for (const prop of discoveredProperties) {
        const newProperty = await api.properties.create(token, {
          name: prop.name,
          address: prop.address || prop.name,
        });
        importedPropertyIds.push(newProperty.id);
      }

      // Auto-setup E-bloc supplier and credentials for all imported properties
      if (importedPropertyIds.length > 0) {
        try {
          await api.ebloc.setupSupplierForProperties(token, importedPropertyIds);
        } catch (setupErr) {
          // Log but don't fail the import if setup fails
          console.warn('Failed to auto-setup E-bloc supplier:', setupErr);
        }
      }

      // All properties imported, close dialog
      onOpenChange(false);
      setForm({ username: '', password: '', selectedPropertyId: '' });
      setDiscoveredProperties([]);
      onSuccess();
    } catch (err) {
      onError(err instanceof Error ? err.message : t('errors.generic'));
    } finally {
      setImporting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600">
          <Building2 className="w-4 h-4 mr-2" />
          {t('ebloc.importFromEbloc')}
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-slate-800 border-slate-700 max-w-2xl">
        <DialogHeader>
          <DialogTitle className="text-slate-100">{t('ebloc.importPropertiesFromEbloc')}</DialogTitle>
          <DialogDescription className="text-slate-400 space-y-2">
            <p>{t('ebloc.importDesc')}</p>
            <p className="text-sm text-emerald-400 border border-emerald-700 bg-emerald-950/30 p-3 rounded">
              🔒 {t('ebloc.privacyNote')}
            </p>
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label className="text-slate-300">{t('ebloc.eblocUsername')}</Label>
            <Input
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              className="bg-slate-700 border-slate-600 text-slate-100"
              placeholder="your-email@example.com"
              disabled={discovering || importing}
            />
          </div>
          <div>
            <Label className="text-slate-300">{t('ebloc.eblocPassword')}</Label>
            <Input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="bg-slate-700 border-slate-600 text-slate-100"
              disabled={discovering || importing}
            />
          </div>
          {discoveredProperties.length === 0 ? (
            <Button
              onClick={handleDiscover}
              className="w-full bg-emerald-600 hover:bg-emerald-700"
              disabled={discovering || !form.username || !form.password}
            >
              {discovering ? (
                <>
                  <Spinner className="w-4 h-4 mr-2" />
                  {t('ebloc.discovering')}
                </>
              ) : (
                t('ebloc.discoverProperties')
              )}
            </Button>
          ) : (
            <div className="space-y-4">
              <div>
                <Label className="text-slate-300">{t('ebloc.selectPropertyToImport')}</Label>
                <Select
                  value={form.selectedPropertyId}
                  onValueChange={(v) => setForm({ ...form, selectedPropertyId: v })}
                  disabled={importing}
                >
                  <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                    <SelectValue placeholder={t('ebloc.selectProperty')} />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-700 border-slate-600">
                    {discoveredProperties.map((prop) => (
                      <SelectItem key={prop.page_id} value={prop.page_id}>
                        {prop.name} - {prop.address}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={() => {
                    if (importSelectedNeedsUpgrade) {
                      onOpenChange(false);
                      // Small delay to ensure dialog closes before navigation
                      setTimeout(() => onUpgradeClick!(), 100);
                    } else {
                      handleImportSelected();
                    }
                  }}
                  onMouseEnter={() => setImportSelectedHovered(true)}
                  onMouseLeave={() => setImportSelectedHovered(false)}
                  className={`flex-1 ${
                    importSelectedNeedsUpgrade 
                      ? (importSelectedHovered 
                          ? "bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-700 hover:to-orange-700"
                          : "bg-emerald-600 hover:bg-emerald-700")
                      : "bg-emerald-600 hover:bg-emerald-700"
                  }`}
                  disabled={importing || !form.selectedPropertyId}
                >
                  {importing ? (
                    <>
                      <Spinner className="w-4 h-4 mr-2" />
                      {t('ebloc.importing')}
                    </>
                  ) : importSelectedNeedsUpgrade && importSelectedHovered ? (
                    <>
                      <Crown className="w-4 h-4 mr-2" />
                      {t('settings.upgradeToProTitle')}
                    </>
                  ) : (
                    t('ebloc.importSelected')
                  )}
                </Button>
                {discoveredProperties.length > 1 && (
                  <Button
                    onClick={() => {
                      if (importAllNeedsUpgrade) {
                        onOpenChange(false);
                        // Small delay to ensure dialog closes before navigation
                        setTimeout(() => onUpgradeClick!(), 100);
                      } else {
                        handleImportAll();
                      }
                    }}
                    onMouseEnter={() => setImportAllHovered(true)}
                    onMouseLeave={() => setImportAllHovered(false)}
                    className={`flex-1 ${
                      importAllNeedsUpgrade 
                        ? (importAllHovered 
                            ? "bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-700 hover:to-orange-700"
                            : "bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600")
                        : "bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600"
                    } disabled:opacity-50`}
                    disabled={importing}
                  >
                    {importing ? (
                      <>
                        <Spinner className="w-4 h-4 mr-2" />
                        {t('ebloc.importing')}
                      </>
                    ) : importAllNeedsUpgrade && importAllHovered ? (
                      <>
                        <Crown className="w-4 h-4 mr-2" />
                        {t('settings.upgradeToProTitle')}
                      </>
                    ) : (
                      t('ebloc.importAll', { count: discoveredProperties.length })
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

