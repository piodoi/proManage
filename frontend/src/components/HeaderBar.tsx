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
    <header className="bg-slate-800 border-b border-slate-700 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Building2 className="w-6 h-6 text-emerald-500" />
          <h1 className="text-xl font-semibold text-slate-100 flex items-center gap-2">
            {t('app.title')}
            {user?.name && <span className="text-sm text-slate-300">- {user.name}</span>}
            {isAdmin && <ShieldCheck className="w-5 h-5 text-emerald-500" />}
          </h1>
        </div>
        <div className="flex items-center gap-4">
          <Button
            onClick={() => navigate('/help')}
            variant="ghost"
            className="text-slate-400 hover:text-slate-100"
            title={t('help.title')}
          >
            <HelpCircle className="w-5 h-5" />
          </Button>
          <Button
            onClick={() => setContactOpen(true)}
            variant="ghost"
            className="text-slate-400 hover:text-slate-100"
            title={t('common.contact') || 'Contact'}
          >
            <Mail className="w-5 h-5" />
          </Button>
          <LanguageSelector />
          {user ? (
            <Button onClick={logout} variant="ghost" className="text-slate-400 hover:text-slate-100">
              <LogOut className="w-4 h-4 mr-2" />
              {t('app.logout')}
            </Button>
          ) : null}
        </div>
      </div>
      <ContactDialog open={contactOpen} onOpenChange={setContactOpen} />
    </header>
  );
}
