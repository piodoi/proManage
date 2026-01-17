import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { api, SubscriptionStatus } from '../api';

type SubscriptionContextType = {
  subscription: SubscriptionStatus | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  
  // Convenience methods for checking limits
  canAddProperty: () => boolean;
  canAddSupplier: () => boolean;
  canAddRenter: () => boolean;
  canUseEmailSync: () => boolean;
  isFreeTier: () => boolean;
  
  // Get limit message for actions
  getLimitMessage: (action: 'property' | 'supplier' | 'renter' | 'email_sync') => string | null;
};

const SubscriptionContext = createContext<SubscriptionContextType | null>(null);

export function SubscriptionProvider({ 
  children, 
  token 
}: { 
  children: ReactNode; 
  token: string | null;
}) {
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!token) {
      setSubscription(null);
      setLoading(false);
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      const sub = await api.subscription.status(token);
      setSubscription(sub);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load subscription');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const canAddProperty = useCallback(() => {
    return subscription?.can_add_property ?? false;
  }, [subscription]);

  const canAddSupplier = useCallback(() => {
    return subscription?.can_add_supplier ?? false;
  }, [subscription]);

  const canAddRenter = useCallback(() => {
    return subscription?.can_add_renter ?? false;
  }, [subscription]);

  const canUseEmailSync = useCallback(() => {
    return subscription?.can_use_email_sync ?? false;
  }, [subscription]);

  const isFreeTier = useCallback(() => {
    return subscription?.is_free_tier ?? true;
  }, [subscription]);

  const getLimitMessage = useCallback((action: 'property' | 'supplier' | 'renter' | 'email_sync'): string | null => {
    if (!subscription) return null;
    
    switch (action) {
      case 'property':
        if (!subscription.can_add_property) {
          if (subscription.is_free_tier) {
            return `Free tier allows only ${subscription.limits.max_properties} property. Upgrade to add more.`;
          }
          return `You have ${subscription.subscription_tier} property subscriptions. Add more subscriptions to add more properties.`;
        }
        break;
      case 'supplier':
        if (!subscription.can_add_supplier) {
          if (subscription.is_free_tier) {
            return `Free tier allows only ${subscription.limits.max_suppliers} suppliers. Upgrade to add more.`;
          }
          return `Maximum ${subscription.limits.max_suppliers_per_property} suppliers per property reached.`;
        }
        break;
      case 'renter':
        if (!subscription.can_add_renter) {
          if (subscription.is_free_tier) {
            return `Free tier allows only ${subscription.limits.max_renters} renters. Upgrade to add more.`;
          }
          return `Maximum ${subscription.limits.max_renters_per_property} renters per property reached.`;
        }
        break;
      case 'email_sync':
        if (!subscription.can_use_email_sync) {
          return 'Email sync is only available with a paid subscription. Upgrade to enable this feature.';
        }
        break;
    }
    return null;
  }, [subscription]);

  return (
    <SubscriptionContext.Provider value={{
      subscription,
      loading,
      error,
      refresh,
      canAddProperty,
      canAddSupplier,
      canAddRenter,
      canUseEmailSync,
      isFreeTier,
      getLimitMessage,
    }}>
      {children}
    </SubscriptionContext.Provider>
  );
}

export function useSubscription(): SubscriptionContextType {
  const context = useContext(SubscriptionContext);
  if (!context) {
    throw new Error('useSubscription must be used within a SubscriptionProvider');
  }
  return context;
}

