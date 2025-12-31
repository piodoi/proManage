import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { AlertTriangle } from 'lucide-react';
import { ExtractionResult, ExtractionPattern } from '@/api';
import { api } from '@/api';
import { useI18n } from '../../lib/i18n';

type PatternSelectionDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  pdfResult: ExtractionResult | null;
  token: string | null;
  onCancel: () => void;
  onConfirm: (patternId: string, patternSupplier: string) => void;
};

export default function PatternSelectionDialog({
  open,
  onOpenChange,
  pdfResult,
  token,
  onCancel,
  onConfirm,
}: PatternSelectionDialogProps) {
  const { t } = useI18n();
  const [patterns, setPatterns] = useState<ExtractionPattern[]>([]);
  const [selectedPatternId, setSelectedPatternId] = useState<string>('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open && token) {
      loadPatterns();
    }
  }, [open, token]);

  const loadPatterns = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await api.extractionPatterns.list(token);
      // Filter to only enabled patterns with vendor_hint
      const enabledPatterns = data.filter(p => p.enabled && p.vendor_hint);
      setPatterns(enabledPatterns);
      if (enabledPatterns.length > 0) {
        setSelectedPatternId(enabledPatterns[0].id);
      }
    } catch (err) {
      console.error('Failed to load patterns:', err);
    } finally {
      setLoading(false);
    }
  };

  const selectedPattern = patterns.find(p => p.id === selectedPatternId);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-slate-800 border-slate-700">
        <DialogHeader>
          <DialogTitle className="text-slate-100 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-500" />
            {t('patternSelection.title')}
          </DialogTitle>
          <DialogDescription className="text-slate-400 sr-only">
            {t('patternSelection.title')}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 text-slate-300">
          <div className="bg-red-900/30 border border-red-700 rounded p-3">
            <p className="text-red-200 text-sm font-medium">
              {t('patternSelection.warning')}
            </p>
            <p className="text-red-300 text-xs mt-1">
              {t('patternSelection.warningDetail')}
            </p>
          </div>
          
          <div>
            <label className="text-slate-300 text-sm font-medium mb-2 block">
              {t('patternSelection.selectPattern')}
            </label>
            {loading ? (
              <div className="text-slate-400 text-sm">{t('patternSelection.loadingPatterns')}</div>
            ) : patterns.length === 0 ? (
              <div className="text-slate-400 text-sm">{t('patternSelection.noPatternsAvailable')}</div>
            ) : (
              <Select value={selectedPatternId} onValueChange={setSelectedPatternId}>
                <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                  <SelectValue placeholder={t('patternSelection.selectPatternPlaceholder')} />
                </SelectTrigger>
                <SelectContent className="bg-slate-700 border-slate-600">
                  {patterns.map((pattern) => (
                    <SelectItem
                      key={pattern.id}
                      value={pattern.id}
                      className="text-slate-100 hover:bg-slate-600"
                    >
                      {pattern.vendor_hint} {pattern.supplier ? `(${pattern.supplier})` : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {pdfResult && (
            <div className="space-y-2 text-sm border-t border-slate-700 pt-4">
              <div>
                <span className="text-slate-400">{t('patternSelection.extractedAmount')}</span>
                <div className="text-slate-200">{pdfResult.amount?.toFixed(2) || t('addressWarning.na')} RON</div>
              </div>
              {pdfResult.bill_number && (
                <div>
                  <span className="text-slate-400">{t('patternSelection.billNumber')}</span>
                  <div className="text-slate-200">{pdfResult.bill_number}</div>
                </div>
              )}
              {pdfResult.address && (
                <div>
                  <span className="text-slate-400">{t('patternSelection.address')}</span>
                  <div className="text-slate-200">{pdfResult.address}</div>
                </div>
              )}
            </div>
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
            onClick={() => {
              if (selectedPattern) {
                onConfirm(selectedPattern.id, selectedPattern.supplier || selectedPattern.vendor_hint || t('patternSelection.unknown'));
              }
            }}
            disabled={!selectedPatternId || loading}
            className="bg-emerald-600 text-white hover:bg-emerald-700"
          >
            {t('patternSelection.useSelectedPattern')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

