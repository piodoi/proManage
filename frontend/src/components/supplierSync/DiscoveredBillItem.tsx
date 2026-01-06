import { Checkbox } from '@/components/ui/checkbox';
import { formatDate, formatAmount } from '../../utils/supplierSyncUtils';
import { useI18n } from '../../lib/i18n';
import { usePreferences } from '../../hooks/usePreferences';

export type DiscoveredBill = {
  id: string;
  supplier_name: string;
  bill_number?: string;
  amount: number;
  due_date: string;
  iban?: string;
  contract_id?: string;
  description: string;
  property_id?: string;
  property_name?: string;
  bill_data?: any;
  source?: string; // 'email' for email bills
  supplier?: string; // Supplier name from pattern
  email_id?: string; // Email ID for marking as read
};

type DiscoveredBillItemProps = {
  bill: DiscoveredBill;
  selected: boolean;
  onToggle: (billId: string) => void;
};

export default function DiscoveredBillItem({ bill, selected, onToggle }: DiscoveredBillItemProps) {
  const { t, language } = useI18n();
  const { preferences } = usePreferences();

  return (
    <div className="flex items-start space-x-3 p-3 bg-slate-700 rounded-lg border border-slate-600">
      <Checkbox
        checked={selected}
        onCheckedChange={() => onToggle(bill.id)}
        className="mt-1"
      />
      <div className="flex-1">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-100">
              <span className="font-bold">{bill.description || bill.supplier_name}</span>
              {bill.property_name && (
                <span className="text-slate-300 ml-2">- {bill.property_name}</span>
              )}
            </p>
          </div>
          <p className="text-sm font-semibold text-slate-100">
            {formatAmount(bill.amount)}
          </p>
        </div>
        <div className="flex items-center space-x-4 mt-1 text-xs text-slate-400">
          {bill.bill_number && (
            <span>{t('bill.billNumber')}: {bill.bill_number}</span>
          )}
          <span>{t('bill.dueDate')}: {formatDate(bill.due_date, preferences.date_format, language)}</span>
          {bill.contract_id && (
            <span>{t('supplier.contractId')}: {bill.contract_id}</span>
          )}
        </div>
      </div>
    </div>
  );
}

