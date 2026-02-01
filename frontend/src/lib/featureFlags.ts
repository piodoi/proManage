export const featureFlags = {
  // Use Vite env vars prefixed with VITE_ (set to 'true' to enable)
  payOnline: import.meta.env.VITE_FEATURE_PAY_ONLINE === 'true',
  barcodeExtraction: import.meta.env.VITE_FEATURE_BARCODE_EXTRACTION === 'true',
};
