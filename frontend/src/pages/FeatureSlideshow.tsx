import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ChevronLeft, ChevronRight, X, Building2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useI18n } from '@/lib/i18n';
import { useSEO } from '@/hooks/useSEO';

interface SlideInfo {
  src: string;
  titleKey: string;
  descriptionKey: string;
}

// Slide metadata - maps filename to translation keys
const slideMetadata: Record<string, { titleKey: string; descriptionKey: string }> = {
  'summary.png': {
    titleKey: 'slideshow.slides.summary.title',
    descriptionKey: 'slideshow.slides.summary.description',
  },
  'propreties.png': {
    titleKey: 'slideshow.slides.properties.title',
    descriptionKey: 'slideshow.slides.properties.description',
  },
  'managesuppliers.png': {
    titleKey: 'slideshow.slides.suppliers.title',
    descriptionKey: 'slideshow.slides.suppliers.description',
  },
  'createpattern.png': {
    titleKey: 'slideshow.slides.patterns.title',
    descriptionKey: 'slideshow.slides.patterns.description',
  },
  'subscriptions.png': {
    titleKey: 'slideshow.slides.subscriptions.title',
    descriptionKey: 'slideshow.slides.subscriptions.description',
  },
};

// Order of slides for presentation
const slideOrder = [
  'summary.png',
  'propreties.png',
  'managesuppliers.png',
  'createpattern.png',
  'subscriptions.png',
];

export default function FeatureSlideshow() {
  const { t } = useI18n();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [slides, setSlides] = useState<SlideInfo[]>([]);
  const [isAutoPlaying, setIsAutoPlaying] = useState(true);

  useSEO({
    title: 'Feature Tour',
    description: 'Explore ProManage features: property management dashboard, utility bill tracking, supplier management, and more.',
  });

  useEffect(() => {
    // Build slides array from the ordered list
    const loadedSlides: SlideInfo[] = slideOrder
      .filter(filename => slideMetadata[filename])
      .map(filename => ({
        src: `/slideshow/${filename}`,
        titleKey: slideMetadata[filename].titleKey,
        descriptionKey: slideMetadata[filename].descriptionKey,
      }));
    
    setSlides(loadedSlides);
  }, []);

  // Auto-advance slideshow
  useEffect(() => {
    if (!isAutoPlaying || slides.length === 0) return;
    
    const timer = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % slides.length);
    }, 5000);

    return () => clearInterval(timer);
  }, [isAutoPlaying, slides.length]);

  const goToNext = () => {
    setIsAutoPlaying(false);
    setCurrentIndex((prev) => (prev + 1) % slides.length);
  };

  const goToPrevious = () => {
    setIsAutoPlaying(false);
    setCurrentIndex((prev) => (prev - 1 + slides.length) % slides.length);
  };

  const goToSlide = (index: number) => {
    setIsAutoPlaying(false);
    setCurrentIndex(index);
  };

  if (slides.length === 0) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-slate-400">{t('common.loading')}</div>
      </div>
    );
  }

  const currentSlide = slides[currentIndex];

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 px-4 sm:px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <Building2 className="w-8 h-8 text-emerald-500" />
            <span className="text-xl font-bold text-slate-100">ProManage</span>
          </Link>
          <div className="flex items-center gap-4">
            <span className="text-slate-400 text-sm hidden sm:block">
              {t('slideshow.featureTour')}
            </span>
            <Link to="/">
              <Button variant="outline" size="sm" className="border-slate-600 text-slate-300 hover:bg-slate-700">
                <X className="w-4 h-4 mr-2" />
                {t('slideshow.backToHome')}
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Slideshow Area */}
      <div className="flex-1 flex flex-col items-center justify-center p-4 sm:p-8">
        <div className="w-full max-w-6xl">
          {/* Slide Title and Description */}
          <div className="text-center mb-6">
            <h2 className="text-2xl sm:text-3xl font-bold text-slate-100 mb-2">
              {t(currentSlide.titleKey)}
            </h2>
            <p className="text-slate-400 text-lg max-w-2xl mx-auto">
              {t(currentSlide.descriptionKey)}
            </p>
          </div>

          {/* Image Container */}
          <div className="relative group">
            {/* Navigation Arrows */}
            <button
              onClick={goToPrevious}
              className="absolute left-2 sm:left-4 top-1/2 -translate-y-1/2 z-10 bg-slate-800/80 hover:bg-slate-700 text-white p-2 sm:p-3 rounded-full transition-all opacity-70 group-hover:opacity-100"
              aria-label="Previous slide"
            >
              <ChevronLeft className="w-5 h-5 sm:w-6 sm:h-6" />
            </button>
            <button
              onClick={goToNext}
              className="absolute right-2 sm:right-4 top-1/2 -translate-y-1/2 z-10 bg-slate-800/80 hover:bg-slate-700 text-white p-2 sm:p-3 rounded-full transition-all opacity-70 group-hover:opacity-100"
              aria-label="Next slide"
            >
              <ChevronRight className="w-5 h-5 sm:w-6 sm:h-6" />
            </button>

            {/* Image with Privacy Blur Overlay */}
            <div className="relative rounded-lg overflow-hidden border border-slate-700 shadow-2xl bg-slate-800">
              <img
                src={currentSlide.src}
                alt={t(currentSlide.titleKey)}
                className="w-full h-auto"
                style={{ maxHeight: '70vh', objectFit: 'contain' }}
              />
              {/* Privacy notice */}
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-slate-900/90 to-transparent p-4">
                <p className="text-slate-400 text-xs text-center">
                  {t('slideshow.privacyNote')}
                </p>
              </div>
            </div>
          </div>

          {/* Slide Indicators */}
          <div className="flex items-center justify-center gap-2 mt-6">
            {slides.map((_, index) => (
              <button
                key={index}
                onClick={() => goToSlide(index)}
                className={`w-3 h-3 rounded-full transition-all ${
                  index === currentIndex
                    ? 'bg-emerald-500 w-8'
                    : 'bg-slate-600 hover:bg-slate-500'
                }`}
                aria-label={`Go to slide ${index + 1}`}
              />
            ))}
          </div>

          {/* Slide Counter */}
          <div className="text-center mt-4">
            <span className="text-slate-500 text-sm">
              {currentIndex + 1} / {slides.length}
            </span>
            {isAutoPlaying && (
              <span className="text-slate-600 text-sm ml-4">
                ({t('slideshow.autoPlaying')})
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Footer CTA */}
      <div className="bg-slate-800 border-t border-slate-700 px-4 sm:px-6 py-6">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-slate-300 text-center sm:text-left">
            {t('slideshow.cta')}
          </p>
          <div className="flex gap-4">
            <Link to="/">
              <Button variant="outline" className="border-slate-600 text-slate-300 hover:bg-slate-700">
                {t('slideshow.backToHome')}
              </Button>
            </Link>
            <Link to="/login">
              <Button className="bg-emerald-600 hover:bg-emerald-700 text-white">
                {t('slideshow.getStarted')}
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
