import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { AlertTriangle, FileText } from 'lucide-react';
import { ExtractionResult } from '@/api';
import { useI18n } from '../../lib/i18n';

type BillConfirmDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  pdfResult: ExtractionResult | null;
  onCancel: () => void;
  onConfirm: () => void;
};

export default function BillConfirmDialog({
  open,
  onOpenChange,
  pdfResult,
  onCancel,
  onConfirm,
}: BillConfirmDialogProps) {
  const { t } = useI18n();
  
  const hasAddressWarning = pdfResult && !pdfResult.address_matches && pdfResult.address_warning;
  
  // Calculate match percentage based on key fields
  const calculateMatchPercentage = (result: ExtractionResult): { percentage: number; found: number; total: number } => {
    const fields = [
      { name: 'amount', hasValue: result.amount !== undefined && result.amount !== null && result.amount > 0 },
      { name: 'address', hasValue: !!result.address },
      { name: 'bill_number', hasValue: !!result.bill_number },
      { name: 'due_date', hasValue: !!result.due_date },
      { name: 'bill_date', hasValue: !!result.bill_date },
      { name: 'contract_id', hasValue: !!result.contract_id },
      { name: 'iban', hasValue: !!result.iban },
      { name: 'legal_name', hasValue: !!result.legal_name },
    ];
    
    const found = fields.filter(f => f.hasValue).length;
    const total = fields.length;
    const percentage = Math.round((found / total) * 100);
    
    return { percentage, found, total };
  };
  
  const matchInfo = pdfResult ? calculateMatchPercentage(pdfResult) : { percentage: 0, found: 0, total: 0 };
  
  // Get color class for percentage
  const getPercentageColor = (pct: number): string => {
    if (pct < 30) return 'text-red-400';
    if (pct < 75) return 'text-orange-400';
    return 'text-emerald-400';
  };
  
  // Check if a value is missing/empty
  const hasAmount = pdfResult?.amount !== undefined && pdfResult?.amount !== null && pdfResult.amount > 0;
  const hasAddress = !!pdfResult?.address;
  
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-slate-800 border-slate-700 max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-slate-100 flex items-center gap-2">
            {hasAddressWarning ? (
              <AlertTriangle className="w-5 h-5 text-yellow-500" />
            ) : (
              <FileText className="w-5 h-5 text-emerald-500" />
            )}
            {t('billConfirm.title')}
          </DialogTitle>
          <DialogDescription className="text-slate-400 sr-only">
            {t('billConfirm.title')}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 text-slate-300">
          {pdfResult && (
            <>
              {/* Match percentage indicator */}
              <div className="flex items-center justify-between bg-slate-750/50 border border-slate-700 rounded-lg px-4 py-2">
                <span className="text-sm text-slate-400">{t('billConfirm.fieldsMatched')}</span>
                <div className="flex items-center gap-2">
                  <span className={`text-lg font-bold ${getPercentageColor(matchInfo.percentage)}`}>
                    {matchInfo.percentage}%
                  </span>
                  <span className="text-xs text-slate-500">
                    ({matchInfo.found}/{matchInfo.total})
                  </span>
                </div>
              </div>
              
              {/* Address warning section */}
              {hasAddressWarning && (
                <div className="bg-yellow-900/30 border border-yellow-700/50 rounded-lg p-3 space-y-2">
                  <div className="flex items-center gap-2 text-yellow-400 font-medium">
                    <AlertTriangle className="w-4 h-4" />
                    {t('addressWarning.title')}
                  </div>
                  <p className="text-sm text-yellow-200/80">
                    {pdfResult.address_warning || t('addressWarning.defaultMessage')}
                  </p>
                  {pdfResult.address_confidence !== undefined && (
                    <div className="flex items-center gap-2 text-sm">
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
              )}
              
              {/* Bill details */}
              <div className="space-y-3 border border-slate-700 rounded-lg p-4 bg-slate-750/50">
                <div className="text-sm font-medium text-slate-200 border-b border-slate-700 pb-2">
                  {t('billConfirm.extractedDetails')}
                </div>
                
                {/* Pattern/Supplier */}
                {pdfResult.matched_pattern_name && (
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">{t('billConfirm.supplier')}</span>
                    <span className="text-slate-200 font-medium">{pdfResult.matched_pattern_name}</span>
                  </div>
                )}
                
                {/* Bill Type */}
                {pdfResult.matched_pattern_bill_type && (
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">{t('bill.billType')}</span>
                    <span className="text-slate-200">{t(`bill.${pdfResult.matched_pattern_bill_type}`)}</span>
                  </div>
                )}
                
                {/* Amount - Always show, red if missing */}
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">{t('common.amount')}</span>
                  <span className={`font-medium ${hasAmount ? 'text-emerald-400' : 'text-red-400'}`}>
                    {hasAmount ? `${pdfResult.amount!.toFixed(2)} RON` : t('billConfirm.notFound')}
                  </span>
                </div>
                
                {/* Bill Number */}
                {pdfResult.bill_number && (
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">{t('bill.billNumber')}</span>
                    <span className="text-slate-200">{pdfResult.bill_number}</span>
                  </div>
                )}
                
                {/* Due Date */}
                {pdfResult.due_date && (
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">{t('bill.dueDate')}</span>
                    <span className="text-slate-200">{pdfResult.due_date}</span>
                  </div>
                )}
                
                {/* Bill Date */}
                {pdfResult.bill_date && (
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">{t('billConfirm.billDate')}</span>
                    <span className="text-slate-200">{pdfResult.bill_date}</span>
                  </div>
                )}
                
                {/* Contract ID */}
                {pdfResult.contract_id && (
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">{t('billConfirm.contractId')}</span>
                    <span className="text-slate-200">{pdfResult.contract_id}</span>
                  </div>
                )}
                
                {/* Address section - Always show extracted address, red if missing */}
                <div className="border-t border-slate-700 pt-3 mt-3 space-y-2">
                  {pdfResult.property_address && (
                    <div className="text-sm">
                      <span className="text-slate-400">{t('addressWarning.propertyAddress')}</span>
                      <div className="text-slate-200 mt-0.5">{pdfResult.property_address}</div>
                    </div>
                  )}
                  <div className="text-sm">
                    <span className="text-slate-400">{t('addressWarning.extractedAddress')}</span>
                    <div className={`mt-0.5 ${hasAddress ? 'text-slate-200' : 'text-red-400'}`}>
                      {hasAddress ? pdfResult.address : t('billConfirm.notFound')}
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Confirmation prompt */}
              <p className="text-sm text-slate-400 text-center">
                {t('billConfirm.confirmPrompt')}
              </p>
            </>
          )}
        </div>
        <DialogFooter className="gap-2">
          <Button
            onClick={onCancel}
            className="bg-slate-700 text-slate-100 hover:bg-slate-600"
          >
            {t('common.cancel')}
          </Button>
          <Button
            onClick={onConfirm}
            disabled={!hasAmount}
            className="bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {t('billConfirm.addBill')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
