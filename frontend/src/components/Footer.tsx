import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail } from 'lucide-react';
import { useAuth } from '@/App';
import { useI18n } from '@/lib/i18n';
import ContactDialog from '@/components/ContactDialog';

export default function Footer() {
  const { token } = useAuth();
  const { t } = useI18n();
  const [contactOpen, setContactOpen] = useState(false);

  const handleContactClick = () => {
    if (token) {
      setContactOpen(true);
    } else {
      // Redirect to login if not logged in
      window.location.href = '/login';
    }
  };

  return (
    <footer className="bg-slate-800 border-t border-slate-700 py-4 px-6 mt-auto">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="text-slate-500 text-sm">
          © {new Date().getFullYear()} ProManage. {t('footer.allRightsReserved')}
        </div>
        
        <div className="flex items-center gap-6">
          <Link
            to="/privacy"
            className="text-slate-400 hover:text-slate-200 text-sm transition-colors"
          >
            {t('footer.privacyPolicy')}
          </Link>
          <Link
            to="/terms"
            className="text-slate-400 hover:text-slate-200 text-sm transition-colors"
          >
            {t('footer.termsOfService')}
          </Link>
          <button
            onClick={handleContactClick}
            className="text-slate-400 hover:text-slate-200 flex items-center gap-1 text-sm transition-colors"
            title={token ? t('common.contact') : t('common.contactSignInRequired')}
          >
            <Mail className="w-4 h-4" />
            <span>{t('footer.contactSupport')}</span>
          </button>
        </div>
      </div>
      
      <ContactDialog open={contactOpen} onOpenChange={setContactOpen} />
    </footer>
  );
}
