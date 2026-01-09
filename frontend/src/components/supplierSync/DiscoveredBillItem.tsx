import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { formatDate, formatAmount } from '../../utils/supplierSyncUtils';
import { useI18n } from '../../lib/i18n';
import { usePreferences } from '../../hooks/usePreferences';
import { Property } from '../../api';

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
  address_confidence?: number; // Confidence score for property match (0-100)
  match_reason?: string; // Reason for property match
  bill_data?: any;
  source?: string; // 'email' for email bills
  supplier?: string; // Supplier name from pattern
  email_id?: string; // Email ID for marking as read
};

type DiscoveredBillItemProps = {
  bill: DiscoveredBill;
  selected: boolean;
  onToggle: (billId: string) => void;
  properties?: Property[];
  onPropertyChange?: (billId: string, propertyId: string) => void;
};

export default function DiscoveredBillItem({ bill, selected, onToggle, properties, onPropertyChange }: DiscoveredBillItemProps) {
  const { t, language } = useI18n();
  const { preferences } = usePreferences();

  // Show property selector if:
  // 1. No property matched (property_id is null)
  // 2. Property matched but confidence < 100%
  const confidence = bill.address_confidence ?? 100; // Default to 100 if not provided
  const needsPropertySelection = properties && properties.length > 0 && (
    !bill.property_id || confidence < 100
  );

  return (
    <div className="flex items-start space-x-3 p-3 bg-slate-700 rounded-lg border border-slate-600">
      <Checkbox
        checked={selected}
        onCheckedChange={() => onToggle(bill.id)}
        className="mt-1"
      />
      <div className="flex-1 space-y-2">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-100">
              <span className="font-bold">{bill.description || bill.supplier_name}</span>
              {bill.property_name && (
                <span className="text-slate-300 ml-2">- {bill.property_name}</span>
              )}
              {needsPropertySelection && !bill.property_id && (
                <span className="text-amber-400 ml-2">⚠️ {t('bill.selectProperty')}</span>
              )}
            </p>
          </div>
          <p className="text-sm font-semibold text-slate-100">
            {formatAmount(bill.amount)}
          </p>
        </div>
        <div className="flex items-center space-x-4 text-xs text-slate-400">
          {bill.bill_number && (
            <span>{t('bill.billNumber')}: {bill.bill_number}</span>
          )}
          <span>{t('bill.dueDate')}: {formatDate(bill.due_date, preferences.date_format, language)}</span>
          {bill.contract_id && (
            <span>{t('supplier.contractId')}: {bill.contract_id}</span>
          )}
        </div>
        {needsPropertySelection && onPropertyChange && (
          <div className="pt-2">
            <Label className="text-xs text-slate-300 mb-1 block">
              {bill.property_id && confidence < 100 ? (
                <>
                  {t('bill.confirmProperty')}: <span className="text-yellow-400">({confidence}% {t('bill.confidence').toLowerCase()})</span>
                </>
              ) : (
                <span>{t('property.selectProperty')}:</span>
              )}
            </Label>
            <Select
              value={bill.property_id || ''}
              onValueChange={(value) => onPropertyChange(bill.id, value)}
            >
              <SelectTrigger className="bg-slate-600 border-slate-500 text-slate-100 h-8 text-xs">
                <SelectValue placeholder={t('property.selectProperty')} />
              </SelectTrigger>
              <SelectContent className="bg-slate-700 border-slate-600">
                {properties.map((property) => (
                  <SelectItem key={property.id} value={property.id} className="text-xs">
                    {property.name} - {property.address}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>
    </div>
  );
}

