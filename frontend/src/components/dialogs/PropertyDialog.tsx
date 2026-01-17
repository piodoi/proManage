import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Plus, Crown } from 'lucide-react';
import { useI18n } from '../../lib/i18n';

type PropertyDialogProps = {
  token: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onError: (error: string) => void;
  canAddProperty: boolean;
  onUpgradeClick?: () => void;  // Callback to navigate to subscription
};

export default function PropertyDialog({
  token,
  open,
  onOpenChange,
  onSuccess,
  onError,
  canAddProperty,
  onUpgradeClick,
}: PropertyDialogProps) {
  const { t } = useI18n();
  const [form, setForm] = useState({ name: '', address: '' });
  const [isHovered, setIsHovered] = useState(false);
  
  const needsUpgrade = !canAddProperty && onUpgradeClick;

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

  const handleTriggerClick = (e: React.MouseEvent) => {
    if (needsUpgrade) {
      e.preventDefault();
      e.stopPropagation();
      onUpgradeClick!();
    } else {
      onOpenChange(true);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <Button
        type="button"
        className={needsUpgrade 
          ? (isHovered 
              ? "bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-700 hover:to-orange-700" 
              : "bg-emerald-600 hover:bg-emerald-700")
          : "bg-emerald-600 hover:bg-emerald-700"
        }
        onClick={handleTriggerClick}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        {needsUpgrade && isHovered ? (
          <>
            <Crown className="w-4 h-4 mr-2" />
            {t('settings.upgradeToProTitle')}
          </>
        ) : (
          <>
            <Plus className="w-4 h-4 mr-2" />
            {t('property.addProperty')}
          </>
        )}
      </Button>
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

