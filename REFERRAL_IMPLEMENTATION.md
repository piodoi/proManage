# Referral System Implementation Guide

## Overview
Complete "Skip a Month" referral rewards system for ProManage. When a user subscribes via a referral link, the referrer gets their next billing delayed by 30 days using Stripe's `trial_end` parameter.

## Backend Implementation

### 1. Database Migration
Run the migration to add referral tables:
```bash
# For MySQL
mysql -u root -p ultrafinu_promanage < backend/migrations/add_referral_system.sql

# For PostgreSQL  
psql -d promanage < backend/migrations/add_referral_system.sql
```

### 2. Models Added (`app/models.py`)
- `User.referral_code`: Unique code for sharing
- `User.referred_by`: ID of referrer
- `User.referral_reward_applied`: Reward status
- `User.referral_signup_date`: When user signed up via referral
- `ReferralReward`: Complete tracking model

### 3. API Endpoints (`app/routes/referral_routes.py`)

**GET /referrals/link**
- Returns user's referral code and link
- Auto-generates code if user doesn't have one
- Returns stats: total_referrals, pending_rewards, applied_rewards

**GET /referrals/stats**
- Detailed breakdown of all referrals
- Shows who signed up, who subscribed, reward status

### 4. Auth Flow (`app/routes/auth_routes.py`)
- `RegisterRequest` now accepts `referral_code`
- On email confirmation, creates `ReferralReward` record
- Links user to referrer via `referred_by` field

### 5. Stripe Integration (`app/routes/stripe_routes.py`)
- Calls `check_and_apply_referral_reward()` when subscription activates
- Uses `stripe.Subscription.modify()` to extend `trial_end` by 30 days
- Sets `proration_behavior='none'` to skip charges
- Marks reward as applied in database

## Frontend Implementation

### 1. API Client (`frontend/src/api.ts`)
Added `referrals` namespace:
```typescript
api.referrals.getLink(token, frontendUrl?)
api.referrals.getStats(token)
```

### 2. Login/Register Page Updates Needed

**File:** `frontend/src/pages/Login.tsx`

Add URL parameter detection:
```typescript
const [searchParams] = useSearchParams();
const referralCode = searchParams.get('ref');
```

Pass `referral_code` to register API:
```typescript
const response = await fetch(`${API_URL}/auth/register`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: formEmail,
    password: formPassword,
    name: formName,
    referral_code: referralCode  // ← Add this
  })
});
```

### 3. Referral Dashboard Component

**Create:** `frontend/src/components/ReferralDashboard.tsx`

```typescript
import { useState, useEffect } from 'react';
import { api } from '../api';
import { useAuth } from '../App';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Copy, Check, Users, Clock, Gift } from 'lucide-react';

export function ReferralDashboard() {
  const { token } = useAuth();
  const [link, setLink] = useState<string>('');
  const [code, setCode] = useState<string>('');
  const [stats, setStats] = useState<any>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!token) return;
    
    // Get referral link
    api.referrals.getLink(token, window.location.origin)
      .then(data => {
        setLink(data.referral_link);
        setCode(data.referral_code);
      });
    
    // Get stats
    api.referrals.getStats(token)
      .then(setStats);
  }, [token]);

  const copyLink = () => {
    navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Refer Friends & Skip a Month Free!</CardTitle>
          <CardDescription>
            Share your referral link. When someone subscribes, you get 1 month free!
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <input 
              type="text" 
              value={link} 
              readOnly 
              className="flex-1 px-3 py-2 border rounded"
            />
            <Button onClick={copyLink}>
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {copied ? 'Copied!' : 'Copy'}
            </Button>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            Your referral code: <code className="font-mono font-bold">{code}</code>
          </p>
        </CardContent>
      </Card>

      {stats && (
        <div className="grid grid-cols-3 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2">
                <Users className="h-5 w-5 text-blue-500" />
                <div>
                  <p className="text-2xl font-bold">{stats.total_referrals}</p>
                  <p className="text-sm text-muted-foreground">Total Referrals</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-yellow-500" />
                <div>
                  <p className="text-2xl font-bold">{stats.pending_rewards}</p>
                  <p className="text-sm text-muted-foreground">Pending Rewards</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2">
                <Gift className="h-5 w-5 text-green-500" />
                <div>
                  <p className="text-2xl font-bold">{stats.applied_rewards}</p>
                  <p className="text-sm text-muted-foreground">Months Earned</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
```

### 4. Add to Settings

**In:** `frontend/src/components/SettingsView.tsx`

Add new tab:
```tsx
import { ReferralDashboard } from './ReferralDashboard';

// In tabs array:
{ value: 'referrals', label: t('settings.tabs.referrals') }

// In tab content:
<TabsContent value="referrals">
  <ReferralDashboard />
</TabsContent>
```

### 5. Translation Keys

**Add to:** `frontend/src/locales/en.json`
```json
{
  "settings": {
    "tabs": {
      "referrals": "Referrals"
    }
  },
  "referrals": {
    "title": "Refer Friends & Skip a Month",
    "description": "Share your link. When someone subscribes, you get 1 month free!",
    "yourCode": "Your referral code",
    "copyLink": "Copy Link",
    "copied": "Copied!",
    "totalReferrals": "Total Referrals",
    "pendingRewards": "Pending Rewards",
    "monthsEarned": "Months Earned"
  }
}
```

**Add to:** `frontend/src/locales/ro.json`
```json
{
  "settings": {
    "tabs": {
      "referrals": "Recomandări"
    }
  },
  "referrals": {
    "title": "Recomandă prieteni și sari o lună",
    "description": "Distribuie linkul. Când cineva se abonează, primești 1 lună gratis!",
    "yourCode": "Codul tău de recomandare",
    "copyLink": "Copiază Linkul",
    "copied": "Copiat!",
    "totalReferrals": "Total Recomandări",
    "pendingRewards": "Recompense în Așteptare",
    "monthsEarned": "Luni Câștigate"
  }
}
```

## Testing Flow

1. **User A** (referrer):
   - Goes to Settings → Referrals tab
   - Copies referral link (e.g., `https://app.com/login?ref=ABC123XY`)

2. **User B** (referred):
   - Clicks link → redirected to `/login?ref=ABC123XY`
   - Registers account → `referred_by` set to User A's ID
   - `ReferralReward` record created with `reward_applied=false`

3. **User B subscribes**:
   - Completes Stripe checkout
   - Webhook triggers → `subscription_tier` updated
   - `check_and_apply_referral_reward()` called
   - User A's subscription extended by 30 days via `trial_end`
   - `reward_applied` set to `true`

4. **User A**:
   - Sees "Applied Rewards: 1" in dashboard
   - Next billing date automatically moved forward 30 days

## Stripe Reward Mechanism

```python
# Current period ends Jan 31
current_period_end = 1706745600  # Unix timestamp

# Add 30 days (in seconds)
new_trial_end = current_period_end + (30 * 24 * 60 * 60)

# Update subscription
stripe.Subscription.modify(
    subscription_id,
    trial_end=new_trial_end,
    proration_behavior='none'  # No charges for extension
)
```

Result: Next billing happens on Feb 28 instead of Jan 31.

## Security Notes

- Referral codes are 8-character random strings (uppercase + digits)
- Codes checked for uniqueness before assignment
- Rewards only applied once per referred user
- Requires active subscription to receive reward
- Stripe customer ID verified before modification

## Files Modified

**Backend:**
- `app/models.py` - Added User referral fields + ReferralReward model
- `app/routes/auth_routes.py` - Accept referral_code in registration
- `app/routes/stripe_routes.py` - Trigger reward on subscription
- `app/main.py` - Register referral router
- `migrations/add_referral_system.sql` - Database schema

**Frontend:**
- `src/api.ts` - Referral API endpoints
- `src/pages/Login.tsx` - Detect `?ref=` parameter
- `src/components/ReferralDashboard.tsx` - New component (to create)
- `src/components/SettingsView.tsx` - Add referrals tab
- `src/locales/en.json` + `ro.json` - Translation keys

## Next Steps

1. Run database migration
2. Update `Login.tsx` to pass referral code
3. Create `ReferralDashboard.tsx` component
4. Add referrals tab to SettingsView
5. Test complete flow with Stripe test mode
6. Deploy backend with new routes
