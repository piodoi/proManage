import { useState } from 'react';
import { useAuth } from '../App';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: { client_id: string; callback: (response: { credential: string }) => void }) => void;
          renderButton: (element: HTMLElement, config: { theme: string; size: string }) => void;
        };
      };
    };
    FB?: {
      init: (config: { appId: string; version: string }) => void;
      login: (callback: (response: { authResponse?: { accessToken: string } }) => void, config: { scope: string }) => void;
    };
  }
}

export default function Login() {
  const { login } = useAuth();
  const [error, setError] = useState('');
  const [demoMode, setDemoMode] = useState(false);
  const [demoEmail, setDemoEmail] = useState('');
  const [demoName, setDemoName] = useState('');

  const handleDemoLogin = async () => {
    if (!demoEmail || !demoName) {
      setError('Please enter email and name for demo');
      return;
    }
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/auth/demo?email=${encodeURIComponent(demoEmail)}&name=${encodeURIComponent(demoName)}`,
        { method: 'POST' }
      );
      if (response.ok) {
        const data = await response.json();
        login(data.access_token, data.user);
      } else {
        setError('Demo login failed. Is the backend running?');
      }
    } catch {
      setError('Could not connect to backend. Make sure it is running on port 8000.');
    }
  };

  const handleGoogleLogin = async () => {
    setError('Google OAuth requires configuration. Use demo mode for testing.');
  };

  const handleFacebookLogin = async () => {
    setError('Facebook OAuth requires configuration. Use demo mode for testing.');
  };

  const handleAdminLogin = async () => {
    try {
      const mockToken = btoa(JSON.stringify({ sub: 'admin-1', email: 'admin@promanage.local', role: 'admin' }));
      login(mockToken, {
        id: 'admin-1',
        email: 'admin@promanage.local',
        name: 'System Admin',
        role: 'admin',
        subscription_status: 'none',
        created_at: new Date().toISOString(),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <Card className="w-full max-w-md bg-slate-800 border-slate-700">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl text-slate-100">ProManage</CardTitle>
          <CardDescription className="text-slate-400">
            Property & Rent Management
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <div className="p-3 bg-red-900/50 border border-red-700 rounded text-red-200 text-sm">
              {error}
            </div>
          )}

          {!demoMode ? (
            <>
              <Button
                onClick={handleGoogleLogin}
                className="w-full bg-white text-slate-900 hover:bg-slate-100"
              >
                <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                  <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Continue with Google
              </Button>

              <Button
                onClick={handleFacebookLogin}
                className="w-full bg-blue-600 hover:bg-blue-700"
              >
                <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                </svg>
                Continue with Facebook
              </Button>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t border-slate-600" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-slate-800 px-2 text-slate-400">Or</span>
                </div>
              </div>

              <Button
                onClick={() => setDemoMode(true)}
                variant="outline"
                className="w-full border-slate-600 text-slate-300 hover:bg-slate-700"
              >
                Demo Mode (Landlord)
              </Button>

              <Button
                onClick={handleAdminLogin}
                variant="outline"
                className="w-full border-slate-600 text-slate-300 hover:bg-slate-700"
              >
                Admin Login
              </Button>
            </>
          ) : (
            <>
              <div className="space-y-2">
                <Label htmlFor="email" className="text-slate-300">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={demoEmail}
                  onChange={(e) => setDemoEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="bg-slate-700 border-slate-600 text-slate-100"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="name" className="text-slate-300">Name</Label>
                <Input
                  id="name"
                  value={demoName}
                  onChange={(e) => setDemoName(e.target.value)}
                  placeholder="Your Name"
                  className="bg-slate-700 border-slate-600 text-slate-100"
                />
              </div>
              <Button
                onClick={handleDemoLogin}
                className="w-full bg-emerald-600 hover:bg-emerald-700"
              >
                Start Demo
              </Button>
              <Button
                onClick={() => setDemoMode(false)}
                variant="outline"
                className="w-full border-slate-600 text-slate-300 hover:bg-slate-700"
              >
                Back
              </Button>
            </>
          )}

          <p className="text-xs text-slate-500 text-center mt-4">
            Renters: Use the link provided by your landlord
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
