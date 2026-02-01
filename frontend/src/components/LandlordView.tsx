import { useState, useEffect, useCallback, useRef } from 'react';
import { api, Property, Renter, Bill, SubscriptionStatus } from '../api';
import { useAuth } from '../App';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { List, Grid, RefreshCw, GripVertical, Loader2 } from 'lucide-react';
import PropertyCard from './PropertyCard';
import PropertyDialog from './dialogs/PropertyDialog';
import EblocImportDialog from './dialogs/EblocImportDialog';
import AllPropertiesSyncDialog from './dialogs/AllPropertiesSyncDialog';
import { useI18n } from '../lib/i18n';
import { usePreferences } from '../hooks/usePreferences';
import { useScrollPreservation } from '../hooks/useScrollPreservation';
import { useExchangeRates } from '../hooks/useExchangeRates';

type LandlordViewProps = {
  token: string | null;
  onError?: (error: string) => void;
  hideSettings?: boolean;
  onNavigateToSubscription?: () => void;
};

type PropertyWithBills = {
  property: Property;
  bills: Bill[];
  billsLoading: boolean;
  billsLoaded: boolean;
};

export default function LandlordView({ token, onError, hideSettings: _hideSettings = false, onNavigateToSubscription }: LandlordViewProps) {
  const { user } = useAuth();
  const { t } = useI18n();
  const { preferences, loading: preferencesLoading, setPropertyOrder, setViewMode } = usePreferences();
  const { saveScroll, restoreScroll } = useScrollPreservation();
  const [propertiesWithBills, setPropertiesWithBills] = useState<PropertyWithBills[]>([]);
  const [renters, setRenters] = useState<Record<string, Renter[]>>({});
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showPropertyForm, setShowPropertyForm] = useState(false);
  const [showEblocDiscover, setShowEblocDiscover] = useState(false);
  const [showAllPropertiesSync, setShowAllPropertiesSync] = useState(false);
  const viewMode = (preferences.view_mode as 'list' | 'grid') || 'list';
  const { exchangeRates } = useExchangeRates();
  
  // Navigate to subscription tab (use parent callback if available)
  const navigateToSubscription = () => {
    if (onNavigateToSubscription) {
      onNavigateToSubscription();
    }
  };
  
  // Drag and drop state
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const dragItemRef = useRef<number | null>(null);

  // Wait for preferences to load before loading data (so property_order is available)
  // Also re-run when property_order changes (e.g., on first login when preferences are loaded)
  useEffect(() => {
    if (!preferencesLoading) {
      loadData();
    }
  }, [token, preferencesLoading, preferences.property_order]);

  const handleError = (err: unknown) => {
    const message = err instanceof Error ? err.message : t('errors.generic');
    setError(message);
    if (onError) {
      onError(message);
    }
  };

  // Sort properties by saved order preference
  const sortPropertiesByOrder = useCallback((properties: Property[], order: string[] | null | undefined): Property[] => {
    if (!order || order.length === 0) return properties;
    
    const orderMap = new Map(order.map((id, index) => [id, index]));
    return [...properties].sort((a, b) => {
      const aIndex = orderMap.get(a.id) ?? Infinity;
      const bIndex = orderMap.get(b.id) ?? Infinity;
      return aIndex - bIndex;
    });
  }, []);

  // Load bills for a single property
  const loadBillsForProperty = useCallback(async (propertyId: string) => {
    if (!token) return;
    
    try {
      const bills = await api.bills.listByProperty(token, propertyId);
      setPropertiesWithBills(prev => 
        prev.map(pwb => 
          pwb.property.id === propertyId 
            ? { ...pwb, bills, billsLoading: false, billsLoaded: true }
            : pwb
        )
      );
    } catch (err) {
      console.error(`Failed to load bills for property ${propertyId}:`, err);
      setPropertiesWithBills(prev => 
        prev.map(pwb => 
          pwb.property.id === propertyId 
            ? { ...pwb, billsLoading: false, billsLoaded: true }
            : pwb
        )
      );
    }
  }, [token]);

  const loadData = async (shouldRestoreScroll = false) => {
    if (!token) return;
    setLoading(true);
    try {
      // First, load properties and subscription status
      const [propsData, subData] = await Promise.all([
        api.properties.list(token),
        api.subscription.status(token),
      ]);

      // Sort properties by saved order
      const sortedProps = sortPropertiesByOrder(propsData, preferences.property_order);
      
      // Initialize properties with empty bills and loading state
      const initialPropertiesWithBills: PropertyWithBills[] = sortedProps.map(prop => ({
        property: prop,
        bills: [],
        billsLoading: true,
        billsLoaded: false,
      }));
      
      setPropertiesWithBills(initialPropertiesWithBills);
      setSubscription(subData);
      setLoading(false);

      // Now load bills and renters sequentially for each property
      // This allows properties to display immediately while their bills load
      for (const prop of sortedProps) {
        // Load bills for this property
        loadBillsForProperty(prop.id);
        
        // Load renters for this property
        try {
          const rentersData = await api.renters.list(token, prop.id);
          setRenters(prev => ({ ...prev, [prop.id]: rentersData }));
        } catch (err) {
          console.error(`Failed to load renters for property ${prop.id}:`, err);
        }
      }
    } catch (err) {
      handleError(err);
      setLoading(false);
    } finally {
      // Restore scroll position after initial data loads if requested
      if (shouldRestoreScroll) {
        restoreScroll();
      }
    }
  };

  // Refresh bills for a specific property
  const refreshPropertyBills = useCallback(async (propertyId: string) => {
    if (!token) return;
    
    // Set loading state for this specific property
    setPropertiesWithBills(prev => 
      prev.map(pwb => 
        pwb.property.id === propertyId 
          ? { ...pwb, billsLoading: true }
          : pwb
      )
    );
    
    await loadBillsForProperty(propertyId);
  }, [token, loadBillsForProperty]);

  const handleDeleteProperty = async (propertyId: string) => {
    if (!token) return;
    if (!confirm(t('property.confirmDelete'))) {
      return;
    }
    try {
      await api.properties.delete(token, propertyId);
      // Remove from local state
      setPropertiesWithBills(prev => prev.filter(pwb => pwb.property.id !== propertyId));
      // Update property order preference
      const newOrder = propertiesWithBills
        .filter(pwb => pwb.property.id !== propertyId)
        .map(pwb => pwb.property.id);
      setPropertyOrder(newOrder);
    } catch (err) {
      handleError(err);
    }
  };

  // Drag and drop handlers
  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
    dragItemRef.current = index;
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;
    setDragOverIndex(index);
  };

  const handleDragLeave = () => {
    setDragOverIndex(null);
  };

  const handleDrop = (e: React.DragEvent, dropIndex: number) => {
    e.preventDefault();
    const dragIndex = dragItemRef.current;
    
    if (dragIndex === null || dragIndex === dropIndex) {
      setDraggedIndex(null);
      setDragOverIndex(null);
      return;
    }

    // Reorder properties
    const newOrder = [...propertiesWithBills];
    const [draggedItem] = newOrder.splice(dragIndex, 1);
    newOrder.splice(dropIndex, 0, draggedItem);
    
    setPropertiesWithBills(newOrder);
    
    // Save the new order to preferences
    const propertyIds = newOrder.map(pwb => pwb.property.id);
    setPropertyOrder(propertyIds);

    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  // Render property card with drag handle
  const renderPropertyCard = (pwb: PropertyWithBills, index: number, isDraggable: boolean) => {
    const isDragging = draggedIndex === index;
    const isDragOver = dragOverIndex === index;
    
    return (
      <div
        key={pwb.property.id}
        draggable={isDraggable}
        onDragStart={() => handleDragStart(index)}
        onDragOver={(e) => handleDragOver(e, index)}
        onDragLeave={handleDragLeave}
        onDrop={(e) => handleDrop(e, index)}
        onDragEnd={handleDragEnd}
        className={`
          relative transition-all duration-200
          ${isDragging ? 'opacity-50 scale-95' : ''}
          ${isDragOver ? 'ring-2 ring-emerald-500 ring-offset-2 ring-offset-slate-900' : ''}
        `}
      >
        {isDraggable && (
          <div 
            className="absolute left-0 top-0 bottom-0 w-7 flex items-center justify-center cursor-grab active:cursor-grabbing z-10 bg-gradient-to-r from-slate-800/80 to-transparent rounded-l-lg"
            title={t('property.dragToReorder')}
          >
            <GripVertical className="w-5 h-5 text-slate-500 hover:text-slate-300" />
          </div>
        )}
        <div className={isDraggable ? 'ml-1' : ''}>
          <div className="relative">
            {pwb.billsLoading && (
              <div className="absolute top-2 right-2 z-10">
                <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />
              </div>
            )}
            <PropertyCard
              token={token}
              property={pwb.property}
              renters={renters[pwb.property.id] || []}
              bills={pwb.bills}
              exchangeRates={exchangeRates}
              onDelete={handleDeleteProperty}
              onDataChange={() => refreshPropertyBills(pwb.property.id)}
              onError={setError}
              subscription={subscription}
              onUpgradeClick={navigateToSubscription}
            />
          </div>
        </div>
      </div>
    );
  };

  const renderPropertiesContent = () => {
    if (loading) {
      return <div className="text-slate-400 text-center py-8">{t('common.loading')}</div>;
    }
    
    if (propertiesWithBills.length === 0) {
      return (
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="py-8 text-center text-slate-400">
            {t('property.noProperties')}
          </CardContent>
        </Card>
      );
    }

    if (viewMode === 'grid') {
      return (
        <div className="grid grid-cols-2 gap-3">
          {propertiesWithBills.map((pwb, index) => renderPropertyCard(pwb, index, true))}
        </div>
      );
    }

    return (
      <div className="space-y-3">
        {propertiesWithBills.map((pwb, index) => renderPropertyCard(pwb, index, true))}
      </div>
    );
  };

  return (
    <>
      {error && !error.includes('E-bloc') && (
        <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded text-red-200">
          {error}
          <button onClick={() => setError('')} className="ml-2 text-red-400 hover:text-red-200">x</button>
        </div>
      )}

      <div className="space-y-3">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Button
                onClick={() => setViewMode(viewMode === 'list' ? 'grid' : 'list')}
                className="bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600"
                title={viewMode === 'list' ? t('property.switchToGrid') : t('property.switchToList')}
              >
                {viewMode === 'list' ? <Grid className="w-4 h-4 mr-2" /> : <List className="w-4 h-4 mr-2" />}
                {viewMode === 'list' ? t('property.gridView') : t('property.listView')}
              </Button>
              <Button
                onClick={() => {
                  saveScroll();
                  setShowAllPropertiesSync(true);
                }}
                className="bg-emerald-600 text-white hover:bg-emerald-700 border border-emerald-700"
                title={t('supplier.syncAllProperties')}
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                {t('supplier.syncBills')}
              </Button>
            </div>
            <h2 className="text-lg font-medium text-slate-100">{t('property.properties')}</h2>
            <div className="flex gap-2">
              <EblocImportDialog
                token={token}
                open={showEblocDiscover}
                onOpenChange={(open) => {
                  if (open) {
                    saveScroll();
                  }
                  setShowEblocDiscover(open);
                }}
                onSuccess={() => loadData(true)}
                onError={setError}
                subscription={subscription}
                onUpgradeClick={navigateToSubscription}
              />
              <PropertyDialog
                token={token}
                open={showPropertyForm}
                onOpenChange={(open) => {
                  if (open) {
                    saveScroll();
                  }
                  setShowPropertyForm(open);
                }}
                onSuccess={() => loadData(true)}
                onError={setError}
                canAddProperty={user?.role === 'admin' || (subscription ? subscription.can_add_property : false)}
                onUpgradeClick={navigateToSubscription}
              />
            </div>
          </div>

          {renderPropertiesContent()}
          
          <AllPropertiesSyncDialog
            token={token}
            properties={propertiesWithBills.map(pwb => pwb.property)}
            open={showAllPropertiesSync}
            onOpenChange={(open) => {
              if (open) {
                saveScroll();
              }
              setShowAllPropertiesSync(open);
            }}
            onSuccess={() => loadData(true)}
            onError={setError}
            subscription={subscription}
            onUpgradeClick={navigateToSubscription}
          />
      </div>
    </>
  );
}
