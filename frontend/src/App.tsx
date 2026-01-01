import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect, createContext, useContext } from 'react';
import { api, User } from './api';
import AdminDashboard from './pages/AdminDashboard';
import LandlordDashboard from './pages/LandlordDashboard';
import RenterView from './pages/RenterView';
import Login from './pages/Login';
import ConfirmEmail from './pages/ConfirmEmail';
import { I18nProvider, useI18n } from './lib/i18n';
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
        <BrowserRouter>
          <Routes>
                      <Route path="/login" element={user ? <Navigate to="/" /> : <Login />} />
                      <Route path="/confirm-email" element={<ConfirmEmail />} />
                      <Route path="/renter/:token" element={<RenterView />} />
            <Route
              path="/admin/*"
              element={
                user?.role === 'admin' ? <AdminDashboard /> : <Navigate to="/login" />
              }
            />
            <Route
              path="/*"
              element={
                user ? (
                  user.role === 'admin' ? (
                    <Navigate to="/admin" />
                  ) : (
                    <LandlordDashboard />
                  )
                ) : (
                  <Navigate to="/login" />
                )
              }
            />
          </Routes>
        </BrowserRouter>
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
