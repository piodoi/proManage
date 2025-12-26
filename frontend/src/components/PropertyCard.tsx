import { useState } from 'react';
import { api, Property, Renter, Bill } from '../api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { ExternalLink, Trash2, Pencil, Copy } from 'lucide-react';
import PropertyBillsView from './PropertyBillsView';
import RenterDialog from './dialogs/RenterDialog';
import EblocSyncDialog from './dialogs/EblocSyncDialog';

type PropertyCardProps = {
  token: string | null;
  property: Property;
  renters: Renter[];
  bills: Bill[];
  exchangeRates: { EUR: number; USD: number; RON: number };
  onDelete: (propertyId: string) => void;
  onDataChange: () => void;
  onError: (error: string) => void;
};

export default function PropertyCard({
  token,
  property,
  renters,
  bills,
  exchangeRates,
  onDelete,
  onDataChange,
  onError,
}: PropertyCardProps) {
  const [showRenterDialog, setShowRenterDialog] = useState(false);
  const [showEblocSync, setShowEblocSync] = useState(false);
  const [editingRenter, setEditingRenter] = useState<Renter | null>(null);
  const [renterLink, setRenterLink] = useState<{ token: string; link: string } | null>(null);

  const handleGetRenterLink = async (renterId: string) => {
    if (!token) return;
    try {
      const link = await api.renters.getLink(token, renterId);
      setRenterLink({ token: link.access_token, link: link.link });
    } catch (err) {
      onError(err instanceof Error ? err.message : 'An error occurred');
    }
  };

  const handleDeleteRenter = async (renterId: string) => {
    if (!token) return;
    if (!confirm('Are you sure you want to delete this renter? This will also delete all associated bills.')) {
      return;
    }
    try {
      await api.renters.delete(token, renterId);
      onDataChange();
    } catch (err) {
      onError(err instanceof Error ? err.message : 'An error occurred');
    }
  };

  const openEditRenter = (renter: Renter) => {
    setEditingRenter(renter);
    setShowRenterDialog(true);
  };

  return (
    <>
      <Card key={property.id} className="bg-slate-800 border-slate-700">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-slate-100">{property.name}</CardTitle>
            <p className="text-sm text-slate-400">{property.address}</p>
          </div>
          <div className="flex gap-2">
            <EblocSyncDialog
              token={token}
              property={property}
              open={showEblocSync}
              onOpenChange={setShowEblocSync}
              onSuccess={onDataChange}
              onError={onError}
            />
            <RenterDialog
              token={token}
              propertyId={property.id}
              renter={editingRenter}
              open={showRenterDialog}
              onOpenChange={(open) => {
                setShowRenterDialog(open);
                if (!open) {
                  setEditingRenter(null);
                }
              }}
              onSuccess={onDataChange}
              onError={onError}
            />
            <Button
              size="sm"
              onClick={() => onDelete(property.id)}
              className="bg-slate-700 text-red-400 hover:bg-slate-600 hover:text-red-200 border border-slate-600"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="mb-3">
            <span className="text-slate-200 font-medium">Renters</span>
          </div>
          {renters.length === 0 ? (
            <p className="text-slate-500 text-xs">No renters yet</p>
          ) : (
            <div className="space-y-1">
              {renters.map((renter) => {
                const rentAmountEUR = renter.rent_amount_eur || 0;
                const rentAmountRON = rentAmountEUR > 0
                  ? (rentAmountEUR * exchangeRates.RON).toFixed(2)
                  : '0.00';

                return (
                  <div key={renter.id} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-300 font-medium">{renter.name}</span>
                      {(rentAmountEUR > 0 || renter.rent_day || renter.start_contract_date) && (
                        <span className="text-xs text-slate-400">
                          {rentAmountEUR > 0 && (
                            <>
                              <span>{rentAmountEUR.toFixed(2)} EUR</span>
                              <span className="ml-1">({rentAmountRON} RON)</span>
                            </>
                          )}
                          {renter.rent_day && (
                            <span className="ml-2">• Due day: {renter.rent_day}</span>
                          )}
                          {renter.start_contract_date && (
                            <span className="ml-2">• Start: {new Date(renter.start_contract_date).toLocaleDateString()}</span>
                          )}
                        </span>
                      )}
                    </div>
                    <div className="flex gap-1">
                      <Button
                        size="sm"
                        onClick={() => openEditRenter(renter)}
                        className="bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600 h-6 px-2 w-6"
                        title="Edit renter"
                      >
                        <Pencil className="w-3 h-3" />
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handleGetRenterLink(renter.id)}
                        className="bg-slate-700 text-emerald-400 hover:bg-slate-600 hover:text-emerald-300 border border-slate-600 h-6 px-2 w-6"
                        title="Get renter link"
                      >
                        <ExternalLink className="w-3 h-3" />
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handleDeleteRenter(renter.id)}
                        className="bg-slate-700 text-red-400 hover:bg-slate-600 hover:text-red-200 border border-slate-600 h-6 px-2 w-6"
                        title="Delete renter"
                      >
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
        <CardContent className="pt-0">
          <PropertyBillsView
            token={token}
            propertyId={property.id}
            renters={renters}
            bills={bills}
            onError={onError}
            onBillsChange={onDataChange}
          />
        </CardContent>
      </Card>

      {/* Renter Link Dialog */}
      <Dialog open={!!renterLink} onOpenChange={(open) => !open && setRenterLink(null)}>
        <DialogContent className="bg-slate-800 border-slate-700">
          <DialogHeader>
            <DialogTitle className="text-slate-100">Renter Access Link</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-slate-400 text-sm">
              Share this link with your renter. They can use it to view and pay their bills without logging in.
            </p>
            <div className="flex gap-2">
              <Input
                readOnly
                value={renterLink ? `${window.location.origin}/renter/${renterLink.token}` : ''}
                className="bg-slate-700 border-slate-600 text-slate-100"
              />
              <Button
                onClick={() => renterLink && navigator.clipboard.writeText(`${window.location.origin}/renter/${renterLink.token}`)}
                variant="outline"
                className="border-slate-600"
              >
                <Copy className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

