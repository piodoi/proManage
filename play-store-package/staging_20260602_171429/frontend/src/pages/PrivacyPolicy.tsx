import { useI18n } from '@/lib/i18n';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import Footer from '@/components/Footer';

export default function PrivacyPolicy() {
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
            <h1 className="text-3xl font-bold text-slate-100 mb-6">{t('privacy.title')}</h1>
            <p className="text-slate-400 text-sm mb-8">{t('privacy.lastUpdated')}: {t('privacy.lastUpdatedDate')}</p>

            <div className="space-y-8 text-slate-300">
              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('privacy.introduction.title')}</h2>
                <p>{t('privacy.introduction.content')}</p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('privacy.dataCollection.title')}</h2>
                <p className="mb-3">{t('privacy.dataCollection.content')}</p>
                <ul className="list-disc list-inside space-y-2 text-slate-400">
                  <li>{t('privacy.dataCollection.item1')}</li>
                  <li>{t('privacy.dataCollection.item2')}</li>
                  <li>{t('privacy.dataCollection.item3')}</li>
                  <li>{t('privacy.dataCollection.item4')}</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('privacy.dataUse.title')}</h2>
                <p className="mb-3">{t('privacy.dataUse.content')}</p>
                <ul className="list-disc list-inside space-y-2 text-slate-400">
                  <li>{t('privacy.dataUse.item1')}</li>
                  <li>{t('privacy.dataUse.item2')}</li>
                  <li>{t('privacy.dataUse.item3')}</li>
                  <li>{t('privacy.dataUse.item4')}</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('privacy.dataStorage.title')}</h2>
                <p>{t('privacy.dataStorage.content')}</p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('privacy.dataSharing.title')}</h2>
                <p>{t('privacy.dataSharing.content')}</p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('privacy.cookies.title')}</h2>
                <p>{t('privacy.cookies.content')}</p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('privacy.userRights.title')}</h2>
                <p className="mb-3">{t('privacy.userRights.content')}</p>
                <ul className="list-disc list-inside space-y-2 text-slate-400">
                  <li>{t('privacy.userRights.item1')}</li>
                  <li>{t('privacy.userRights.item2')}</li>
                  <li>{t('privacy.userRights.item3')}</li>
                  <li>{t('privacy.userRights.item4')}</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('privacy.changes.title')}</h2>
                <p>{t('privacy.changes.content')}</p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-slate-100 mb-3">{t('privacy.contact.title')}</h2>
                <p>{t('privacy.contact.content')}</p>
              </section>
            </div>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}
