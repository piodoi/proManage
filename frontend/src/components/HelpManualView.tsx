import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import {
  Building2,
  Users,
  Settings,
  Bell,
  Wrench,
  Mail,
  Download,
  CheckCircle,
  AlertTriangle,
  Info,
  Home,
  CreditCard
} from 'lucide-react';
import { useI18n } from '../lib/i18n';

export default function HelpManualView() {
  const { t } = useI18n();
  const [expandedSection, setExpandedSection] = useState<string>('getting-started');

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100 flex items-center gap-2">
            <Info className="w-6 h-6 text-emerald-500" />
            {t('help.title')}
          </CardTitle>
          <p className="text-slate-400 text-sm mt-2">
            {t('help.subtitle')}
          </p>
        </CardHeader>
        <CardContent>
          <Accordion type="single" collapsible value={expandedSection} onValueChange={setExpandedSection}>
            
            {/* Getting Started */}
            <AccordionItem value="getting-started" className="border-slate-700">
              <AccordionTrigger className="text-slate-100 hover:text-emerald-400">
                <div className="flex items-center gap-2">
                  <Home className="w-5 h-5 text-emerald-500" />
                  {t('help.gettingStarted.title')}
                </div>
              </AccordionTrigger>
              <AccordionContent className="text-slate-300 space-y-4">
                <p>{t('help.gettingStarted.intro')}</p>
                <div className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <h4 className="text-emerald-400 font-semibold">{t('help.gettingStarted.quickStart')}</h4>
                  <ol className="list-decimal list-inside space-y-2 text-sm">
                    <li>{t('help.gettingStarted.step1')}</li>
                    <li>{t('help.gettingStarted.step2')}</li>
                    <li>{t('help.gettingStarted.step3')}</li>
                    <li>{t('help.gettingStarted.step4')}</li>
                    <li>{t('help.gettingStarted.step5')}</li>
                  </ol>
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* Properties Section */}
            <AccordionItem value="properties" className="border-slate-700">
              <AccordionTrigger className="text-slate-100 hover:text-emerald-400">
                <div className="flex items-center gap-2">
                  <Building2 className="w-5 h-5 text-blue-500" />
                  {t('help.properties.title')}
                </div>
              </AccordionTrigger>
              <AccordionContent className="text-slate-300 space-y-4">
                <p>{t('help.properties.intro')}</p>
                
                <div className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <h4 className="text-blue-400 font-semibold">{t('help.properties.addProperty')}</h4>
                  <p className="text-sm">{t('help.properties.addPropertyDesc')}</p>
                </div>

                <div className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <h4 className="text-blue-400 font-semibold">{t('help.properties.manageSuppliers')}</h4>
                  <p className="text-sm">{t('help.properties.manageSuppliersDesc')}</p>
                  
                  <div className="bg-amber-900/30 border border-amber-700 rounded p-3 mt-3">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <h5 className="text-amber-400 font-semibold text-sm">{t('help.properties.importantTip')}</h5>
                        <p className="text-amber-200 text-sm mt-1">{t('help.properties.emailSyncTip')}</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <h4 className="text-blue-400 font-semibold">{t('help.properties.addBills')}</h4>
                  <p className="text-sm">{t('help.properties.addBillsDesc')}</p>
                  <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                    <li>{t('help.properties.addBillManual')}</li>
                    <li>{t('help.properties.addBillPdf')}</li>
                    <li>{t('help.properties.addBillEmail')}</li>
                  </ul>
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* Renters Section */}
            <AccordionItem value="renters" className="border-slate-700">
              <AccordionTrigger className="text-slate-100 hover:text-emerald-400">
                <div className="flex items-center gap-2">
                  <Users className="w-5 h-5 text-purple-500" />
                  {t('help.renters.title')}
                </div>
              </AccordionTrigger>
              <AccordionContent className="text-slate-300 space-y-4">
                <p>{t('help.renters.intro')}</p>
                
                <div className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <h4 className="text-purple-400 font-semibold">{t('help.renters.addRenter')}</h4>
                  <p className="text-sm">{t('help.renters.addRenterDesc')}</p>
                </div>

                <div className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <h4 className="text-purple-400 font-semibold">{t('help.renters.accessLink')}</h4>
                  <p className="text-sm">{t('help.renters.accessLinkDesc')}</p>
                </div>

                <div className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <h4 className="text-purple-400 font-semibold">{t('help.renters.rentBills')}</h4>
                  <p className="text-sm">{t('help.renters.rentBillsDesc')}</p>
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* Email Sync Section */}
            <AccordionItem value="email-sync" className="border-slate-700">
              <AccordionTrigger className="text-slate-100 hover:text-emerald-400">
                <div className="flex items-center gap-2">
                  <Mail className="w-5 h-5 text-cyan-500" />
                  {t('help.emailSync.title')}
                </div>
              </AccordionTrigger>
              <AccordionContent className="text-slate-300 space-y-4">
                <p>{t('help.emailSync.intro')}</p>
                
                <div className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <h4 className="text-cyan-400 font-semibold">{t('help.emailSync.setup')}</h4>
                  <ol className="list-decimal list-inside text-sm space-y-2">
                    <li>{t('help.emailSync.step1')}</li>
                    <li>{t('help.emailSync.step2')}</li>
                    <li>{t('help.emailSync.step3')}</li>
                  </ol>
                </div>

                <div className="bg-amber-900/30 border border-amber-700 rounded p-3">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <h5 className="text-amber-400 font-semibold text-sm">{t('help.emailSync.bestPractice')}</h5>
                      <p className="text-amber-200 text-sm mt-1">{t('help.emailSync.bestPracticeDesc')}</p>
                    </div>
                  </div>
                </div>

                <div className="bg-emerald-900/30 border border-emerald-700 rounded p-3">
                  <div className="flex items-start gap-2">
                    <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <h5 className="text-emerald-400 font-semibold text-sm">{t('help.emailSync.howItWorks')}</h5>
                      <p className="text-emerald-200 text-sm mt-1">{t('help.emailSync.howItWorksDesc')}</p>
                    </div>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* Tools Section */}
            <AccordionItem value="tools" className="border-slate-700">
              <AccordionTrigger className="text-slate-100 hover:text-emerald-400">
                <div className="flex items-center gap-2">
                  <Wrench className="w-5 h-5 text-orange-500" />
                  {t('help.tools.title')}
                </div>
              </AccordionTrigger>
              <AccordionContent className="text-slate-300 space-y-4">
                <p>{t('help.tools.intro')}</p>
                
                <div className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <h4 className="text-orange-400 font-semibold">{t('help.tools.createPattern')}</h4>
                  <p className="text-sm">{t('help.tools.createPatternDesc')}</p>
                  
                  <div className="bg-slate-800 rounded p-3 mt-2">
                    <h5 className="text-slate-200 font-semibold text-sm mb-2">{t('help.tools.howToCreate')}</h5>
                    <ol className="list-decimal list-inside text-sm space-y-2">
                      <li>{t('help.tools.createStep1')}</li>
                      <li>{t('help.tools.createStep2')}</li>
                      <li>{t('help.tools.createStep3')}</li>
                      <li>{t('help.tools.createStep4')}</li>
                      <li>{t('help.tools.createStep5')}</li>
                    </ol>
                  </div>
                </div>

                <div className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <h4 className="text-orange-400 font-semibold">{t('help.tools.importantFields')}</h4>
                  <p className="text-sm">{t('help.tools.importantFieldsDesc')}</p>
                  <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                    <li><strong className="text-emerald-400">{t('common.amount')}</strong> - {t('help.tools.fieldAmount')}</li>
                    <li><strong className="text-emerald-400">{t('bill.billNumber')}</strong> - {t('help.tools.fieldBillNumber')}</li>
                    <li><strong className="text-emerald-400">{t('bill.dueDate')}</strong> - {t('help.tools.fieldDueDate')}</li>
                    <li><strong className="text-emerald-400">{t('bill.billDate')}</strong> - {t('help.tools.fieldBillDate')}</li>
                    <li><strong className="text-emerald-400">IBAN</strong> - {t('help.tools.fieldIban')}</li>
                    <li><strong className="text-emerald-400">{t('supplier.contractId')}</strong> - {t('help.tools.fieldContractId')}</li>
                  </ul>
                </div>

                <div className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <h4 className="text-orange-400 font-semibold">{t('help.tools.matchPattern')}</h4>
                  <p className="text-sm">{t('help.tools.matchPatternDesc')}</p>
                </div>

                <div className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <h4 className="text-orange-400 font-semibold">{t('help.tools.editPattern')}</h4>
                  <p className="text-sm">{t('help.tools.editPatternDesc')}</p>
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* E-Bloc Import Section */}
            <AccordionItem value="ebloc" className="border-slate-700">
              <AccordionTrigger className="text-slate-100 hover:text-emerald-400">
                <div className="flex items-center gap-2">
                  <Download className="w-5 h-5 text-indigo-500" />
                  {t('help.ebloc.title')}
                </div>
              </AccordionTrigger>
              <AccordionContent className="text-slate-300 space-y-4">
                <p>{t('help.ebloc.intro')}</p>
                
                <div className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <h4 className="text-indigo-400 font-semibold">{t('help.ebloc.howToImport')}</h4>
                  <ol className="list-decimal list-inside text-sm space-y-2">
                    <li>{t('help.ebloc.step1')}</li>
                    <li>{t('help.ebloc.step2')}</li>
                    <li>{t('help.ebloc.step3')}</li>
                    <li>{t('help.ebloc.step4')}</li>
                    <li>{t('help.ebloc.step5')}</li>
                  </ol>
                </div>

                <div className="bg-emerald-900/30 border border-emerald-700 rounded p-3">
                  <div className="flex items-start gap-2">
                    <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <h5 className="text-emerald-400 font-semibold text-sm">{t('help.ebloc.whatGetsImported')}</h5>
                      <ul className="text-emerald-200 text-sm mt-1 list-disc list-inside">
                        <li>{t('help.ebloc.imported1')}</li>
                        <li>{t('help.ebloc.imported2')}</li>
                        <li>{t('help.ebloc.imported3')}</li>
                      </ul>
                    </div>
                  </div>
                </div>

                <div className="bg-blue-900/30 border border-blue-700 rounded p-3">
                  <div className="flex items-start gap-2">
                    <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <h5 className="text-blue-400 font-semibold text-sm">{t('help.ebloc.privacyNote')}</h5>
                      <p className="text-blue-200 text-sm mt-1">{t('help.ebloc.privacyNoteDesc')}</p>
                    </div>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* Notifications Section */}
            <AccordionItem value="notifications" className="border-slate-700">
              <AccordionTrigger className="text-slate-100 hover:text-emerald-400">
                <div className="flex items-center gap-2">
                  <Bell className="w-5 h-5 text-red-500" />
                  {t('help.notifications.title')}
                </div>
              </AccordionTrigger>
              <AccordionContent className="text-slate-300 space-y-4">
                <p>{t('help.notifications.intro')}</p>
                
                <div className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <h4 className="text-red-400 font-semibold">{t('help.notifications.paymentNotifications')}</h4>
                  <p className="text-sm">{t('help.notifications.paymentNotificationsDesc')}</p>
                </div>

                <div className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <h4 className="text-red-400 font-semibold">{t('help.notifications.actions')}</h4>
                  <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                    <li><strong className="text-emerald-400">{t('common.confirm')}</strong> - {t('help.notifications.confirmDesc')}</li>
                    <li><strong className="text-red-400">{t('common.reject')}</strong> - {t('help.notifications.rejectDesc')}</li>
                    <li><strong className="text-slate-400">{t('notifications.clearAll')}</strong> - {t('help.notifications.clearAllDesc')}</li>
                  </ul>
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* Settings Section */}
            <AccordionItem value="settings" className="border-slate-700">
              <AccordionTrigger className="text-slate-100 hover:text-emerald-400">
                <div className="flex items-center gap-2">
                  <Settings className="w-5 h-5 text-gray-500" />
                  {t('help.settings.title')}
                </div>
              </AccordionTrigger>
              <AccordionContent className="text-slate-300 space-y-4">
                <p>{t('help.settings.intro')}</p>
                
                <div className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <h4 className="text-gray-400 font-semibold">{t('help.settings.personalDetails')}</h4>
                  <p className="text-sm">{t('help.settings.personalDetailsDesc')}</p>
                </div>

                <div className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <h4 className="text-gray-400 font-semibold">{t('help.settings.emailConfig')}</h4>
                  <p className="text-sm">{t('help.settings.emailConfigDesc')}</p>
                </div>

                <div className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <h4 className="text-gray-400 font-semibold">{t('help.settings.rentBillsSettings')}</h4>
                  <p className="text-sm">{t('help.settings.rentBillsSettingsDesc')}</p>
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* Subscription Section */}
            <AccordionItem value="subscription" className="border-slate-700">
              <AccordionTrigger className="text-slate-100 hover:text-emerald-400">
                <div className="flex items-center gap-2">
                  <CreditCard className="w-5 h-5 text-amber-500" />
                  {t('help.subscription.title')}
                </div>
              </AccordionTrigger>
              <AccordionContent className="text-slate-300 space-y-4">
                <p>{t('help.subscription.intro')}</p>
                
                <div className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <h4 className="text-amber-400 font-semibold">{t('help.subscription.freeTier')}</h4>
                  <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                    <li>{t('help.subscription.freeFeature1')}</li>
                    <li>{t('help.subscription.freeFeature2')}</li>
                    <li>{t('help.subscription.freeFeature3')}</li>
                  </ul>
                </div>

                <div className="bg-slate-900 rounded-lg p-4 space-y-3">
                  <h4 className="text-amber-400 font-semibold">{t('help.subscription.proTier')}</h4>
                  <ul className="list-disc list-inside text-sm space-y-1 ml-2">
                    <li>{t('help.subscription.proFeature1')}</li>
                    <li>{t('help.subscription.proFeature2')}</li>
                    <li>{t('help.subscription.proFeature3')}</li>
                    <li>{t('help.subscription.proFeature4')}</li>
                  </ul>
                </div>
              </AccordionContent>
            </AccordionItem>

          </Accordion>
        </CardContent>
      </Card>
    </div>
  );
}
