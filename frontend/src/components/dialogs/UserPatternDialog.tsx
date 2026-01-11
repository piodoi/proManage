import { useState, useEffect, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Search, Crown, Plus, AlertCircle, Check, FileText } from 'lucide-react';
import { useI18n } from '../../lib/i18n';
import { api, UserPatternInfo } from '../../api';

type UserPatternDialogProps = {
  token: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onError: (error: string) => void;
};

export default function UserPatternDialog({
  token,
  open,
  onOpenChange,
  onSuccess,
  onError,
}: UserPatternDialogProps) {
  const { t } = useI18n();
  const [patterns, setPatterns] = useState<UserPatternInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPattern, setSelectedPattern] = useState<UserPatternInfo | null>(null);
  const [newPatternId, setNewPatternId] = useState('');
  const [newPatternName, setNewPatternName] = useState('');
  const [copying, setCopying] = useState(false);
  const [copyError, setCopyError] = useState('');
  const [copySuccess, setCopySuccess] = useState(false);

  useEffect(() => {
    if (open && token) {
      loadPatterns();
    }
  }, [open, token]);

  useEffect(() => {
    // Reset state when dialog closes
    if (!open) {
      setSelectedPattern(null);
      setNewPatternId('');
      setNewPatternName('');
      setCopyError('');
      setCopySuccess(false);
      setSearchQuery('');
    }
  }, [open]);

  useEffect(() => {
    // Pre-fill new pattern ID and name when selecting a pattern
    if (selectedPattern) {
      setNewPatternId(selectedPattern.pattern_name.toLowerCase().replace(/\s+/g, '.'));
      setNewPatternName(selectedPattern.pattern_name);
      setCopyError('');
      setCopySuccess(false);
    }
  }, [selectedPattern]);

  const loadPatterns = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await api.admin.userPatterns.list(token);
      setPatterns(data);
    } catch (err) {
      onError(err instanceof Error ? err.message : t('errors.generic'));
    } finally {
      setLoading(false);
    }
  };

  const filteredPatterns = useMemo(() => {
    if (!searchQuery.trim()) return patterns;
    const query = searchQuery.toLowerCase();
    return patterns.filter(p =>
      p.pattern_name.toLowerCase().includes(query) ||
      p.supplier?.toLowerCase().includes(query) ||
      p.user_email.toLowerCase().includes(query) ||
      p.user_name.toLowerCase().includes(query) ||
      p.bill_type.toLowerCase().includes(query)
    );
  }, [patterns, searchQuery]);

  const handleCopy = async () => {
    if (!token || !selectedPattern || !newPatternId.trim()) return;
    
    setCopying(true);
    setCopyError('');
    setCopySuccess(false);
    
    try {
      await api.admin.userPatterns.copyToAdmin(token, {
        user_id: selectedPattern.user_id,
        filename: selectedPattern.filename,
        new_pattern_id: newPatternId.trim(),
        new_name: newPatternName.trim() || undefined,
      });
      setCopySuccess(true);
      // Close dialog after short delay to show success
      setTimeout(() => {
        onOpenChange(false);
        onSuccess();
      }, 1000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('errors.generic');
      setCopyError(errorMessage);
    } finally {
      setCopying(false);
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleDateString();
    } catch {
      return dateStr;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-slate-800 border-slate-700 max-w-3xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-slate-100 flex items-center gap-2">
            <FileText className="w-5 h-5" />
            {t('admin.userPatterns.title')}
          </DialogTitle>
          <DialogDescription className="text-slate-400">
            {t('admin.userPatterns.description')}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-hidden flex flex-col gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-slate-700 border-slate-600 text-slate-100 pl-10"
              placeholder={t('admin.userPatterns.searchPlaceholder')}
            />
          </div>

          {/* Pattern list */}
          <div className="flex-1 overflow-y-auto border border-slate-700 rounded-lg min-h-[200px]">
            {loading ? (
              <div className="flex items-center justify-center h-32 text-slate-400">
                {t('common.loading')}...
              </div>
            ) : filteredPatterns.length === 0 ? (
              <div className="flex items-center justify-center h-32 text-slate-400">
                {patterns.length === 0 ? t('admin.userPatterns.noPatterns') : t('admin.userPatterns.noResults')}
              </div>
            ) : (
              <div className="divide-y divide-slate-700">
                {filteredPatterns.map((pattern) => (
                  <div
                    key={`${pattern.user_id}-${pattern.filename}`}
                    className={`p-3 cursor-pointer transition-colors ${
                      selectedPattern?.filename === pattern.filename && selectedPattern?.user_id === pattern.user_id
                        ? 'bg-emerald-900/30 border-l-2 border-emerald-500'
                        : 'hover:bg-slate-700/50'
                    }`}
                    onClick={() => setSelectedPattern(pattern)}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-slate-100 truncate">
                            {pattern.pattern_name}
                          </span>
                          {pattern.subscription_tier > 0 && (
                            <Crown className="w-4 h-4 text-amber-400 flex-shrink-0" title={t('admin.userPatterns.activeSubscription')} />
                          )}
                        </div>
                        <div className="text-sm text-slate-400 truncate">
                          {pattern.supplier || t('admin.userPatterns.noSupplier')}
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-1 flex-shrink-0">
                        <Badge variant="outline" className="text-xs bg-slate-700 text-slate-300 border-slate-600">
                          {pattern.bill_type}
                        </Badge>
                        <span className="text-xs text-slate-500">
                          {pattern.field_count} {t('admin.userPatterns.fields')}
                        </span>
                      </div>
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
                      <span>{pattern.user_name}</span>
                      <span>•</span>
                      <span>{pattern.user_email}</span>
                      <span>•</span>
                      <span>{formatDate(pattern.created_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Copy form */}
          {selectedPattern && (
            <div className="border-t border-slate-700 pt-4 space-y-3">
              <div className="text-sm font-medium text-slate-300">
                {t('admin.userPatterns.copyAs')}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-slate-400 text-xs">{t('admin.userPatterns.patternId')}</Label>
                  <Input
                    value={newPatternId}
                    onChange={(e) => {
                      setNewPatternId(e.target.value);
                      setCopyError('');
                    }}
                    className="bg-slate-700 border-slate-600 text-slate-100"
                    placeholder="e.g. supplier.name"
                  />
                  <p className="text-xs text-slate-500 mt-1">{t('admin.userPatterns.patternIdHint')}</p>
                </div>
                <div>
                  <Label className="text-slate-400 text-xs">{t('admin.userPatterns.patternName')}</Label>
                  <Input
                    value={newPatternName}
                    onChange={(e) => setNewPatternName(e.target.value)}
                    className="bg-slate-700 border-slate-600 text-slate-100"
                    placeholder={t('admin.userPatterns.optionalNewName')}
                  />
                </div>
              </div>

              {copyError && (
                <div className="flex items-center gap-2 text-red-400 text-sm bg-red-900/20 p-2 rounded">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {copyError}
                </div>
              )}

              {copySuccess && (
                <div className="flex items-center gap-2 text-emerald-400 text-sm bg-emerald-900/20 p-2 rounded">
                  <Check className="w-4 h-4 flex-shrink-0" />
                  {t('admin.userPatterns.copySuccess')}
                </div>
              )}

              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                  className="bg-slate-700 text-slate-100 hover:bg-slate-600 border-slate-600"
                >
                  {t('common.cancel')}
                </Button>
                <Button
                  onClick={handleCopy}
                  disabled={copying || !newPatternId.trim() || copySuccess}
                  className="bg-emerald-600 hover:bg-emerald-700"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  {copying ? t('common.saving') : t('admin.userPatterns.createSupplier')}
                </Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

