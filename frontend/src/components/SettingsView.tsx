import { useState, useEffect } from 'react';
import { api, SubscriptionStatus } from '../api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Mail, Settings } from 'lucide-react';

type SettingsViewProps = {
  token: string | null;
  onError?: (error: string) => void;
};

export default function SettingsView({ token, onError }: SettingsViewProps) {
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [showEmailConfig, setShowEmailConfig] = useState(false);
  const [emailForm, setEmailForm] = useState({ config_type: 'forwarding' as 'direct' | 'forwarding', forwarding_email: '' });

  useEffect(() => {
    if (token) {
      loadSubscription();
    }
  }, [token]);

  const loadSubscription = async () => {
    if (!token) return;
    try {
      const sub = await api.subscription.status(token);
      setSubscription(sub);
    } catch (err) {
      if (onError) {
        onError(err instanceof Error ? err.message : 'Failed to load subscription');
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
        onError(err instanceof Error ? err.message : 'Failed to configure email');
      }
    }
  };

  return (
    <div className="space-y-4">
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100 flex items-center gap-2">
            <Mail className="w-5 h-5" />
            Email Bill Import
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-slate-400 text-sm">
            Configure email access to automatically import bills. You can either grant direct access to your Gmail
            or set up email forwarding to a dedicated address.
          </p>
          <Dialog open={showEmailConfig} onOpenChange={setShowEmailConfig}>
            <DialogTrigger asChild>
              <Button className="bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600">
                Configure Email
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-slate-800 border-slate-700">
              <DialogHeader>
                <DialogTitle className="text-slate-100">Email Configuration</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label className="text-slate-300">Access Type</Label>
                  <Select value={emailForm.config_type} onValueChange={(v) => setEmailForm({ ...emailForm, config_type: v as 'direct' | 'forwarding' })}>
                    <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-700 border-slate-600">
                      <SelectItem value="direct">Direct Gmail Access</SelectItem>
                      <SelectItem value="forwarding">Email Forwarding</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {emailForm.config_type === 'forwarding' && (
                  <div>
                    <Label className="text-slate-300">Forwarding Email</Label>
                    <Input
                      value={emailForm.forwarding_email}
                      onChange={(e) => setEmailForm({ ...emailForm, forwarding_email: e.target.value })}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                      placeholder="bills@promanage.local"
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      Forward your utility bills to this address for automatic processing
                    </p>
                  </div>
                )}
                {emailForm.config_type === 'direct' && (
                  <p className="text-sm text-slate-400">
                    Direct Gmail access requires OAuth configuration. Contact support to enable this feature.
                  </p>
                )}
                <Button onClick={handleConfigureEmail} className="w-full bg-emerald-600 hover:bg-emerald-700">
                  Save Configuration
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </CardContent>
      </Card>

      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100">Subscription Status</CardTitle>
        </CardHeader>
        <CardContent>
          {subscription && (
            <div className="space-y-2">
              <p className="text-slate-300">
                Status: <span className={subscription.status === 'active' ? 'text-green-400' : 'text-amber-400'}>
                  {subscription.status}
                </span>
              </p>
              <p className="text-slate-300">Properties: {subscription.property_count}</p>
              {subscription.expires && (
                <p className="text-slate-300">Expires: {new Date(subscription.expires).toLocaleDateString()}</p>
              )}
              {!subscription.can_add_property && (
                <p className="text-amber-400 text-sm mt-2">
                  Upgrade to add more properties. Contact admin for subscription.
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

