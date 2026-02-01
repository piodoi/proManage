import React, { useState, useEffect, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { api, RenterInfo, RenterBill, RenterBalance, getRenterBillPdfUrl, PaymentNotificationCreate, RenterAccountCreate, RenterPreferencesUpdate } from '../api';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Building2, Receipt, Banknote, ChevronDown, ChevronRight, FileText, Copy, Check, Clock, Send, CreditCard, User, Settings, Eye, EyeOff, Mail, Bell, LogIn } from 'lucide-react';
import { featureFlags } from '../lib/featureFlags';
import { UtilityPaymentDialog } from '../components/dialogs/UtilityPaymentDialog';
import { useI18n } from '../lib/i18n';
import { formatDateWithPreferences } from '../lib/utils';
import { TransactionResponse } from '../utils/utility';

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
  const [expandedGroups, setExpandedGroups] = useState<Set<string> | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [selectedIbanCurrency, setSelectedIbanCurrency] = useState<string | null>(null);
  const [notifyingPayment, setNotifyingPayment] = useState(false);
  const [paymentNote, setPaymentNote] = useState('');
  const [paymentAmount, setPaymentAmount] = useState<string>('');
  const [paymentCurrency, setPaymentCurrency] = useState<string>('RON');
  const [previousPaymentCurrency, setPreviousPaymentCurrency] = useState<string>('RON');
  
  // Utility payment dialog state
  const [showUtilityPayment, setShowUtilityPayment] = useState(false);
  const [utilityPaymentBill, setUtilityPaymentBill] = useState<RenterBill | null>(null);

  // Account and settings dialog state
  const [showAccountDialog, setShowAccountDialog] = useState(false);
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [showLoginDialog, setShowLoginDialog] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loginPassword, setLoginPassword] = useState('');
  const [loggingIn, setLoggingIn] = useState(false);
  const [accountForm, setAccountForm] = useState({
    password: '',
    passwordConfirm: '',
    email: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false);
  const [creatingAccount, setCreatingAccount] = useState(false);
  const [savingPreferences, setSavingPreferences] = useState(false);

  // Toggle group expansion
  const toggleGroup = (groupKey: string) => {
    setExpandedGroups(prev => {
      const newSet = new Set(prev || []);
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

  // Helper function to sort bills: unpaid (ascending by due date), then paid (descending by due date)
  const sortBillsForDisplay = (billItems: RenterBill[]): RenterBill[] => {
    const unpaidBills = billItems.filter(item => item.bill.status !== 'paid');
    const paidBills = billItems.filter(item => item.bill.status === 'paid');
    
    // Sort unpaid bills by due_date ascending (soonest first)
    unpaidBills.sort((a, b) =>
      new Date(a.bill.due_date).getTime() - new Date(b.bill.due_date).getTime()
    );
    
    // Sort paid bills by due_date descending (most recent first)
    paidBills.sort((a, b) =>
      new Date(b.bill.due_date).getTime() - new Date(a.bill.due_date).getTime()
    );
    
    // Unpaid bills first, then paid bills
    return [...unpaidBills, ...paidBills];
  };

  const groupedBills = useMemo((): BillGroup[] => {
    // Separate rent bills from other bills
    const rentBills = bills.filter(item => item.bill.bill_type === 'rent');
    const otherBills = bills.filter(item => item.bill.bill_type !== 'rent');

    const groups: BillGroup[] = [];

    // Group all rent bills together
    if (rentBills.length > 0) {
      const sortedRentBills = sortBillsForDisplay(rentBills);
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
      const sortedBills = sortBillsForDisplay(billItems);
      groups.push({
        groupKey: `desc-${sortedBills[0].bill.description || t('bill.noDescription')}`,
        latestBill: sortedBills[0],
        olderBills: sortedBills.slice(1),
      });
    });

    // Sort groups: groups with unpaid bills first (by earliest due date), then groups with only paid bills (by most recent due date)
    groups.sort((a, b) => {
      const aHasUnpaid = a.latestBill.bill.status !== 'paid' || a.olderBills.some(item => item.bill.status !== 'paid');
      const bHasUnpaid = b.latestBill.bill.status !== 'paid' || b.olderBills.some(item => item.bill.status !== 'paid');
      
      if (aHasUnpaid && !bHasUnpaid) return -1;
      if (!aHasUnpaid && bHasUnpaid) return 1;
      
      // Both have unpaid or both are paid - sort by the first bill's due date
      if (aHasUnpaid && bHasUnpaid) {
        // For groups with unpaid bills, sort by earliest due date (ascending)
        return new Date(a.latestBill.bill.due_date).getTime() - new Date(b.latestBill.bill.due_date).getTime();
      } else {
        // For groups with only paid bills, sort by most recent due date (descending)
        return new Date(b.latestBill.bill.due_date).getTime() - new Date(a.latestBill.bill.due_date).getTime();
      }
    });

    return groups;
  }, [bills, t]);

  // Initialize expanded groups - expand groups that have pending/overdue bills in older bills
  useEffect(() => {
    if (expandedGroups === null && groupedBills.length > 0) {
      const groupsToExpand = new Set<string>();
      groupedBills.forEach(group => {
        // Check if any older bill is pending or overdue
        const hasUnpaidOlderBills = group.olderBills.some(
          item => item.bill.status === 'pending' || item.bill.status === 'overdue'
        );
        if (hasUnpaidOlderBills) {
          groupsToExpand.add(group.groupKey);
        }
      });
      setExpandedGroups(groupsToExpand);
    }
  }, [groupedBills, expandedGroups]);

  // Apply language from backend (DB) - works even without login
  useEffect(() => {
    if (info?.renter.language) {
      const renterLang = info.renter.language as 'en' | 'ro';
      if (renterLang === 'en' || renterLang === 'ro') {
        setLanguage(renterLang);
      }
    } else {
      // Default to Romanian for renters if no language set
      const savedLang = localStorage.getItem('language');
      if (!savedLang) {
        setLanguage('ro');
      }
    }
  }, [setLanguage, info?.renter.language]);

  // Save language preference to backend when changed (only if logged in)
  const handleLanguageChange = async (newLanguage: 'en' | 'ro') => {
    setLanguage(newLanguage);
    if (token && isLoggedIn) {
      try {
        await api.renter.updatePreferences(token, { language: newLanguage });
        // Update local info
        if (info) {
          setInfo({
            ...info,
            renter: { ...info.renter, language: newLanguage }
          });
        }
      } catch (err) {
        console.error('Failed to save language preference:', err);
      }
    }
  };

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
    // Set default payment amount to remaining bill amount
    setPaymentAmount(bill.remaining.toFixed(2));
    // Set default payment currency to bill currency
    const billCurrency = bill.bill.currency || 'RON';
    setPaymentCurrency(billCurrency);
    setPreviousPaymentCurrency(billCurrency);
    // Set default IBAN currency when opening dialog
    setSelectedIbanCurrency(getDefaultIbanCurrency());
  };

  // Handle payment currency change - auto-convert amount
  const handlePaymentCurrencyChange = (newCurrency: string) => {
    if (paymentAmount && balance?.exchange_rates && previousPaymentCurrency !== newCurrency) {
      const currentAmount = parseFloat(paymentAmount);
      if (!isNaN(currentAmount) && currentAmount > 0) {
        const convertedAmount = convertAmount(currentAmount, previousPaymentCurrency, newCurrency);
        setPaymentAmount(convertedAmount.toFixed(2));
      }
    }
    setPreviousPaymentCurrency(newCurrency);
    setPaymentCurrency(newCurrency);
  };

  // Handle "I made the transfer" button click
  const handleNotifyPayment = async () => {
    if (!payingBill || !token) return;
    
    const amount = parseFloat(paymentAmount);
    if (isNaN(amount) || amount <= 0) {
      setError(t('errors.invalidAmount') || 'Please enter a valid amount');
      return;
    }
    
    setNotifyingPayment(true);
    try {
      const data: PaymentNotificationCreate = {
        bill_id: payingBill.bill.id,
        amount: amount,
        currency: paymentCurrency,
        renter_note: paymentNote || undefined,
      };
      
      await api.renter.notifyPayment(token, data);
      
      // Reload bills to show updated notification status
      const billsData = await api.renter.bills(token);
      setBills(billsData);
      
      setPayingBill(null);
      setPaymentNote('');
      setPaymentAmount('');
      setPaymentCurrency('RON');
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.generic'));
    } finally {
      setNotifyingPayment(false);
    }
  };

  // Handle account creation
  const handleCreateAccount = async () => {
    if (!token) return;
    
    if (!accountForm.password || !accountForm.passwordConfirm) {
      setError(t('renter.passwordRequired'));
      return;
    }
    
    if (accountForm.password !== accountForm.passwordConfirm) {
      setError(t('renter.passwordMismatch'));
      return;
    }
    
    if (accountForm.password.length < 6) {
      setError(t('renter.passwordTooShort'));
      return;
    }
    
    setCreatingAccount(true);
    try {
      const data: RenterAccountCreate = {
        password: accountForm.password,
        password_confirm: accountForm.passwordConfirm,
        email: accountForm.email || undefined,
      };
      
      await api.renter.createAccount(token, data);
      
      // Reload info to get updated account status
      const infoData = await api.renter.info(token);
      setInfo(infoData);
      
      setShowAccountDialog(false);
      setAccountForm({ password: '', passwordConfirm: '', email: '' });
      // Auto-login after account creation
      setIsLoggedIn(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.generic'));
    } finally {
      setCreatingAccount(false);
    }
  };

  // Handle login
  const handleLogin = async () => {
    if (!token) return;
    
    if (!loginPassword) {
      setError(t('renter.passwordRequired'));
      return;
    }
    
    setLoggingIn(true);
    try {
      await api.renter.login(token, loginPassword);
      
      setIsLoggedIn(true);
      setShowLoginDialog(false);
      setLoginPassword('');
      // Open settings after successful login
      setShowSettingsDialog(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.generic'));
    } finally {
      setLoggingIn(false);
    }
  };

  // Handle email notifications toggle
  const handleEmailNotificationsToggle = async (enabled: boolean) => {
    if (!token || !info) return;
    
    // Check if email is available
    if (enabled && !info.renter.email) {
      setError(t('renter.emailRequiredForNotifications'));
      return;
    }
    
    setSavingPreferences(true);
    try {
      const data: RenterPreferencesUpdate = {
        email_notifications: enabled,
      };
      
      await api.renter.updatePreferences(token, data);
      
      // Reload info to get updated preferences
      const infoData = await api.renter.info(token);
      setInfo(infoData);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.generic'));
    } finally {
      setSavingPreferences(false);
    }
  };

  // Handle adding email (for renters without email set by landlord)
  const handleAddEmail = async (email: string) => {
    if (!token) return;
    
    if (!email || !email.includes('@')) {
      setError(t('renter.invalidEmail'));
      return;
    }
    
    setSavingPreferences(true);
    try {
      await api.renter.updateEmail(token, email);
      
      // Reload info to get updated email
      const infoData = await api.renter.info(token);
      setInfo(infoData);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.generic'));
    } finally {
      setSavingPreferences(false);
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
      <header className="bg-slate-800 border-b border-slate-700 px-3 sm:px-6 py-3 sm:py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Building2 className="w-6 h-6 text-emerald-500" />
            <div>
              <h1 className="text-xl font-semibold text-slate-100">{t('app.title')}</h1>
              <p className="text-sm text-slate-400">{t('renter.portal')}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {/* Account/Login/Settings Button */}
            {info && (
              <>
                {info.renter.has_account ? (
                  isLoggedIn ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowSettingsDialog(true)}
                      className="text-slate-300 hover:text-slate-100 hover:bg-slate-700"
                    >
                      <Settings className="w-4 h-4 mr-1" />
                      {t('renter.settings')}
                    </Button>
                  ) : (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowLoginDialog(true)}
                      className="text-slate-300 hover:text-slate-100 hover:bg-slate-700"
                    >
                      <LogIn className="w-4 h-4 mr-1" />
                      {t('auth.signInButton')}
                    </Button>
                  )
                ) : (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowAccountDialog(true)}
                    className="text-slate-300 hover:text-slate-100 hover:bg-slate-700"
                  >
                    <User className="w-4 h-4 mr-1" />
                    {t('renter.createAccount')}
                  </Button>
                )}
              </>
            )}
            
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
                  onClick={() => handleLanguageChange('en')}
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
                  onClick={() => handleLanguageChange('ro')}
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
        </div>
      </header>

      <main className="p-3 sm:p-6 max-w-4xl mx-auto mobile-scroll">
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
          <CardContent className="p-0 overflow-x-auto mobile-scroll">
            {bills.length === 0 ? (
              <div className="p-6 text-center text-slate-400">{t('renter.noBills')}</div>
            ) : (
              <Table className="min-w-[600px]">
                <TableHeader>
                  <TableRow className="border-slate-700">
                    <TableHead className="text-slate-400 text-xs sm:text-sm">{t('common.description')}</TableHead>
                    <TableHead className="text-slate-400 text-xs sm:text-sm">{t('bill.billType')}</TableHead>
                    <TableHead className="text-slate-400 text-xs sm:text-sm">{t('common.amount')}</TableHead>
                    <TableHead className="text-slate-400 text-xs sm:text-sm">{t('renter.remaining')}</TableHead>
                    <TableHead className="text-slate-400 text-xs sm:text-sm">{t('bill.dueDate')}</TableHead>
                    <TableHead className="text-slate-400 text-xs sm:text-sm">{t('common.status')}</TableHead>
                    <TableHead className="text-slate-400 text-xs sm:text-sm">{t('common.actions')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {groupedBills.map((group) => {
                    const isExpanded = expandedGroups?.has(group.groupKey) ?? false;
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
                                {featureFlags.payOnline && item.bill.bill_type !== 'rent' && item.bill.bill_number && (
                                  <Button
                                    size="sm"
                                    onClick={() => {
                                      setUtilityPaymentBill(item);
                                      setShowUtilityPayment(true);
                                    }}
                                    className="bg-blue-600 hover:bg-blue-700"
                                    title={t('utility.payOnlineBtn')}
                                  >
                                    <CreditCard className="w-4 h-4 mr-1" />
                                    {t('utility.payOnlineBtn')}
                                  </Button>
                                )}
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
          
          // Filter bills for balance calculation based on warning days
          // Only include bills with due dates within the warning threshold (today + warning_days)
          const warningDays = info?.rent_warning_days ?? 5;
          const cutoffDate = new Date();
          cutoffDate.setDate(cutoffDate.getDate() + warningDays);
          cutoffDate.setHours(23, 59, 59, 999); // End of the cutoff day
          
          const balanceBills = bills.filter(b => {
            const dueDate = new Date(b.bill.due_date);
            // Include bills that are due on or before the cutoff date
            return dueDate <= cutoffDate;
          });

          return (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-3 mb-4">
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="pt-3 sm:pt-4 px-2 sm:px-4 pb-3 sm:pb-4">
                <p className="text-slate-400 text-xs sm:text-sm">{t('renter.totalThisMonth') || 'Total This Month'}</p>
                <p className="text-xl sm:text-2xl font-bold text-slate-100">
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
              <CardContent className="pt-3 sm:pt-4 px-2 sm:px-4 pb-3 sm:pb-4">
                <p className="text-slate-400 text-xs sm:text-sm">{t('renter.totalPaid')}</p>
                <p className="text-xl sm:text-2xl font-bold text-green-400">
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
              <CardContent className="pt-3 sm:pt-4 px-2 sm:px-4 pb-3 sm:pb-4">
                <p className="text-slate-400 text-xs sm:text-sm mb-1 sm:mb-2">{t('renter.balance')}</p>
                
                {/* Bills breakdown inside balance card - bills with non-zero remaining within warning days */}
                {balanceBills.filter(b => b.remaining !== 0).length > 0 && (
                  <div className="mb-2 space-y-0 text-xs">
                    {balanceBills.filter(b => b.remaining !== 0).map((item) => (
                      <div key={item.bill.id} className={`flex justify-between items-center ${item.remaining < 0 ? 'text-green-400' : 'text-slate-400'}`}>
                        <span className="truncate mr-1">{item.bill.description}</span>
                        <span className="tabular-nums text-right flex-shrink-0 whitespace-nowrap">
                           {item.bill.currency && item.bill.currency !== 'RON' && (
                          <> {item.remaining.toFixed(2)} {item.bill.currency} / </>
                          )}
                          {balance.exchange_rates && item.bill.currency && item.bill.currency !== 'RON'
                            ? (item.remaining * (balance.exchange_rates.RON) / (balance.exchange_rates[item.bill.currency as keyof typeof balance.exchange_rates] || 1)).toFixed(2)
                            : item.remaining.toFixed(2)
                          } RON
                        </span>
                      </div>
                    ))}
                    <div className="border-t border-slate-700 mt-1 pt-1"></div>
                  </div>
                )}
                
                <div className="flex justify-end items-baseline gap-1">
                  <p className={`text-xl sm:text-2xl font-bold tabular-nums ${
                    balanceBills.reduce((sum, b) => {
                      const ronValue = balance.exchange_rates && b.bill.currency && b.bill.currency !== 'RON'
                        ? (b.remaining * (balance.exchange_rates.RON || 4.97) / (balance.exchange_rates[b.bill.currency as keyof typeof balance.exchange_rates] || 1))
                        : b.remaining;
                      return sum + ronValue;
                    }, 0) > 0 ? 'text-amber-400' : 'text-green-400'
                  }`}>
                    {balanceBills
                      .reduce((sum, b) => {
                        const ronValue = balance.exchange_rates && b.bill.currency && b.bill.currency !== 'RON'
                          ? (b.remaining * (balance.exchange_rates.RON || 4.97) / (balance.exchange_rates[b.bill.currency as keyof typeof balance.exchange_rates] || 1))
                          : b.remaining;
                        return sum + ronValue;
                      }, 0)
                      .toFixed(2)}
                  </p>
                  <p className={`text-base sm:text-lg font-medium ${
                    balanceBills.reduce((sum, b) => sum + b.remaining, 0) > 0 ? 'text-amber-400' : 'text-green-400'
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

              {/* No payment info available - show references and PDF link */}
              {!getPaymentInfo(payingBill) && (
                <div className="bg-slate-900 border border-slate-700 rounded-lg p-4 space-y-3">
                  {/* For direct debit bills without landlord IBAN, show specific message */}
                  {payingBill?.is_direct_debit ? (
                    <>
                      <div className="bg-blue-900/30 border border-blue-700 rounded-lg p-3 mb-3">
                        <p className="text-blue-300 text-sm text-center">
                          {t('renter.directDebitNote') || 'This is a direct debit bill. The landlord pays the supplier and you pay the landlord.'}
                        </p>
                      </div>
                      <p className="text-amber-400 text-sm text-center">
                        {t('renter.landlordIbanNotConfigured') || 'Landlord bank details not configured. Please contact your landlord.'}
                      </p>
                    </>
                  ) : (
                    <p className="text-amber-400 text-sm text-center">
                      {t('renter.checkBillForPaymentInfo') || 'Check the bill for payment information'}
                    </p>
                  )}
                  
                  {/* Bill details section */}
                  <div className="space-y-2 pt-2 border-t border-slate-700">
                    {/* Amount */}
                    <div className="space-y-1">
                      <p className="text-slate-500 text-xs uppercase">{t('common.amount')}</p>
                      <div className="flex items-center justify-between bg-slate-800 rounded px-3 py-2">
                        <span className="text-emerald-400 font-mono text-sm font-bold">
                          {payingBill?.remaining.toFixed(2)} {payingBill?.bill.currency || 'RON'}
                        </span>
                        <button
                          onClick={() => copyToClipboard(payingBill?.remaining.toFixed(2) || '', 'amount')}
                          className="text-slate-400 hover:text-slate-200 transition-colors p-1"
                          title={t('common.copy') || 'Copy'}
                        >
                          {copiedField === 'amount' ? (
                            <Check className="w-4 h-4 text-emerald-400" />
                          ) : (
                            <Copy className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                  
                  {/* PDF Link if available */}
                  {payingBill?.has_pdf && token && (
                    <div className="flex justify-center">
                      <Button
                        variant="outline"
                        onClick={() => window.open(getRenterBillPdfUrl(token, payingBill.bill.id), '_blank')}
                        className="border-slate-600 text-blue-400 hover:bg-slate-700 hover:text-blue-300"
                      >
                        <FileText className="w-4 h-4 mr-2" />
                        {t('renter.downloadPdf') || 'Download PDF'}
                      </Button>
                    </div>
                  )}
                  
                  {/* Bill Number - only show for non-direct-debit bills */}
                  {!payingBill?.is_direct_debit && payingBill?.bill.bill_number && (
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
                  
                  {/* Contract ID - only show for non-direct-debit bills */}
                  {!payingBill?.is_direct_debit && payingBill?.bill.contract_id && (
                    <div className="space-y-1">
                      <p className="text-slate-500 text-xs uppercase">{t('renter.reference') || 'Reference'}</p>
                      <div className="flex items-center justify-between bg-slate-800 rounded px-3 py-2">
                        <span className="text-slate-200 font-mono text-sm">{payingBill.bill.contract_id}</span>
                        <button
                          onClick={() => copyToClipboard(payingBill.bill.contract_id || '', 'contractId')}
                          className="text-slate-400 hover:text-slate-200 transition-colors p-1"
                          title={t('common.copy') || 'Copy'}
                        >
                          {copiedField === 'contractId' ? (
                            <Check className="w-4 h-4 text-emerald-400" />
                          ) : (
                            <Copy className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    </div>
                  )}
                  
                  {/* Payment Details - client_code */}
                  {(() => {
                    const paymentDetails = payingBill?.bill.payment_details as { client_code?: string } | null;
                    if (paymentDetails?.client_code) {
                      return (
                        <div className="space-y-1">
                          <p className="text-slate-500 text-xs uppercase">{t('renter.reference2') || 'Reference 2'}</p>
                          <div className="flex items-center justify-between bg-slate-800 rounded px-3 py-2">
                            <span className="text-slate-200 font-mono text-sm">{paymentDetails.client_code}</span>
                            <button
                              onClick={() => copyToClipboard(paymentDetails.client_code || '', 'clientCode')}
                              className="text-slate-400 hover:text-slate-200 transition-colors p-1"
                              title={t('common.copy') || 'Copy'}
                            >
                              {copiedField === 'clientCode' ? (
                                <Check className="w-4 h-4 text-emerald-400" />
                              ) : (
                                <Copy className="w-4 h-4" />
                              )}
                            </button>
                          </div>
                        </div>
                      );
                    }
                    return null;
                  })()}
                </div>
              )}

              {/* Payment Notification Section */}
              <div className="border-t border-slate-700 pt-4 mt-4">
                <p className="text-slate-300 text-sm mb-2">
                  {t('renter.notifyPaymentDescription') || 'After making the transfer, notify the landlord:'}
                </p>
                
                {/* Payment Amount and Currency */}
                <div className="space-y-2 mb-4">
                  <label className="text-slate-400 text-xs">
                    {t('renter.paymentAmount') || 'Amount Paid'}
                  </label>
                  <div className="flex gap-2">
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={paymentAmount}
                      onChange={(e) => setPaymentAmount(e.target.value)}
                      placeholder={payingBill?.remaining.toFixed(2) || '0.00'}
                      className="bg-slate-900 border-slate-600 text-slate-200 placeholder:text-slate-500 flex-1"
                    />
                    <Select
                      value={paymentCurrency}
                      onValueChange={handlePaymentCurrencyChange}
                    >
                      <SelectTrigger className="bg-slate-900 border-slate-600 text-slate-200 w-24">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-800 border-slate-600">
                        <SelectItem value="RON" className="text-slate-200 hover:bg-slate-700">RON</SelectItem>
                        <SelectItem value="EUR" className="text-slate-200 hover:bg-slate-700">EUR</SelectItem>
                        <SelectItem value="USD" className="text-slate-200 hover:bg-slate-700">USD</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  {payingBill && paymentAmount && (() => {
                    const enteredAmount = parseFloat(paymentAmount);
                    if (isNaN(enteredAmount)) return null;
                    
                    const billCurrency = payingBill.bill.currency || 'RON';
                    // Convert entered amount to bill currency for comparison
                    const enteredAmountInBillCurrency = paymentCurrency === billCurrency
                      ? enteredAmount
                      : convertAmount(enteredAmount, paymentCurrency, billCurrency);
                    
                    // Use a small tolerance for floating point comparison
                    const difference = enteredAmountInBillCurrency - payingBill.remaining;
                    if (Math.abs(difference) < 0.01) return null;
                    
                    const displayRemaining = paymentCurrency === billCurrency
                      ? payingBill.remaining
                      : convertAmount(payingBill.remaining, billCurrency, paymentCurrency);
                    
                    return (
                      <p className="text-xs text-amber-400">
                        {difference > 0
                          ? t('renter.payingMore') || `You're paying more than the bill amount (${displayRemaining.toFixed(2)} ${paymentCurrency}). The extra will be added to your balance.`
                          : t('renter.payingLess') || `You're paying less than the bill amount (${displayRemaining.toFixed(2)} ${paymentCurrency}). The remaining will stay on your balance.`
                        }
                      </p>
                    );
                  })()}
                </div>
                
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
        
        {/* Utility Payment Dialog */}
        <UtilityPaymentDialog
          open={showUtilityPayment}
          onClose={() => {
            setShowUtilityPayment(false);
            setUtilityPaymentBill(null);
          }}
          billBarcode={utilityPaymentBill?.bill.bill_number || ''}
          mode="renter"
          onSuccess={(_transaction: TransactionResponse) => {
            // Reload bills to show updated status
            if (token) {
              api.renter.bills(token)
                .then(setBills)
                .catch((err) => setError(err instanceof Error ? err.message : t('errors.generic')));
            }
            setShowUtilityPayment(false);
            setUtilityPaymentBill(null);
          }}
        />

        {/* Login Dialog */}
        <Dialog open={showLoginDialog} onOpenChange={setShowLoginDialog}>
          <DialogContent className="bg-slate-800 border-slate-700">
            <DialogHeader>
              <DialogTitle className="text-slate-100">{t('auth.signInButton')}</DialogTitle>
              <DialogDescription className="text-slate-400">
                {t('renter.loginDesc')}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label className="text-slate-300">{t('common.password')} *</Label>
                <div className="relative">
                  <Input
                    type={showPassword ? 'text' : 'password'}
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    className="bg-slate-700 border-slate-600 text-slate-100 pr-10"
                    placeholder={t('auth.passwordPlaceholder')}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleLogin();
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  setShowLoginDialog(false);
                  setLoginPassword('');
                }}
                className="border-slate-600 text-slate-300 hover:bg-slate-700"
              >
                {t('common.cancel')}
              </Button>
              <Button
                onClick={handleLogin}
                disabled={loggingIn || !loginPassword}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                {loggingIn ? t('auth.signingIn') : t('auth.signInButton')}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Create Account Dialog */}
        <Dialog open={showAccountDialog} onOpenChange={setShowAccountDialog}>
          <DialogContent className="bg-slate-800 border-slate-700">
            <DialogHeader>
              <DialogTitle className="text-slate-100">{t('renter.createAccount')}</DialogTitle>
              <DialogDescription className="text-slate-400">
                {t('renter.createAccountDesc')}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              {/* Email (only if not set by landlord) */}
              {info && !info.renter.email && (
                <div>
                  <Label className="text-slate-300">
                    <Mail className="w-4 h-4 inline mr-1" />
                    {t('common.email')} ({t('common.optional').toLowerCase()})
                  </Label>
                  <Input
                    type="email"
                    value={accountForm.email}
                    onChange={(e) => setAccountForm({ ...accountForm, email: e.target.value })}
                    className="bg-slate-700 border-slate-600 text-slate-100"
                    placeholder={t('auth.emailPlaceholder')}
                  />
                  <p className="text-xs text-slate-500 mt-1">
                    {t('renter.addEmailNote')}
                  </p>
                </div>
              )}
              
              {/* Password */}
              <div>
                <Label className="text-slate-300">{t('renter.password')} *</Label>
                <div className="relative">
                  <Input
                    type={showPassword ? 'text' : 'password'}
                    value={accountForm.password}
                    onChange={(e) => setAccountForm({ ...accountForm, password: e.target.value })}
                    className="bg-slate-700 border-slate-600 text-slate-100 pr-10"
                    placeholder={t('auth.passwordPlaceholder')}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              
              {/* Confirm Password */}
              <div>
                <Label className="text-slate-300">{t('renter.confirmPassword')} *</Label>
                <div className="relative">
                  <Input
                    type={showPasswordConfirm ? 'text' : 'password'}
                    value={accountForm.passwordConfirm}
                    onChange={(e) => setAccountForm({ ...accountForm, passwordConfirm: e.target.value })}
                    className="bg-slate-700 border-slate-600 text-slate-100 pr-10"
                    placeholder={t('renter.confirmPasswordPlaceholder')}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPasswordConfirm(!showPasswordConfirm)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
                  >
                    {showPasswordConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setShowAccountDialog(false)}
                className="border-slate-600 text-slate-300 hover:bg-slate-700"
              >
                {t('common.cancel')}
              </Button>
              <Button
                onClick={handleCreateAccount}
                disabled={creatingAccount || !accountForm.password || !accountForm.passwordConfirm}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                {creatingAccount ? t('common.saving') : t('renter.createAccount')}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Settings Dialog */}
        <Dialog open={showSettingsDialog} onOpenChange={setShowSettingsDialog}>
          <DialogContent className="bg-slate-800 border-slate-700">
            <DialogHeader>
              <DialogTitle className="text-slate-100">{t('renter.settings')}</DialogTitle>
              <DialogDescription className="text-slate-400">
                {t('renter.settingsDesc')}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              {/* Email display/add */}
              <div>
                <Label className="text-slate-300">
                  <Mail className="w-4 h-4 inline mr-1" />
                  {t('common.email')}
                </Label>
                {info?.renter.email ? (
                  <div className="mt-1">
                    <p className="text-slate-200">{info.renter.email}</p>
                    {info.renter.email_set_by_landlord && (
                      <p className="text-xs text-slate-500">{t('renter.emailSetByLandlord')}</p>
                    )}
                  </div>
                ) : (
                  <div className="flex gap-2 mt-1">
                    <Input
                      type="email"
                      placeholder={t('auth.emailPlaceholder')}
                      className="bg-slate-700 border-slate-600 text-slate-100"
                      id="add-email-input"
                    />
                    <Button
                      onClick={() => {
                        const input = document.getElementById('add-email-input') as HTMLInputElement;
                        if (input?.value) handleAddEmail(input.value);
                      }}
                      disabled={savingPreferences}
                      className="bg-emerald-600 hover:bg-emerald-700"
                    >
                      {t('common.add')}
                    </Button>
                  </div>
                )}
              </div>
              
              {/* Email notifications toggle */}
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-slate-300">
                    <Bell className="w-4 h-4 inline mr-1" />
                    {t('renter.emailNotifications')}
                  </Label>
                  <p className="text-xs text-slate-500">{t('renter.emailNotificationsDesc')}</p>
                </div>
                <Checkbox
                  checked={info?.renter.email_notifications || false}
                  onCheckedChange={(checked) => handleEmailNotificationsToggle(!!checked)}
                  disabled={savingPreferences || !info?.renter.email}
                  className="border-slate-600 data-[state=checked]:bg-emerald-600"
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setShowSettingsDialog(false)}
                className="border-slate-600 text-slate-300 hover:bg-slate-700"
              >
                {t('common.close')}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </main>
    </div>
  );
}
