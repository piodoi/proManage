import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { AlertTriangle } from 'lucide-react';
import { ExtractionResult } from '@/api';
import { useI18n } from '../../lib/i18n';

type AddressWarningDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  pdfResult: ExtractionResult | null;
  onCancel: () => void;
  onConfirm: () => void;
};

export default function AddressWarningDialog({
  open,
  onOpenChange,
  pdfResult,
  onCancel,
  onConfirm,
}: AddressWarningDialogProps) {
  const { t } = useI18n();
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-slate-800 border-slate-700">
        <DialogHeader>
          <DialogTitle className="text-slate-100 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-500" />
            {t('addressWarning.title')}
          </DialogTitle>
          <DialogDescription className="text-slate-400 sr-only">
            {t('addressWarning.title')}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 text-slate-300">
          {pdfResult && (
            <>
              <div className="space-y-2">
                <p className="text-slate-200">
                  {pdfResult.address_warning || t('addressWarning.defaultMessage')}
                </p>
                {pdfResult.address_confidence !== undefined && (
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">{t('addressWarning.confidenceScore')}</span>
                    <span className={`font-medium ${
                      pdfResult.address_confidence >= 70 ? 'text-emerald-400' :
                      pdfResult.address_confidence >= 40 ? 'text-yellow-400' :
                      'text-red-400'
                    }`}>
                      {pdfResult.address_confidence}%
                    </span>
                  </div>
                )}
              </div>
              <div className="space-y-2 text-sm border-t border-slate-700 pt-4">
                <div>
                  <span className="text-slate-400">{t('addressWarning.propertyAddress')}</span>
                  <div className="text-slate-200 mt-1">{pdfResult.property_address || t('addressWarning.na')}</div>
                </div>
                <div>
                  <span className="text-slate-400">{t('addressWarning.extractedAddress')}</span>
                  <div className="text-slate-200 mt-1">{pdfResult.address || t('addressWarning.na')}</div>
                </div>
                {pdfResult.amount !== undefined && pdfResult.amount !== null && (
                  <div>
                    <span className="text-slate-400">{t('addressWarning.amount')}</span>
                    <div className="text-slate-200 mt-1">{pdfResult.amount.toFixed(2)} RON</div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
        <DialogFooter>
          <Button
            onClick={onCancel}
            className="bg-slate-700 text-slate-100 hover:bg-slate-600"
          >
            {t('common.cancel')}
          </Button>
          <Button
            onClick={onConfirm}
            className="bg-emerald-600 text-white hover:bg-emerald-700"
          >
            {t('addressWarning.addBillAnyway')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

