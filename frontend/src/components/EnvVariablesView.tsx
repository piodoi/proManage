import { useState, useEffect, useCallback } from 'react';
import { api, EnvVariable } from '../api';
import { useAuth } from '../App';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { 
  Server, 
  Monitor, 
  Save, 
  RefreshCw, 
  AlertTriangle, 
  CheckCircle2, 
  Eye, 
  EyeOff,
  Database,
  Shield,
  Key,
  Mail,
  Globe,
  Zap,
  Settings2
} from 'lucide-react';
import { useI18n } from '../lib/i18n';
import { reloadFeatureFlags } from '../lib/featureFlags';

// Get actual frontend runtime values from import.meta.env (excluding feature flags)
const getFrontendRuntimeVars = (): EnvVariable[] => {
  const vars: EnvVariable[] = [];
  
  // Non-feature VITE_ prefixed env vars available at runtime
  const runtimeVars: Record<string, { value: string; category: string; description: string }> = {
    'VITE_API_URL': { 
      value: import.meta.env.VITE_API_URL || '', 
      category: 'api', 
      description: 'Backend API URL' 
    },
    'VITE_GOOGLE_CLIENT_ID': { 
      value: import.meta.env.VITE_GOOGLE_CLIENT_ID || '', 
      category: 'oauth', 
      description: 'Google OAuth client ID' 
    },
    'VITE_FACEBOOK_APP_ID': { 
      value: import.meta.env.VITE_FACEBOOK_APP_ID || '', 
      category: 'oauth', 
      description: 'Facebook OAuth app ID' 
    },
  };
  
  for (const [key, info] of Object.entries(runtimeVars)) {
    vars.push({
      key,
      value: info.value,
      source: 'frontend',
      category: info.category,
      description: info.description,
      is_secret: false,
    });
  }
  
  return vars;
};

// Category icons mapping
const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  database: <Database className="w-4 h-4" />,
  security: <Shield className="w-4 h-4" />,
  oauth: <Key className="w-4 h-4" />,
  email: <Mail className="w-4 h-4" />,
  cors: <Globe className="w-4 h-4" />,
  api: <Globe className="w-4 h-4" />,
  feature: <Zap className="w-4 h-4" />,
  stripe: <Key className="w-4 h-4" />,
  other: <Settings2 className="w-4 h-4" />,
};

// Category display names
const CATEGORY_NAMES: Record<string, string> = {
  database: 'Database',
  security: 'Security',
  oauth: 'OAuth',
  email: 'Email',
  cors: 'CORS',
  api: 'API',
  feature: 'Feature Flags',
  stripe: 'Stripe',
  other: 'Other',
};

export default function EnvVariablesView() {
  const { token } = useAuth();
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Environment variables
  const [backendVars, setBackendVars] = useState<EnvVariable[]>([]);
  const [editedBackend, setEditedBackend] = useState<Record<string, string>>({});
  
  // Feature flags (editable, stored in backend JSON)
  const [featureFlags, setFeatureFlags] = useState<Record<string, boolean>>({});
  const [originalFeatureFlags, setOriginalFeatureFlags] = useState<Record<string, boolean>>({});
  
  // Frontend vars are read directly from runtime - no editing
  const frontendVars = getFrontendRuntimeVars();
  
  // Show/hide secret values
  const [revealedSecrets, setRevealedSecrets] = useState<Set<string>>(new Set());
  
  // Active tab
  const [activeTab, setActiveTab] = useState('features');

  const loadData = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError('');
    
    try {
      const [varsResponse, flagsResponse] = await Promise.all([
        api.admin.env.getVariables(token),
        api.admin.env.getFeatureFlags(token),
      ]);
      
      setBackendVars(varsResponse.backend);
      setFeatureFlags(flagsResponse);
      setOriginalFeatureFlags(flagsResponse);
      setEditedBackend({});
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load environment variables');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Group variables by category
  const groupByCategory = (vars: EnvVariable[]): Record<string, EnvVariable[]> => {
    const groups: Record<string, EnvVariable[]> = {};
    vars.forEach(v => {
      const cat = v.category || 'other';
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(v);
    });
    return groups;
  };

  const handleVariableChange = (key: string, value: string) => {
    setEditedBackend(prev => ({ ...prev, [key]: value }));
  };

  const toggleRevealSecret = (key: string) => {
    setRevealedSecrets(prev => {
      const newSet = new Set(prev);
      if (newSet.has(key)) {
        newSet.delete(key);
      } else {
        newSet.add(key);
      }
      return newSet;
    });
  };

  const handleSaveBackend = async () => {
    if (!token || Object.keys(editedBackend).length === 0) return;
    setSaving(true);
    setError('');
    setSuccess('');
    
    try {
      const result = await api.admin.env.updateVariables(token, editedBackend, 'backend');
      setSuccess(result.message);
      setEditedBackend({});
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save backend variables');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveFeatureFlags = async () => {
    if (!token) return;
    
    // Check if any flags changed
    const hasChanges = Object.keys(featureFlags).some(
      key => featureFlags[key] !== originalFeatureFlags[key]
    );
    
    if (!hasChanges) return;
    
    setSaving(true);
    setError('');
    setSuccess('');
    
    try {
      const result = await api.admin.env.updateFeatureFlags(token, featureFlags);
      setSuccess(result.message);
      setOriginalFeatureFlags({ ...featureFlags });
      // Reload feature flags in the app
      await reloadFeatureFlags();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save feature flags');
    } finally {
      setSaving(false);
    }
  };

  const handleRestart = async (service: 'backend') => {
    if (!token) return;
    setError('');
    setSuccess('');
    
    try {
      const result = await api.admin.env.restart(token, service);
      setSuccess(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to restart ${service}`);
    }
  };

  // Render backend variable input (editable)
  const renderVariableInput = (v: EnvVariable, edited: Record<string, string>) => {
    const currentValue = edited[v.key] !== undefined ? edited[v.key] : v.value;
    const isEdited = edited[v.key] !== undefined && edited[v.key] !== v.value;
    const isRevealed = revealedSecrets.has(v.key);
    
    return (
      <div key={v.key} className="flex items-start gap-2 py-2 border-b border-slate-700 last:border-b-0">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Label className="text-slate-300 font-mono text-sm">{v.key}</Label>
            {v.is_secret && (
              <Badge variant="outline" className="text-xs text-yellow-500 border-yellow-500/50">
                Secret
              </Badge>
            )}
            {isEdited && (
              <Badge variant="outline" className="text-xs text-emerald-500 border-emerald-500/50">
                Modified
              </Badge>
            )}
          </div>
          {v.description && (
            <p className="text-xs text-slate-500 mb-1">{v.description}</p>
          )}
          <div className="flex items-center gap-2">
            <Input
              type={v.is_secret && !isRevealed ? 'password' : 'text'}
              value={currentValue}
              onChange={(e) => handleVariableChange(v.key, e.target.value)}
              className="bg-slate-700 border-slate-600 text-slate-100 font-mono text-sm"
              placeholder={v.is_secret ? '••••••••' : 'Not set'}
            />
            {v.is_secret && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => toggleRevealSecret(v.key)}
                className="text-slate-400 hover:text-slate-100"
              >
                {isRevealed ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  };

  // Render frontend runtime variable (read-only)
  const renderRuntimeVariable = (v: EnvVariable) => {
    const displayValue = v.value || t('admin.env.notSet') || 'Not set';
    const isSet = Boolean(v.value);
    
    return (
      <div key={v.key} className="flex items-start gap-2 py-2 border-b border-slate-700 last:border-b-0">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Label className="text-slate-300 font-mono text-sm">{v.key}</Label>
            {v.category === 'feature' && (
              <Badge 
                variant="outline" 
                className={`text-xs ${v.value === 'true' ? 'text-emerald-500 border-emerald-500/50' : 'text-slate-500 border-slate-500/50'}`}
              >
                {v.value === 'true' ? 'ON' : 'OFF'}
              </Badge>
            )}
          </div>
          {v.description && (
            <p className="text-xs text-slate-500 mb-1">{v.description}</p>
          )}
          <div className={`px-3 py-2 rounded font-mono text-sm ${
            isSet 
              ? 'bg-slate-700/50 text-slate-200' 
              : 'bg-slate-800/50 text-slate-500 italic'
          }`}>
            {displayValue}
          </div>
        </div>
      </div>
    );
  };

  const renderCategoryGroup = (category: string, vars: EnvVariable[], edited: Record<string, string>) => {
    return (
      <AccordionItem key={category} value={category}>
        <AccordionTrigger className="text-slate-200 hover:text-slate-100">
          <div className="flex items-center gap-2">
            {CATEGORY_ICONS[category] || CATEGORY_ICONS.other}
            <span>{CATEGORY_NAMES[category] || category}</span>
            <Badge variant="secondary" className="ml-2">{vars.length}</Badge>
          </div>
        </AccordionTrigger>
        <AccordionContent>
          <div className="space-y-1 pl-6">
            {vars.map(v => renderVariableInput(v, edited))}
          </div>
        </AccordionContent>
      </AccordionItem>
    );
  };

  const renderRuntimeCategoryGroup = (category: string, vars: EnvVariable[]) => {
    return (
      <AccordionItem key={category} value={category}>
        <AccordionTrigger className="text-slate-200 hover:text-slate-100">
          <div className="flex items-center gap-2">
            {CATEGORY_ICONS[category] || CATEGORY_ICONS.other}
            <span>{CATEGORY_NAMES[category] || category}</span>
            <Badge variant="secondary" className="ml-2">{vars.length}</Badge>
          </div>
        </AccordionTrigger>
        <AccordionContent>
          <div className="space-y-1 pl-6">
            {vars.map(v => renderRuntimeVariable(v))}
          </div>
        </AccordionContent>
      </AccordionItem>
    );
  };

  // Feature flag display names and info
  const FEATURE_FLAG_INFO: Record<string, { name: string; description: string }> = {
    payOnline: { 
      name: t('admin.env.featurePayOnline') || 'Online Payment', 
      description: t('admin.env.featurePayOnlineDesc') || 'Allow users to pay utility bills online through integrated payment providers'
    },
    barcodeExtraction: { 
      name: t('admin.env.featureBarcodeExtraction') || 'Barcode Extraction', 
      description: t('admin.env.featureBarcodeExtractionDesc') || 'Extract barcodes from uploaded bill PDFs for easier payment'
    },
    facebookLogin: { 
      name: t('admin.env.featureFacebookLogin') || 'Facebook Login', 
      description: t('admin.env.featureFacebookLoginDesc') || 'Enable Facebook OAuth authentication'
    },
    demoLogin: { 
      name: t('admin.env.featureDemoLogin') || 'Demo Login', 
      description: t('admin.env.featureDemoLoginDesc') || 'Show demo login button on login page'
    },
    usBuild: { 
      name: t('admin.env.featureUsBuild') || 'US Build', 
      description: t('admin.env.featureUsBuildDesc') || 'Use USD currency and US locale settings'
    },
  };

  if (loading) {
    return (
      <div className="text-slate-400 text-center py-8">{t('common.loading')}</div>
    );
  }

  const backendGroups = groupByCategory(backendVars);
  const frontendGroups = groupByCategory(frontendVars);
  const hasBackendChanges = Object.keys(editedBackend).length > 0;
  const hasFeatureFlagChanges = Object.keys(featureFlags).some(
    key => featureFlags[key] !== originalFeatureFlags[key]
  );

  return (
    <div className="space-y-4">
      {error && (
        <div className="p-3 bg-red-900/50 border border-red-700 rounded text-red-200 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          {error}
          <button onClick={() => setError('')} className="ml-auto text-red-400 hover:text-red-200">×</button>
        </div>
      )}
      
      {success && (
        <div className="p-3 bg-emerald-900/50 border border-emerald-700 rounded text-emerald-200 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          {success}
          <button onClick={() => setSuccess('')} className="ml-auto text-emerald-400 hover:text-emerald-200">×</button>
        </div>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="bg-slate-800 border-b border-slate-700 rounded-none h-auto p-0 gap-0 w-full justify-start">
          <TabsTrigger 
            value="features" 
            className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-4 py-2 border-b-2 border-transparent"
          >
            <Zap className="w-4 h-4 mr-2" />
            {t('admin.env.featureFlags') || 'Feature Flags'}
            {hasFeatureFlagChanges && <Badge className="ml-2 bg-amber-600">*</Badge>}
          </TabsTrigger>
          <TabsTrigger 
            value="backend" 
            className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-4 py-2 border-b-2 border-transparent"
          >
            <Server className="w-4 h-4 mr-2" />
            {t('admin.env.backendEnv') || 'Backend'}
            {hasBackendChanges && <Badge className="ml-2 bg-amber-600">*</Badge>}
          </TabsTrigger>
          <TabsTrigger 
            value="frontend" 
            className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-4 py-2 border-b-2 border-transparent"
          >
            <Monitor className="w-4 h-4 mr-2" /> {'Frontend'}
          </TabsTrigger>
        </TabsList>

        <div className="bg-slate-800 border border-t-0 border-slate-700 rounded-b-lg">
          <TabsContent value="features" className="m-0 p-4">
            <Card className="bg-slate-800 border-0 shadow-none">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-slate-100 flex items-center gap-2">
                  <Zap className="w-5 h-5" />
                  {t('admin.env.featureFlags') || 'Feature Flags'}
                </CardTitle>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={loadData}
                    className="bg-slate-700 text-slate-100 hover:bg-slate-600"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    {t('common.refresh') || 'Refresh'}
                  </Button>
                  <Button
                    onClick={handleSaveFeatureFlags}
                    disabled={!hasFeatureFlagChanges || saving}
                    className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50"
                  >
                    <Save className="w-4 h-4 mr-2" />
                    {saving ? (t('common.saving') || 'Saving...') : (t('common.save') || 'Save')}
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-slate-400 text-sm mb-4">
                  {t('admin.env.featureFlagsDesc') || 'Toggle features on or off. Changes take effect immediately for new sessions.'}
                </p>
                <div className="space-y-4">
                  {Object.entries(featureFlags).map(([key, value]) => {
                    const info = FEATURE_FLAG_INFO[key] || { name: key, description: '' };
                    const isChanged = value !== originalFeatureFlags[key];
                    return (
                      <div 
                        key={key} 
                        className={`flex items-center justify-between p-3 rounded-lg border ${
                          isChanged ? 'bg-amber-900/20 border-amber-600/50' : 'bg-slate-700/50 border-slate-600'
                        }`}
                      >
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <Label className="text-slate-200 font-medium">{info.name}</Label>
                            {isChanged && (
                              <Badge variant="outline" className="text-xs text-amber-500 border-amber-500/50">
                                Modified
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-slate-400 mt-1">{info.description}</p>
                        </div>
                        <Switch
                          checked={value}
                          onCheckedChange={(checked) => setFeatureFlags(prev => ({ ...prev, [key]: checked }))}
                          className="data-[state=checked]:bg-emerald-600"
                        />
                      </div>
                    );
                  })}
                </div>
                
                <div className="mt-6 p-4 bg-emerald-900/20 rounded-lg border border-emerald-600/30">
                  <div className="flex items-start gap-2">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-slate-300 font-medium">{t('admin.env.liveChanges') || 'Live Changes'}</p>
                      <p className="text-slate-400 text-sm mt-1">
                        {t('admin.env.liveChangesDesc') || 'Feature flags are stored on the server and take effect immediately for new user sessions. Users may need to refresh the page to see changes.'}
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="backend" className="m-0 p-4">
            <Card className="bg-slate-800 border-0 shadow-none">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-slate-100 flex items-center gap-2">
                  <Server className="w-5 h-5" />
                  {t('admin.env.backendEnv') || 'Backend Environment Variables'}
                </CardTitle>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleRestart('backend')}
                    className="bg-amber-600/20 text-amber-400 hover:bg-amber-600/30 border-amber-600/50"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    {t('admin.env.restartBackend') || 'Restart Backend'}
                  </Button>
                  <Button
                    onClick={handleSaveBackend}
                    disabled={!hasBackendChanges || saving}
                    className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50"
                  >
                    <Save className="w-4 h-4 mr-2" />
                    {saving ? (t('common.saving') || 'Saving...') : (t('common.save') || 'Save')}
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-slate-400 text-sm mb-4">
                  {t('admin.env.backendEnvDesc') || 'Configure backend environment variables. Changes require a backend restart to take effect.'}
                </p>
                <Accordion type="multiple" defaultValue={['database', 'security']} className="w-full">
                  {Object.entries(backendGroups)
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([category, vars]) => renderCategoryGroup(category, vars, editedBackend))}
                </Accordion>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="frontend" className="m-0 p-4">
            <Card className="bg-slate-800 border-0 shadow-none">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-slate-100 flex items-center gap-2">
                  <Monitor className="w-5 h-5" />
                  {t('admin.env.frontendEnv') || 'Frontend Environment Variables'}
                  <Badge className="ml-2 bg-slate-600 text-xs">{t('admin.env.readOnly') || 'Runtime'}</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-400 text-sm mb-4">
                  {t('admin.env.frontendRuntimeDesc') || 'Current runtime values for this frontend instance. These values are baked in at build time.'}
                </p>
                <Accordion type="multiple" defaultValue={['api', 'oauth', 'feature']} className="w-full">
                  {Object.entries(frontendGroups)
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([category, vars]) => renderRuntimeCategoryGroup(category, vars))}
                </Accordion>
                
                <div className="mt-6 p-4 bg-blue-900/20 rounded-lg border border-blue-600/30">
                  <div className="flex items-start gap-2">
                    <Monitor className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-slate-300 font-medium">{'Runtime Values'}</p>
                      <p className="text-slate-400 text-sm mt-1">
                        {'These values reflect the actual configuration of this running frontend instance, not the source files. To change these values, update the environment variables and rebuild the frontend.'}
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
