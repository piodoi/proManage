import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { api, RenterInfo, RenterBill, RenterBalance } from '../api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Building2, Receipt, CreditCard, Banknote } from 'lucide-react';
import { useI18n } from '../lib/i18n';
import { formatDateWithPreferences } from '../lib/utils';

export default function RenterView() {
  const { token } = useParams<{ token: string }>();
  const { t, language, setLanguage } = useI18n();
  const [info, setInfo] = useState<RenterInfo | null>(null);
  const [bills, setBills] = useState<RenterBill[]>([]);
  const [balance, setBalance] = useState<RenterBalance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [payingBill, setPayingBill] = useState<RenterBill | null>(null);

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

  const openPayDialog = (bill: RenterBill) => {
    setPayingBill(bill);
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
                  {bills.map((item) => (
                    <TableRow key={item.bill.id} className="border-slate-700">
                      <TableCell className="text-slate-200">{item.bill.description}</TableCell>
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
                      <TableCell className={item.bill.status === 'paid' || item.is_direct_debit ? 'text-green-400' : item.remaining > 0 ? 'text-amber-400' : 'text-green-400'}>
                        {item.bill.status === 'paid' || item.is_direct_debit ? (
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
                        {item.is_direct_debit ? (
                          <span className="px-3 py-1 rounded text-xs bg-blue-900 text-blue-200">
                            {t('bill.directDebit')}
                          </span>
                        ) : item.bill.status !== 'paid' ? (
                          <Button
                            size="sm"
                            onClick={() => openPayDialog(item)}
                            className="bg-emerald-600 hover:bg-emerald-700"
                          >
                            {t('renter.pay')}
                          </Button>
                        ) : null}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Balance Cards */}
        {balance && (
          <div className="grid grid-cols-3 gap-4 mb-6">
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="pt-6">
                <p className="text-slate-400 text-sm">{t('renter.totalThisMonth') || 'Total This Month'}</p>
                <p className="text-2xl font-bold text-slate-100">
                  {bills
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
                  {bills
                    .filter(b => b.bill.status === 'paid' && !b.is_direct_debit)
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
                
                {/* Bills breakdown inside balance card - only unpaid bills (excluding direct debit) */}
                {bills.filter(b => b.bill.status !== 'paid' && !b.is_direct_debit).length > 0 && (
                  <div className="mb-3 space-y-0.5 text-xs">
                    {bills.filter(b => b.bill.status !== 'paid' && !b.is_direct_debit).map((item) => (
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
        )}

        <Dialog open={!!payingBill} onOpenChange={(open) => !open && setPayingBill(null)}>
          <DialogContent className="bg-slate-800 border-slate-700">
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

              <div className="space-y-2">
                <p className="text-slate-300 text-sm">{t('renter.paymentMethod') || 'Payment Method'}:</p>
                
                {/* Supplier Payment Link - placeholder for future */}
                <Button
                  className="w-full bg-slate-700 text-slate-100 hover:bg-slate-600 border border-slate-600"
                  disabled
                >
                  <Banknote className="w-4 h-4 mr-2" />
                  Pay via Supplier Portal
                  <span className="ml-2 text-xs text-slate-500">(Coming soon)</span>
                </Button>

                {/* Stripe Payment */}
                <Button
                  className="w-full bg-emerald-600 hover:bg-emerald-700"
                  disabled
                >
                  <CreditCard className="w-4 h-4 mr-2" />
                  Pay with Stripe
                  <span className="ml-2 text-xs text-emerald-200">(Coming soon)</span>
                </Button>
              </div>

              <p className="text-xs text-slate-500 text-center">
                Payment integration will be available soon
              </p>
            </div>
          </DialogContent>
        </Dialog>
      </main>
    </div>
  );
}
