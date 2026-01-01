import { useI18n } from '../lib/i18n';
import { usePreferences } from '../hooks/usePreferences';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

// Flag images - served from public folder
const FLAG_IMAGES: Record<string, string> = {
  en: '/flags/uk-flag.gif',
  ro: '/flags/ro-flag.gif',
};

const LANGUAGE_NAMES: Record<string, string> = {
  en: 'English',
  ro: 'Română',
};

export function LanguageSelector() {
  const { language, setLanguage } = useI18n();
  const { setLanguage: setPrefLanguage } = usePreferences();

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
            alt={`${language} flag`}
            className="h-4 w-auto mr-2"
          />
          <span className="text-xs uppercase">{language}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="bg-slate-800 border-slate-700">
        <DropdownMenuItem
          onClick={() => {
            setLanguage('en');
            setPrefLanguage('en');
          }}
          className="text-slate-100 hover:bg-slate-700 cursor-pointer flex items-center justify-start"
        >
          <img 
            src={FLAG_IMAGES.en} 
            alt="UK flag"
            className="h-5 w-8 object-cover mr-3 flex-shrink-0"
          />
          <span className="flex-1 text-left">English</span>
          {language === 'en' && <span className="ml-2 text-emerald-400 flex-shrink-0">✓</span>}
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => {
            setLanguage('ro');
            setPrefLanguage('ro');
          }}
          className="text-slate-100 hover:bg-slate-700 cursor-pointer flex items-center justify-start"
        >
          <img 
            src={FLAG_IMAGES.ro} 
            alt="Romanian flag"
            className="h-5 w-8 object-cover mr-3 flex-shrink-0"
          />
          <span className="flex-1 text-left">Română</span>
          {language === 'ro' && <span className="ml-2 text-emerald-400 flex-shrink-0">✓</span>}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

