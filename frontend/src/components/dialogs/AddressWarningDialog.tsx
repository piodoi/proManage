import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { AlertTriangle } from 'lucide-react';
import { ExtractionResult } from '@/api';

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
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-slate-800 border-slate-700">
        <DialogHeader>
          <DialogTitle className="text-slate-100 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-500" />
            Address Mismatch Warning
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4 text-slate-300">
          <p>{pdfResult?.address_warning}</p>
          {pdfResult && (
            <div className="space-y-2 text-sm">
              <div>
                <span className="text-slate-400">Property Address:</span>
                <div className="text-slate-200">{pdfResult.property_address || 'N/A'}</div>
              </div>
              <div>
                <span className="text-slate-400">Extracted Address:</span>
                <div className="text-slate-200">{pdfResult.address || 'N/A'}</div>
              </div>
                {pdfResult.amount !== undefined && pdfResult.amount !== null && (
                  <div>
                    <span className="text-slate-400">Amount:</span>
                    <div className="text-slate-200">{pdfResult.amount.toFixed(2)} RON</div>
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
            Cancel
          </Button>
          <Button
            onClick={onConfirm}
            className="bg-emerald-600 text-white hover:bg-emerald-700"
          >
            Add Bill Anyway
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

