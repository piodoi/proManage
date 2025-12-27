const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

type RequestOptions = {
  method?: string;
  body?: unknown;
  token?: string | null;
};

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, token } = options;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const response = await fetch(`${API_URL}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }
  return response.json();
}

export const api = {
  health: () => request<{ status: string }>('/health'),

  auth: {
    google: (token: string) => request<AuthResponse>(`/auth/google?token=${token}`, { method: 'POST' }),
    facebook: (token: string) => request<AuthResponse>(`/auth/facebook?token=${token}`, { method: 'POST' }),
    me: (token: string) => request<User>('/auth/me', { token }),
  },

  admin: {
    listUsers: (token: string, page: number = 1, limit: number = 50) => 
      request<{ users: User[]; total: number; page: number; limit: number; total_pages: number }>(`/admin/users?page=${page}&limit=${limit}`, { token }),
    createUser: (token: string, data: UserCreate) => request<User>('/admin/users', { method: 'POST', body: data, token }),
    getUser: (token: string, id: string) => request<User>(`/admin/users/${id}`, { token }),
    updateUser: (token: string, id: string, data: UserUpdate) => request<User>(`/admin/users/${id}`, { method: 'PUT', body: data, token }),
    deleteUser: (token: string, id: string) => request<{ status: string }>(`/admin/users/${id}`, { method: 'DELETE', token }),
    updateSubscription: (token: string, id: string, tier: number, expires?: string) =>
      request<User>(`/admin/users/${id}/subscription?tier=${tier}${expires ? `&expires=${expires}` : ''}`, { method: 'PUT', token }),
  },

  properties: {
    list: (token: string) => request<Property[]>('/properties', { token }),
    create: (token: string, data: PropertyCreate) => request<Property>('/properties', { method: 'POST', body: data, token }),
    get: (token: string, id: string) => request<Property>(`/properties/${id}`, { token }),
    update: (token: string, id: string, data: PropertyUpdate) => request<Property>(`/properties/${id}`, { method: 'PUT', body: data, token }),
    delete: (token: string, id: string) => request<{ status: string }>(`/properties/${id}`, { method: 'DELETE', token }),
  },


  renters: {
    list: (token: string, propertyId: string) => request<Renter[]>(`/properties/${propertyId}/renters`, { token }),
    create: (token: string, propertyId: string, data: RenterCreate) => request<Renter>(`/properties/${propertyId}/renters`, { method: 'POST', body: data, token }),
    get: (token: string, id: string) => request<Renter>(`/renters/${id}`, { token }),
    update: (token: string, id: string, data: RenterUpdate) => request<Renter>(`/renters/${id}`, { method: 'PUT', body: data, token }),
    delete: (token: string, id: string) => request<{ status: string }>(`/renters/${id}`, { method: 'DELETE', token }),
    getLink: (token: string, id: string) => request<{ access_token: string; link: string }>(`/renters/${id}/link`, { token }),
  },

  bills: {
    list: (token: string) => request<Bill[]>('/bills', { token }),
    create: (token: string, data: BillCreate) => request<Bill>('/bills', { method: 'POST', body: data, token }),
    get: (token: string, id: string) => request<Bill>(`/bills/${id}`, { token }),
    update: (token: string, id: string, data: BillUpdate) => request<Bill>(`/bills/${id}`, { method: 'PUT', body: data, token }),
    delete: (token: string, id: string) => request<{ status: string }>(`/bills/${id}`, { method: 'DELETE', token }),
  },

  renter: {
    info: (token: string) => request<RenterInfo>(`/renter/${token}`),
    bills: (token: string) => request<RenterBill[]>(`/renter/${token}/bills`),
    balance: (token: string) => request<RenterBalance>(`/renter/${token}/balance`),
    pay: (token: string, data: PaymentCreate) => request<PaymentResponse>(`/renter/${token}/pay`, { method: 'POST', body: data }),
  },

  email: {
    configure: (token: string, data: EmailConfigCreate) => request<EmailConfig>('/email/configure', { method: 'POST', body: data, token }),
    getConfig: (token: string) => request<EmailConfig>('/email/config', { token }),
    process: (token: string, subject: string, body: string, sender: string) =>
      request<EmailProcessResult>(`/email/process?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}&sender=${encodeURIComponent(sender)}`, { method: 'POST', token }),
  },

  ebloc: {
    discover: (token: string, data: { username: string; password: string }) => request<{ status: string; properties: Array<{ page_id: string; name: string; address: string; url: string }> }>('/ebloc/discover', { method: 'POST', body: data, token }),
    configure: (token: string, data: EblocConfigCreate) => request<{ status: string; message: string }>('/ebloc/configure', { method: 'POST', body: data, token }),
    getConfig: (token: string) => request<{ username: string; password?: string; configured: boolean }>('/ebloc/config', { token }),
    sync: (token: string, propertyId: string, associationId?: string) => request<{ status: string; property_id: string; property_name: string; matches?: Array<{ id: string; nume: string; address: string; score: number }>; balance?: { outstanding_debt: number; last_payment_date?: string; oldest_debt_month?: string }; bills_created: number; payments_created: number }>(`/ebloc/sync/${propertyId}${associationId ? `?association_id=${associationId}` : ''}`, { method: 'POST', token }),
  },

  subscription: {
    status: (token: string) => request<SubscriptionStatus>('/subscription/status', { token }),
  },

  payments: {
    list: (token: string) => request<Payment[]>('/payments', { token }),
  },

  billParser: {
    parse: async (token: string, file: File, propertyId: string): Promise<ExtractionResult> => {
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch(`${API_URL}/bills/parse-pdf?property_id=${propertyId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || 'Request failed');
      }
      return response.json();
    },
    createFromPdf: (token: string, data: any) => request<Bill>('/bills/create-from-pdf', { method: 'POST', body: data, token }),
  },

  extractionPatterns: {
    list: (token: string) => request<ExtractionPattern[]>('/admin/extraction-patterns', { token }),
    create: (token: string, data: ExtractionPatternCreate) =>
      request<ExtractionPattern>('/admin/extraction-patterns', { method: 'POST', body: data, token }),
    get: (token: string, id: string) => request<ExtractionPattern>(`/admin/extraction-patterns/${id}`, { token }),
    update: (token: string, id: string, data: ExtractionPatternUpdate) =>
      request<ExtractionPattern>(`/admin/extraction-patterns/${id}`, { method: 'PUT', body: data, token }),
    delete: (token: string, id: string) =>
      request<{ status: string }>(`/admin/extraction-patterns/${id}`, { method: 'DELETE', token }),
  },
};

export type User = {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'landlord';
  oauth_provider?: 'google' | 'facebook';
  subscription_status: 'active' | 'expired' | 'none';  // Deprecated, use subscription_tier
  subscription_tier?: number;  // 0 = off, 1 = on (defaults to 0 if not present)
  subscription_expires?: string;
  created_at: string;
  password_hash?: string;  // For display purposes only
};

export type UserCreate = { email: string; name: string; role: 'admin' | 'landlord'; password?: string };
export type UserUpdate = { email?: string; name?: string; role?: 'admin' | 'landlord'; password?: string };

export type Property = {
  id: string;
  landlord_id: string;
  address: string;
  name: string;
  created_at: string;
};

export type PropertyCreate = { address: string; name: string };
export type PropertyUpdate = { address?: string; name?: string };

export type Renter = {
  id: string;
  property_id: string;
  name: string;
  email?: string;
  phone?: string;
  rent_day?: number;  // Day of month (1-28) for recurring rent
  start_contract_date?: string;  // Optional start date of contract
  rent_amount_eur?: number;
  access_token: string;
  created_at: string;
};

export type RenterCreate = { 
  name: string; 
  email?: string; 
  phone?: string;
  rent_day?: number;  // Day of month (1-28) for recurring rent
  start_contract_date?: string;  // Optional start date of contract
  rent_amount_eur?: number;
};
export type RenterUpdate = { 
  name?: string; 
  email?: string; 
  phone?: string;
  rent_day?: number;  // Day of month (1-28) for recurring rent
  start_contract_date?: string;  // Optional start date of contract
  rent_amount_eur?: number;
};

export type Bill = {
  id: string;
  property_id: string;
  renter_id?: string;  // undefined/null means bill applies to all renters in the property
  bill_type: 'rent' | 'utilities' | 'ebloc' | 'other';
  description: string;
  amount: number;
  due_date: string;
  iban?: string;
  bill_number?: string;
  status: 'pending' | 'paid' | 'overdue';
  created_at: string;
};

export type BillCreate = {
  property_id: string;
  renter_id?: string;  // undefined/null means bill applies to all renters in the property
  bill_type: 'rent' | 'utilities' | 'ebloc' | 'other';
  description: string;
  amount: number;
  due_date: string;
  iban?: string;
  bill_number?: string;
};

export type BillUpdate = {
  description?: string;
  amount?: number;
  due_date?: string;
  iban?: string;
  bill_number?: string;
  status?: 'pending' | 'paid' | 'overdue';
};

export type Payment = {
  id: string;
  bill_id: string;
  amount: number;
  method: 'bank_transfer' | 'payment_service';
  status: 'pending' | 'completed' | 'failed';
  commission: number;
  created_at: string;
};

export type PaymentCreate = {
  bill_id: string;
  amount: number;
  method: 'bank_transfer' | 'payment_service';
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type RenterInfo = {
  renter: { id: string; name: string };
  property: { id: string; name: string; address: string } | null;
};

export type RenterBill = {
  bill: Bill;
  paid_amount: number;
  remaining: number;
};

export type RenterBalance = {
  total_due: number;
  total_paid: number;
  balance: number;
};

export type PaymentResponse = {
  payment: Payment;
  commission: number;
  total_with_commission: number;
  bank_transfer_info?: {
    iban: string;
    bill_number: string;
    amount: number;
    reference: string;
  };
};

export type EmailConfig = {
  id: string;
  landlord_id: string;
  config_type: 'direct' | 'forwarding';
  forwarding_email?: string;
  created_at: string;
};

export type EmailConfigCreate = {
  config_type: 'direct' | 'forwarding';
  forwarding_email?: string;
};

export type EmailProcessResult = {
  status: string;
  bill?: Bill;
  extracted?: {
    iban?: string;
    bill_number?: string;
    amount?: number;
    address?: string;
  };
  message?: string;
};

export type EblocConfigCreate = {
  username: string;
  password: string;
};

export type SubscriptionStatus = {
  status: 'active' | 'expired' | 'none';
  expires?: string;
  property_count: number;
  needs_subscription: boolean;
  can_add_property: boolean;
};

export type ExtractionPattern = {
  id: string;
  name: string;
  bill_type: 'rent' | 'utilities' | 'ebloc' | 'other';
  supplier?: string;
  vendor_hint?: string;
  iban_pattern?: string;
  amount_pattern?: string;
  address_pattern?: string;
  bill_number_pattern?: string;
  priority: number;
  enabled: boolean;
  created_at: string;
};

export type ExtractionPatternCreate = {
  name: string;
  bill_type: 'rent' | 'utilities' | 'ebloc' | 'other';
  vendor_hint?: string;
  iban_pattern?: string;
  amount_pattern?: string;
  address_pattern?: string;
  bill_number_pattern?: string;
  priority?: number;
};

export type ExtractionPatternUpdate = {
  name?: string;
  bill_type?: 'rent' | 'utilities' | 'ebloc' | 'other';
  vendor_hint?: string;
  iban_pattern?: string;
  amount_pattern?: string;
  address_pattern?: string;
  bill_number_pattern?: string;
  priority?: number;
  enabled?: boolean;
};

export type ExtractionResult = {
  iban?: string;
  contract_id?: string;
  bill_number?: string;
  amount?: number;
  due_date?: string;
  address?: string;
  consumption_location?: string;
  business_name?: string;
  all_addresses: string[];
  bank_accounts: Array<{bank: string; iban: string}>;
  matched_pattern_id?: string;
  matched_pattern_name?: string;
  matched_pattern_supplier?: string;
  raw_text?: string;
  address_matches?: boolean;
  address_warning?: string;
  property_address?: string;
};
