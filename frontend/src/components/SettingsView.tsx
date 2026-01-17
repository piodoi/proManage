import { useState, useEffect, useCallback } from 'react';
import { api, SubscriptionStatus, User as ApiUser, StripeConfig, StripeSubscription } from '../api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Mail, AlertCircle, User, Copy, Check, Crown, Zap, Building2, Users, FileText, CheckCircle2, Loader2, CreditCard, Plus, Minus, Lock } from 'lucide-react';
import { useI18n } from '../lib/i18n';
import { usePreferences } from '../hooks/usePreferences';
import { validateIban, formatIban } from '../utils/iban';

type SettingsViewProps = {
  token: string | null;
  user: ApiUser | null;
  onError?: (error: string) => void;
  forceTab?: string;  // Force a specific tab to be active
  hideTabBar?: boolean; // Hide the tab bar (useful when embedding as main tab)
  onNavigateToSubscription?: () => void; // Callback to navigate to main subscription tab
};

export default function SettingsView({ token, user, onError, forceTab, hideTabBar = false, onNavigateToSubscription }: SettingsViewProps) {
  const { t, language } = useI18n();
  const { preferences, setRentWarningDays, setRentCurrency, setBillCurrency, setDateFormat, setPhoneNumber, setLandlordName, setPersonalEmail, setIban } = usePreferences();
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [stripeConfig, setStripeConfig] = useState<StripeConfig | null>(null);
  const [stripeSubscription, setStripeSubscription] = useState<StripeSubscription | null>(null);
  const [emailCopied, setEmailCopied] = useState(false);
  const [rentWarningDaysInput, setRentWarningDaysInput] = useState<string>('');
  const [phoneNumberInput, setPhoneNumberInput] = useState<string>('');
  const [landlordNameInput, setLandlordNameInput] = useState<string>('');
  const [personalEmailInput, setPersonalEmailInput] = useState<string>('');
  const [ibanInput, setIbanInput] = useState<string>('');
  const [ibanError, setIbanError] = useState<string>('');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState<boolean>(false);
  const [propertyQuantity, setPropertyQuantity] = useState<number>(1);
  const [isSubscribing, setIsSubscribing] = useState(false);
  const [activeTab, setActiveTab] = useState<string>(() => {
    return forceTab || sessionStorage.getItem('settingsActiveTab') || 'personal';
  });

  // Update active tab when forceTab changes
  useEffect(() => {
    if (forceTab) {
      setActiveTab(forceTab);
    }
  }, [forceTab]);

  const handleTabChange = (value: string) => {
    setActiveTab(value);
    sessionStorage.setItem('settingsActiveTab', value);
  };

  // Check for success/cancel URL params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('subscription_success') === 'true') {
      // Reload subscription data
      if (token) {
        loadSubscription();
        loadStripeData();
      }
      // Clean up URL
      window.history.replaceState({}, '', window.location.pathname);
    } else if (params.get('subscription_cancelled') === 'true') {
      // Clean up URL
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  const loadSubscription = useCallback(async () => {
    if (!token) return;
    try {
      const sub = await api.subscription.status(token);
      setSubscription(sub);
    } catch (err) {
      if (onError) {
        onError(err instanceof Error ? err.message : t('settings.loadSubscriptionError'));
      }
    }
  }, [token, onError, t]);

  const loadStripeData = useCallback(async () => {
    if (!token) return;
    try {
      const [config, stripeSub] = await Promise.all([
        api.stripe.config(token),
        api.stripe.subscription(token),
      ]);
      setStripeConfig(config);
      setStripeSubscription(stripeSub);
    } catch (err) {
      console.error('Failed to load Stripe data:', err);
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      loadSubscription();
      loadStripeData();
    }
  }, [token, loadSubscription, loadStripeData]);

  useEffect(() => {
    if (preferences.rent_warning_days !== undefined) {
      setRentWarningDaysInput(preferences.rent_warning_days.toString());
    }
  }, [preferences.rent_warning_days]);

  useEffect(() => {
    setPhoneNumberInput(preferences.phone_number || '');
  }, [preferences.phone_number]);

  useEffect(() => {
    setLandlordNameInput(preferences.landlord_name || '');
  }, [preferences.landlord_name]);

  useEffect(() => {
    setPersonalEmailInput(preferences.personal_email || '');
  }, [preferences.personal_email]);

  useEffect(() => {
    setIbanInput(preferences.iban || '');
  }, [preferences.iban]);

  // Check if there are unsaved changes
  useEffect(() => {
    const phoneChanged = (phoneNumberInput.trim() || null) !== (preferences.phone_number || null);
    const landlordChanged = (landlordNameInput.trim() || null) !== (preferences.landlord_name || null);
    const emailChanged = (personalEmailInput.trim() || null) !== (preferences.personal_email || null);
    const ibanChanged = (ibanInput.replace(/\s+/g, '').trim() || null) !== (preferences.iban || null);
    
    setHasUnsavedChanges(phoneChanged || landlordChanged || emailChanged || ibanChanged);
  }, [phoneNumberInput, landlordNameInput, personalEmailInput, ibanInput, preferences.phone_number, preferences.landlord_name, preferences.personal_email, preferences.iban]);

  const handleSavePersonalDetails = () => {
    // Validate IBAN if provided
    if (ibanInput.trim()) {
      const cleanedIban = ibanInput.replace(/\s+/g, '');
      if (!validateIban(cleanedIban)) {
        setIbanError(t('settings.invalidIban') || 'Invalid IBAN format');
        return;
      }
      setIban(cleanedIban);
    } else {
      setIban(null);
    }
    setIbanError('');
    
    setPhoneNumber(phoneNumberInput.trim() || null);
    setLandlordName(landlordNameInput.trim() || null);
    setPersonalEmail(personalEmailInput.trim() || null);
    
    // Reset unsaved changes flag after save
    setHasUnsavedChanges(false);
  };

  const handleIbanChange = (value: string) => {
    setIbanInput(value);
    setIbanError('');
  };

  const handleIbanBlur = () => {
    if (ibanInput.trim()) {
      const cleanedIban = ibanInput.replace(/\s+/g, '');
      if (!validateIban(cleanedIban)) {
        setIbanError(t('settings.invalidIban') || 'Invalid IBAN format');
      } else {
        // Format the IBAN for display
        setIbanInput(formatIban(cleanedIban));
        setIbanError('');
      }
    }
  };

  const handleCopyEmail = async () => {
    if (!user) return;
    const email = `proManage.bill+${user.id}@gmail.com`;
    try {
      await navigator.clipboard.writeText(email);
      setEmailCopied(true);
      setTimeout(() => setEmailCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy email:', err);
    }
  };

  const handleSubscribe = async () => {
    if (!token || !stripeConfig?.enabled) return;
    
    setIsSubscribing(true);
    try {
      const successUrl = `${window.location.origin}/settings?subscription_success=true`;
      const cancelUrl = `${window.location.origin}/settings?subscription_cancelled=true`;
      
      const session = await api.stripe.createCheckout(token, propertyQuantity, successUrl, cancelUrl);
      
      // Redirect to Stripe Checkout
      window.location.href = session.url;
    } catch (err) {
      if (onError) {
        onError(err instanceof Error ? err.message : 'Failed to create checkout session');
      }
      setIsSubscribing(false);
    }
  };

  const handleManageSubscription = async () => {
    if (!token) return;
    
    try {
      const returnUrl = `${window.location.origin}/settings`;
      const session = await api.stripe.createPortal(token, returnUrl);
      window.location.href = session.url;
    } catch (err) {
      if (onError) {
        onError(err instanceof Error ? err.message : 'Failed to open subscription portal');
      }
    }
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString(language === 'ro' ? 'ro-RO' : 'en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <div className="space-y-0">
      <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
        {!hideTabBar && (
          <TabsList className="bg-slate-800 border-b border-slate-700 rounded-none rounded-t-lg h-auto p-0 gap-0 w-full justify-start">
            <TabsTrigger value="personal" className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-4 py-2 border-b-2 border-transparent">
              {t('settings.personalDetails')}
            </TabsTrigger>
            <TabsTrigger value="rent-bills" className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-4 py-2 border-b-2 border-transparent">
              {t('settings.rentWarning')}
            </TabsTrigger>
            <TabsTrigger value="email" className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-4 py-2 border-b-2 border-transparent">
              {t('settings.emailBillImport')}
            </TabsTrigger>
          </TabsList>
        )}

        <div className={`bg-slate-800 border border-slate-700 ${hideTabBar ? 'rounded-lg' : 'border-t-0 rounded-b-lg'}`}>
          <TabsContent value="subscription" className="m-0 p-6 space-y-6">
            {/* Current Plan Card */}
            <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <CardTitle className="text-slate-100 flex items-center gap-2">
                    {subscription?.is_free_tier ? (
                      <>
                        <Zap className="w-5 h-5 text-slate-400" />
                        {t('settings.freeTier')}
                      </>
                    ) : (
                      <>
                        <Crown className="w-5 h-5 text-amber-400" />
                        {t('settings.paidTier')}
                      </>
                    )}
                  </CardTitle>
                  {/* Email Sync Status - Compact inline */}
                  {subscription && (
                    <div className="flex items-center gap-2">
                      <Mail className="w-4 h-4 text-slate-400" />
                      <span className="text-slate-400 text-sm">{t('settings.emailSyncFeature')}:</span>
                      {subscription.limits.email_sync_enabled ? (
                        <span className="flex items-center gap-1 text-emerald-400 text-sm">
                          <CheckCircle2 className="w-4 h-4" />
                          {t('settings.available')}
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-slate-500 text-sm">
                          <Lock className="w-4 h-4" />
                          Pro
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {subscription && (
                  <div className="space-y-4">
                    {/* Usage Stats */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {/* Properties */}
                      <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                        <div className="flex items-center gap-2 mb-2">
                          <Building2 className="w-4 h-4 text-emerald-400" />
                          <span className="text-slate-300 text-sm">{t('settings.propertiesUsage')}</span>
                        </div>
                        <div className="flex items-baseline gap-2">
                          <span className="text-2xl font-bold text-slate-100">{subscription.property_count}</span>
                          <span className="text-slate-500">/ {subscription.limits.max_properties}</span>
                        </div>
                        <div className="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full transition-all ${
                              subscription.property_count >= subscription.limits.max_properties 
                                ? 'bg-red-500' 
                                : subscription.property_count >= subscription.limits.max_properties * 0.8 
                                  ? 'bg-amber-500' 
                                  : 'bg-emerald-500'
                            }`}
                            style={{ width: `${Math.min(100, (subscription.property_count / subscription.limits.max_properties) * 100)}%` }}
                          />
                        </div>
                      </div>
                      
                      {/* Suppliers */}
                      <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                        <div className="flex items-center gap-2 mb-2">
                          <FileText className="w-4 h-4 text-blue-400" />
                          <span className="text-slate-300 text-sm">{t('settings.suppliersUsage')}</span>
                        </div>
                        <div className="flex items-baseline gap-2">
                          <span className="text-2xl font-bold text-slate-100">{subscription.supplier_count}</span>
                          <span className="text-slate-500">/ {subscription.limits.max_suppliers}</span>
                        </div>
                        <div className="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full transition-all ${
                              subscription.supplier_count >= subscription.limits.max_suppliers 
                                ? 'bg-red-500' 
                                : subscription.supplier_count >= subscription.limits.max_suppliers * 0.8 
                                  ? 'bg-amber-500' 
                                  : 'bg-blue-500'
                            }`}
                            style={{ width: `${Math.min(100, (subscription.supplier_count / subscription.limits.max_suppliers) * 100)}%` }}
                          />
                        </div>
                        <p className="text-xs text-slate-500 mt-1">
                          {subscription.limits.max_suppliers_per_property} {t('settings.perPropertyLimit')}
                        </p>
                      </div>
                      
                      {/* Renters */}
                      <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                        <div className="flex items-center gap-2 mb-2">
                          <Users className="w-4 h-4 text-purple-400" />
                          <span className="text-slate-300 text-sm">{t('settings.rentersUsage')}</span>
                        </div>
                        <div className="flex items-baseline gap-2">
                          <span className="text-2xl font-bold text-slate-100">{subscription.renter_count}</span>
                          <span className="text-slate-500">/ {subscription.limits.max_renters}</span>
                        </div>
                        <div className="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full transition-all ${
                              subscription.renter_count >= subscription.limits.max_renters 
                                ? 'bg-red-500' 
                                : subscription.renter_count >= subscription.limits.max_renters * 0.8 
                                  ? 'bg-amber-500' 
                                  : 'bg-purple-500'
                            }`}
                            style={{ width: `${Math.min(100, (subscription.renter_count / subscription.limits.max_renters) * 100)}%` }}
                          />
                        </div>
                        <p className="text-xs text-slate-500 mt-1">
                          {subscription.limits.max_renters_per_property} {t('settings.perPropertyLimit')}
                        </p>
                      </div>
                    </div>
                    
                    {/* Active Subscription Details */}
                    {stripeSubscription?.has_subscription && stripeSubscription.current_period_end && (
                      <div className="bg-emerald-900/20 border border-emerald-700/50 rounded-lg p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <CreditCard className="w-5 h-5 text-emerald-400" />
                            <div>
                              <p className="text-emerald-300 font-medium">
                                {stripeSubscription.quantity} {t('settings.propertiesPaid')}
                              </p>
                              <p className="text-emerald-400/70 text-sm">
                                {stripeSubscription.cancel_at_period_end 
                                  ? `${t('settings.endsOn')}: ${formatDate(stripeSubscription.current_period_end)}`
                                  : `${t('settings.renewsOn')}: ${formatDate(stripeSubscription.current_period_end)}`
                                }
                              </p>
                            </div>
                          </div>
                          <Button 
                            onClick={handleManageSubscription}
                            variant="outline"
                            className="border-emerald-600 text-emerald-400 hover:bg-emerald-900/30"
                          >
                            {t('settings.manageSubscription')}
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Upgrade Card (for free tier users) */}
            {subscription?.is_free_tier && stripeConfig?.enabled && (
              <Card className="bg-gradient-to-br from-amber-900/20 to-orange-900/20 border-amber-700/50">
                <CardHeader>
                  <CardTitle className="text-amber-300 flex items-center gap-2">
                    <Crown className="w-5 h-5" />
                    {t('settings.upgradeToProTitle')}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-slate-300 mb-6">
                    {t('settings.upgradeToProDesc')}
                  </p>
                  
                  {/* Property Quantity Selector */}
                  <div className="mb-6">
                    <Label className="text-slate-300 mb-3 block">{t('settings.propertiesWanted')}</Label>
                    <div className="flex items-center gap-4">
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() => setPropertyQuantity(Math.max(1, propertyQuantity - 1))}
                        disabled={propertyQuantity <= 1}
                        className="border-slate-600 text-slate-300 hover:bg-slate-700"
                      >
                        <Minus className="w-4 h-4" />
                      </Button>
                      <span className="text-3xl font-bold text-amber-300 min-w-[60px] text-center">
                        {propertyQuantity}
                      </span>
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() => setPropertyQuantity(propertyQuantity + 1)}
                        className="border-slate-600 text-slate-300 hover:bg-slate-700"
                      >
                        <Plus className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                  
                  {/* Subscribe Button */}
                  <Button
                    onClick={handleSubscribe}
                    disabled={isSubscribing}
                    className="w-full bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-700 hover:to-orange-700 text-white font-semibold py-6"
                  >
                    {isSubscribing ? (
                      <>
                        <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                        {t('settings.subscribing')}
                      </>
                    ) : (
                      <>
                        <CreditCard className="w-5 h-5 mr-2" />
                        {t('settings.subscribe')}
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* Add More Properties Card (for paid users) */}
            {subscription && !subscription.is_free_tier && stripeConfig?.enabled && (
              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-slate-100 font-medium">{t('settings.addMoreProperties')}</h3>
                      <p className="text-slate-400 text-sm">
                        {t('settings.changeSubscription')}
                      </p>
                    </div>
                    <Button 
                      onClick={handleManageSubscription}
                      className="bg-emerald-600 hover:bg-emerald-700"
                    >
                      <Plus className="w-4 h-4 mr-2" />
                      {t('settings.addMoreProperties')}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Stripe Not Configured Warning */}
            {stripeConfig && !stripeConfig.enabled && (
              <div className="bg-amber-900/20 border border-amber-700/50 rounded-lg p-4">
                <div className="flex items-center gap-3">
                  <AlertCircle className="w-5 h-5 text-amber-400" />
                  <p className="text-amber-300">{t('settings.stripeNotConfigured')}</p>
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="personal" className="m-0 p-6 space-y-4">
            <Card className="bg-slate-800 border-0 shadow-none">
              <CardHeader>
                <CardTitle className="text-slate-100 flex items-center gap-2">
                  <User className="w-5 h-5" />
                  {t('settings.personalDetails')}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-slate-400 text-sm">
                  {t('settings.personalDetailsDesc')}
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label className="text-slate-300">{t('settings.landlordName')}</Label>
                    <Input
                      type="text"
                      value={landlordNameInput}
                      onChange={(e) => setLandlordNameInput(e.target.value)}
                      className="bg-slate-700 border-slate-600 text-slate-100 mt-1"
                      placeholder={t('settings.landlordNamePlaceholder')}
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      {t('settings.landlordNameHelp')}
                    </p>
                  </div>
                  <div>
                    <Label className="text-slate-300">{t('settings.personalEmail')}</Label>
                    <Input
                      type="email"
                      value={personalEmailInput}
                      onChange={(e) => setPersonalEmailInput(e.target.value)}
                      className="bg-slate-700 border-slate-600 text-slate-100 mt-1"
                      placeholder={t('settings.personalEmailPlaceholder')}
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      {t('settings.personalEmailHelp')}
                    </p>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label className="text-slate-300">{t('settings.phoneNumberLabel')}</Label>
                    <Input
                      type="tel"
                      value={phoneNumberInput}
                      onChange={(e) => setPhoneNumberInput(e.target.value)}
                      className="bg-slate-700 border-slate-600 text-slate-100 mt-1"
                      placeholder={t('settings.phoneNumberPlaceholder')}
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      {t('settings.phoneNumberHelp')}
                    </p>
                  </div>
                  <div>
                    <Label className="text-slate-300">{t('settings.iban')}</Label>
                    <Input
                      type="text"
                      value={ibanInput}
                      onChange={(e) => handleIbanChange(e.target.value)}
                      onBlur={handleIbanBlur}
                      className={`bg-slate-700 border-slate-600 text-slate-100 mt-1 ${ibanError ? 'border-red-500' : ''}`}
                      placeholder={t('settings.ibanPlaceholder')}
                    />
                    {ibanError && (
                      <p className="text-xs text-red-400 mt-1">
                        {ibanError}
                      </p>
                    )}
                    <p className="text-xs text-slate-500 mt-1">
                      {t('settings.ibanHelp')}
                    </p>
                  </div>
                </div>
                <Button
                  onClick={handleSavePersonalDetails}
                  className="bg-emerald-600 hover:bg-emerald-700"
                  disabled={!hasUnsavedChanges || !!ibanError}
                >
                  {t('common.save')}
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="rent-bills" className="m-0 p-6 space-y-4">
            <Card className="bg-slate-800 border-0 shadow-none">
              <CardHeader>
                <CardTitle className="text-slate-100 flex items-center gap-2">
                  <AlertCircle className="w-5 h-5" />
                  {t('settings.rentWarning')}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <Label className="text-slate-300">{t('settings.warningBeforeRentDue')}</Label>
                    <Input
                      type="number"
                      min="1"
                      max="30"
                      value={rentWarningDaysInput}
                      onChange={(e) => {
                        const value = e.target.value;
                        setRentWarningDaysInput(value);
                        const numValue = parseInt(value, 10);
                        if (!isNaN(numValue) && numValue >= 1 && numValue <= 30) {
                          setRentWarningDays(numValue);
                        }
                      }}
                      className="bg-slate-700 border-slate-600 text-slate-100 mt-1"
                      placeholder="5"
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      {t('settings.rentWarningHelp')}
                    </p>
                  </div>
                  <div>
                    <Label className="text-slate-300">{t('settings.rentCurrency')}</Label>
                    <Select
                      value={preferences.rent_currency || 'EUR'}
                      onValueChange={(value) => setRentCurrency(value)}
                    >
                      <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100 mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-700 border-slate-600">
                        <SelectItem value="EUR">EUR</SelectItem>
                        <SelectItem value="RON">RON</SelectItem>
                        <SelectItem value="USD">USD</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-slate-500 mt-1">
                      {t('settings.rentCurrencyHelp')}
                    </p>
                  </div>
                  <div>
                    <Label className="text-slate-300">{t('settings.billCurrency')}</Label>
                    <Select
                      value={preferences.bill_currency || 'RON'}
                      onValueChange={(value) => setBillCurrency(value)}
                    >
                      <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100 mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-700 border-slate-600">
                        <SelectItem value="EUR">EUR</SelectItem>
                        <SelectItem value="RON">RON</SelectItem>
                        <SelectItem value="USD">USD</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-slate-500 mt-1">
                      {t('settings.billCurrencyHelp')}
                    </p>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                  <div>
                    <Label className="text-slate-300">{t('settings.dateFormat')}</Label>
                    <Select
                      value={preferences.date_format || 'DD/MM/YYYY'}
                      onValueChange={(value) => setDateFormat(value)}
                    >
                      <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100 mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-700 border-slate-600">
                        <SelectItem value="DD/MM/YYYY">{t('settings.dateFormatShort')}</SelectItem>
                        <SelectItem value="DD/Month/YYYY">{t('settings.dateFormatLong')}</SelectItem>
                        <SelectItem value="MM/DD/YYYY">{t('settings.dateFormatAmerican')}</SelectItem>
                        <SelectItem value="DD/MM/YY">{t('settings.dateFormatShortYear')}</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-slate-500 mt-1">
                      {t('settings.dateFormatHelp')}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="email" className="m-0 p-6 space-y-4">
            <Card className="bg-slate-800 border-0 shadow-none">
              <CardHeader>
                <CardTitle className="text-slate-100 flex items-center gap-2">
                  <Mail className="w-5 h-5" />
                  {t('settings.emailBillImport')}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {subscription && !subscription.can_use_email_sync ? (
                  /* Show upgrade prompt for free tier */
                  <div className="space-y-4">
                    <div className="bg-amber-900/20 border border-amber-700/50 rounded-lg p-6 text-center">
                      <Lock className="w-12 h-12 text-amber-400 mx-auto mb-4" />
                      <h3 className="text-amber-300 font-medium text-lg mb-2">{t('settings.emailSyncFeature')}</h3>
                      <p className="text-slate-400 text-sm mb-4">
                        {t('settings.upgradeToProDesc')}
                      </p>
                      <Button
                        onClick={() => onNavigateToSubscription?.()}
                        className="bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-700 hover:to-orange-700"
                      >
                        <Crown className="w-4 h-4 mr-2" />
                        {t('settings.subscribeForEmailSync')}
                      </Button>
                    </div>
                  </div>
                ) : (
                  /* Show email config for paid tier */
                  <>
                    <p className="text-slate-400 text-sm">
                      {t('settings.emailConfigDesc')}
                    </p>
                    <div>
                      <Label className="text-slate-300">{t('settings.emailAddressLabel')}</Label>
                      <div className="flex gap-2 mt-2">
                        <Input
                          type="text"
                          value={user ? `proManage.bill+${user.id}@gmail.com` : ''}
                          readOnly
                          className="bg-slate-700 border-slate-600 text-slate-100 font-mono"
                        />
                        <Button
                          onClick={handleCopyEmail}
                          className="bg-emerald-600 hover:bg-emerald-700 flex items-center gap-2"
                        >
                          {emailCopied ? (
                            <>
                              <Check className="w-4 h-4" />
                              {t('settings.emailCopied')}
                            </>
                          ) : (
                            <>
                              <Copy className="w-4 h-4" />
                              {t('settings.copyEmail')}
                            </>
                          )}
                        </Button>
                      </div>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
