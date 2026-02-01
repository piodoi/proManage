import { useState, useEffect, useCallback, useRef, createContext, useContext, ReactNode } from 'react';
import { api, Preferences } from '../api';
import { useAuth } from '../App';

const DEBOUNCE_DELAY = 500; // 500ms debounce delay

const defaultPreferences: Preferences = {
  language: 'en',
  view_mode: 'list',
  rent_warning_days: 5,
  rent_currency: 'EUR',
  bill_currency: 'RON',
  date_format: 'DD/MM/YYYY',
  phone_number: null,
  landlord_name: null,
  personal_email: null,
  iban: null,
  iban_eur: null,
  iban_usd: null,
  property_order: null
};

type PreferencesContextType = {
  preferences: Preferences;
  loading: boolean;
  setLanguage: (language: string) => void;
  setViewMode: (view_mode: string) => void;
  setRentWarningDays: (rent_warning_days: number) => void;
  setRentCurrency: (rent_currency: string) => void;
  setBillCurrency: (bill_currency: string) => void;
  setDateFormat: (date_format: string) => void;
  setPhoneNumber: (phone_number: string | null) => void;
  setLandlordName: (landlord_name: string | null) => void;
  setPersonalEmail: (personal_email: string | null) => void;
  setIban: (iban: string | null) => void;
  setIbanEur: (iban_eur: string | null) => void;
  setIbanUsd: (iban_usd: string | null) => void;
  setPropertyOrder: (property_order: string[] | null) => void;
  savePreferences: (updates: Partial<Preferences>) => void;
};

const PreferencesContext = createContext<PreferencesContextType | null>(null);

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  const [preferences, setPreferences] = useState<Preferences>(defaultPreferences);
  const [loading, setLoading] = useState(true);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const pendingSaveRef = useRef<Partial<Preferences> | null>(null);

  // Load preferences on mount or token change
  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    api.preferences.get(token)
      .then(setPreferences)
      .catch(err => {
        console.error('[usePreferences] Failed to load preferences:', err);
        // Use defaults on error
      })
      .finally(() => setLoading(false));
  }, [token]);

  // Sync preferences.language to localStorage and trigger i18n update
  useEffect(() => {
    if (preferences.language) {
      const currentLang = localStorage.getItem('language');
      if (currentLang !== preferences.language) {
        localStorage.setItem('language', preferences.language);
        // Dispatch storage event to notify i18n context
        window.dispatchEvent(new StorageEvent('storage', {
          key: 'language',
          newValue: preferences.language,
          oldValue: currentLang,
        }));
      }
    }
  }, [preferences.language]);

  // Save preferences with debouncing
  const savePreferences = useCallback((updates: Partial<Preferences>) => {
    if (!token) return;

    // Update local state immediately for responsive UI
    setPreferences(prev => ({ ...prev, ...updates }));
    
    // Store pending updates
    pendingSaveRef.current = { ...pendingSaveRef.current, ...updates };

    // Clear existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Set new timer
    debounceTimerRef.current = setTimeout(() => {
      if (pendingSaveRef.current) {
        const toSave = pendingSaveRef.current;
        pendingSaveRef.current = null;
        
        api.preferences.save(token, toSave)
          .then(() => {
            // Don't update state here - we already updated optimistically
            // Updating again would create a new object reference and trigger re-renders
          })
          .catch(err => {
            console.error('[usePreferences] Failed to save preferences:', err);
            // Revert to previous state on error
            api.preferences.get(token)
              .then(setPreferences)
              .catch(() => {
                // If we can't reload, at least log the error
                console.error('[usePreferences] Failed to reload preferences after save error');
              });
          });
      }
    }, DEBOUNCE_DELAY);
  }, [token]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  const value: PreferencesContextType = {
    preferences,
    loading,
    setLanguage: (language: string) => savePreferences({ language }),
    setViewMode: (view_mode: string) => savePreferences({ view_mode }),
    setRentWarningDays: (rent_warning_days: number) => savePreferences({ rent_warning_days }),
    setRentCurrency: (rent_currency: string) => savePreferences({ rent_currency }),
    setBillCurrency: (bill_currency: string) => savePreferences({ bill_currency }),
    setDateFormat: (date_format: string) => savePreferences({ date_format }),
    setPhoneNumber: (phone_number: string | null) => savePreferences({ phone_number }),
    setLandlordName: (landlord_name: string | null) => savePreferences({ landlord_name }),
    setPersonalEmail: (personal_email: string | null) => savePreferences({ personal_email }),
    setIban: (iban: string | null) => savePreferences({ iban }),
    setIbanEur: (iban_eur: string | null) => savePreferences({ iban_eur }),
    setIbanUsd: (iban_usd: string | null) => savePreferences({ iban_usd }),
    setPropertyOrder: (property_order: string[] | null) => savePreferences({ property_order }),
    savePreferences,
  };

  return (
    <PreferencesContext.Provider value={value}>
      {children}
    </PreferencesContext.Provider>
  );
}

export function usePreferences() {
  const context = useContext(PreferencesContext);
  if (!context) {
    throw new Error('usePreferences must be used within a PreferencesProvider');
  }
  return context;
}

