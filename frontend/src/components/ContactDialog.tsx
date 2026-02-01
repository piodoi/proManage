import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useAuth } from '@/App';
import { useI18n } from '@/lib/i18n';

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export default function ContactDialog({ open, onOpenChange }: Props) {
  const { token, user } = useAuth();
  const { t } = useI18n();
  const [reason, setReason] = useState('Suggestions');
  const [message, setMessage] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [sending, setSending] = useState(false);
  const [fromEmail, setFromEmail] = useState(user?.email || '');

  const submit = async () => {
    if (!token) {
      alert(t('common.contactSignInRequired') || 'Please sign in to contact support');
      return;
    }
    setSending(true);
    try {
      const form = new FormData();
      form.append('reason', reason);
      form.append('message', message);
      // optional from_email field (frontend may send it, but server will always include current_user.email)
      if (fromEmail) form.append('from_email', fromEmail);
      if (file) form.append('file', file);

      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/email/contact`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Failed to send' }));
        throw new Error(err.detail || 'Failed to send contact');
      }
      onOpenChange(false);
      setMessage('');
      setFile(null);
    } catch (e) {
      console.error('[Contact] send failed', e);
      alert((e as Error).message || 'Failed to send contact');
    } finally {
      setSending(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-slate-800 border-slate-700 max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-slate-100">{t('common.contact') || 'Contact'}</DialogTitle>
          <DialogDescription className="text-slate-400 sr-only">Contact support</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <Label className="text-slate-300">{t('common.contactReason') || 'Reason'}</Label>
            <Select value={reason} onValueChange={(v) => setReason(v)}>
              <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-700 border-slate-600">
                <SelectItem value="Suggestions">Suggestions</SelectItem>
                <SelectItem value="Bug report">Bug report</SelectItem>
                <SelectItem value="Other">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label className="text-slate-300">{t('common.message') || 'Message'}</Label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className="w-full min-h-[120px] bg-slate-700 border-slate-600 text-slate-100 p-2 rounded"
            />
          </div>

          <div>
            <Label className="text-slate-300">{t('common.attachment') || 'Attachment (PDF or image, max 3MB)'}</Label>
            <input
              type="file"
              accept="application/pdf,image/*"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="text-slate-100"
            />
          </div>

          <div>
            <Label className="text-slate-300">{t('common.yourEmail') || 'Your email (optional)'}</Label>
            <input
              type="email"
              value={fromEmail}
              onChange={(e) => setFromEmail(e.target.value)}
              className="w-full bg-slate-700 border-slate-600 text-slate-100 p-2 rounded"
              placeholder={t('common.email')}
            />
          </div>

          <div className="flex justify-end gap-2">
            <Button onClick={() => onOpenChange(false)} variant="outline" className="bg-slate-700 text-slate-100 hover:bg-slate-600">
              {t('common.cancel')}
            </Button>
            <Button onClick={submit} className="bg-emerald-600 hover:bg-emerald-700" disabled={sending || !token}>
              {sending ? `${t('common.sending') || 'Sending...'}` : (t('common.send') || 'Send')}
            </Button>
          </div>
          {!token && (
            <p className="text-amber-400 text-sm text-center mt-2">{t('common.contactSignInRequired') || 'Please sign in to contact support'}</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
