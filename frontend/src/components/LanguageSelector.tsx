import { useI18n, getAvailableLanguages } from '../lib/i18n';
import { usePreferences } from '../hooks/usePreferences';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { featureFlags } from '../lib/featureFlags';

// Flag images - served from public folder
// US_BUILD: US flag for English, French flag for French
// Standard: UK flag for English, Romanian flag for Romanian
const FLAG_IMAGES: Record<string, string> = featureFlags.usBuild ? {
  en: '/flags/us-flag.gif',
  fr: '/flags/fr-flag.png',
} : {
  ro: '/flags/ro-flag.gif',
  en: '/flags/uk-flag.gif',
  fr: '/flags/fr-flag.png',
};

const LANGUAGE_NAMES: Record<string, string> = {
  en: 'English',
  ro: 'Română',
  fr: 'Français',
};

const FLAG_ALTS: Record<string, string> = featureFlags.usBuild ? {
  en: 'US flag',
  fr: 'French flag',
} : {
  ro: 'Romanian flag',
  en: 'UK flag',
  fr: 'French flag',
};


export function LanguageSelector() {
  const { language, setLanguage } = useI18n();
  const { setLanguage: setPrefLanguage } = usePreferences();
  const availableLanguages = getAvailableLanguages();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="text-slate-300 hover:text-slate-100 hover:bg-slate-700"
        >
          <img 
            src={FLAG_IMAGES[language]} 
            alt={FLAG_ALTS[language]}
            className="h-4 w-auto mr-2"
          />
          <span className="text-xs uppercase">{language}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="bg-slate-800 border-slate-700">
        {availableLanguages.map((lang) => (
          <DropdownMenuItem
            key={lang}
            onClick={() => {
              setLanguage(lang);
              setPrefLanguage(lang);
            }}
            className="text-slate-100 hover:bg-slate-700 cursor-pointer flex items-center justify-start"
          >
            <img 
              src={FLAG_IMAGES[lang]} 
              alt={FLAG_ALTS[lang]}
              className="h-5 w-8 object-cover mr-3 flex-shrink-0"
            />
            <span className="flex-1 text-left">{LANGUAGE_NAMES[lang]}</span>
            {language === lang && <span className="ml-2 text-emerald-400 flex-shrink-0">✓</span>}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

