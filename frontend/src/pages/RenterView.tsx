import React, { useState, useEffect, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { api, RenterInfo, RenterBill, RenterBalance, getRenterBillPdfUrl, PaymentNotificationCreate } from '../api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Building2, Receipt, CreditCard, Banknote, ChevronDown, ChevronRight, FileText, Copy, Check, Clock, CheckCircle, XCircle, Send } from 'lucide-react';
import { useI18n } from '../lib/i18n';
import { formatDateWithPreferences } from '../lib/utils';

// Type for available IBAN options
type IbanOption = {
  currency: string;
  iban: string;
  label: string;
};

export default function RenterView() {
  const { token } = useParams<{ token: string }>();
  const { t, language, setLanguage } = useI18n();
  const [info, setInfo] = useState<RenterInfo | null>(null);
  const [bills, setBills] = useState<RenterBill[]>([]);
  const [balance, setBalance] = useState<RenterBalance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [payingBill, setPayingBill] = useState<RenterBill | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [selectedIbanCurrency, setSelectedIbanCurrency] = useState<string | null>(null);
  const [notifyingPayment, setNotifyingPayment] = useState(false);
  const [paymentNote, setPaymentNote] = useState('');

  // Toggle group expansion
  const toggleGroup = (groupKey: string) => {
    setExpandedGroups(prev => {
      const newSet = new Set(prev);
      if (newSet.has(groupKey)) {
        newSet.delete(groupKey);
      } else {
        newSet.add(groupKey);
      }
      return newSet;
    });
  };

  // Group bills by bill_type for rent, by description for others
  type BillGroup = {
    groupKey: string;
    latestBill: RenterBill;
    olderBills: RenterBill[];
  };

  const groupedBills = useMemo((): BillGroup[] => {
    // Separate rent bills from other bills
    const rentBills = bills.filter(item => item.bill.bill_type === 'rent');
    const otherBills = bills.filter(item => item.bill.bill_type !== 'rent');

    const groups: BillGroup[] = [];

    // Group all rent bills together
    if (rentBills.length > 0) {
      const sortedRentBills = [...rentBills].sort((a, b) =>
        new Date(b.bill.due_date).getTime() - new Date(a.bill.due_date).getTime()
      );
      groups.push({
        groupKey: 'type-rent',
        latestBill: sortedRentBills[0],
        olderBills: sortedRentBills.slice(1),
      });
    }

    // Group other bills by description (case-insensitive)
    const descriptionBillsMap = new Map<string, RenterBill[]>();
    otherBills.forEach(item => {
      const description = item.bill.description || t('bill.noDescription');
      const key = description.toLowerCase();
      if (!descriptionBillsMap.has(key)) {
        descriptionBillsMap.set(key, []);
      }
      descriptionBillsMap.get(key)!.push(item);
    });

    descriptionBillsMap.forEach((billItems) => {
      const sortedBills = [...billItems].sort((a, b) =>
        new Date(b.bill.due_date).getTime() - new Date(a.bill.due_date).getTime()
      );
      groups.push({
        groupKey: `desc-${sortedBills[0].bill.description || t('bill.noDescription')}`,
        latestBill: sortedBills[0],
        olderBills: sortedBills.slice(1),
      });
    });

    // Sort groups by latest bill due_date descending
    groups.sort((a, b) =>
      new Date(b.latestBill.bill.due_date).getTime() - new Date(a.latestBill.bill.due_date).getTime()
    );

    return groups;
  }, [bills, t]);

  // Default to Romanian for renters
  useEffect(() => {
    const savedLang = localStorage.getItem('language');
    if (!savedLang) {
      setLanguage('ro');
    }
  }, [setLanguage]);

  useEffect(() => {
    if (token) {
      loadData();
    }
  }, [token]);

  const loadData = async () => {
    if (!token) return;
    try {
      const [infoData, billsData, balanceData] = await Promise.all([
        api.renter.info(token),
        api.renter.bills(token),
        api.renter.balance(token),
      ]);
      setInfo(infoData);
      setBills(billsData);
      setBalance(balanceData);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.invalidLink'));
    } finally {
      setLoading(false);
    }
  };

  // Get available IBAN options for rent/direct debit bills
  const getAvailableIbans = (): IbanOption[] => {
    const ibans: IbanOption[] = [];
    
    // RON IBAN (landlord_iban is the RON IBAN)
    if (info?.landlord_iban) {
      ibans.push({ currency: 'RON', iban: info.landlord_iban, label: `RON - ${info.landlord_iban}` });
    }
    // EUR IBAN
    if (info?.landlord_iban_eur) {
      ibans.push({ currency: 'EUR', iban: info.landlord_iban_eur, label: `EUR - ${info.landlord_iban_eur}` });
    }
    // USD IBAN
    if (info?.landlord_iban_usd) {
      ibans.push({ currency: 'USD', iban: info.landlord_iban_usd, label: `USD - ${info.landlord_iban_usd}` });
    }
    
    return ibans;
  };

  // Get the default IBAN currency based on rent_currency preference
  const getDefaultIbanCurrency = (): string | null => {
    const availableIbans = getAvailableIbans();
    if (availableIbans.length === 0) return null;
    
    // Try to use rent_currency preference first
    const rentCurrency = info?.rent_currency || 'EUR';
    const preferredIban = availableIbans.find(i => i.currency === rentCurrency);
    if (preferredIban) return preferredIban.currency;
    
    // Fall back to first available IBAN
    return availableIbans[0].currency;
  };

  const openPayDialog = (bill: RenterBill) => {
    setPayingBill(bill);
    setCopiedField(null);
    setPaymentNote('');
    // Set default IBAN currency when opening dialog
    setSelectedIbanCurrency(getDefaultIbanCurrency());
  };

  // Handle "I made the transfer" button click
  const handleNotifyPayment = async () => {
    if (!payingBill || !token) return;
    
    setNotifyingPayment(true);
    try {
      const data: PaymentNotificationCreate = {
        bill_id: payingBill.bill.id,
        amount: payingBill.remaining,
        currency: payingBill.bill.currency || 'RON',
        renter_note: paymentNote || undefined,
      };
      
      await api.renter.notifyPayment(token, data);
      
      // Reload bills to show updated notification status
      const billsData = await api.renter.bills(token);
      setBills(billsData);
      
      setPayingBill(null);
      setPaymentNote('');
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.generic'));
    } finally {
      setNotifyingPayment(false);
    }
  };

  // Copy to clipboard helper
  const copyToClipboard = async (text: string, fieldName: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(fieldName);
      setTimeout(() => setCopiedField(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // Get the currently selected IBAN
  const getSelectedIban = (): IbanOption | null => {
    const availableIbans = getAvailableIbans();
    if (!selectedIbanCurrency) return availableIbans[0] || null;
    return availableIbans.find(i => i.currency === selectedIbanCurrency) || availableIbans[0] || null;
  };

  // Get payment info for the current bill
  const getPaymentInfo = (bill: RenterBill | null) => {
    if (!bill) return null;
    
    // For rent bills or direct debit bills, use landlord's IBAN and name from preferences
    // (landlord pays direct debit bills, so renter pays landlord)
    if (bill.bill.bill_type === 'rent' || bill.is_direct_debit) {
      const selectedIban = getSelectedIban();
      if (selectedIban && info?.landlord_name) {
        return {
          iban: selectedIban.iban,
          ibanCurrency: selectedIban.currency,
          beneficiary: info.landlord_name,
          reference: bill.bill.contract_id || bill.bill.description,
          reference2: null, // No second reference for rent/direct debit
        };
      }
      return null;
    }
    
    // For other bills, use bill's IBAN and legal_name
    // Reference 1 = contract_id, Reference 2 = payment_details.client_code (if available)
    if (bill.bill.iban && bill.bill.legal_name) {
      const paymentDetails = bill.bill.payment_details as { client_code?: string } | null;
      return {
        iban: bill.bill.iban,
        ibanCurrency: null,
        beneficiary: bill.bill.legal_name,
        reference: bill.bill.contract_id || bill.bill.bill_number || bill.bill.id,
        reference2: paymentDetails?.client_code || null,
      };
    }
    
    return null;
  };

  // Convert amount to a specific currency
  const convertAmount = (amount: number, fromCurrency: string, toCurrency: string): number => {
    if (fromCurrency === toCurrency || !balance?.exchange_rates) return amount;
    
    const fromRate = balance.exchange_rates[fromCurrency as keyof typeof balance.exchange_rates] || 1;
    const toRate = balance.exchange_rates[toCurrency as keyof typeof balance.exchange_rates] || 1;
    
    return amount * toRate / fromRate;
  };

  // Calculate RON amount from foreign currency
  const getAmountInRon = (amount: number, currency: string | undefined) => {
    if (!currency || currency === 'RON' || !balance?.exchange_rates) {
      return null;
    }
    const ronRate = balance.exchange_rates.RON || 4.97;
    const currencyRate = balance.exchange_rates[currency as keyof typeof balance.exchange_rates] || 1;
    return (amount * ronRate / currencyRate).toFixed(2);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-slate-400">{t('common.loading')}</div>
      </div>
    );
  }

  if (error && !info) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <Card className="w-full max-w-md bg-slate-800 border-slate-700">
          <CardContent className="py-8 text-center">
            <p className="text-red-400">{error}</p>
            <p className="text-slate-500 text-sm mt-2">
              {t('renter.portal')}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900">
      <header className="bg-slate-800 border-b border-slate-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Building2 className="w-6 h-6 text-emerald-500" />
            <div>
              <h1 className="text-xl font-semibold text-slate-100">{t('app.title')}</h1>
              <p className="text-sm text-slate-400">{t('renter.portal')}</p>
            </div>
          </div>
          
          {/* Language Selector */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="text-slate-300 hover:text-slate-100 hover:bg-slate-700"
              >
                <img 
                  src={language === 'en' ? '/flags/uk-flag.gif' : '/flags/ro-flag.gif'} 
                  alt={`${language} flag`}
                  className="h-4 w-auto mr-2"
                />
                <span className="text-xs uppercase">{language}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="bg-slate-800 border-slate-700">
              <DropdownMenuItem
                onClick={() => setLanguage('en')}
                className="text-slate-100 hover:bg-slate-700 cursor-pointer flex items-center justify-start"
              >
                <img 
                  src="/flags/uk-flag.gif" 
                  alt="UK flag"
                  className="h-5 w-8 object-cover mr-3 flex-shrink-0"
                />
                <span className="flex-1 text-left">English</span>
                {language === 'en' && <span className="ml-2 text-emerald-400 flex-shrink-0">✓</span>}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => setLanguage('ro')}
                className="text-slate-100 hover:bg-slate-700 cursor-pointer flex items-center justify-start"
              >
                <img 
                  src="/flags/ro-flag.gif" 
                  alt="Romanian flag"
                  className="h-5 w-8 object-cover mr-3 flex-shrink-0"
                />
                <span className="flex-1 text-left">Română</span>
                {language === 'ro' && <span className="ml-2 text-emerald-400 flex-shrink-0">✓</span>}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      <main className="p-6 max-w-4xl mx-auto">
        {error && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded text-red-200">
            {error}
            <button onClick={() => setError('')} className="ml-2 text-red-400 hover:text-red-200">x</button>
          </div>
        )}

        {info && (
          <Card className="bg-slate-800 border-slate-700 mb-6">
            <CardHeader>
              <CardTitle className="text-slate-100">{t('renter.welcome', { name: info.renter.name })}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 text-sm">
                {info.property && (
                  <div>
                    <span className="text-slate-400">{t('renter.property')}</span>
                    <p className="text-slate-200">{info.property.name}</p>
                    <p className="text-slate-400 text-xs">{info.property.address}</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Bills Table */}
        <Card className="bg-slate-800 border-slate-700 mb-6">
          <CardHeader>
            <CardTitle className="text-slate-100 flex items-center gap-2">
              <Receipt className="w-5 h-5" />
              {t('renter.bills')}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {bills.length === 0 ? (
              <div className="p-6 text-center text-slate-400">{t('renter.noBills')}</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="border-slate-700">
                    <TableHead className="text-slate-400">{t('common.description')}</TableHead>
                    <TableHead className="text-slate-400">{t('bill.billType')}</TableHead>
                    <TableHead className="text-slate-400">{t('common.amount')}</TableHead>
                    <TableHead className="text-slate-400">{t('renter.remaining')}</TableHead>
                    <TableHead className="text-slate-400">{t('bill.dueDate')}</TableHead>
                    <TableHead className="text-slate-400">{t('common.status')}</TableHead>
                    <TableHead className="text-slate-400">{t('common.actions')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {groupedBills.map((group) => {
                    const isExpanded = expandedGroups.has(group.groupKey);
                    const hasOlderBills = group.olderBills.length > 0;
                    // Check if all older bills are paid
                    const allOlderBillsPaid = group.olderBills.every(item => item.bill.status === 'paid');

                    // Render function for a single bill row
                    const renderBillRow = (item: RenterBill, isGroupHeader: boolean = false) => (
                      <TableRow key={item.bill.id} className={`border-slate-700 ${!isGroupHeader ? 'bg-slate-900/50' : ''}`}>
                        <TableCell className="text-slate-200">
                          <div className={`flex items-center gap-1 ${!isGroupHeader ? 'pl-6' : ''}`}>
                            {isGroupHeader && hasOlderBills && (
                              <button
                                onClick={() => toggleGroup(group.groupKey)}
                                className="p-0.5 hover:bg-slate-700 rounded transition-colors"
                                title={isExpanded ? t('common.collapse') : t('common.expand')}
                              >
                                {isExpanded ? (
                                  <ChevronDown className="w-4 h-4 text-slate-400" />
                                ) : (
                                  <ChevronRight className="w-4 h-4 text-slate-400" />
                                )}
                              </button>
                            )}
                            {isGroupHeader && hasOlderBills && !isExpanded && (
                              <span className={`text-xs font-medium mr-1 ${allOlderBillsPaid ? 'text-emerald-400' : 'text-red-400'}`}>
                                +{group.olderBills.length}
                              </span>
                            )}
                            {item.bill.description}
                          </div>
                        </TableCell>
                        <TableCell className="text-slate-300">{t(`bill.${item.bill.bill_type}`)}</TableCell>
                        <TableCell className="text-slate-200">
                          {item.bill.currency && item.bill.currency !== 'RON' ? (
                            <div>
                              <div>{item.bill.amount.toFixed(2)} {item.bill.currency}</div>
                              {balance?.exchange_rates && (
                                <div className="text-xs text-slate-400">
                                  {(item.bill.amount * (balance.exchange_rates.RON || 4.97) / (balance.exchange_rates[item.bill.currency as keyof typeof balance.exchange_rates] || 1)).toFixed(2)} RON
                                </div>
                              )}
                            </div>
                          ) : (
                            <span>{item.bill.amount.toFixed(2)} RON</span>
                          )}
                        </TableCell>
                        <TableCell className={item.bill.status === 'paid' ? 'text-green-400' : item.remaining > 0 ? 'text-amber-400' : 'text-green-400'}>
                          {item.bill.status === 'paid' ? (
                            '0.00'
                          ) : item.bill.currency && item.bill.currency !== 'RON' ? (
                            <div>
                              <div>{item.remaining.toFixed(2)} {item.bill.currency}</div>
                              {balance?.exchange_rates && (
                                <div className="text-xs text-slate-400">
                                  {(item.remaining * (balance.exchange_rates.RON || 4.97) / (balance.exchange_rates[item.bill.currency as keyof typeof balance.exchange_rates] || 1)).toFixed(2)} RON
                                </div>
                              )}
                            </div>
                          ) : (
                            <span>{item.remaining.toFixed(2)} RON</span>
                          )}
                        </TableCell>
                        <TableCell className="text-slate-300">
                          {formatDateWithPreferences(item.bill.due_date, info?.date_format || 'DD/MM/YYYY', language)}
                        </TableCell>
                        <TableCell>
                          <span className={`px-2 py-1 rounded text-xs ${
                            item.bill.status === 'paid' ? 'bg-green-900 text-green-200' :
                            item.bill.status === 'overdue' ? 'bg-red-900 text-red-200' :
                            'bg-amber-900 text-amber-200'
                          }`}>
                            {t(`bill.status.${item.bill.status}`)}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {item.bill.status !== 'paid' && (
                              <>
                                <Button
                                  size="sm"
                                  onClick={() => openPayDialog(item)}
                                  className="bg-emerald-600 hover:bg-emerald-700"
                                >
                                  {t('renter.pay')}
                                </Button>
                                {item.is_direct_debit && (
                                  <span className="px-2 py-1 rounded text-xs bg-blue-900 text-blue-200 whitespace-nowrap">
                                    {t('bill.directDebit')}
                                  </span>
                                )}
                              </>
                            )}
                            {item.has_pdf && token && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => window.open(getRenterBillPdfUrl(token, item.bill.id), '_blank')}
                                className="border-slate-600 text-blue-400 hover:bg-slate-700 hover:text-blue-300 h-8 w-8 p-0"
                                title={t('renter.downloadPdf') || 'Download PDF'}
                              >
                                <FileText className="w-4 h-4" />
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );

                    return (
                      <React.Fragment key={group.groupKey}>
                        {/* Latest bill (group header) */}
                        {renderBillRow(group.latestBill, true)}
                        {/* Older bills (expanded) */}
                        {isExpanded && group.olderBills.map(item => renderBillRow(item, false))}
                      </React.Fragment>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Balance Cards */}
        {balance && (() => {
          // Filter bills for current month
          const now = new Date();
          const currentMonth = now.getMonth();
          const currentYear = now.getFullYear();
          const thisMonthBills = bills.filter(b => {
            const dueDate = new Date(b.bill.due_date);
            return dueDate.getMonth() === currentMonth && dueDate.getFullYear() === currentYear;
          });

          return (
          <div className="grid grid-cols-3 gap-4 mb-6">
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="pt-6">
                <p className="text-slate-400 text-sm">{t('renter.totalThisMonth') || 'Total This Month'}</p>
                <p className="text-2xl font-bold text-slate-100">
                  {thisMonthBills
                    .reduce((sum, b) => {
                      const ronValue = balance.exchange_rates && b.bill.currency && b.bill.currency !== 'RON'
                        ? (b.bill.amount * (balance.exchange_rates.RON || 4.97) / (balance.exchange_rates[b.bill.currency as keyof typeof balance.exchange_rates] || 1))
                        : b.bill.amount;
                      return sum + ronValue;
                    }, 0)
                    .toFixed(2)} RON
                </p>
              </CardContent>
            </Card>
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="pt-6">
                <p className="text-slate-400 text-sm">{t('renter.totalPaid')}</p>
                <p className="text-2xl font-bold text-green-400">
                  {thisMonthBills
                    .filter(b => b.bill.status === 'paid')
                    .reduce((sum, b) => {
                      const ronValue = balance.exchange_rates && b.bill.currency && b.bill.currency !== 'RON'
                        ? (b.bill.amount * (balance.exchange_rates.RON || 4.97) / (balance.exchange_rates[b.bill.currency as keyof typeof balance.exchange_rates] || 1))
                        : b.bill.amount;
                      return sum + ronValue;
                    }, 0)
                    .toFixed(2)} RON
                </p>
              </CardContent>
            </Card>
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="pt-6">
                <p className="text-slate-400 text-sm mb-3">{t('renter.balance')}</p>
                
                {/* Bills breakdown inside balance card - all unpaid bills */}
                {bills.filter(b => b.bill.status !== 'paid').length > 0 && (
                  <div className="mb-3 space-y-0.5 text-xs">
                    {bills.filter(b => b.bill.status !== 'paid').map((item) => (
                      <div key={item.bill.id} className="flex justify-between items-center text-slate-400">
                        <span className="truncate mr-2">{item.bill.description}</span>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          {item.bill.currency && item.bill.currency !== 'RON' && (
                            <span className="whitespace-nowrap">{item.bill.amount.toFixed(2)} {item.bill.currency} /</span>
                          )}
                          <span className="tabular-nums text-right min-w-[60px]">
                            {balance.exchange_rates && item.bill.currency && item.bill.currency !== 'RON' 
                              ? (item.bill.amount * (balance.exchange_rates.RON || 4.97) / (balance.exchange_rates[item.bill.currency as keyof typeof balance.exchange_rates] || 1)).toFixed(2)
                              : item.bill.amount.toFixed(2)
                            }
                          </span>
                          <span className="w-8 text-left">RON</span>
                        </div>
                      </div>
                    ))}
                    <div className="border-t border-slate-700 mt-1 pt-1"></div>
                  </div>
                )}
                
                <div className="flex justify-end items-baseline gap-1">
                  <p className={`text-2xl font-bold tabular-nums ${
                    bills.filter(b => b.bill.status !== 'paid').reduce((sum, b) => {
                      const ronValue = balance.exchange_rates && b.bill.currency && b.bill.currency !== 'RON'
                        ? (b.bill.amount * (balance.exchange_rates.RON || 4.97) / (balance.exchange_rates[b.bill.currency as keyof typeof balance.exchange_rates] || 1))
                        : b.bill.amount;
                      return sum + ronValue;
                    }, 0) > 0 ? 'text-amber-400' : 'text-green-400'
                  }`}>
                    {bills
                      .filter(b => b.bill.status !== 'paid')
                      .reduce((sum, b) => {
                        const ronValue = balance.exchange_rates && b.bill.currency && b.bill.currency !== 'RON'
                          ? (b.bill.amount * (balance.exchange_rates.RON || 4.97) / (balance.exchange_rates[b.bill.currency as keyof typeof balance.exchange_rates] || 1))
                          : b.bill.amount;
                        return sum + ronValue;
                      }, 0)
                      .toFixed(2)}
                  </p>
                  <p className={`text-lg font-medium ${
                    bills.filter(b => b.bill.status !== 'paid').reduce((sum, b) => sum + b.bill.amount, 0) > 0 ? 'text-amber-400' : 'text-green-400'
                  }`}>
                    RON
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
          );
        })()}

        <Dialog open={!!payingBill} onOpenChange={(open) => !open && setPayingBill(null)}>
          <DialogContent className="bg-slate-800 border-slate-700 max-w-md">
            <DialogHeader>
              <DialogTitle className="text-slate-100">{t('renter.payBill')}</DialogTitle>
              <DialogDescription className="text-slate-400 sr-only">
                {t('renter.payBill')}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <p className="text-slate-300 font-medium">{payingBill?.bill.description}</p>
                <p className="text-slate-400 text-sm mt-1">
                  {t('common.amount')}: {payingBill?.bill.amount.toFixed(2)} {payingBill?.bill.currency || 'RON'}
                </p>
              </div>

              {/* Bank Transfer Details */}
              {(() => {
                const paymentInfo = getPaymentInfo(payingBill);
                const availableIbans = getAvailableIbans();
                const isRentOrDirectDebit = payingBill?.bill.bill_type === 'rent' || payingBill?.is_direct_debit;
                const showIbanSelector = isRentOrDirectDebit && availableIbans.length > 1;
                
                if (paymentInfo) {
                  // Get the bill's original currency
                  const billCurrency = payingBill?.bill.currency || 'RON';
                  const remaining = payingBill?.remaining || 0;
                  
                  return (
                    <div className="bg-slate-900 border border-slate-700 rounded-lg p-4 space-y-3">
                      <div className="flex items-center gap-2 mb-2">
                        <Banknote className="w-5 h-5 text-emerald-400" />
                        <p className="text-slate-200 font-medium">{t('renter.bankTransfer') || 'Bank Transfer'}</p>
                      </div>
                      
                      {/* Beneficiary */}
                      <div className="space-y-1">
                        <p className="text-slate-500 text-xs uppercase">{t('renter.beneficiary') || 'Beneficiary'}</p>
                        <div className="flex items-center justify-between bg-slate-800 rounded px-3 py-2">
                          <span className="text-slate-200 font-mono text-sm">{paymentInfo.beneficiary}</span>
                          <button
                            onClick={() => copyToClipboard(paymentInfo.beneficiary, 'beneficiary')}
                            className="text-slate-400 hover:text-slate-200 transition-colors p-1"
                            title={t('common.copy') || 'Copy'}
                          >
                            {copiedField === 'beneficiary' ? (
                              <Check className="w-4 h-4 text-emerald-400" />
                            ) : (
                              <Copy className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </div>
                      
                      {/* IBAN - with dropdown if multiple available */}
                      <div className="space-y-1">
                        <p className="text-slate-500 text-xs uppercase">
                          IBAN {paymentInfo.ibanCurrency && `(${paymentInfo.ibanCurrency})`}
                        </p>
                        {showIbanSelector ? (
                          <div className="space-y-2">
                            <Select
                              value={selectedIbanCurrency || ''}
                              onValueChange={(value) => setSelectedIbanCurrency(value)}
                            >
                              <SelectTrigger className="bg-slate-800 border-slate-600 text-slate-200">
                                <SelectValue placeholder={t('renter.selectIban') || 'Select IBAN'} />
                              </SelectTrigger>
                              <SelectContent className="bg-slate-800 border-slate-600">
                                {availableIbans.map((ibanOption) => (
                                  <SelectItem
                                    key={ibanOption.currency}
                                    value={ibanOption.currency}
                                    className="text-slate-200 hover:bg-slate-700"
                                  >
                                    <span className="font-semibold text-emerald-400">{ibanOption.currency}</span>
                                    <span className="ml-2 font-mono text-xs">{ibanOption.iban}</span>
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            <div className="flex items-center justify-between bg-slate-800 rounded px-3 py-2">
                              <span className="text-slate-200 font-mono text-sm tracking-wider">{paymentInfo.iban}</span>
                              <button
                                onClick={() => copyToClipboard(paymentInfo.iban, 'iban')}
                                className="text-slate-400 hover:text-slate-200 transition-colors p-1"
                                title={t('common.copy') || 'Copy'}
                              >
                                {copiedField === 'iban' ? (
                                  <Check className="w-4 h-4 text-emerald-400" />
                                ) : (
                                  <Copy className="w-4 h-4" />
                                )}
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="flex items-center justify-between bg-slate-800 rounded px-3 py-2">
                            <span className="text-slate-200 font-mono text-sm tracking-wider">{paymentInfo.iban}</span>
                            <button
                              onClick={() => copyToClipboard(paymentInfo.iban, 'iban')}
                              className="text-slate-400 hover:text-slate-200 transition-colors p-1"
                              title={t('common.copy') || 'Copy'}
                            >
                              {copiedField === 'iban' ? (
                                <Check className="w-4 h-4 text-emerald-400" />
                              ) : (
                                <Copy className="w-4 h-4" />
                              )}
                            </button>
                          </div>
                        )}
                      </div>
                      
                      {/* Amount - show in multiple currencies based on available IBANs */}
                      <div className="space-y-1">
                        <p className="text-slate-500 text-xs uppercase">{t('common.amount')}</p>
                        <div className="bg-slate-800 rounded px-3 py-2 space-y-2">
                          {/* Primary amount - in selected IBAN currency or bill currency */}
                          {(() => {
                            const displayCurrency = isRentOrDirectDebit && paymentInfo.ibanCurrency
                              ? paymentInfo.ibanCurrency
                              : billCurrency;
                            const displayAmount = displayCurrency === billCurrency
                              ? remaining
                              : convertAmount(remaining, billCurrency, displayCurrency);
                            
                            return (
                              <div className="flex items-center justify-between">
                                <span className="text-emerald-400 font-mono text-sm font-bold">
                                  {displayAmount.toFixed(2)} {displayCurrency}
                                </span>
                                <button
                                  onClick={() => copyToClipboard(displayAmount.toFixed(2), 'amount')}
                                  className="text-slate-400 hover:text-slate-200 transition-colors p-1"
                                  title={`${t('common.copy') || 'Copy'} ${displayCurrency}`}
                                >
                                  {copiedField === 'amount' ? (
                                    <Check className="w-4 h-4 text-emerald-400" />
                                  ) : (
                                    <Copy className="w-4 h-4" />
                                  )}
                                </button>
                              </div>
                            );
                          })()}
                          
                          {/* Show amounts in other available currencies */}
                          {isRentOrDirectDebit && availableIbans.length > 0 && (
                            <div className="border-t border-slate-700 pt-2 space-y-1">
                              {availableIbans
                                .filter(iban => iban.currency !== (paymentInfo.ibanCurrency || billCurrency))
                                .map((iban) => {
                                  const convertedAmount = convertAmount(remaining, billCurrency, iban.currency);
                                  return (
                                    <div key={iban.currency} className="flex items-center justify-between text-slate-400">
                                      <span className="font-mono text-xs">
                                        {convertedAmount.toFixed(2)} {iban.currency}
                                      </span>
                                      <button
                                        onClick={() => copyToClipboard(convertedAmount.toFixed(2), `amount_${iban.currency}`)}
                                        className="text-slate-500 hover:text-slate-300 transition-colors p-0.5"
                                        title={`${t('common.copy') || 'Copy'} ${iban.currency}`}
                                      >
                                        {copiedField === `amount_${iban.currency}` ? (
                                          <Check className="w-3 h-3 text-emerald-400" />
                                        ) : (
                                          <Copy className="w-3 h-3" />
                                        )}
                                      </button>
                                    </div>
                                  );
                                })}
                              {/* Always show rent currency if not already shown */}
                              {info?.rent_currency &&
                               !availableIbans.some(i => i.currency === info.rent_currency) &&
                               info.rent_currency !== (paymentInfo.ibanCurrency || billCurrency) && (
                                <div className="flex items-center justify-between text-slate-400">
                                  <span className="font-mono text-xs">
                                    {convertAmount(remaining, billCurrency, info.rent_currency).toFixed(2)} {info.rent_currency}
                                  </span>
                                  <button
                                    onClick={() => copyToClipboard(convertAmount(remaining, billCurrency, info.rent_currency!).toFixed(2), `amount_${info.rent_currency}`)}
                                    className="text-slate-500 hover:text-slate-300 transition-colors p-0.5"
                                    title={`${t('common.copy') || 'Copy'} ${info.rent_currency}`}
                                  >
                                    {copiedField === `amount_${info.rent_currency}` ? (
                                      <Check className="w-3 h-3 text-emerald-400" />
                                    ) : (
                                      <Copy className="w-3 h-3" />
                                    )}
                                  </button>
                                </div>
                              )}
                            </div>
                          )}
                          
                          {/* For non-rent bills, show RON equivalent if bill is in foreign currency */}
                          {!isRentOrDirectDebit && billCurrency !== 'RON' && getAmountInRon(remaining, billCurrency) && (
                            <div className="border-t border-slate-700 pt-2">
                              <div className="flex items-center justify-between text-slate-400">
                                <span className="font-mono text-xs">
                                  {getAmountInRon(remaining, billCurrency)} RON
                                </span>
                                <button
                                  onClick={() => copyToClipboard(getAmountInRon(remaining, billCurrency) || '', 'amountRon')}
                                  className="text-slate-500 hover:text-slate-300 transition-colors p-0.5"
                                  title={`${t('common.copy') || 'Copy'} RON`}
                                >
                                  {copiedField === 'amountRon' ? (
                                    <Check className="w-3 h-3 text-emerald-400" />
                                  ) : (
                                    <Copy className="w-3 h-3" />
                                  )}
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                      
                      {/* Bill Number - only for non-rent bills */}
                      {!isRentOrDirectDebit && payingBill?.bill.bill_number && (
                        <div className="space-y-1">
                          <p className="text-slate-500 text-xs uppercase">{t('renter.billNumber') || 'Bill Number'}</p>
                          <div className="flex items-center justify-between bg-slate-800 rounded px-3 py-2">
                            <span className="text-slate-200 font-mono text-sm">{payingBill.bill.bill_number}</span>
                            <button
                              onClick={() => copyToClipboard(payingBill.bill.bill_number || '', 'billNumber')}
                              className="text-slate-400 hover:text-slate-200 transition-colors p-1"
                              title={t('common.copy') || 'Copy'}
                            >
                              {copiedField === 'billNumber' ? (
                                <Check className="w-4 h-4 text-emerald-400" />
                              ) : (
                                <Copy className="w-4 h-4" />
                              )}
                            </button>
                          </div>
                        </div>
                      )}
                      
                      {/* Reference */}
                      <div className="space-y-1">
                        <p className="text-slate-500 text-xs uppercase">{t('renter.reference') || 'Reference'}</p>
                        <div className="flex items-center justify-between bg-slate-800 rounded px-3 py-2">
                          <span className="text-slate-200 font-mono text-sm truncate mr-2">{paymentInfo.reference}</span>
                          <button
                            onClick={() => copyToClipboard(paymentInfo.reference, 'reference')}
                            className="text-slate-400 hover:text-slate-200 transition-colors p-1 flex-shrink-0"
                            title={t('common.copy') || 'Copy'}
                          >
                            {copiedField === 'reference' ? (
                              <Check className="w-4 h-4 text-emerald-400" />
                            ) : (
                              <Copy className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </div>
                      
                      {/* Reference 2 - payment_details.client_code for non-rent bills */}
                      {paymentInfo.reference2 && (
                        <div className="space-y-1">
                          <p className="text-slate-500 text-xs uppercase">{t('renter.reference2') || 'Reference 2'}</p>
                          <div className="flex items-center justify-between bg-slate-800 rounded px-3 py-2">
                            <span className="text-slate-200 font-mono text-sm truncate mr-2">{paymentInfo.reference2}</span>
                            <button
                              onClick={() => copyToClipboard(paymentInfo.reference2 || '', 'reference2')}
                              className="text-slate-400 hover:text-slate-200 transition-colors p-1 flex-shrink-0"
                              title={t('common.copy') || 'Copy'}
                            >
                              {copiedField === 'reference2' ? (
                                <Check className="w-4 h-4 text-emerald-400" />
                              ) : (
                                <Copy className="w-4 h-4" />
                              )}
                            </button>
                          </div>
                        </div>
                      )}
                      
                      <p className="text-xs text-slate-500 text-center mt-2">
                        {t('renter.bankTransferNote') || 'Use these details to make a bank transfer'}
                      </p>
                    </div>
                  );
                }
                return null;
              })()}

              {/* No payment info available */}
              {!getPaymentInfo(payingBill) && (
                <div className="space-y-2">
                  <p className="text-slate-300 text-sm">{t('renter.paymentMethod') || 'Payment Method'}:</p>
                  
                  {/* Supplier Payment Link - placeholder for future */}
                  <Button
                    className="w-full bg-slate-700 text-slate-100 hover:bg-slate-600 border border-slate-600"
                    disabled
                  >
                    <Banknote className="w-4 h-4 mr-2" />
                    {t('renter.payViaSupplier') || 'Pay via Supplier Portal'}
                    <span className="ml-2 text-xs text-slate-500">({t('common.comingSoon') || 'Coming soon'})</span>
                  </Button>

                  {/* Stripe Payment */}
                  <Button
                    className="w-full bg-emerald-600 hover:bg-emerald-700"
                    disabled
                  >
                    <CreditCard className="w-4 h-4 mr-2" />
                    {t('renter.payWithStripe') || 'Pay with Stripe'}
                    <span className="ml-2 text-xs text-emerald-200">({t('common.comingSoon') || 'Coming soon'})</span>
                  </Button>
                  
                  <p className="text-xs text-slate-500 text-center">
                    {t('renter.paymentComingSoon') || 'Payment integration will be available soon'}
                  </p>
                </div>
              )}

              {/* Payment Notification Section */}
              <div className="border-t border-slate-700 pt-4 mt-4">
                <p className="text-slate-300 text-sm mb-2">
                  {t('renter.notifyPaymentDescription') || 'After making the transfer, notify the landlord:'}
                </p>
                
                {/* Optional note */}
                <div className="space-y-2 mb-4">
                  <label className="text-slate-400 text-xs">
                    {t('renter.paymentNote') || 'Note (optional)'}
                  </label>
                  <Textarea
                    value={paymentNote}
                    onChange={(e) => setPaymentNote(e.target.value)}
                    placeholder={t('renter.paymentNotePlaceholder') || 'e.g., Transfer reference, date, etc.'}
                    className="bg-slate-900 border-slate-600 text-slate-200 placeholder:text-slate-500 resize-none"
                    rows={2}
                  />
                </div>
              </div>
            </div>
            
            <DialogFooter className="flex gap-2 sm:gap-2">
              <Button
                variant="outline"
                onClick={() => setPayingBill(null)}
                className="border-slate-600 text-slate-300 hover:bg-slate-700"
              >
                {t('common.cancel') || 'Cancel'}
              </Button>
              <Button
                onClick={handleNotifyPayment}
                disabled={notifyingPayment}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                {notifyingPayment ? (
                  <>
                    <Clock className="w-4 h-4 mr-2 animate-spin" />
                    {t('common.sending') || 'Sending...'}
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4 mr-2" />
                    {t('renter.iMadeTheTransfer') || 'I made the transfer'}
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </main>
    </div>
  );
}
