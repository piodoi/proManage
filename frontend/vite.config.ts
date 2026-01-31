import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      // Add your allowed hosts here, e.g.:
      '.ultramic.ro',
      '.lhr.life',  // wildcard subdomain
    ],
  },
  build: {
    chunkSizeWarningLimit: 150,
    rollupOptions: {
      output: {
        manualChunks(id) {
          // React core - split into smaller pieces
          if (id.includes('node_modules/react-dom/client')) {
            return 'react-dom-client';
          }
          if (id.includes('node_modules/react-dom')) {
            return 'react-dom';
          }
          if (id.includes('node_modules/react/') || id.includes('node_modules/scheduler')) {
            return 'react-core';
          }
          if (id.includes('node_modules/react-router')) {
            return 'react-router';
          }
          
          // Radix UI - split by component groups
          if (id.includes('@radix-ui/react-dialog')) {
            return 'ui-dialog';
          }
          if (id.includes('@radix-ui/react-alert-dialog')) {
            return 'ui-alert-dialog';
          }
          if (id.includes('@radix-ui/react-select')) {
            return 'ui-select';
          }
          if (id.includes('@radix-ui/react-dropdown')) {
            return 'ui-dropdown';
          }
          if (id.includes('@radix-ui/react-menubar')) {
            return 'ui-menubar';
          }
          if (id.includes('@radix-ui/react-popover')) {
            return 'ui-popover';
          }
          if (id.includes('@radix-ui/react-hover-card')) {
            return 'ui-hover-card';
          }
          if (id.includes('@radix-ui/react-accordion')) {
            return 'ui-accordion';
          }
          if (id.includes('@radix-ui/react-collapsible')) {
            return 'ui-collapsible';
          }
          if (id.includes('@radix-ui/react-tabs')) {
            return 'ui-tabs';
          }
          if (id.includes('@radix-ui/react-checkbox') || 
              id.includes('@radix-ui/react-radio') ||
              id.includes('@radix-ui/react-switch') ||
              id.includes('@radix-ui/react-toggle') ||
              id.includes('@radix-ui/react-slider')) {
            return 'ui-inputs';
          }
          if (id.includes('@radix-ui/react-toast')) {
            return 'ui-toast';
          }
          if (id.includes('@radix-ui/react-tooltip')) {
            return 'ui-tooltip';
          }
          if (id.includes('@radix-ui/react-progress')) {
            return 'ui-progress';
          }
          if (id.includes('@radix-ui/react-scroll-area')) {
            return 'ui-scroll-area';
          }
          if (id.includes('@radix-ui/react-navigation')) {
            return 'ui-navigation';
          }
          if (id.includes('@radix-ui/react-separator') ||
              id.includes('@radix-ui/react-avatar') ||
              id.includes('@radix-ui/react-label') ||
              id.includes('@radix-ui/react-slot')) {
            return 'ui-layout';
          }
          // Radix primitives (shared utilities)
          if (id.includes('@radix-ui/primitive') ||
              id.includes('@radix-ui/react-primitive') ||
              id.includes('@radix-ui/react-presence') ||
              id.includes('@radix-ui/react-portal') ||
              id.includes('@radix-ui/react-focus-scope') ||
              id.includes('@radix-ui/react-focus-guards') ||
              id.includes('@radix-ui/react-dismissable-layer') ||
              id.includes('@radix-ui/react-roving-focus') ||
              id.includes('@radix-ui/react-collection') ||
              id.includes('@radix-ui/react-context') ||
              id.includes('@radix-ui/react-compose-refs') ||
              id.includes('@radix-ui/react-use-')) {
            return 'ui-radix-primitives';
          }
          
          // Icons - split lucide
          if (id.includes('lucide-react')) {
            return 'icons';
          }
          
          // Date utilities
          if (id.includes('date-fns')) {
            return 'date-utils';
          }
          
          // Form handling
          if (id.includes('react-hook-form') || id.includes('@hookform')) {
            return 'forms';
          }
          if (id.includes('zod')) {
            return 'validation';
          }
          
          // Other utilities
          if (id.includes('clsx') || id.includes('tailwind-merge') || id.includes('class-variance-authority')) {
            return 'css-utils';
          }
          if (id.includes('cmdk')) {
            return 'cmdk';
          }
          if (id.includes('sonner')) {
            return 'sonner';
          }
          if (id.includes('vaul')) {
            return 'vaul';
          }
          if (id.includes('embla-carousel')) {
            return 'carousel';
          }
          if (id.includes('input-otp')) {
            return 'input-otp';
          }
          
          // Locales - split by language
          if (id.includes('/src/locales/en.json')) {
            return 'locale-en';
          }
          if (id.includes('/src/locales/ro.json')) {
            return 'locale-ro';
          }
          
          // App code - split by feature
          if (id.includes('/src/pages/RenterView')) {
            return 'page-renter';
          }
          if (id.includes('/src/pages/Dashboard')) {
            return 'page-dashboard';
          }
          if (id.includes('/src/pages/Login') || id.includes('/src/pages/ConfirmEmail')) {
            return 'page-auth';
          }
          
          // Dialogs - split into groups
          if (id.includes('/src/components/dialogs/PropertyDialog') ||
              id.includes('/src/components/dialogs/PropertySupplierSettingsDialog')) {
            return 'dialogs-property';
          }
          if (id.includes('/src/components/dialogs/RenterDialog') ||
              id.includes('/src/components/dialogs/RenterAccessLinkDialog')) {
            return 'dialogs-renter';
          }
          if (id.includes('/src/components/dialogs/BillConfirmDialog') ||
              id.includes('/src/components/dialogs/UtilityPaymentDialog')) {
            return 'dialogs-bills';
          }
          if (id.includes('/src/components/dialogs/')) {
            return 'dialogs-other';
          }
          
          // Main components - split by feature
          if (id.includes('/src/components/LandlordView')) {
            return 'view-landlord';
          }
          if (id.includes('/src/components/PropertyCard') ||
              id.includes('/src/components/PropertyBillsView')) {
            return 'view-property';
          }
          if (id.includes('/src/components/NotificationsView')) {
            return 'view-notifications';
          }
          if (id.includes('/src/components/SettingsView') ||
              id.includes('/src/components/HelpManualView')) {
            return 'view-settings';
          }
          if (id.includes('/src/components/SummaryView')) {
            return 'view-summary';
          }
          if (id.includes('/src/components/TextPatternView')) {
            return 'view-patterns';
          }
          
          if (id.includes('/src/components/ui/')) {
            return 'ui-components';
          }
          if (id.includes('/src/components/supplierSync/')) {
            return 'supplier-sync';
          }
          if (id.includes('/src/hooks/')) {
            return 'hooks';
          }
          if (id.includes('/src/utils/') || id.includes('/src/lib/')) {
            return 'app-utils';
          }
        },
      },
    },
  },
})
