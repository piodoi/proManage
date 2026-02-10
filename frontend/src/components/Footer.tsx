import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, Building2 } from 'lucide-react';
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

  // Determine whether this runtime appears to be the US or EU site (hostname + build flag)
  const host = typeof window !== 'undefined' ? window.location.hostname : '';
  const envUSBuild = (import.meta.env.VITE_FEATURE_US_BUILD || 'false') === 'true';
  const isUSHost = host.includes('imanage') ? true : host.includes('promanage') ? false : envUSBuild;

  // Detect user region via browser metadata (no API call): prefer language region, then timezone.
  const EU_COUNTRY_CODES = new Set([
    'AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','GR','HU','IE','IT','LV','LT','LU','MT','NL','PL','PT','RO','SK','SI','ES','SE'
  ]);

  const getUserRegion = (): 'US' | 'EU' | 'UNKNOWN' => {
    if (typeof navigator === 'undefined') return 'UNKNOWN';

    // 1) Check language region tag (e.g., en-US, ro-RO)
    const lang = (navigator.languages && navigator.languages[0]) || navigator.language || '';
    const parts = lang.split('-');
    if (parts.length > 1) {
      const region = parts[1].toUpperCase();
      if (region === 'US') return 'US';
      if (EU_COUNTRY_CODES.has(region)) return 'EU';
    }

    // 2) Check timezone (e.g., Europe/Berlin or America/New_York)
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
      if (tz.startsWith('Europe/')) return 'EU';
      if (tz.startsWith('America/')) return 'US';
    } catch (e) {
      // ignore
    }

    return 'UNKNOWN';
  };

  const userRegion = getUserRegion();

  // Show reciprocal link only if the user is browsing from the opposite region to the host
  const showReciprocalLink = (typeof window !== 'undefined') && (
    (isUSHost && userRegion === 'EU') || (!isUSHost && userRegion === 'US')
  );

  const targetUrl = isUSHost ? 'https://promanage.urun.me' : 'https://imanage.urun.me';
  const targetNameKey = isUSHost ? 'footer.euSiteName' : 'footer.usSiteName';
  return (
    <footer className="bg-slate-800 border-t border-slate-700 py-4 px-6 mt-auto">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-slate-500 text-sm">
          <Building2 className="w-4 h-4 text-emerald-500" />
          <span>© {new Date().getFullYear()} ProManage. {import.meta.env.VITE_API_VERSION} {t('footer.allRightsReserved')}</span>
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
      {showReciprocalLink && (
        <div className="max-w-7xl mx-auto mt-2 text-center text-slate-400 text-sm">
          <span>{t('footer.switchPrefix')}{' '}</span>
          <a href={targetUrl} className="text-sky-400 hover:underline">{t(targetNameKey)}</a>
        </div>
      )}
      
      <ContactDialog open={contactOpen} onOpenChange={setContactOpen} />
    </footer>
  );
}
