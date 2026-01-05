import { useState, useEffect } from 'react';
import { api, SubscriptionStatus, User as ApiUser } from '../api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Mail, AlertCircle, User, Copy, Check } from 'lucide-react';
import { useI18n } from '../lib/i18n';
import { usePreferences } from '../hooks/usePreferences';
import SupplierCredentialsSettings from './SupplierCredentialsSettings';
import { validateIban, formatIban } from '../utils/iban';

type SettingsViewProps = {
  token: string | null;
  user: ApiUser | null;
  onError?: (error: string) => void;
};

export default function SettingsView({ token, user, onError }: SettingsViewProps) {
  const { t } = useI18n();
  const { preferences, setRentWarningDays, setRentCurrency, setBillCurrency, setPhoneNumber, setLandlordName, setPersonalEmail, setIban } = usePreferences();
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [emailCopied, setEmailCopied] = useState(false);
  const [rentWarningDaysInput, setRentWarningDaysInput] = useState<string>('');
  const [phoneNumberInput, setPhoneNumberInput] = useState<string>('');
  const [landlordNameInput, setLandlordNameInput] = useState<string>('');
  const [personalEmailInput, setPersonalEmailInput] = useState<string>('');
  const [ibanInput, setIbanInput] = useState<string>('');
  const [ibanError, setIbanError] = useState<string>('');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>(() => {
    // Get from sessionStorage if available, otherwise default
    return sessionStorage.getItem('settingsActiveTab') || 'subscription';
  });

  const handleTabChange = (value: string) => {
    setActiveTab(value);
    sessionStorage.setItem('settingsActiveTab', value);
  };

  useEffect(() => {
    if (token) {
      loadSubscription();
    }
  }, [token]);

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

  const loadSubscription = async () => {
    if (!token) return;
    try {
      const sub = await api.subscription.status(token);
      setSubscription(sub);
    } catch (err) {
      if (onError) {
        onError(err instanceof Error ? err.message : t('settings.loadSubscriptionError'));
      }
    }
  };

  return (
    <div className="space-y-0">
      <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
        <TabsList className="bg-slate-800 border-b border-slate-700 rounded-none rounded-t-lg h-auto p-0 gap-0 w-full justify-start">
          <TabsTrigger value="subscription" className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-4 py-2 border-b-2 border-transparent">
            {t('settings.subscriptionStatus')}
          </TabsTrigger>
          <TabsTrigger value="personal" className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-4 py-2 border-b-2 border-transparent">
            {t('settings.personalDetails')}
          </TabsTrigger>
          <TabsTrigger value="rent-bills" className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-4 py-2 border-b-2 border-transparent">
            {t('settings.rentWarning')}
          </TabsTrigger>
          <TabsTrigger value="suppliers" className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-4 py-2 border-b-2 border-transparent">
            {t('settings.manageSuppliersCredentials')}
          </TabsTrigger>
          <TabsTrigger value="email" className="data-[state=active]:bg-slate-700 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none px-4 py-2 border-b-2 border-transparent">
            {t('settings.emailBillImport')}
          </TabsTrigger>
        </TabsList>

        <div className="bg-slate-800 border border-t-0 border-slate-700 rounded-b-lg">
          <TabsContent value="subscription" className="m-0 p-6 space-y-4">
        <Card className="bg-slate-800 border-0 shadow-none">
          <CardHeader>
            <CardTitle className="text-slate-100">{t('settings.subscriptionStatus')}</CardTitle>
          </CardHeader>
          <CardContent>
            {subscription && (
              <div className="space-y-2">
                <p className="text-slate-300">
                  {t('common.status')}: <span className={subscription.status === 'active' ? 'text-green-400' : 'text-amber-400'}>
                    {subscription.status}
                  </span>
                </p>
                <p className="text-slate-300">{t('settings.properties')}: {subscription.property_count}</p>
                {subscription.expires && (
                  <p className="text-slate-300">{t('settings.expires')}: {new Date(subscription.expires).toLocaleDateString()}</p>
                )}
                {!subscription.can_add_property && (
                  <p className="text-amber-400 text-sm mt-2">
                    {t('settings.upgradeMessage')}
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
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
          </CardContent>
        </Card>
          </TabsContent>

          <TabsContent value="suppliers" className="m-0 p-6 space-y-4">
          <SupplierCredentialsSettings token={token} onError={onError} />
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
          </CardContent>
        </Card>
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
