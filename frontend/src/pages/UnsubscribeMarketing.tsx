import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Check, X } from 'lucide-react';
import { api } from '../api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';

export default function UnsubscribeMarketing() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const userId = searchParams.get('user_id');
    const unsubscribeToken = searchParams.get('token');

    if (!userId || !unsubscribeToken) {
      setStatus('error');
      setMessage('This unsubscribe link is invalid.');
      return;
    }

    api.email
      .unsubscribeMarketing(userId, unsubscribeToken)
      .then((response) => {
        setStatus('success');
        setMessage(response.message);
      })
      .catch((error: Error) => {
        setStatus('error');
        setMessage(error.message || 'Failed to unsubscribe.');
      });
  }, [searchParams]);

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <Card className="w-full max-w-md bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-2xl text-center text-slate-100">Email Preferences</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-center">
          {status === 'loading' && (
            <>
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500 mx-auto" />
              <p className="text-slate-300">Updating your preference...</p>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="w-12 h-12 bg-emerald-500 rounded-full flex items-center justify-center mx-auto">
                <Check className="w-6 h-6 text-white" />
              </div>
              <p className="text-emerald-300">{message}</p>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="w-12 h-12 bg-red-500 rounded-full flex items-center justify-center mx-auto">
                <X className="w-6 h-6 text-white" />
              </div>
              <p className="text-red-300">{message}</p>
            </>
          )}

          <Button asChild className="bg-emerald-600 hover:bg-emerald-700">
            <Link to="/">Back to home</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
