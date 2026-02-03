import { Link } from 'react-router-dom';
import { Building2, Receipt, Users, Bell, Shield, Clock, ChevronRight, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import Footer from '@/components/Footer';
import { LanguageSelector } from '@/components/LanguageSelector';
import { useI18n } from '@/lib/i18n';
import { useSEO } from '@/hooks/useSEO';

export default function LandingPage() {
  const { t } = useI18n();
  
  useSEO({
    title: 'Property Management Software for Landlords',
    description: 'Simplify rental property management. Track utility bills, manage tenants, and automate rent collection for vacation homes and rental properties. Free to start.',
    keywords: 'property management, rental property software, landlord tools, utility bill tracking, tenant management, vacation home management, rent collection app, property expenses tracker'
  });

  const features = [
    {
      icon: Receipt,
      title: t('landing.features.billTracking.title'),
      description: t('landing.features.billTracking.description'),
    },
    {
      icon: Users,
      title: t('landing.features.tenantManagement.title'),
      description: t('landing.features.tenantManagement.description'),
    },
    {
      icon: Bell,
      title: t('landing.features.notifications.title'),
      description: t('landing.features.notifications.description'),
    },
    {
      icon: Shield,
      title: t('landing.features.secure.title'),
      description: t('landing.features.secure.description'),
    },
    {
      icon: Clock,
      title: t('landing.features.automation.title'),
      description: t('landing.features.automation.description'),
    },
    {
      icon: Building2,
      title: t('landing.features.multiProperty.title'),
      description: t('landing.features.multiProperty.description'),
    },
  ];

  const benefits = [
    t('landing.benefits.item1'),
    t('landing.benefits.item2'),
    t('landing.benefits.item3'),
    t('landing.benefits.item4'),
    t('landing.benefits.item5'),
    t('landing.benefits.item6'),
  ];

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 px-4 sm:px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Building2 className="w-8 h-8 text-emerald-500" />
            <span className="text-xl font-bold text-slate-100">ProManage</span>
          </div>
          <div className="flex items-center gap-4">
            <LanguageSelector />
            <Link to="/login">
              <Button variant="outline" className="border-emerald-500 text-emerald-400 hover:bg-emerald-500/10">
                {t('landing.signIn')}
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-16 sm:py-24 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto text-center">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-slate-100 mb-6">
            {t('landing.hero.title')}
          </h1>
          <p className="text-xl sm:text-2xl text-slate-400 mb-8 max-w-3xl mx-auto">
            {t('landing.hero.subtitle')}
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/login">
              <Button size="lg" className="bg-emerald-600 hover:bg-emerald-700 text-white px-8 py-6 text-lg">
                {t('landing.hero.getStarted')}
                <ChevronRight className="ml-2 w-5 h-5" />
              </Button>
            </Link>
            <Link to="/features">
              <Button size="lg" variant="outline" className="border-slate-600 text-slate-300 hover:bg-slate-800 px-8 py-6 text-lg">
                {t('landing.hero.tryDemo')}
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Who is it for Section */}
      <section className="py-16 px-4 sm:px-6 bg-slate-800/50">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold text-slate-100 text-center mb-4">
            {t('landing.whoIsItFor.title')}
          </h2>
          <p className="text-slate-400 text-center mb-12 max-w-2xl mx-auto">
            {t('landing.whoIsItFor.subtitle')}
          </p>
          <div className="grid md:grid-cols-3 gap-8">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-slate-100 flex items-center gap-2">
                  <Building2 className="w-6 h-6 text-emerald-500" />
                  {t('landing.whoIsItFor.vacationHome.title')}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-400">{t('landing.whoIsItFor.vacationHome.description')}</p>
              </CardContent>
            </Card>
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-slate-100 flex items-center gap-2">
                  <Users className="w-6 h-6 text-emerald-500" />
                  {t('landing.whoIsItFor.landlord.title')}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-400">{t('landing.whoIsItFor.landlord.description')}</p>
              </CardContent>
            </Card>
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-slate-100 flex items-center gap-2">
                  <Shield className="w-6 h-6 text-emerald-500" />
                  {t('landing.whoIsItFor.propertyManager.title')}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-400">{t('landing.whoIsItFor.propertyManager.description')}</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold text-slate-100 text-center mb-4">
            {t('landing.features.title')}
          </h2>
          <p className="text-slate-400 text-center mb-12 max-w-2xl mx-auto">
            {t('landing.features.subtitle')}
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <Card key={index} className="bg-slate-800 border-slate-700 hover:border-emerald-500/50 transition-colors">
                <CardHeader>
                  <feature.icon className="w-10 h-10 text-emerald-500 mb-2" />
                  <CardTitle className="text-slate-100">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-slate-400">{feature.description}</CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="py-16 px-4 sm:px-6 bg-slate-800/50">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl sm:text-4xl font-bold text-slate-100 mb-6">
                {t('landing.benefits.title')}
              </h2>
              <ul className="space-y-4">
                {benefits.map((benefit, index) => (
                  <li key={index} className="flex items-start gap-3">
                    <Check className="w-6 h-6 text-emerald-500 flex-shrink-0 mt-0.5" />
                    <span className="text-slate-300">{benefit}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-slate-800 rounded-lg p-8 border border-slate-700">
              <h3 className="text-2xl font-bold text-slate-100 mb-4">{t('landing.cta.title')}</h3>
              <p className="text-slate-400 mb-6">{t('landing.cta.description')}</p>
              <Link to="/login">
                <Button className="w-full bg-emerald-600 hover:bg-emerald-700 text-white py-6 text-lg">
                  {t('landing.cta.button')}
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-16 px-4 sm:px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold text-slate-100 text-center mb-12">
            {t('landing.faq.title')}
          </h2>
          <div className="space-y-6">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-slate-100 text-lg">{t('landing.faq.q1.question')}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-400">{t('landing.faq.q1.answer')}</p>
              </CardContent>
            </Card>
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-slate-100 text-lg">{t('landing.faq.q2.question')}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-400">{t('landing.faq.q2.answer')}</p>
              </CardContent>
            </Card>
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-slate-100 text-lg">{t('landing.faq.q3.question')}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-400">{t('landing.faq.q3.answer')}</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
