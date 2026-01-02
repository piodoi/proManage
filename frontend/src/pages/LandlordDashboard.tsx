import { useState } from 'react';
import { useAuth } from '../App';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LogOut, Building2, Settings, FileText } from 'lucide-react';
import LandlordView from '../components/LandlordView';
import SummaryView from '../components/SummaryView';
import SettingsView from '../components/SettingsView';
import TextPatternView from '../components/TextPatternView';
import { useI18n } from '../lib/i18n';
import { LanguageSelector } from '../components/LanguageSelector';

export default function LandlordDashboard() {
  const { user, token, logout } = useAuth();
  const { t } = useI18n();
  const [error, setError] = useState('');

  return (
    <div className="min-h-screen bg-slate-900">
      <header className="bg-slate-800 border-b border-slate-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Building2 className="w-6 h-6 text-emerald-500" />
            <div>
              <h1 className="text-xl font-semibold text-slate-100">{t('app.title')}</h1>
              <p className="text-sm text-slate-400">{user?.name}</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <LanguageSelector />
            <Button onClick={logout} variant="ghost" className="text-slate-400 hover:text-slate-100">
              <LogOut className="w-4 h-4 mr-2" />
              {t('app.logout')}
            </Button>
          </div>
        </div>
      </header>

      <main className="p-6">
        {error && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded text-red-200">
            {error}
            <button onClick={() => setError('')} className="ml-2 text-red-400 hover:text-red-200">x</button>
          </div>
        )}

        <Tabs defaultValue="summary" className="space-y-4">
          <TabsList className="bg-slate-800 border border-slate-700">
            <TabsTrigger value="summary" className="data-[state=active]:bg-slate-700">
              <FileText className="w-4 h-4 mr-2" />
              {t('summary.summary')}
            </TabsTrigger>
            <TabsTrigger value="property" className="data-[state=active]:bg-slate-700">
              <Building2 className="w-4 h-4 mr-2" />
              {t('property.properties')}
            </TabsTrigger>
            <TabsTrigger value="settings" className="data-[state=active]:bg-slate-700">
              <Settings className="w-4 h-4 mr-2" />
              {t('settings.settings')}
            </TabsTrigger>
            <TabsTrigger value="tools" className="data-[state=active]:bg-slate-700">
              <FileText className="w-4 h-4 mr-2" />
              Tools
            </TabsTrigger>
          </TabsList>

          <TabsContent value="summary" className="space-y-4">
            <SummaryView />
          </TabsContent>

          <TabsContent value="property" className="space-y-4">
            <LandlordView token={token} onError={setError} hideSettings />
          </TabsContent>

          <TabsContent value="settings" className="space-y-4">
            <SettingsView token={token} onError={setError} />
          </TabsContent>

          <TabsContent value="tools" className="space-y-4">
            <TextPatternView />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
