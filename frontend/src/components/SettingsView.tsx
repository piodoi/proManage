import { useState, useEffect } from 'react';
import { api, SubscriptionStatus } from '../api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Mail, Settings, AlertCircle, Phone } from 'lucide-react';
import { useI18n } from '../lib/i18n';
import { usePreferences } from '../hooks/usePreferences';
import SupplierCredentialsSettings from './SupplierCredentialsSettings';

type SettingsViewProps = {
  token: string | null;
  onError?: (error: string) => void;
};

export default function SettingsView({ token, onError }: SettingsViewProps) {
  const { t } = useI18n();
  const { preferences, setRentWarningDays, setRentCurrency, setBillCurrency, setPhoneNumber } = usePreferences();
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [showEmailConfig, setShowEmailConfig] = useState(false);
  const [emailForm, setEmailForm] = useState({ config_type: 'forwarding' as 'direct' | 'forwarding', forwarding_email: '' });
  const [rentWarningDaysInput, setRentWarningDaysInput] = useState<string>('');
  const [phoneNumberInput, setPhoneNumberInput] = useState<string>('');

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

  const handleSavePhoneNumber = () => {
    setPhoneNumber(phoneNumberInput || null);
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

  const handleConfigureEmail = async () => {
    if (!token) return;
    try {
      await api.email.configure(token, emailForm);
      setShowEmailConfig(false);
      if (onError) {
        onError('');
      }
    } catch (err) {
      if (onError) {
        onError(err instanceof Error ? err.message : t('settings.configureEmailError'));
      }
    }
  };

  return (
    <div className="space-y-4">
      <Card className="bg-slate-800 border-slate-700">
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
          <Dialog open={showEmailConfig} onOpenChange={setShowEmailConfig}>
            <DialogTrigger asChild>
              <Button className="bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600">
                {t('settings.configureEmail')}
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-slate-800 border-slate-700">
              <DialogHeader>
                <DialogTitle className="text-slate-100">{t('settings.emailConfig')}</DialogTitle>
                <DialogDescription className="text-slate-400 sr-only">
                  {t('settings.emailConfig')}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label className="text-slate-300">{t('settings.accessType')}</Label>
                  <Select value={emailForm.config_type} onValueChange={(v) => setEmailForm({ ...emailForm, config_type: v as 'direct' | 'forwarding' })}>
                    <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-700 border-slate-600">
                      <SelectItem value="direct">{t('settings.directGmailAccess')}</SelectItem>
                      <SelectItem value="forwarding">{t('settings.emailForwarding')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {emailForm.config_type === 'forwarding' && (
                  <div>
                    <Label className="text-slate-300">{t('settings.forwardingEmail')}</Label>
                    <Input
                      value={emailForm.forwarding_email}
                      onChange={(e) => setEmailForm({ ...emailForm, forwarding_email: e.target.value })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                      placeholder={t('settings.forwardingEmailPlaceholder')}
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      {t('settings.forwardingEmailHelp')}
                    </p>
                  </div>
                )}
                {emailForm.config_type === 'direct' && (
                  <p className="text-sm text-slate-400">
                    {t('settings.directGmailDesc')}
                  </p>
                )}
                <Button onClick={handleConfigureEmail} className="w-full bg-emerald-600 hover:bg-emerald-700">
                  {t('settings.saveConfiguration')}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </CardContent>
      </Card>

      <Card className="bg-slate-800 border-slate-700">
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

      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100 flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            {t('settings.rentWarning')}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-slate-400 text-sm">
            {t('settings.rentWarningDesc')}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
            <div className="grid grid-cols-2 gap-4">
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
          </div>
        </CardContent>
      </Card>

      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100 flex items-center gap-2">
            <Phone className="w-5 h-5" />
            {t('settings.phoneNumber')}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-slate-400 text-sm">
            {t('settings.phoneNumberDesc')}
          </p>
          <div>
            <Label className="text-slate-300">{t('settings.phoneNumberLabel')}</Label>
            <div className="flex gap-2 mt-1">
              <Input
                type="tel"
                value={phoneNumberInput}
                onChange={(e) => setPhoneNumberInput(e.target.value)}
                className="bg-slate-700 border-slate-600 text-slate-100"
                placeholder={t('settings.phoneNumberPlaceholder')}
              />
              <Button
                onClick={handleSavePhoneNumber}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                {t('common.save')}
              </Button>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              {t('settings.phoneNumberHelp')}
            </p>
          </div>
        </CardContent>
      </Card>

      <SupplierCredentialsSettings token={token} onError={onError} />
    </div>
  );
}

