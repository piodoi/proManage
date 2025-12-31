import { useState, useEffect } from 'react';
import { api, Renter } from '../../api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Users } from 'lucide-react';
import { useI18n } from '../../lib/i18n';

type RenterDialogProps = {
  token: string | null;
  propertyId: string;
  renter: Renter | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onError: (error: string) => void;
};

export default function RenterDialog({
  token,
  propertyId,
  renter,
  open,
  onOpenChange,
  onSuccess,
  onError,
}: RenterDialogProps) {
  const { t } = useI18n();
  const [form, setForm] = useState({
    name: '',
    rent_day: '',
    start_contract_date: '',
    rent_amount: '',
    rent_currency: 'EUR' as 'EUR' | 'RON' | 'USD',
    email: '',
    phone: '',
  });

  // Sync form when renter changes
  useEffect(() => {
    if (renter) {
      let formattedStartDate = '';
      if (renter.start_contract_date) {
        try {
          const date = new Date(renter.start_contract_date);
          if (!isNaN(date.getTime())) {
            formattedStartDate = date.toISOString().split('T')[0];
          }
        } catch (e) {
          console.error('[RenterDialog] Error formatting start_contract_date:', e);
        }
      }

      setForm({
        name: renter.name || '',
        rent_day: renter.rent_day ? renter.rent_day.toString() : '',
        start_contract_date: formattedStartDate,
        rent_amount: renter.rent_amount_eur ? renter.rent_amount_eur.toString() : '',
        rent_currency: 'EUR',
        email: renter.email || '',
        phone: renter.phone || '',
      });
    } else {
      setForm({
        name: '',
        rent_day: '',
        start_contract_date: '',
        rent_amount: '',
        rent_currency: 'EUR',
        email: '',
        phone: '',
      });
    }
  }, [renter]);

  const handleSubmit = async () => {
    if (!token) return;
    if (!form.name || !form.rent_amount || !form.rent_day) {
      onError(t('renter.requiredFields'));
      return;
    }

    try {
      const rentAmountEUR = parseFloat(form.rent_amount);
      const rentDay = form.rent_day ? parseInt(form.rent_day, 10) : undefined;
      const startContractDate = form.start_contract_date || undefined;

      if (renter) {
        await api.renters.update(token, renter.id, {
          name: form.name,
          email: form.email || undefined,
          phone: form.phone || undefined,
          rent_day: rentDay,
          start_contract_date: startContractDate,
          rent_amount_eur: rentAmountEUR,
        });
      } else {
        await api.renters.create(token, propertyId, {
          name: form.name,
          email: form.email || undefined,
          phone: form.phone || undefined,
          rent_day: rentDay,
          start_contract_date: startContractDate,
          rent_amount_eur: rentAmountEUR,
        });
      }

      onOpenChange(false);
      onSuccess();
    } catch (err) {
      onError(err instanceof Error ? err.message : t('errors.generic'));
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" className="bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600">
          <Users className="w-4 h-4 mr-1" />
          {renter ? t('renter.editRenter') : t('renter.addRenter')}
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-slate-800 border-slate-700" key={`renter-dialog-${renter?.id || 'new'}`}>
        <DialogHeader>
          <DialogTitle className="text-slate-100">
            {renter ? t('renter.editRenter') : t('renter.addRenter')}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label className="text-slate-300">{t('common.name')} *</Label>
            <Input
              key={`name-${renter?.id || 'new'}`}
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="bg-slate-700 border-slate-600 text-slate-100"
              placeholder={t('renter.renterNamePlaceholder')}
              required
            />
          </div>
          <div>
            <Label className="text-slate-300">{t('renter.rentDay')} *</Label>
            <Input
              key={`rent_day-${renter?.id || 'new'}`}
              type="number"
              min="1"
              max="28"
              value={form.rent_day}
              onChange={(e) => setForm({ ...form, rent_day: e.target.value })}
              className="bg-slate-700 border-slate-600 text-slate-100"
              placeholder={t('renter.rentDayPlaceholder')}
              required
            />
            <p className="text-xs text-slate-500 mt-1">
              {t('renter.rentDayHelp')}
            </p>
          </div>
          <div>
            <Label className="text-slate-300">{t('renter.startContractDate')}</Label>
            <Input
              key={`start_contract_date-${renter?.id || 'new'}`}
              type="date"
              value={form.start_contract_date}
              onChange={(e) => setForm({ ...form, start_contract_date: e.target.value })}
              className="bg-slate-700 border-slate-600 text-slate-100"
            />
            <p className="text-xs text-slate-500 mt-1">
              {t('renter.startContractDateHelp')}
            </p>
          </div>
          <div>
            <Label className="text-slate-300">{t('renter.rentAmount')}</Label>
            <div className="flex gap-2 items-center">
              <Input
                key={`rent_amount-${renter?.id || 'new'}`}
                type="number"
                step="0.01"
                value={form.rent_amount}
                onChange={(e) => setForm({ ...form, rent_amount: e.target.value })}
                className="bg-slate-700 border-slate-600 text-slate-100 w-32 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                placeholder="0.00"
                required
              />
              <Select
                key={`rent_currency-${renter?.id || 'new'}`}
                value={form.rent_currency}
                onValueChange={(v) => setForm({ ...form, rent_currency: v as 'EUR' | 'RON' | 'USD' })}
              >
                <SelectTrigger className="w-20 h-10 bg-slate-700 border-slate-600 text-slate-100">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-slate-700 border-slate-600">
                  <SelectItem value="EUR">EUR</SelectItem>
                  <SelectItem value="RON">RON</SelectItem>
                  <SelectItem value="USD">USD</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              {t('renter.rentAmountHelp')}
            </p>
          </div>
          <div>
            <Label className="text-slate-300">{t('renter.phone')} ({t('common.or').toLowerCase()})</Label>
            <Input
              key={`phone-${renter?.id || 'new'}`}
              type="tel"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              className="bg-slate-700 border-slate-600 text-slate-100"
              placeholder={t('renter.phonePlaceholder')}
            />
          </div>
          <div>
            <Label className="text-slate-300">{t('common.email')} ({t('common.or').toLowerCase()})</Label>
            <Input
              key={`email-${renter?.id || 'new'}`}
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="bg-slate-700 border-slate-600 text-slate-100"
              placeholder={t('auth.emailPlaceholder')}
            />
          </div>
          <Button
            onClick={handleSubmit}
            className="w-full bg-emerald-600 hover:bg-emerald-700"
            disabled={!form.name || !form.rent_amount || !form.rent_day}
          >
            {renter ? t('renter.updateRenter') : t('renter.addRenter')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

