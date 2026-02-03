// Feature flags that can be toggled at runtime via admin panel
// Stored in backend userdata/admin/feature_flags.json

export interface FeatureFlags {
  payOnline: boolean;
  barcodeExtraction: boolean;
  facebookLogin: boolean;
  demoLogin: boolean;
  usBuild: boolean;
}

// Default flags (used before API loads)
const DEFAULT_FLAGS: FeatureFlags = {
  payOnline: false,
  barcodeExtraction: false,
  facebookLogin: false,
  demoLogin: false,
  usBuild: false,
};

// In-memory cache of feature flags
let cachedFlags: FeatureFlags = { ...DEFAULT_FLAGS };
let isLoaded = false;
let loadPromise: Promise<FeatureFlags> | null = null;

// Get the API URL from environment
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Fetch feature flags from the backend API.
 * Caches the result for subsequent calls.
 */
export async function loadFeatureFlags(): Promise<FeatureFlags> {
  if (isLoaded) {
    return cachedFlags;
  }
  
  // Prevent multiple simultaneous requests
  if (loadPromise) {
    return loadPromise;
  }
  
  loadPromise = (async () => {
    try {
      const response = await fetch(`${API_URL}/admin/env/feature-flags/public`);
      if (response.ok) {
        const flags = await response.json();
        cachedFlags = { ...DEFAULT_FLAGS, ...flags };
        isLoaded = true;
      }
    } catch (error) {
      console.warn('Failed to load feature flags from API, using defaults:', error);
    }
    return cachedFlags;
  })();
  
  return loadPromise;
}

/**
 * Get current feature flags (from cache).
 * Call loadFeatureFlags() first to ensure they're loaded.
 */
export function getFeatureFlags(): FeatureFlags {
  return cachedFlags;
}

/**
 * Force reload feature flags from the backend.
 */
export async function reloadFeatureFlags(): Promise<FeatureFlags> {
  isLoaded = false;
  loadPromise = null;
  return loadFeatureFlags();
}

// For backward compatibility - export as an object that can be accessed synchronously
// Note: Components should use loadFeatureFlags() on mount for fresh values
export const featureFlags = new Proxy({} as FeatureFlags, {
  get(_, prop: keyof FeatureFlags) {
    return cachedFlags[prop];
  }
});
