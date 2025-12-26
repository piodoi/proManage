import { useState, useEffect } from 'react';
import { api, Property } from '../../api';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Spinner } from '@/components/ui/spinner';

type EblocSyncDialogProps = {
  token: string | null;
  property: Property;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onError: (error: string) => void;
};

export default function EblocSyncDialog({
  token,
  property,
  open,
  onOpenChange,
  onSuccess,
  onError,
}: EblocSyncDialogProps) {
  const [matches, setMatches] = useState<Array<{ id: string; nume: string; address: string; score: number }> | null>(null);
  const [selectedMatch, setSelectedMatch] = useState<string>('');
  const [syncing, setSyncing] = useState(false);

  // Auto-search when dialog opens
  useEffect(() => {
    if (open && token && !matches && !syncing) {
      setSyncing(true);
      setMatches(null);
      setSelectedMatch('');

      api.ebloc.sync(token, property.id)
        .then((result) => {
          setSyncing(false);
          if (result.status === 'multiple_matches' && result.matches && result.matches.length > 0) {
            setMatches(result.matches);
            setSelectedMatch(result.matches[0]?.id || '');
          } else {
            // Single match or success - sync completed automatically
            onOpenChange(false);
            onSuccess();
          }
        })
        .catch((err) => {
          setSyncing(false);
          onError(err instanceof Error ? err.message : 'Failed to sync E-bloc data');
        });
    }
  }, [open, token, property.id, matches, syncing, onOpenChange, onSuccess, onError]);

  const handleSync = async () => {
    if (!token || !selectedMatch) return;
    setSyncing(true);
    onError('');

    try {
      await api.ebloc.sync(token, property.id, selectedMatch);
      setMatches(null);
      setSelectedMatch('');
      setSyncing(false);
      onOpenChange(false);
      onSuccess();
    } catch (err) {
      setSyncing(false);
      onError(err instanceof Error ? err.message : 'Failed to sync E-bloc data');
    }
  };

  return (
    <Dialog open={open} onOpenChange={(open) => {
      onOpenChange(open);
      if (!open) {
        setMatches(null);
        setSelectedMatch('');
        setSyncing(false);
      }
    }}>
      <DialogTrigger asChild>
        <Button size="sm" className="bg-slate-700 text-slate-100 hover:bg-slate-600 hover:text-white border border-slate-600">
          Sync E-Bloc
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-slate-800 border-slate-700">
        <DialogHeader>
          <DialogTitle className="text-slate-100">Sync E-Bloc.ro</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <p className="text-sm text-slate-300 font-medium mb-1">Syncing from Property:</p>
            <p className="text-sm text-slate-100 font-semibold">{property.name}</p>
            {property.address && (
              <p className="text-xs text-slate-400 mt-1">{property.address}</p>
            )}
          </div>

          {/* Loading state - searching for matches */}
          {syncing && !matches && (
            <div className="flex flex-col items-center justify-center py-8 space-y-4">
              <Spinner className="w-8 h-8 text-slate-400" />
              <p className="text-sm text-slate-400">Searching for matching E-bloc association...</p>
            </div>
          )}

          {/* Matches found - show selection */}
          {!syncing && matches && matches.length > 0 && (
            <div className="space-y-4">
              <div>
                <Label className="text-slate-300">
                  {matches[0]?.score === 0
                    ? 'No exact match found. Please select the correct association:'
                    : 'Multiple matches found. Please select the correct association:'}
                </Label>
                <Select
                  value={selectedMatch}
                  onValueChange={setSelectedMatch}
                >
                  <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                    <SelectValue placeholder="Select association" />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-700 border-slate-600">
                    {matches.map((match) => (
                      <SelectItem key={match.id} value={match.id}>
                        {match.nume} - {match.address}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {selectedMatch && (
                <Button
                  onClick={handleSync}
                  className="w-full bg-emerald-600 hover:bg-emerald-700"
                  disabled={!selectedMatch || syncing}
                >
                  {syncing ? (
                    <>
                      <Spinner className="w-4 h-4 mr-2" />
                      Syncing...
                    </>
                  ) : (
                    'Sync Debts'
                  )}
                </Button>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

