import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from '@/components/ui/dialog';
import { Plus } from 'lucide-react';
import { useI18n } from '../../lib/i18n';

type PropertyDialogProps = {
  token: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onError: (error: string) => void;
  canAddProperty: boolean;
};

export default function PropertyDialog({
  token,
  open,
  onOpenChange,
  onSuccess,
  onError,
  canAddProperty,
}: PropertyDialogProps) {
  const { t } = useI18n();
  const [form, setForm] = useState({ name: '', address: '' });

  const handleSubmit = async () => {
    if (!token) return;
    try {
      const { api } = await import('../../api');
      await api.properties.create(token, form);
      setForm({ name: '', address: '' });
      onOpenChange(false);
      onSuccess();
    } catch (err) {
      onError(err instanceof Error ? err.message : t('errors.generic'));
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button
          className="bg-emerald-600 hover:bg-emerald-700"
          disabled={!canAddProperty}
        >
          <Plus className="w-4 h-4 mr-2" />
          {t('property.addProperty')}
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-slate-800 border-slate-700">
        <DialogHeader>
          <DialogTitle className="text-slate-100">{t('property.addProperty')}</DialogTitle>
          <DialogDescription className="text-slate-400 sr-only">
            {t('property.addProperty')}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label className="text-slate-300">{t('common.name')}</Label>
            <Input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="bg-slate-700 border-slate-600 text-slate-100"
              placeholder={t('property.propertyName')}
            />
          </div>
          <div>
            <Label className="text-slate-300">{t('property.address')}</Label>
            <Input
              value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
              className="bg-slate-700 border-slate-600 text-slate-100"
              placeholder={t('property.addressPlaceholder')}
            />
          </div>
          <Button onClick={handleSubmit} className="w-full bg-emerald-600 hover:bg-emerald-700">
            {t('property.addProperty')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

