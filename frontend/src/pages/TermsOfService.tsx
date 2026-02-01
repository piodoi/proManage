import { useI18n } from '@/lib/i18n';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import Footer from '@/components/Footer';

export default function TermsOfService() {
  const { t } = useI18n();

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col">
      <div className="flex-1 p-6">
        <div className="max-w-4xl mx-auto">
          <Link
            to="/login"
            className="inline-flex items-center text-slate-400 hover:text-slate-200 mb-6 transition-colors"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            {t('common.back')}
          </Link>

          <div className="bg-slate-800 border border-slate-700 rounded-lg p-8">
            <h1 className="text-3xl font-bold text-slate-100 mb-6">{t('terms.title')}</h1>
            <p className="text-slate-400 text-sm mb-8">{t('terms.lastUpdated')}: {t('terms.lastUpdatedDate')}</p>

            <div className="space-y-8 text-slate-300">
              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('terms.acceptance.title')}</h2>
                <p>{t('terms.acceptance.content')}</p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('terms.description.title')}</h2>
                <p>{t('terms.description.content')}</p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('terms.accounts.title')}</h2>
                <p className="mb-3">{t('terms.accounts.content')}</p>
                <ul className="list-disc list-inside space-y-2 text-slate-400">
                  <li>{t('terms.accounts.item1')}</li>
                  <li>{t('terms.accounts.item2')}</li>
                  <li>{t('terms.accounts.item3')}</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('terms.acceptableUse.title')}</h2>
                <p className="mb-3">{t('terms.acceptableUse.content')}</p>
                <ul className="list-disc list-inside space-y-2 text-slate-400">
                  <li>{t('terms.acceptableUse.item1')}</li>
                  <li>{t('terms.acceptableUse.item2')}</li>
                  <li>{t('terms.acceptableUse.item3')}</li>
                  <li>{t('terms.acceptableUse.item4')}</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('terms.intellectualProperty.title')}</h2>
                <p>{t('terms.intellectualProperty.content')}</p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('terms.payment.title')}</h2>
                <p>{t('terms.payment.content')}</p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('terms.termination.title')}</h2>
                <p>{t('terms.termination.content')}</p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('terms.disclaimer.title')}</h2>
                <p>{t('terms.disclaimer.content')}</p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('terms.liability.title')}</h2>
                <p>{t('terms.liability.content')}</p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('terms.changes.title')}</h2>
                <p>{t('terms.changes.content')}</p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('terms.governingLaw.title')}</h2>
                <p>{t('terms.governingLaw.content')}</p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('terms.contact.title')}</h2>
                <p>{t('terms.contact.content')}</p>
              </section>
            </div>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}
