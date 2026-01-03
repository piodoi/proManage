import { useState, useEffect, useCallback, useRef } from 'react';
import { api, Preferences } from '../api';
import { useAuth } from '../App';

const DEBOUNCE_DELAY = 500; // 500ms debounce delay

export function usePreferences() {
  const { token } = useAuth();
  const [preferences, setPreferences] = useState<Preferences>({
    language: 'en',
    view_mode: 'list',
    rent_warning_days: 5,
    rent_currency: 'EUR',
    bill_currency: 'RON',
    phone_number: null,
    landlord_name: null,
    personal_email: null,
    iban: null
  });
  const [loading, setLoading] = useState(true);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const pendingSaveRef = useRef<Partial<Preferences> | null>(null);

  // Load preferences on mount
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
          .then(saved => {
            setPreferences(saved);
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

  return {
    preferences,
    loading,
    setLanguage: (language: string) => savePreferences({ language }),
    setViewMode: (view_mode: string) => savePreferences({ view_mode }),
    setRentWarningDays: (rent_warning_days: number) => savePreferences({ rent_warning_days }),
    setRentCurrency: (rent_currency: string) => savePreferences({ rent_currency }),
    setBillCurrency: (bill_currency: string) => savePreferences({ bill_currency }),
    setPhoneNumber: (phone_number: string | null) => savePreferences({ phone_number }),
    setLandlordName: (landlord_name: string | null) => savePreferences({ landlord_name }),
    setPersonalEmail: (personal_email: string | null) => savePreferences({ personal_email }),
    setIban: (iban: string | null) => savePreferences({ iban }),
    savePreferences,
  };
}

