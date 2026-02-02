import { Building2, ShieldCheck, HelpCircle, Mail, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/App';
import { useI18n } from '@/lib/i18n';
import { LanguageSelector } from '@/components/LanguageSelector';
import ContactDialog from '@/components/ContactDialog';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function HeaderBar() {
  const { user, logout } = useAuth();
  const { t } = useI18n();
  const [contactOpen, setContactOpen] = useState(false);
  const isAdmin = user?.role === 'admin';
  const navigate = useNavigate();

  return (
    <header className="bg-slate-800 border-b border-slate-700 px-2 sm:px-6 py-2 sm:py-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1 sm:gap-3 min-w-0 flex-shrink">
          <Building2 className="w-5 h-5 sm:w-6 sm:h-6 text-emerald-500 flex-shrink-0" />
          <h1 className="text-sm sm:text-xl font-semibold text-slate-100 flex items-center gap-1 sm:gap-2 truncate">
            <span className="hidden sm:inline">{t('app.title')}</span>
            <span className="sm:hidden">PM</span>
            {user?.name && <span className="text-xs sm:text-sm text-slate-300 truncate">- {user.name}</span>}
            {isAdmin && <ShieldCheck className="w-4 h-4 sm:w-5 sm:h-5 text-emerald-500 flex-shrink-0" />}
          </h1>
        </div>
        <div className="flex items-center gap-1 sm:gap-4 flex-shrink-0">
          <Button
            onClick={() => navigate('/help')}
            variant="ghost"
            size="sm"
            className="text-slate-400 hover:text-slate-100 px-1 sm:px-2"
            title={t('help.title')}
          >
            <HelpCircle className="w-4 h-4 sm:w-5 sm:h-5" />
          </Button>
          <Button
            onClick={() => setContactOpen(true)}
            variant="ghost"
            size="sm"
            className="text-slate-400 hover:text-slate-100 px-1 sm:px-2"
            title={t('common.contact') || 'Contact'}
          >
            <Mail className="w-4 h-4 sm:w-5 sm:h-5" />
          </Button>
          <LanguageSelector />
          {user ? (
            <Button onClick={logout} variant="ghost" size="sm" className="text-slate-400 hover:text-slate-100 px-1 sm:px-2">
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline ml-2">{t('app.logout')}</span>
            </Button>
          ) : null}
        </div>
      </div>
      <ContactDialog open={contactOpen} onOpenChange={setContactOpen} />
    </header>
  );
}
