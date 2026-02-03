import { useEffect } from 'react';

interface SEOProps {
  title?: string;
  description?: string;
  keywords?: string;
}

const defaultTitle = 'ProManage - Property & Rental Bill Management for Landlords';
const defaultDescription = 'Simplify rental property management. Track utility bills, manage tenants, automate rent collection and monitor expenses for vacation homes and rental properties.';

export function useSEO({ title, description, keywords }: SEOProps = {}) {
  useEffect(() => {
    // Update document title
    const fullTitle = title ? `${title} | ProManage` : defaultTitle;
    document.title = fullTitle;

    // Update meta description
    const metaDescription = document.querySelector('meta[name="description"]');
    if (metaDescription) {
      metaDescription.setAttribute('content', description || defaultDescription);
    }

    // Update meta keywords if provided
    if (keywords) {
      const metaKeywords = document.querySelector('meta[name="keywords"]');
      if (metaKeywords) {
        metaKeywords.setAttribute('content', keywords);
      }
    }

    // Update OG tags
    const ogTitle = document.querySelector('meta[property="og:title"]');
    if (ogTitle) {
      ogTitle.setAttribute('content', fullTitle);
    }

    const ogDescription = document.querySelector('meta[property="og:description"]');
    if (ogDescription) {
      ogDescription.setAttribute('content', description || defaultDescription);
    }

    // Update Twitter tags
    const twitterTitle = document.querySelector('meta[name="twitter:title"]');
    if (twitterTitle) {
      twitterTitle.setAttribute('content', fullTitle);
    }

    const twitterDescription = document.querySelector('meta[name="twitter:description"]');
    if (twitterDescription) {
      twitterDescription.setAttribute('content', description || defaultDescription);
    }

    // Cleanup - restore defaults when component unmounts
    return () => {
      document.title = defaultTitle;
      if (metaDescription) {
        metaDescription.setAttribute('content', defaultDescription);
      }
    };
  }, [title, description, keywords]);
}

export default useSEO;
