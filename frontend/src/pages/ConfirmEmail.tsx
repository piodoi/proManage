import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Check, X } from 'lucide-react';
import { useI18n } from '../lib/i18n';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function ConfirmEmail() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login, user, token } = useAuth();
  const { t } = useI18n();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [error, setError] = useState('');

  // Check if user is already logged in
  useEffect(() => {
    if (user && token) {
      // User is already logged in, redirect to dashboard
      navigate('/');
      return;
    }
  }, [user, token, navigate]);

  useEffect(() => {
    // If already logged in, don't process token
    if (user && token) {
      return;
    }

    const tokenParam = searchParams.get('token');
    
    if (!tokenParam) {
      setStatus('error');
      setError(t('auth.noToken'));
      return;
    }

    const confirmEmail = async () => {
      try {
        const response = await fetch(`${API_URL}/auth/confirm-email`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: tokenParam }),
        });

        if (response.ok) {
          const data = await response.json();
          setStatus('success');
          login(data.access_token, data.user, data.preferences);
          // Don't auto-redirect, let user click button
        } else {
          const err = await response.json();
          setStatus('error');
          setError(err.detail || t('auth.confirmEmailFailed'));
        }
      } catch {
        setStatus('error');
        setError(t('errors.connectionError'));
      }
    };

    confirmEmail();
  }, [searchParams, login, user, token]);

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <Card className="w-full max-w-md bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-2xl text-center text-slate-100">
            {t('auth.emailConfirmation')}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {status === 'loading' && (
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500 mx-auto mb-4"></div>
              <p className="text-slate-300">{t('auth.confirmingEmail')}</p>
            </div>
          )}

          {status === 'success' && (
            <div className="text-center">
              <div className="w-12 h-12 bg-emerald-500 rounded-full flex items-center justify-center mx-auto mb-4">
                <Check className="w-6 h-6 text-white" />
              </div>
              <p className="text-emerald-400 font-medium mb-2">{t('auth.emailConfirmed')}</p>
              <p className="text-slate-400 text-sm mb-4">{t('auth.accountActivated')}</p>
              <Button
                onClick={() => navigate('/')}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                {t('auth.goToDashboard')}
              </Button>
            </div>
          )}

          {status === 'error' && (
            <div className="text-center">
              <div className="w-12 h-12 bg-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
                <X className="w-6 h-6 text-white" />
              </div>
              <p className="text-red-400 font-medium mb-2">{t('auth.confirmationFailed')}</p>
              <p className="text-slate-400 text-sm mb-4">{error}</p>
              <p className="text-slate-500 text-xs mb-4">
                {error.toLowerCase().includes('expired') || error.toLowerCase().includes('invalid')
                  ? t('auth.linkExpired')
                  : t('auth.tryAgainOrContact')}
              </p>
              <Button
                onClick={() => navigate('/login')}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                {t('auth.goToLogin')}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
