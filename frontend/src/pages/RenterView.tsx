import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { api, RenterInfo, RenterBill, RenterBalance, PaymentResponse } from '../api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Building2, Receipt, CreditCard, Banknote, Copy } from 'lucide-react';
import { useI18n } from '../lib/i18n';

export default function RenterView() {
  const { token } = useParams<{ token: string }>();
  const { t } = useI18n();
  const [info, setInfo] = useState<RenterInfo | null>(null);
  const [bills, setBills] = useState<RenterBill[]>([]);
  const [balance, setBalance] = useState<RenterBalance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [payingBill, setPayingBill] = useState<RenterBill | null>(null);
  const [paymentMethod, setPaymentMethod] = useState<'bank_transfer' | 'payment_service'>('bank_transfer');
  const [paymentAmount, setPaymentAmount] = useState('');
  const [paymentResult, setPaymentResult] = useState<PaymentResponse | null>(null);

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

  const handlePay = async () => {
    if (!token || !payingBill) return;
    try {
      const result = await api.renter.pay(token, {
        bill_id: payingBill.bill.id,
        amount: parseFloat(paymentAmount),
        method: paymentMethod,
      });
      setPaymentResult(result);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.generic'));
    }
  };

  const openPayDialog = (bill: RenterBill) => {
    setPayingBill(bill);
    setPaymentAmount(bill.remaining.toString());
    setPaymentMethod('bank_transfer');
    setPaymentResult(null);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
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
        <div className="flex items-center gap-3">
          <Building2 className="w-6 h-6 text-emerald-500" />
          <div>
            <h1 className="text-xl font-semibold text-slate-100">{t('app.title')}</h1>
            <p className="text-sm text-slate-400">{t('renter.portal')}</p>
          </div>
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

        {balance && (
          <div className="grid grid-cols-3 gap-4 mb-6">
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="pt-6">
                <p className="text-slate-400 text-sm">{t('renter.totalDue')}</p>
                <p className="text-2xl font-bold text-slate-100">{balance.total_due.toFixed(2)} RON</p>
              </CardContent>
            </Card>
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="pt-6">
                <p className="text-slate-400 text-sm">{t('renter.totalPaid')}</p>
                <p className="text-2xl font-bold text-green-400">{balance.total_paid.toFixed(2)} RON</p>
              </CardContent>
            </Card>
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="pt-6">
                <p className="text-slate-400 text-sm">{t('renter.balance')}</p>
                <p className={`text-2xl font-bold ${balance.balance > 0 ? 'text-amber-400' : 'text-green-400'}`}>
                  {balance.balance.toFixed(2)} RON
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        <Card className="bg-slate-800 border-slate-700">
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
                      <TableCell className="text-slate-200">{item.bill.amount.toFixed(2)} RON</TableCell>
                      <TableCell className={item.remaining > 0 ? 'text-amber-400' : 'text-green-400'}>
                        {item.remaining.toFixed(2)} RON
                      </TableCell>
                      <TableCell className="text-slate-300">
                        {new Date(item.bill.due_date).toLocaleDateString()}
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
                        {item.remaining > 0 && (
                          <Button
                            size="sm"
                            onClick={() => openPayDialog(item)}
                            className="bg-emerald-600 hover:bg-emerald-700"
                          >
                            {t('renter.pay')}
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Dialog open={!!payingBill} onOpenChange={(open) => !open && setPayingBill(null)}>
          <DialogContent className="bg-slate-800 border-slate-700">
            <DialogHeader>
              <DialogTitle className="text-slate-100">{t('renter.payBill')}</DialogTitle>
            </DialogHeader>
            {!paymentResult ? (
              <div className="space-y-4">
                <div>
                  <p className="text-slate-300">{payingBill?.bill.description}</p>
                  <p className="text-slate-400 text-sm">{t('renter.remaining')}: {payingBill?.remaining.toFixed(2)} RON</p>
                </div>

                <div>
                  <Label className="text-slate-300">{t('renter.paymentAmount')}</Label>
                  <Input
                    type="number"
                    value={paymentAmount}
                    onChange={(e) => setPaymentAmount(e.target.value)}
                    className="bg-slate-700 border-slate-600 text-slate-100"
                  />
                </div>

                <div>
                  <Label className="text-slate-300">{t('renter.paymentMethod')}</Label>
                  <div className="grid grid-cols-2 gap-2 mt-2">
                    <Button
                      variant={paymentMethod === 'bank_transfer' ? 'default' : 'outline'}
                      onClick={() => setPaymentMethod('bank_transfer')}
                      className={paymentMethod === 'bank_transfer' ? 'bg-emerald-600' : 'bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600'}
                    >
                      <Banknote className="w-4 h-4 mr-2" />
                      {t('renter.bankTransfer')}
                    </Button>
                    <Button
                      variant={paymentMethod === 'payment_service' ? 'default' : 'outline'}
                      onClick={() => setPaymentMethod('payment_service')}
                      className={paymentMethod === 'payment_service' ? 'bg-emerald-600' : 'bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600'}
                    >
                      <CreditCard className="w-4 h-4 mr-2" />
                      {t('renter.paymentService')}
                    </Button>
                  </div>
                </div>

                {paymentMethod === 'payment_service' && (
                  <p className="text-amber-400 text-sm">
                    {t('renter.commission')}: {(parseFloat(paymentAmount || '0') * 0.02).toFixed(2)} RON {t('renter.totalWithCommission')}
                  </p>
                )}

                <Button onClick={handlePay} className="w-full bg-emerald-600 hover:bg-emerald-700">
                  {paymentMethod === 'bank_transfer' ? t('renter.bankTransfer') : t('renter.pay')}
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {paymentResult.bank_transfer_info ? (
                  <>
                    <p className="text-green-400">{t('renter.bankTransferDetails')}</p>
                    <div className="bg-slate-700 p-4 rounded space-y-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-slate-400 text-xs">{t('renter.iban')}</p>
                          <p className="text-slate-100 font-mono">{paymentResult.bank_transfer_info.iban}</p>
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => copyToClipboard(paymentResult.bank_transfer_info!.iban)}
                          className="text-slate-400"
                        >
                          <Copy className="w-4 h-4" />
                        </Button>
                      </div>
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-slate-400 text-xs">{t('renter.reference')}</p>
                          <p className="text-slate-100">{paymentResult.bank_transfer_info.reference}</p>
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => copyToClipboard(paymentResult.bank_transfer_info!.reference)}
                          className="text-slate-400"
                        >
                          <Copy className="w-4 h-4" />
                        </Button>
                      </div>
                      <div>
                        <p className="text-slate-400 text-xs">{t('common.amount')}</p>
                        <p className="text-slate-100 text-lg font-bold">{paymentResult.bank_transfer_info.amount.toFixed(2)} RON</p>
                      </div>
                    </div>
                    <p className="text-slate-400 text-sm">
                      {t('renter.pleaseMakeTransfer')}
                    </p>
                  </>
                ) : (
                  <>
                    <p className="text-green-400">{t('renter.paymentInitiated')}</p>
                    <div className="bg-slate-700 p-4 rounded">
                      <p className="text-slate-300">{t('common.amount')}: {paymentResult.payment.amount.toFixed(2)} RON</p>
                      {paymentResult.commission > 0 && (
                        <p className="text-slate-400 text-sm">{t('renter.commission')}: {paymentResult.commission.toFixed(2)} RON</p>
                      )}
                      <p className="text-slate-100 font-bold mt-2">
                        {t('renter.totalWithCommission')}: {paymentResult.total_with_commission.toFixed(2)} RON
                      </p>
                    </div>
                  </>
                )}
                <Button
                  onClick={() => { setPayingBill(null); setPaymentResult(null); }}
                  className="w-full bg-slate-700 hover:bg-slate-600"
                >
                  {t('common.close')}
                </Button>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </main>
    </div>
  );
}
