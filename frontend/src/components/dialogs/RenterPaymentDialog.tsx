import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Renter } from '../../api';
import { getAvailableCurrencies } from '../../lib/currencyConfig';
import { useI18n } from '../../lib/i18n';
import { formatAmount } from '../../utils/currency';

type RenterPaymentDialogProps = {
  renter: Renter | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  paymentAmount: string;
  onPaymentAmountChange: (value: string) => void;
  paymentCurrency: 'EUR' | 'RON' | 'USD';
  onPaymentCurrencyChange: (value: 'EUR' | 'RON' | 'USD') => void;
  includeCommonBills: boolean;
  onIncludeCommonBillsChange: (value: boolean) => void;
  applyingCredit: boolean;
  recordingPayment: boolean;
  onApplyCredit: () => void;
  onRecordPayment: () => void;
};

export default function RenterPaymentDialog({
  renter,
  open,
  onOpenChange,
  paymentAmount,
  onPaymentAmountChange,
  paymentCurrency,
  onPaymentCurrencyChange,
  includeCommonBills,
  onIncludeCommonBillsChange,
  applyingCredit,
  recordingPayment,
  onApplyCredit,
  onRecordPayment,
}: RenterPaymentDialogProps) {
  const { t } = useI18n();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-slate-800 border-slate-700 pr-14 sm:pr-16">
        <DialogHeader>
          <DialogTitle className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-4 pr-2 text-slate-100">
            <span className="min-w-0 pr-2">{t('renter.recordPayment')}{renter ? `: ${renter.name}` : ''}</span>
            <span className="whitespace-nowrap text-right text-sm font-normal text-slate-300">
              {t('renter.credit')}: {formatAmount(renter?.credit || 0, renter?.credit_currency || 'RON')}
            </span>
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label className="text-slate-300">{t('renter.paymentAmount')}</Label>
            <div className="mt-1 flex gap-2">
              <Input
                type="number"
                step="0.01"
                min="0"
                value={paymentAmount}
                onChange={(e) => onPaymentAmountChange(e.target.value)}
                className="bg-slate-700 border-slate-600 text-slate-100"
                placeholder="0.00"
              />
              <Select value={paymentCurrency} onValueChange={(value) => onPaymentCurrencyChange(value as 'EUR' | 'RON' | 'USD')}>
                <SelectTrigger className="w-24 bg-slate-700 border-slate-600 text-slate-100">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-slate-700 border-slate-600">
                  {getAvailableCurrencies().map((currency) => (
                    <SelectItem key={currency} value={currency}>{currency}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex items-start gap-3 rounded-md border border-slate-700 bg-slate-900/60 px-3 py-2">
            <Checkbox
              checked={includeCommonBills}
              onCheckedChange={(checked) => onIncludeCommonBillsChange(checked === true)}
              className="mt-0.5 border-slate-500 data-[state=checked]:bg-emerald-600 data-[state=checked]:border-emerald-600"
            />
            <div className="space-y-1">
              <Label className="text-slate-200">{t('renter.includeCommonBills')}</Label>
              <p className="text-xs text-slate-400">{t('renter.includeCommonBillsHelp')}</p>
            </div>
          </div>
          <Button
            onClick={onApplyCredit}
            disabled={applyingCredit || recordingPayment || (renter?.credit || 0) <= 0}
            className="w-full bg-slate-700 text-slate-100 hover:bg-slate-600"
          >
            {applyingCredit ? t('common.loading') : t('renter.applyCredit')}
          </Button>
          <Button
            onClick={onRecordPayment}
            disabled={recordingPayment || applyingCredit}
            className="w-full bg-emerald-600 hover:bg-emerald-700"
          >
            {recordingPayment ? t('common.loading') : t('renter.recordPayment')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}