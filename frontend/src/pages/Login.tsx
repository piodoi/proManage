import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../App';
import { Button } from '@/components/ui/button';
import HeaderBar from '@/components/HeaderBar';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useI18n } from '../lib/i18n';
import { featureFlags } from '../lib/featureFlags';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

interface GooglePromptNotification {
  isNotDisplayed: () => boolean;
  isSkippedMoment: () => boolean;
  isDismissedMoment: () => boolean;
  getNotDisplayedReason: () => string;
  getSkippedReason: () => string;
  getDismissedReason: () => string;
}

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: { client_id: string; callback: (response: { credential: string }) => void }) => void;
          renderButton: (element: HTMLElement, config: { theme: string; size: string; width?: number }) => void;
          prompt: (callback?: (notification: GooglePromptNotification) => void) => void;
        };
      };
    };
    FB?: {
      init: (config: { appId: string; version: string }) => void;
      login: (callback: (response: { authResponse?: { accessToken: string } }) => void, config: { scope: string }) => void;
    };
  }
}

type AuthMode = 'main' | 'demo' | 'register' | 'login' | 'confirm';

export default function Login() {
  const { login } = useAuth();
  const { t } = useI18n();
  const [error, setError] = useState('');
  const [authMode, setAuthMode] = useState<AuthMode>('main');
  const [demoEmail, setDemoEmail] = useState('');
  const [demoName, setDemoName] = useState('');
  const [formEmail, setFormEmail] = useState('');
  const [formPassword, setFormPassword] = useState('');
  const [formName, setFormName] = useState('');
    const [loading, setLoading] = useState(false);
    const [confirmationToken, setConfirmationToken] = useState('');
    const [emailSent, setEmailSent] = useState(false);

  const handleGoogleCredential = useCallback(async (credential: string) => {
    try {
      const response = await fetch(`${API_URL}/auth/google?id_token=${encodeURIComponent(credential)}`, {
        method: 'POST',
      });
      if (response.ok) {
        const data = await response.json();
        login(data.access_token, data.user, data.preferences);
      } else {
        const err = await response.json();
        setError(err.detail || 'Google login failed');
      }
    } catch {
      setError('Could not connect to backend. Make sure it is running.');
    }
  }, [login]);

  useEffect(() => {
    console.log('[Google OAuth] Initializing, GOOGLE_CLIENT_ID present:', !!GOOGLE_CLIENT_ID);
    if (!GOOGLE_CLIENT_ID) {
      console.warn('[Google OAuth] No GOOGLE_CLIENT_ID configured, skipping GIS load');
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => {
      console.log('[Google OAuth] GIS script loaded');
      if (window.google) {
        console.log('[Google OAuth] window.google available, initializing...');
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: (response: { credential: string }) => {
            console.log('[Google OAuth] Credential received from Google');
            handleGoogleCredential(response.credential);
          },
        });
        // Render a visible Google button as a fallback for environments where One Tap is suppressed
        try {
          const el = document.getElementById('google-button');
          if (el) {
            window.google.accounts.id.renderButton(el, { theme: 'outline', size: 'large', width: 400 });
          }
        } catch (e) {
          console.warn('[Google OAuth] renderButton failed', e);
        }
        console.log('[Google OAuth] Initialization complete');
      } else {
        console.error('[Google OAuth] window.google not available after script load');
      }
    };
    script.onerror = (e) => {
      console.error('[Google OAuth] Failed to load GIS script:', e);
    };
    document.body.appendChild(script);
    return () => {
      document.body.removeChild(script);
    };
  }, [handleGoogleCredential]);

  const handleDemoLogin = async () => {
    if (!demoEmail || !demoName) {
      setError(t('auth.demoEmailRequired'));
      return;
    }
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/auth/demo?email=${encodeURIComponent(demoEmail)}&name=${encodeURIComponent(demoName)}`,
        { method: 'POST' }
      );
      if (response.ok) {
        const data = await response.json();
        login(data.access_token, data.user, data.preferences);
      } else {
        setError('Demo login failed. Is the backend running?');
      }
    } catch {
      setError('Could not connect to backend. Make sure it is running on port 8000.');
    }
  };

  const handleFacebookLogin = async () => {
    setError('Facebook OAuth requires configuration. Use demo mode for testing.');
  };

  const handleEmailRegister = async () => {
    if (!formEmail || !formPassword || !formName) {
      setError(t('auth.fillAllFields'));
      return;
    }
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: formEmail, password: formPassword, name: formName }),
      });
            if (response.ok) {
              const data = await response.json();
              setAuthMode('confirm');
              setEmailSent(data.email_sent || false);
              if (data.confirmation_token) {
                setConfirmationToken(data.confirmation_token);
              }
              setError('');
            }else {
        const err = await response.json();
        setError(err.detail || 'Registration failed');
      }
    } catch {
      setError('Could not connect to backend. Make sure it is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmEmail = async () => {
    if (!confirmationToken) {
      setError('No confirmation token');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_URL}/auth/confirm-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: confirmationToken }),
      });
      if (response.ok) {
        const data = await response.json();
        login(data.access_token, data.user, data.preferences);
      } else {
        const err = await response.json();
        setError(err.detail || 'Confirmation failed');
      }
    } catch {
      setError('Could not connect to backend. Make sure it is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleEmailLogin = async () => {
    if (!formEmail || !formPassword) {
      setError(t('auth.enterEmailPassword'));
      return;
    }
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: formEmail, password: formPassword }),
      });
      if (response.ok) {
        const data = await response.json();
        login(data.access_token, data.user, data.preferences);
      } else {
        const err = await response.json();
        setError(err.detail || 'Login failed');
      }
    } catch {
      setError('Could not connect to backend. Make sure it is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900">
      <HeaderBar />
      <div className="flex items-center justify-center p-4">
        <Card className="w-full max-w-md bg-slate-800 border-slate-700">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl text-slate-100">{t('app.title')}</CardTitle>
            <CardDescription className="text-slate-400">{t('app.subtitle')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {error && (
              <div className="p-3 bg-red-900/50 border border-red-700 rounded text-red-200 text-sm">{error}</div>
            )}

            {authMode === 'main' && (
              <React.Fragment>
                <Button
                  onClick={() => setAuthMode('login')}
                  className="w-full bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600"
                >
                  {t('auth.signIn')}
                </Button>

                <Button
                  onClick={() => setAuthMode('register')}
                  className="w-full bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600"
                >
                  {t('auth.createAccount')}
                </Button>

                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t border-slate-600" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-slate-800 px-2 text-slate-400">{t('common.or')}</span>
                  </div>
                </div>

                <div id="google-button" className="w-full [&>div]:w-full [&>div>div]:w-full" />

                {featureFlags.facebookLogin && (
                  <Button onClick={handleFacebookLogin} className="w-full bg-blue-600 hover:bg-blue-700">
                    {t('auth.continueWithFacebook')}
                  </Button>
                )}

                {featureFlags.demoLogin && (
                  <React.Fragment>
                    <div className="relative">
                      <div className="absolute inset-0 flex items-center">
                        <span className="w-full border-t border-slate-600" />
                      </div>
                      <div className="relative flex justify-center text-xs uppercase">
                        <span className="bg-slate-800 px-2 text-slate-400">Dev</span>
                      </div>
                    </div>

                    <Button onClick={() => setAuthMode('demo')} variant="ghost" className="w-full text-slate-500 hover:text-slate-300 hover:bg-slate-700">
                      {t('auth.demoMode')}
                    </Button>
                  </React.Fragment>
                )}
              </React.Fragment>
            )}

            {authMode === 'login' && (
              <React.Fragment>
                <div className="space-y-2">
                  <Label htmlFor="login-email" className="text-slate-300">{t('common.email')}</Label>
                  <Input
                    id="login-email"
                    type="email"
                    value={formEmail}
                    onChange={(e) => setFormEmail(e.target.value)}
                    placeholder={t('auth.emailPlaceholder')}
                    className="bg-slate-700 border-slate-600 text-slate-100"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="login-password" className="text-slate-300">{t('common.password')}</Label>
                  <Input
                    id="login-password"
                    type="password"
                    value={formPassword}
                    onChange={(e) => setFormPassword(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleEmailLogin();
                      }
                    }}
                    placeholder={t('renter.passwordPlaceholder')}
                    className="bg-slate-700 border-slate-600 text-slate-100"
                  />
                </div>
                <Button onClick={handleEmailLogin} disabled={loading} className="w-full bg-emerald-600 hover:bg-emerald-700">
                  {loading ? t('auth.signingIn') : t('auth.signInButton')}
                </Button>
                <Button onClick={() => { setAuthMode('main'); setError(''); }} className="w-full bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600">
                  {t('common.back')}
                </Button>
                <p className="text-xs text-slate-500 text-center">
                  {t('auth.dontHaveAccount')}{' '}
                  <button onClick={() => setAuthMode('register')} className="text-emerald-400 hover:underline">{t('auth.createOne')}</button>
                </p>
              </React.Fragment>
            )}

            {authMode === 'register' && (
              <React.Fragment>
                <div className="space-y-2">
                  <Label htmlFor="register-name" className="text-slate-300">{t('common.name')}</Label>
                  <Input id="register-name" value={formName} onChange={(e) => setFormName(e.target.value)} placeholder={t('auth.namePlaceholder')} className="bg-slate-700 border-slate-600 text-slate-100" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="register-email" className="text-slate-300">{t('common.email')}</Label>
                  <Input id="register-email" type="email" value={formEmail} onChange={(e) => setFormEmail(e.target.value)} placeholder={t('auth.emailPlaceholder')} className="bg-slate-700 border-slate-600 text-slate-100" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="register-password" className="text-slate-300">{t('common.password')}</Label>
                  <Input id="register-password" type="password" value={formPassword} onChange={(e) => setFormPassword(e.target.value)} placeholder={t('auth.minPassword')} className="bg-slate-700 border-slate-600 text-slate-100" />
                </div>
                <Button onClick={handleEmailRegister} disabled={loading} className="w-full bg-emerald-600 hover:bg-emerald-700">{loading ? t('auth.creatingAccount') : t('auth.createAccountButton')}</Button>
                <Button onClick={() => { setAuthMode('main'); setError(''); }} className="w-full bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600">{t('common.back')}</Button>
                <p className="text-xs text-slate-500 text-center">{t('auth.alreadyHaveAccount')}{' '}<button onClick={() => setAuthMode('login')} className="text-emerald-400 hover:underline">{t('auth.signInButton')}</button></p>
              </React.Fragment>
            )}

            {authMode === 'confirm' && (
              <React.Fragment>
                {emailSent ? (
                  <div className="p-4 bg-emerald-900/30 border border-emerald-700 rounded text-emerald-200 text-sm">
                    <p className="font-medium mb-2">{t('auth.checkEmail')}</p>
                    <p className="text-xs text-emerald-300">{t('auth.emailSent')}</p>
                    <p className="text-xs text-emerald-300 mt-2">{t('auth.linkExpires')}</p>
                  </div>
                ) : (
                  <React.Fragment>
                    <div className="p-4 bg-amber-900/30 border border-amber-700 rounded text-amber-200 text-sm">
                      <p className="font-medium mb-2">{t('auth.emailNotConfigured')}</p>
                      <p className="text-xs text-amber-300">{t('auth.emailNotConfiguredDesc')}</p>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="confirm-token" className="text-slate-300">{t('auth.confirmationToken')}</Label>
                      <Input id="confirm-token" value={confirmationToken} onChange={(e) => setConfirmationToken(e.target.value)} placeholder={t('auth.pasteToken')} className="bg-slate-700 border-slate-600 text-slate-100 font-mono text-xs" />
                    </div>
                    <Button onClick={handleConfirmEmail} disabled={loading || !confirmationToken} className="w-full bg-emerald-600 hover:bg-emerald-700">{loading ? t('auth.confirming') : t('auth.confirmEmail')}</Button>
                  </React.Fragment>
                )}
                <Button onClick={() => { setAuthMode('main'); setError(''); setConfirmationToken(''); setEmailSent(false); }} className="w-full bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600">{emailSent ? t('auth.backToLogin') : t('common.cancel')}</Button>
              </React.Fragment>
            )}

            {authMode === 'demo' && (
              <React.Fragment>
                <div className="space-y-2">
                  <Label htmlFor="demo-email" className="text-slate-300">{t('common.email')}</Label>
                  <Input id="demo-email" type="email" value={demoEmail} onChange={(e) => setDemoEmail(e.target.value)} placeholder={t('auth.emailPlaceholder')} className="bg-slate-700 border-slate-600 text-slate-100" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="demo-name" className="text-slate-300">{t('common.name')}</Label>
                  <Input id="demo-name" value={demoName} onChange={(e) => setDemoName(e.target.value)} placeholder={t('auth.namePlaceholder')} className="bg-slate-700 border-slate-600 text-slate-100" />
                </div>
                <Button onClick={handleDemoLogin} className="w-full bg-emerald-600 hover:bg-emerald-700">{t('auth.startDemo')}</Button>
                <Button onClick={() => { setAuthMode('main'); setError(''); }} className="w-full bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600">{t('common.back')}</Button>
              </React.Fragment>
            )}

            <p className="text-xs text-slate-500 text-center mt-4">{t('auth.rentersUseLink')}</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
