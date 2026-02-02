import { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';
import enTranslations from '../locales/en.json';
import roTranslations from '../locales/ro.json';
import frTranslations from '../locales/fr.json';
import enLegal from '../locales/legal/en.json';
import roLegal from '../locales/legal/ro.json';
import frLegal from '../locales/legal/fr.json';
import { featureFlags } from './featureFlags';

type TranslationKey = string;

// Merge main translations with legal documents
const translations: Record<string, any> = {
  en: { ...enTranslations, ...enLegal },
  ro: { ...roTranslations, ...roLegal },
  fr: { ...frTranslations, ...frLegal },
};

type Language = 'en' | 'ro' | 'fr';

// Get default language based on build mode
function getDefaultLanguage(): Language {
  const saved = localStorage.getItem('language') as Language;
  if (featureFlags.usBuild) {
    // US build: allow 'en' or 'fr', default to 'en'
    return (saved === 'en' || saved === 'fr') ? saved : 'en';
  }
  // Standard build: allow 'en', 'ro', or 'fr', default to 'ro'
  return (saved === 'en' || saved === 'ro' || saved === 'fr') ? saved : 'ro';
}

// Validate language based on build mode
function validateLanguage(lang: string): Language {
  if (featureFlags.usBuild) {
    return (lang === 'en' || lang === 'fr') ? lang as Language : 'en';
  }
  return (lang === 'en' || lang === 'ro' || lang === 'fr') ? lang as Language : 'ro';
}

// Get available languages based on build mode
export function getAvailableLanguages(): Language[] {
  if (featureFlags.usBuild) {
    return ['en', 'fr'];
  }
  return ['ro', 'en', 'fr'];  // Romanian first (default), then English, then French
}

interface I18nContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextType | undefined>(undefined);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => getDefaultLanguage());
  
  // Use ref to track current language for storage event handler
  const languageRef = useRef(language);
  useEffect(() => {
    languageRef.current = language;
  }, [language]);

  // Listen for language changes from preferences (storage events)
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      // Only react to language key changes
      if (e.key !== 'language' && e.key !== null) return;
      
      const saved = localStorage.getItem('language') as Language;
      const validLang = validateLanguage(saved || 'en');
      // Only update if the language is valid AND different from current
      if (validLang !== languageRef.current) {
        setLanguageState(validLang);
      }
    };
    
    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []); // Empty deps - handler uses ref for current value

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem('language', lang);
  };

  const t = (key: TranslationKey, params?: Record<string, string | number>): string => {
    const keys = key.split('.');
    let value: any = translations[language];
    
    for (const k of keys) {
      if (value && typeof value === 'object' && k in value) {
        value = value[k];
      } else {
        // Fallback to English if key not found
        value = translations.en;
        for (const k2 of keys) {
          if (value && typeof value === 'object' && k2 in value) {
            value = value[k2];
          } else {
            return key; // Return key if not found in any language
          }
        }
        break;
      }
    }

    if (typeof value !== 'string') {
      return key;
    }

    // Replace parameters
    if (params) {
      return value.replace(/\{(\w+)\}/g, (match, paramKey) => {
        return params[paramKey]?.toString() || match;
      });
    }

    return value;
  };

  return (
    <I18nContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within an I18nProvider');
  }
  return context;
}

