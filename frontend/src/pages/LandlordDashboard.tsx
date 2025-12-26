import { useAuth } from '../App';
import { Button } from '@/components/ui/button';
import { LogOut, Building2 } from 'lucide-react';
import LandlordView from '../components/LandlordView';

export default function LandlordDashboard() {
  const { user, token, logout } = useAuth();

  return (
    <div className="min-h-screen bg-slate-900">
      <header className="bg-slate-800 border-b border-slate-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Building2 className="w-6 h-6 text-emerald-500" />
            <div>
              <h1 className="text-xl font-semibold text-slate-100">ProManage</h1>
              <p className="text-sm text-slate-400">{user?.name}</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <Button onClick={logout} variant="ghost" className="text-slate-400 hover:text-slate-100">
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <main className="p-6">
        <LandlordView token={token} />
      </main>
    </div>
  );
}
