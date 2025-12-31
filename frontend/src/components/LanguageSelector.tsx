import { useI18n } from '../lib/i18n';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

const FLAG_EMOJIS: Record<string, string> = {
  en: '🇬🇧',
  ro: '🇷🇴',
};

const LANGUAGE_NAMES: Record<string, string> = {
  en: 'English',
  ro: 'Română',
};

export function LanguageSelector() {
  const { language, setLanguage } = useI18n();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="text-slate-300 hover:text-slate-100 hover:bg-slate-700"
        >
          <span className="text-lg mr-2">{FLAG_EMOJIS[language]}</span>
          <span className="text-xs uppercase">{language}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="bg-slate-800 border-slate-700">
        <DropdownMenuItem
          onClick={() => setLanguage('en')}
          className="text-slate-100 hover:bg-slate-700 cursor-pointer"
        >
          <span className="text-lg mr-2">🇬🇧</span>
          <span>English</span>
          {language === 'en' && <span className="ml-auto text-emerald-400">✓</span>}
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => setLanguage('ro')}
          className="text-slate-100 hover:bg-slate-700 cursor-pointer"
        >
          <span className="text-lg mr-2">🇷🇴</span>
          <span>Română</span>
          {language === 'ro' && <span className="ml-auto text-emerald-400">✓</span>}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

