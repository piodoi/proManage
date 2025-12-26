import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Plus } from 'lucide-react';

type PropertyDialogProps = {
  token: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onError: (error: string) => void;
  canAddProperty: boolean;
};

export default function PropertyDialog({
  token,
  open,
  onOpenChange,
  onSuccess,
  onError,
  canAddProperty,
}: PropertyDialogProps) {
  const [form, setForm] = useState({ name: '', address: '' });

  const handleSubmit = async () => {
    if (!token) return;
    try {
      const { api } = await import('../../api');
      await api.properties.create(token, form);
      setForm({ name: '', address: '' });
      onOpenChange(false);
      onSuccess();
    } catch (err) {
      onError(err instanceof Error ? err.message : 'An error occurred');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button
          className="bg-emerald-600 hover:bg-emerald-700"
          disabled={!canAddProperty}
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Property
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-slate-800 border-slate-700">
        <DialogHeader>
          <DialogTitle className="text-slate-100">Add Property</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label className="text-slate-300">Name</Label>
            <Input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="bg-slate-700 border-slate-600 text-slate-100"
              placeholder="My Apartment Building"
            />
          </div>
          <div>
            <Label className="text-slate-300">Address</Label>
            <Input
              value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
              className="bg-slate-700 border-slate-600 text-slate-100"
              placeholder="123 Main St, City"
            />
          </div>
          <Button onClick={handleSubmit} className="w-full bg-emerald-600 hover:bg-emerald-700">
            Create Property
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

