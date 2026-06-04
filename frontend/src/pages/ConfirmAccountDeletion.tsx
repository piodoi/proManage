import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Check, X } from 'lucide-react';
import { api } from '../api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { useAuth } from '../App';
import { useI18n } from '../lib/i18n';

export default function ConfirmAccountDeletion() {
  const [searchParams] = useSearchParams();
  const { logout } = useAuth();
  const { t } = useI18n();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const userId = searchParams.get('user_id');
    const deletionToken = searchParams.get('token');
    const issuedAtParam = searchParams.get('issued_at');
    const issuedAt = issuedAtParam ? Number.parseInt(issuedAtParam, 10) : NaN;

    if (!userId || !deletionToken || Number.isNaN(issuedAt)) {
      setStatus('error');
      setMessage(t('settings.accountDeletionInvalidLink'));
      return;
    }

    api.auth
      .confirmAccountDeletion(userId, deletionToken, issuedAt)
      .then((response) => {
        logout();
        setStatus('success');
        setMessage(response.message || t('settings.accountDeletionCompleted'));
      })
      .catch((error: Error) => {
        setStatus('error');
        setMessage(error.message || t('settings.accountDeletionConfirmFailed'));
      });
  }, [logout, searchParams, t]);

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <Card className="w-full max-w-md bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-2xl text-center text-slate-100">{t('settings.accountDeletionPageTitle')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-center">
          {status === 'loading' && (
            <>
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-500 mx-auto" />
              <p className="text-slate-300">{t('settings.accountDeletionProcessing')}</p>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="w-12 h-12 bg-emerald-500 rounded-full flex items-center justify-center mx-auto">
                <Check className="w-6 h-6 text-white" />
              </div>
              <p className="text-emerald-300">{message}</p>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="w-12 h-12 bg-red-500 rounded-full flex items-center justify-center mx-auto">
                <X className="w-6 h-6 text-white" />
              </div>
              <p className="text-red-300">{message}</p>
            </>
          )}

          <Button asChild className="bg-emerald-600 hover:bg-emerald-700">
            <Link to="/">{t('settings.accountDeletionBackHome')}</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}