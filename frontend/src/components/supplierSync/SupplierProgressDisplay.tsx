import { CheckCircle2, XCircle, Clock, AlertCircle } from 'lucide-react';
import { Spinner } from '@/components/ui/spinner';
import { type SupplierProgressStatus } from '../../utils/supplierSyncUtils';
import { useI18n } from '../../lib/i18n';

export type SupplierProgress = {
  supplier_name: string;
  contract_id?: string;
  status: SupplierProgressStatus;
  bills_found: number;
  bills_created: number;
  error?: string;
  properties_affected?: string[];
};

type SupplierProgressDisplayProps = {
  progress: SupplierProgress[];
};

const getStatusIcon = (status: SupplierProgressStatus) => {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="w-5 h-5 text-emerald-400" />;
    case 'error':
      return <XCircle className="w-5 h-5 text-red-400" />;
    case 'processing':
      return <Spinner className="w-5 h-5 text-blue-400" />;
    default:
      return <Clock className="w-5 h-5 text-slate-400" />;
  }
};

const getStatusText = (status: SupplierProgressStatus, t: (key: string) => string) => {
  switch (status) {
    case 'completed':
      return t('supplier.completed');
    case 'error':
      return t('supplier.error');
    case 'processing':
      return t('supplier.processing');
    case 'starting':
      return t('supplier.starting');
    default:
      return t('common.loading');
  }
};

export default function SupplierProgressDisplay({ progress }: SupplierProgressDisplayProps) {
  const { t } = useI18n();

  return (
    <div className="flex-1 overflow-y-auto border border-slate-600 rounded-lg bg-slate-700/50 p-4 space-y-3">
      {progress.map((item, index) => (
        <div
          key={`${item.supplier_name}_${item.contract_id || 'no_contract'}_${index}`}
          className="bg-slate-700 rounded-lg p-4 border border-slate-600"
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-3 flex-1">
              {getStatusIcon(item.status)}
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-100">
                  {item.supplier_name}
                  {item.contract_id && (
                    <span className="text-xs text-slate-400 ml-2">({item.contract_id})</span>
                  )}
                </p>
                <div className="flex items-center space-x-4 mt-1">
                  <span className="text-xs text-slate-400">
                    {getStatusText(item.status, t)}
                  </span>
                  {item.status === 'completed' && (
                    <span className="text-xs text-slate-400">
                      {t('supplier.billsFound')} {item.bills_found}
                    </span>
                  )}
                  {item.status === 'processing' && item.bills_found > 0 && (
                    <span className="text-xs text-slate-400">
                      {t('supplier.billsFound')} {item.bills_found} {t('bill.bills')}
                    </span>
                  )}
                </div>
                {item.properties_affected && item.properties_affected.length > 0 && (
                  <p className="text-xs text-slate-400 mt-1">
                    {t('supplier.properties')}: {item.properties_affected.length}
                  </p>
                )}
                {item.error && (
                  <div className="mt-2 flex items-start space-x-2">
                    <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-red-400">{item.error}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

