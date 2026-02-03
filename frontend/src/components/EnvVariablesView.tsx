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
  const [frontendVars, setFrontendVars] = useState<EnvVariable[]>([]);
  const [editedBackend, setEditedBackend] = useState<Record<string, string>>({});
  const [editedFrontend, setEditedFrontend] = useState<Record<string, string>>({});
  
  // Feature flags (for easy editing)
  const [featureFlags, setFeatureFlags] = useState<Record<string, boolean>>({});
  const [originalFeatureFlags, setOriginalFeatureFlags] = useState<Record<string, boolean>>({});
  
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
      setFrontendVars(varsResponse.frontend);
      setFeatureFlags(flagsResponse);
      setOriginalFeatureFlags(flagsResponse);
      
      // Reset edited values
      setEditedBackend({});
      setEditedFrontend({});
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

  const handleVariableChange = (key: string, value: string, source: 'backend' | 'frontend') => {
    if (source === 'backend') {
      setEditedBackend(prev => ({ ...prev, [key]: value }));
    } else {
      setEditedFrontend(prev => ({ ...prev, [key]: value }));
    }
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

  const handleSaveFrontend = async () => {
    if (!token || Object.keys(editedFrontend).length === 0) return;
    setSaving(true);
    setError('');
    setSuccess('');
    
    try {
      const result = await api.admin.env.updateVariables(token, editedFrontend, 'frontend');
      setSuccess(result.message);
      setEditedFrontend({});
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save frontend variables');
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
      setOriginalFeatureFlags(featureFlags);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save feature flags');
    } finally {
      setSaving(false);
    }
  };

  const handleRestart = async (service: 'backend' | 'frontend') => {
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

  const renderVariableInput = (v: EnvVariable, edited: Record<string, string>, source: 'backend' | 'frontend') => {
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
              onChange={(e) => handleVariableChange(v.key, e.target.value, source)}
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

  const renderCategoryGroup = (category: string, vars: EnvVariable[], edited: Record<string, string>, source: 'backend' | 'frontend') => {
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
            {vars.map(v => renderVariableInput(v, edited, source))}
          </div>
        </AccordionContent>
      </AccordionItem>
    );
  };

  // Feature flag display names
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
  const frontendGroups = groupByCategory(frontendVars.filter(v => !v.key.includes('FEATURE')));
  const hasBackendChanges = Object.keys(editedBackend).length > 0;
  const hasFrontendChanges = Object.keys(editedFrontend).length > 0;
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
            <Monitor className="w-4 h-4 mr-2" />
            {t('admin.env.frontendEnv') || 'Frontend'}
            {hasFrontendChanges && <Badge className="ml-2 bg-amber-600">*</Badge>}
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
                  {t('admin.env.featureFlagsDesc') || 'Toggle features on or off. Changes require a frontend rebuild to take effect.'}
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
                          <p className="text-xs text-slate-500 font-mono mt-1">VITE_FEATURE_{key.replace(/([A-Z])/g, '_$1').toUpperCase()}</p>
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
                
                <div className="mt-6 p-4 bg-slate-900/50 rounded-lg border border-slate-700">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-slate-300 font-medium">{t('admin.env.rebuildRequired') || 'Rebuild Required'}</p>
                      <p className="text-slate-400 text-sm mt-1">
                        {t('admin.env.rebuildRequiredDesc') || 'Frontend feature flags are baked in at build time. After saving changes, you need to rebuild the frontend:'}
                      </p>
                      <code className="block mt-2 p-2 bg-slate-800 rounded text-emerald-400 text-sm font-mono">
                        cd frontend && npm run build
                      </code>
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
                    .map(([category, vars]) => renderCategoryGroup(category, vars, editedBackend, 'backend'))}
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
                </CardTitle>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleRestart('frontend')}
                    className="bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 border-blue-600/50"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    {t('admin.env.rebuildFrontend') || 'Rebuild Frontend'}
                  </Button>
                  <Button
                    onClick={handleSaveFrontend}
                    disabled={!hasFrontendChanges || saving}
                    className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50"
                  >
                    <Save className="w-4 h-4 mr-2" />
                    {saving ? (t('common.saving') || 'Saving...') : (t('common.save') || 'Save')}
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-slate-400 text-sm mb-4">
                  {t('admin.env.frontendEnvDesc') || 'Configure frontend environment variables. Changes require a frontend rebuild to take effect.'}
                </p>
                <Accordion type="multiple" defaultValue={['api', 'oauth']} className="w-full">
                  {Object.entries(frontendGroups)
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([category, vars]) => renderCategoryGroup(category, vars, editedFrontend, 'frontend'))}
                </Accordion>
                
                <div className="mt-6 p-4 bg-slate-900/50 rounded-lg border border-slate-700">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-slate-300 font-medium">{t('admin.env.rebuildRequired') || 'Rebuild Required'}</p>
                      <p className="text-slate-400 text-sm mt-1">
                        {t('admin.env.frontendRebuildDesc') || 'Frontend variables are baked in at build time. After saving changes:'}
                      </p>
                      <code className="block mt-2 p-2 bg-slate-800 rounded text-emerald-400 text-sm font-mono">
                        cd frontend && npm run build
                      </code>
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
