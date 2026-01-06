import { useState, useEffect, useMemo, useCallback } from 'react';
import { api, Property, Renter, Bill } from '../api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useI18n } from '../lib/i18n';
import { useAuth } from '../App';
import { usePreferences } from '../hooks/usePreferences';
import { formatDateWithPreferences } from '../lib/utils';
import { useExchangeRates } from '../hooks/useExchangeRates';
import { convertCurrency } from '../utils/currency';

export default function SummaryView() {
  const { t, language } = useI18n();
  const { token } = useAuth();
  const { preferences } = usePreferences();
  const rentWarningDays = preferences.rent_warning_days || 5;
  const rentCurrency = preferences.rent_currency || 'EUR';
  const billCurrency = preferences.bill_currency || 'RON';
  const [properties, setProperties] = useState<Property[]>([]);
  const [renters, setRenters] = useState<Record<string, Renter[]>>({});
  const [bills, setBills] = useState<Bill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { exchangeRates } = useExchangeRates();

  useEffect(() => {
    if (token) {
      loadData();
    }
  }, [token]);

  const loadData = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [propsData, billsData] = await Promise.all([
        api.properties.list(token),
        api.bills.list(token),
      ]);

      setProperties(propsData);
      setBills(billsData);

      const rentersMap: Record<string, Renter[]> = {};
      for (const prop of propsData) {
        const rentersData = await api.renters.list(token, prop.id);
        rentersMap[prop.id] = rentersData;
      }
      setRenters(rentersMap);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const summaryData = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    // Group properties by whether they have renters
    const propertiesWithRenters: Array<{
      property: Property;
      renters: Renter[];
      billsDue: Bill[];
      overdueBills: Bill[];
      rentBillsDueSoon: Bill[];
      totalBillsDue: number;
      totalRentDue: number;
      totalRentOverdue: number;
      totalOtherBillsDue: number;
      totalOverdue: number;
      totalRentDueSoon: number;
      billsForDescription: Bill[];
      hasMoreBills: boolean;
      suppliers: Set<string>;
    }> = [];
    
    const propertiesWithoutRenters: Array<{
      property: Property;
      billsDue: Bill[];
      overdueBills: Bill[];
      rentBillsDueSoon: Bill[];
      totalBillsDue: number;
      totalRentDue: number;
      totalRentOverdue: number;
      totalOtherBillsDue: number;
      totalOverdue: number;
      totalRentDueSoon: number;
      billsForDescription: Bill[];
      hasMoreBills: boolean;
      suppliers: Set<string>;
    }> = [];

    properties.forEach(property => {
      const propertyRenters = renters[property.id] || [];
      const propertyBills = bills.filter(b => b.property_id === property.id);
      
      // Calculate bills due (pending bills with due_date >= today) - EXCLUDE RENT BILLS
      const billsDue = propertyBills.filter(b => {
        if (b.status === 'paid') return false; // Exclude paid bills
        if (b.status !== 'pending') return false;
        if (b.bill_type === 'rent') return false; // Exclude rent bills
        const billDate = new Date(b.due_date);
        billDate.setHours(0, 0, 0, 0);
        return billDate >= today;
      });
      
      // Calculate overdue bills (pending or overdue status with due_date < today) - EXCLUDE RENT BILLS
      const overdueBills = propertyBills.filter(b => {
        if (b.status === 'paid') return false; // Exclude paid bills
        if (b.bill_type === 'rent') return false; // Exclude rent bills
        if (b.status !== 'pending' && b.status !== 'overdue') return false;
        const billDate = new Date(b.due_date);
        billDate.setHours(0, 0, 0, 0);
        return billDate < today;
      });
      
      // Calculate rent bills due within configured warning days (0-N days from today)
      // Include overdue bills as well (they're already past due)
      const rentBillsDueSoon = propertyBills.filter(b => {
        if (b.bill_type !== 'rent') return false;
        if (b.status === 'paid') return false; // Exclude paid bills
        if (b.status !== 'pending' && b.status !== 'overdue') return false;
        const billDate = new Date(b.due_date);
        billDate.setHours(0, 0, 0, 0);
        const daysUntilDue = Math.ceil((billDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
        // Include bills that are overdue (negative days) or due within warning days (0 to N days)
        return daysUntilDue <= rentWarningDays;
      });
      
      // Get first 4 bills for description
      const billsForDescription = billsDue.slice(0, 4);
      const hasMoreBills = billsDue.length > 4;
      
      // Extract supplier names from non-rent bills (from description or bill_type)
      const suppliers = new Set<string>();
      [...billsDue, ...overdueBills].forEach(bill => {
        if (bill.bill_type === 'ebloc') {
          suppliers.add('E-bloc');
        } else if (bill.bill_type === 'utilities') {
          // Try to extract supplier name from description
          const desc = bill.description || '';
          // Common patterns: "Hidroelectrica", "Enel", etc.
          const supplierMatch = desc.match(/^([A-Za-z\s]+?)(?:\s|$)/);
          if (supplierMatch) {
            suppliers.add(supplierMatch[1].trim());
          } else {
            suppliers.add('Utilities');
          }
        } else if (bill.bill_type === 'other') {
          const desc = bill.description || '';
          const supplierMatch = desc.match(/^([A-Za-z\s]+?)(?:\s|$)/);
          if (supplierMatch) {
            suppliers.add(supplierMatch[1].trim());
          } else {
            suppliers.add('Other');
          }
        }
      });
      
      // Calculate totals - separate rent bills from other bills
      // Convert all amounts to preferred bill currency for accurate totals
      // Rent bills due: all pending or overdue rent bills (not paid)
      const rentBillsDue = propertyBills.filter(b => {
        if (b.bill_type !== 'rent') return false;
        if (b.status === 'paid') return false; // Exclude paid bills
        // Include all pending and overdue rent bills
        return b.status === 'pending' || b.status === 'overdue';
      });
      // Rent bills overdue: rent bills with due_date < today (past due)
      const rentBillsOverdue = propertyBills.filter(b => {
        if (b.bill_type !== 'rent') return false;
        if (b.status === 'paid') return false; // Exclude paid bills
        if (b.status !== 'overdue') return false;
        const billDate = new Date(b.due_date);
        billDate.setHours(0, 0, 0, 0);
        return billDate < today;
      });
      const totalRentDue = rentBillsDue.reduce((sum, b) => {
        const billCurrencyValue = b.currency || 'RON';
        return sum + convertCurrency(b.amount, billCurrencyValue, billCurrency, exchangeRates);
      }, 0);
      const totalRentOverdue = rentBillsOverdue.reduce((sum, b) => {
        const billCurrencyValue = b.currency || 'RON';
        return sum + convertCurrency(b.amount, billCurrencyValue, billCurrency, exchangeRates);
      }, 0);
      const totalOtherBillsDue = billsDue.reduce((sum, b) => {
        const billCurrencyValue = b.currency || 'RON';
        return sum + convertCurrency(b.amount, billCurrencyValue, billCurrency, exchangeRates);
      }, 0);
      const totalBillsDue = totalRentDue + totalOtherBillsDue; // For property display
      const totalOverdue = overdueBills.reduce((sum, b) => {
        const billCurrencyValue = b.currency || 'RON';
        return sum + convertCurrency(b.amount, billCurrencyValue, billCurrency, exchangeRates);
      }, 0);
      const totalRentDueSoon = rentBillsDueSoon.reduce((sum, b) => {
        const billCurrencyValue = b.currency || 'RON';
        return sum + convertCurrency(b.amount, billCurrencyValue, billCurrency, exchangeRates);
      }, 0);
      
      const propertyData = {
        property,
        billsDue,
        overdueBills,
        rentBillsDueSoon,
        billsForDescription,
        hasMoreBills,
        totalBillsDue,
        totalRentDue,
        totalRentOverdue,
        totalOtherBillsDue,
        totalOverdue,
        totalRentDueSoon,
        suppliers,
      };

      if (propertyRenters.length > 0) {
        propertiesWithRenters.push({
          ...propertyData,
          renters: propertyRenters,
        });
      } else {
        propertiesWithoutRenters.push(propertyData);
      }
    });

    // Calculate overall totals - grouped by properties with/without renters
    const totalsWithRenters = {
      totalBillsDue: propertiesWithRenters.reduce((sum, p) => sum + p.totalBillsDue, 0),
      totalRentDue: propertiesWithRenters.reduce((sum, p) => sum + p.totalRentDue, 0),
      totalRentOverdue: propertiesWithRenters.reduce((sum, p) => sum + p.totalRentOverdue, 0),
      totalOtherBillsDue: propertiesWithRenters.reduce((sum, p) => sum + p.totalOtherBillsDue, 0),
      totalOverdue: propertiesWithRenters.reduce((sum, p) => sum + p.totalOverdue, 0),
      totalRentDueSoon: propertiesWithRenters.reduce((sum, p) => sum + p.totalRentDueSoon, 0),
      suppliers: new Set<string>(),
    };
    propertiesWithRenters.forEach(p => {
      p.suppliers.forEach(s => totalsWithRenters.suppliers.add(s));
    });
    
    const totalsWithoutRenters = {
      totalBillsDue: propertiesWithoutRenters.reduce((sum, p) => sum + p.totalBillsDue, 0),
      totalRentDue: propertiesWithoutRenters.reduce((sum, p) => sum + p.totalRentDue, 0),
      totalRentOverdue: propertiesWithoutRenters.reduce((sum, p) => sum + p.totalRentOverdue, 0),
      totalOtherBillsDue: propertiesWithoutRenters.reduce((sum, p) => sum + p.totalOtherBillsDue, 0),
      totalOverdue: propertiesWithoutRenters.reduce((sum, p) => sum + p.totalOverdue, 0),
      totalRentDueSoon: propertiesWithoutRenters.reduce((sum, p) => sum + p.totalRentDueSoon, 0),
      suppliers: new Set<string>(),
    };
    propertiesWithoutRenters.forEach(p => {
      p.suppliers.forEach(s => totalsWithoutRenters.suppliers.add(s));
    });

    // Combine all properties for display (no separation)
    // Use totalOtherBillsDue instead of totalBillsDue to exclude rent
    const allProperties = [
      ...propertiesWithRenters.map(p => ({ ...p, hasRenters: true, totalBillsDue: p.totalOtherBillsDue })),
      ...propertiesWithoutRenters.map(p => ({ ...p, hasRenters: false, totalBillsDue: p.totalOtherBillsDue }))
    ];

    return {
      allProperties,
      propertiesWithRenters,
      propertiesWithoutRenters,
      totalsWithRenters,
      totalsWithoutRenters,
      overallBillsDue: totalsWithRenters.totalOtherBillsDue + totalsWithoutRenters.totalOtherBillsDue, // Only non-rent bills
      overallOverdue: totalsWithRenters.totalOverdue + totalsWithoutRenters.totalOverdue,
      overallRentDue: totalsWithRenters.totalRentDue + totalsWithoutRenters.totalRentDue,
      overallRentOverdue: totalsWithRenters.totalRentOverdue + totalsWithoutRenters.totalRentOverdue,
      overallRentDueSoon: totalsWithRenters.totalRentDueSoon + totalsWithoutRenters.totalRentDueSoon,
    };
  }, [properties, renters, bills, rentWarningDays, billCurrency, exchangeRates]);

  const formatAmount = (amount: number, currency: string = billCurrency) => {
    return new Intl.NumberFormat('ro-RO', {
      style: 'currency',
      currency: currency,
    }).format(amount);
  };

  // Format bill amount in preferred bill currency
  const formatBillAmount = (bill: Bill) => {
    const billCurrencyValue = bill.currency || 'RON';
    const convertedAmount = convertCurrency(bill.amount, billCurrencyValue, billCurrency, exchangeRates);
    
    // If bill is already in preferred currency, just show it
    if (billCurrencyValue.toUpperCase() === billCurrency.toUpperCase()) {
      return formatAmount(convertedAmount, billCurrency);
    }
    
    // Otherwise show converted amount in preferred currency, with original in parentheses
    return (
      <span>
        {formatAmount(convertedAmount, billCurrency)} ({formatAmount(bill.amount, billCurrencyValue)})
      </span>
    );
  };

  const formatRentAmount = (bill: Bill | number, sourceCurrency?: string) => {
    // Handle both Bill object and number (for backwards compatibility)
    let amount: number;
    let billCurrencyValue: string;
    
    if (typeof bill === 'number') {
      // If number is passed, use provided sourceCurrency or default to RON
      amount = bill;
      billCurrencyValue = sourceCurrency || 'RON';
    } else {
      // New: use bill's currency
      amount = bill.amount;
      billCurrencyValue = bill.currency || 'RON';
    }
    
    // Convert bill amount to RON first (if needed)
    const amountInRON = convertCurrency(amount, billCurrencyValue, 'RON', exchangeRates);
    
    const rentCurrencyUpper = rentCurrency.toUpperCase();
    
    // If preferred currency is RON, show only RON
    if (rentCurrencyUpper === 'RON') {
      return formatAmount(amountInRON, 'RON');
    }
    
    // Convert RON to preferred currency
    // Exchange rates are relative to EUR: RON = 4.97 means 1 EUR = 4.97 RON
    // So: amountRON / RON_rate = amount in EUR
    const ronRate = exchangeRates.RON;
    let convertedAmount = 0;
    
    if (rentCurrencyUpper === 'EUR') {
      convertedAmount = amountInRON / ronRate;
    } else if (rentCurrencyUpper === 'USD') {
      const usdRate = exchangeRates.USD; // USD per EUR
      convertedAmount = (amountInRON / ronRate) * usdRate;
    } else {
      // Fallback to RON only
      return formatAmount(amountInRON, 'RON');
    }
    
    // Show preferred currency first, then RON
    return (
      <span>
        {formatAmount(convertedAmount, rentCurrencyUpper)} / {formatAmount(amountInRON, 'RON')}
      </span>
    );
  };


  if (loading) {
    return (
      <div className="text-slate-400 text-center py-8">{t('common.loading')}</div>
    );
  }

  if (error) {
    return (
      <div className="text-red-400 text-center py-8">{error}</div>
    );
  }

  const { allProperties, propertiesWithRenters, propertiesWithoutRenters, totalsWithRenters, totalsWithoutRenters, overallBillsDue, overallOverdue, overallRentDue, overallRentOverdue } = summaryData;

  return (
    <div className="space-y-6">
      {/* Overall Summary Header */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100 text-xl">Overview</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-slate-700/50 rounded-lg p-4 border border-slate-600">
              <p className="text-xs text-slate-400 mb-1">{t('summary.billsDue')}</p>
              <p className="text-2xl font-semibold text-slate-100">
                {formatAmount(overallBillsDue, billCurrency)}
              </p>
            </div>
            {overallOverdue > 0 && (
              <div className="bg-red-900/20 rounded-lg p-4 border border-red-700/50">
                <p className="text-xs text-red-400 mb-1">{t('summary.overdue')}</p>
                <p className="text-2xl font-semibold text-red-300">
                  {formatAmount(overallOverdue, billCurrency)}
                </p>
              </div>
            )}
            {overallRentDue > 0 && (
              <div className="bg-yellow-900/20 rounded-lg p-4 border border-yellow-700/50">
                <p className="text-xs text-yellow-400 mb-1">{t('summary.rentsDue')}</p>
                <p className="text-2xl font-semibold text-yellow-300">
                  {formatRentAmount(overallRentDue, billCurrency)}
                </p>
              </div>
            )}
            {overallRentOverdue > 0 && (
              <div className="bg-red-900/20 rounded-lg p-4 border border-red-700/50">
                <p className="text-xs text-red-400 mb-1">{t('summary.rentOverdue')}</p>
                <p className="text-2xl font-semibold text-red-300">
                  {formatRentAmount(overallRentOverdue, billCurrency)}
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Grouped Totals */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Properties with Renters - Totals */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-slate-100 text-lg">
              Properties with Renters - Totals
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="bg-slate-700/50 rounded-lg p-3 border border-slate-600">
              <p className="text-xs text-slate-400 mb-1">{t('summary.billsDue')}</p>
              {(() => {
                // Get all bills due for properties with renters, with property info
                const allBillsDue = propertiesWithRenters.flatMap(p => 
                  p.billsDue.map(bill => ({
                    bill,
                    propertyName: p.property.name
                  }))
                );
                return (
                  <>
                    {allBillsDue.map(({ bill, propertyName }) => {
                      let supplierName = 'Other';
                      if (bill.bill_type === 'ebloc') {
                        supplierName = 'E-bloc';
                      } else if (bill.bill_type === 'utilities') {
                        const desc = bill.description || '';
                        const supplierMatch = desc.match(/^([A-Za-z\s]+?)(?:\s|$)/);
                        if (supplierMatch) {
                          supplierName = supplierMatch[1].trim();
                        } else {
                          supplierName = 'Utilities';
                        }
                      } else if (bill.bill_type === 'other') {
                        const desc = bill.description || '';
                        const supplierMatch = desc.match(/^([A-Za-z\s]+?)(?:\s|$)/);
                        if (supplierMatch) {
                          supplierName = supplierMatch[1].trim();
                        }
                      }
                      return (
                        <div key={bill.id} className="flex justify-between items-center text-xs text-slate-400 mb-1">
                          <span className="truncate mr-2">{supplierName} - {propertyName}</span>
                          <span className="text-slate-300 font-medium text-right flex-shrink-0">{formatBillAmount(bill)}</span>
                        </div>
                      );
                    })}
                    {allBillsDue.length > 0 && (
                        <div className="flex justify-between items-center mt-2 pt-2 border-t border-slate-600">
                        <p className="text-xs text-slate-400 font-medium">{t('summary.total')}</p>
                        <p className="text-xl font-semibold text-slate-100 text-right">
                          {formatAmount(totalsWithRenters.totalOtherBillsDue, billCurrency)}
                        </p>
                      </div>
                    )}
                    {allBillsDue.length === 0 && (
                      <p className="text-xl font-semibold text-slate-100 text-right">
                        {formatAmount(totalsWithRenters.totalOtherBillsDue, billCurrency)}
                      </p>
                    )}
                  </>
                );
              })()}
            </div>
            {totalsWithRenters.totalOverdue > 0 && (
              <div className="bg-red-900/20 rounded-lg p-3 border border-red-700/50">
                <p className="text-xs text-red-400 mb-1">{t('summary.overdue')}</p>
                {(() => {
                  // Get all overdue bills for properties with renters, with property info
                  const allOverdueBills = propertiesWithRenters.flatMap(p => 
                    p.overdueBills.map(bill => ({
                      bill,
                      propertyName: p.property.name
                    }))
                  );
                  return (
                    <>
                      {allOverdueBills.map(({ bill, propertyName }) => {
                        let supplierName = 'Other';
                        if (bill.bill_type === 'ebloc') {
                          supplierName = 'E-bloc';
                        } else if (bill.bill_type === 'utilities') {
                          const desc = bill.description || '';
                          const supplierMatch = desc.match(/^([A-Za-z\s]+?)(?:\s|$)/);
                          if (supplierMatch) {
                            supplierName = supplierMatch[1].trim();
                          } else {
                            supplierName = 'Utilities';
                          }
                        } else if (bill.bill_type === 'other') {
                          const desc = bill.description || '';
                          const supplierMatch = desc.match(/^([A-Za-z\s]+?)(?:\s|$)/);
                          if (supplierMatch) {
                            supplierName = supplierMatch[1].trim();
                          }
                        }
                        return (
                          <div key={bill.id} className="flex justify-between items-center text-xs text-slate-400 mb-1">
                            <span className="truncate mr-2">{supplierName} - {propertyName}</span>
                            <span className="text-red-300 font-medium text-right flex-shrink-0">{formatBillAmount(bill)}</span>
                          </div>
                        );
                      })}
                      {allOverdueBills.length > 0 && (
                        <div className="flex justify-between items-center mt-2 pt-2 border-t border-red-700/50">
                          <p className="text-xs text-red-400 font-medium">{t('summary.total')}</p>
                          <p className="text-xl font-semibold text-red-300 text-right">
                            {formatAmount(totalsWithRenters.totalOverdue, billCurrency)}
                          </p>
                        </div>
                      )}
                      {allOverdueBills.length === 0 && (
                        <p className="text-xl font-semibold text-red-300 text-right">
                          {formatAmount(totalsWithRenters.totalOverdue, billCurrency)}
                        </p>
                      )}
                    </>
                  );
                })()}
              </div>
            )}
            {totalsWithRenters.totalRentDueSoon > 0 && (
              <div className="bg-yellow-900/20 rounded-lg p-3 border border-yellow-700/50">
                <p className="text-xs text-yellow-400 mb-1">{t('summary.rentDueSoon')}</p>
                {(() => {
                  // Get all rent bills due soon for properties with renters, with property and renter info
                  const allRentBillsDueSoon = propertiesWithRenters.flatMap(p => 
                    p.rentBillsDueSoon.map(bill => ({
                      bill,
                      propertyName: p.property.name,
                      renterName: (() => {
                        // Find renter for this bill - match by property_id and renter name from bill description if available
                        const propertyRenters = renters[p.property.id] || [];
                        if (bill.description) {
                          // Try to extract renter name from description
                          const descLower = bill.description.toLowerCase();
                          const matchingRenter = propertyRenters.find(r => 
                            descLower.includes(r.name.toLowerCase())
                          );
                          if (matchingRenter) return matchingRenter.name;
                        }
                        // If multiple renters, show first one, otherwise empty
                        return propertyRenters.length === 1 ? propertyRenters[0].name : '';
                      })()
                    }))
                  );
                  return (
                    <>
                      {allRentBillsDueSoon.map(({ bill, renterName }) => (
                        <div key={bill.id} className="flex justify-between items-center text-xs text-slate-400 mb-1">
                          <span className="truncate mr-2">
                            {renterName && `${renterName} - `}
                            {formatDateWithPreferences(bill.due_date, preferences.date_format, language)}
                          </span>
                          <span className="text-slate-300 font-medium text-right flex-shrink-0">{formatRentAmount(bill)}</span>
                        </div>
                      ))}
                      {allRentBillsDueSoon.length > 0 && (
                        <div className="flex justify-between items-center mt-2 pt-2 border-t border-yellow-700/50">
                          <p className="text-xs text-yellow-400 font-medium">{t('summary.total')}</p>
                          <p className="text-xl font-semibold text-yellow-300 text-right">
                            {formatRentAmount(totalsWithRenters.totalRentDueSoon, billCurrency)}
                          </p>
                        </div>
                      )}
                      {allRentBillsDueSoon.length === 0 && (
                        <p className="text-xl font-semibold text-yellow-300 text-right">
                          {formatRentAmount(totalsWithRenters.totalRentDueSoon, billCurrency)}
                        </p>
                      )}
                    </>
                  );
                })()}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Properties without Renters - Totals */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-slate-100 text-lg">
              Properties without Renters - Totals
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="bg-slate-700/50 rounded-lg p-3 border border-slate-600">
              <p className="text-xs text-slate-400 mb-1">{t('summary.billsDue')}</p>
              {(() => {
                // Get all bills due for properties without renters, with property info
                const allBillsDue = propertiesWithoutRenters.flatMap(p => 
                  p.billsDue.map(bill => ({
                    bill,
                    propertyName: p.property.name
                  }))
                );
                return (
                  <>
                    {allBillsDue.map(({ bill, propertyName }) => {
                      let supplierName = 'Other';
                      if (bill.bill_type === 'ebloc') {
                        supplierName = 'E-bloc';
                      } else if (bill.bill_type === 'utilities') {
                        const desc = bill.description || '';
                        const supplierMatch = desc.match(/^([A-Za-z\s]+?)(?:\s|$)/);
                        if (supplierMatch) {
                          supplierName = supplierMatch[1].trim();
                        } else {
                          supplierName = 'Utilities';
                        }
                      } else if (bill.bill_type === 'other') {
                        const desc = bill.description || '';
                        const supplierMatch = desc.match(/^([A-Za-z\s]+?)(?:\s|$)/);
                        if (supplierMatch) {
                          supplierName = supplierMatch[1].trim();
                        }
                      }
                      return (
                        <div key={bill.id} className="flex justify-between items-center text-xs text-slate-400 mb-1">
                          <span className="truncate mr-2">{supplierName} - {propertyName}</span>
                          <span className="text-slate-300 font-medium text-right flex-shrink-0">{formatBillAmount(bill)}</span>
                        </div>
                      );
                    })}
                    {allBillsDue.length > 0 && (
                      <div className="flex justify-between items-center mt-2 pt-2 border-t border-slate-600">
                        <p className="text-xs text-slate-400 font-medium">{t('summary.total')}</p>
                        <p className="text-xl font-semibold text-slate-100 text-right">
                          {formatAmount(totalsWithoutRenters.totalOtherBillsDue, billCurrency)}
                        </p>
                      </div>
                    )}
                    {allBillsDue.length === 0 && (
                      <p className="text-xl font-semibold text-slate-100 text-right">
                        {formatAmount(totalsWithoutRenters.totalOtherBillsDue, billCurrency)}
                      </p>
                    )}
                  </>
                );
              })()}
            </div>
            {totalsWithoutRenters.totalOverdue > 0 && (
              <div className="bg-red-900/20 rounded-lg p-3 border border-red-700/50">
                <p className="text-xs text-red-400 mb-1">{t('summary.overdue')}</p>
                {(() => {
                  // Get all overdue bills for properties without renters, with property info
                  const allOverdueBills = propertiesWithoutRenters.flatMap(p => 
                    p.overdueBills.map(bill => ({
                      bill,
                      propertyName: p.property.name
                    }))
                  );
                  return (
                    <>
                      {allOverdueBills.map(({ bill, propertyName }) => {
                        let supplierName = 'Other';
                        if (bill.bill_type === 'ebloc') {
                          supplierName = 'E-bloc';
                        } else if (bill.bill_type === 'utilities') {
                          const desc = bill.description || '';
                          const supplierMatch = desc.match(/^([A-Za-z\s]+?)(?:\s|$)/);
                          if (supplierMatch) {
                            supplierName = supplierMatch[1].trim();
                          } else {
                            supplierName = 'Utilities';
                          }
                        } else if (bill.bill_type === 'other') {
                          const desc = bill.description || '';
                          const supplierMatch = desc.match(/^([A-Za-z\s]+?)(?:\s|$)/);
                          if (supplierMatch) {
                            supplierName = supplierMatch[1].trim();
                          }
                        }
                        return (
                          <div key={bill.id} className="flex justify-between items-center text-xs text-slate-400 mb-1">
                            <span className="truncate mr-2">{supplierName} - {propertyName}</span>
                            <span className="text-red-300 font-medium text-right flex-shrink-0">{formatBillAmount(bill)}</span>
                          </div>
                        );
                      })}
                      {allOverdueBills.length > 0 && (
                        <div className="flex justify-between items-center mt-2 pt-2 border-t border-red-700/50">
                          <p className="text-xs text-red-400 font-medium">{t('summary.total')}</p>
                          <p className="text-xl font-semibold text-red-300 text-right">
                            {formatAmount(totalsWithoutRenters.totalOverdue, billCurrency)}
                          </p>
                        </div>
                      )}
                      {allOverdueBills.length === 0 && (
                        <p className="text-xl font-semibold text-red-300 text-right">
                          {formatAmount(totalsWithoutRenters.totalOverdue, billCurrency)}
                        </p>
                      )}
                    </>
                  );
                })()}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Compact Property List */}
      {allProperties.length > 0 && (
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-slate-100 text-lg">Properties</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {allProperties.map(({ property, totalBillsDue, totalOverdue, totalRentDueSoon, hasRenters }) => {
                const propertyRenters = renters[property.id] || [];
                return (
                <div key={property.id} className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg border border-slate-600">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-slate-100 truncate">{property.name}</h3>
                    {hasRenters && propertyRenters && propertyRenters.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {propertyRenters.slice(0, 2).map((renter: Renter) => (
                          <span
                            key={renter.id}
                            className="px-1.5 py-0.5 bg-slate-600 text-slate-200 rounded text-xs"
                          >
                            {renter.name}
                          </span>
                        ))}
                        {propertyRenters.length > 2 && (
                          <span className="px-1.5 py-0.5 bg-slate-600 text-slate-400 rounded text-xs">
                            +{propertyRenters.length - 2}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2 ml-3 flex-shrink-0">
                    <div className="text-right">
                      <p className="text-xs text-slate-400">{t('summary.billsDue')}</p>
                      <p className="text-sm font-semibold text-slate-100">{formatAmount(totalBillsDue, billCurrency)}</p>
                    </div>
                    {totalOverdue > 0 && (
                      <div className="text-right">
                        <p className="text-xs text-red-400">{t('summary.overdue')}</p>
                        <p className="text-sm font-semibold text-red-300">{formatAmount(totalOverdue, billCurrency)}</p>
                      </div>
                    )}
                    {totalRentDueSoon > 0 && (
                      <div className="text-right">
                        <p className="text-xs text-yellow-400">{t('summary.rentDueSoon')}</p>
                        <p className="text-sm font-semibold text-yellow-300">{formatRentAmount(totalRentDueSoon, billCurrency)}</p>
                      </div>
                    )}
                  </div>
                </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {properties.length === 0 && (
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="py-8 text-center text-slate-400">
            {t('property.noProperties')}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
