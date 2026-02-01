import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect, createContext, useContext } from 'react';
import { api, User } from './api';
import Dashboard from './pages/Dashboard';
import RenterView from './pages/RenterView';
import Login from './pages/Login';
import ConfirmEmail from './pages/ConfirmEmail';
import HelpManualView from './components/HelpManualView';
import PrivacyPolicy from './pages/PrivacyPolicy';
import TermsOfService from './pages/TermsOfService';
import { I18nProvider, useI18n } from './lib/i18n';
import { PreferencesProvider } from './hooks/usePreferences.tsx';
import { SubscriptionProvider } from './hooks/useSubscription.tsx';
import './App.css';

type AuthContextType = {
  user: User | null;
  token: string | null;
  login: (token: string, user: User, preferences?: { language?: string; view_mode?: string }) => void;
  logout: () => void;
};

export const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  login: () => {},
  logout: () => {},
});

export const useAuth = () => useContext(AuthContext);

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      api.auth.me(token)
        .then(setUser)
        .catch(() => {
          localStorage.removeItem('token');
          setToken(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [token]);

  const login = (newToken: string, newUser: User, preferences?: { language?: string; view_mode?: string }) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
    setUser(newUser);
    
    // Apply preferences if provided
    if (preferences?.language) {
      localStorage.setItem('language', preferences.language);
    }
    if (preferences?.view_mode) {
      localStorage.setItem('view_mode', preferences.view_mode);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  if (loading) {
    return (
      <I18nProvider>
        <LoadingScreen />
      </I18nProvider>
    );
  }

  return (
    <I18nProvider>
      <AuthContext.Provider value={{ user, token, login, logout }}>
        <PreferencesProvider>
          <SubscriptionProvider token={token}>
            <BrowserRouter>
              <Routes>
                <Route path="/login" element={user ? <Navigate to="/" /> : <Login />} />
                <Route path="/confirm-email" element={<ConfirmEmail />} />
                <Route path="/help" element={<HelpManualView />} />
                <Route path="/privacy" element={<PrivacyPolicy />} />
                <Route path="/terms" element={<TermsOfService />} />
                <Route path="/renter/:token" element={<RenterView />} />
                <Route
                  path="/*"
                  element={
                    user ? (
                      <Dashboard />
                    ) : (
                      <Navigate to="/login" />
                    )
                  }
                />
              </Routes>
            </BrowserRouter>
          </SubscriptionProvider>
        </PreferencesProvider>
      </AuthContext.Provider>
    </I18nProvider>
  );
}

function LoadingScreen() {
  const { t } = useI18n();
  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
      <div className="text-slate-400">{t('common.loading')}</div>
    </div>
  );
}

export default App
