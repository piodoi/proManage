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
  
  try {
    console.log(`[API] ${method} ${endpoint}`);
    const response = await fetch(`${API_URL}${endpoint}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      const errorMsg = error.detail || error.message || `HTTP ${response.status}: ${response.statusText}`;
      console.error(`[API] Error ${method} ${endpoint}:`, errorMsg, error);
      throw new Error(errorMsg);
    }
    
    return response.json();
  } catch (err) {
    if (err instanceof Error) {
      console.error(`[API] Exception ${method} ${endpoint}:`, err.message, err);
      throw err;
    }
    console.error(`[API] Unexpected error ${method} ${endpoint}:`, err);
    throw new Error(`Unexpected error: ${String(err)}`);
  }
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
    suppliers: {
      list: (token: string) => request<Supplier[]>('/admin/suppliers', { token }),
      create: (token: string, data: SupplierCreate) => request<Supplier>('/admin/suppliers', { method: 'POST', body: data, token }),
      update: (token: string, id: string, data: SupplierUpdate) => request<Supplier>(`/admin/suppliers/${id}`, { method: 'PUT', body: data, token }),
      delete: (token: string, id: string, removePropertyReferences?: boolean) => 
        request<{ status: string }>(`/admin/suppliers/${id}${removePropertyReferences ? '?remove_property_references=true' : ''}`, { method: 'DELETE', token }),
      getProperties: (token: string, id: string) => 
        request<Array<{ property_id: string; property_name: string; property_address: string; property_supplier_id: string }>>(`/admin/suppliers/${id}/properties`, { token }),
    },
  },

  properties: {
    list: (token: string) => request<Property[]>('/properties', { token }),
    create: (token: string, data: PropertyCreate) => request<Property>('/properties', { method: 'POST', body: data, token }),
    get: (token: string, id: string) => request<Property>(`/properties/${id}`, { token }),
    update: (token: string, id: string, data: PropertyUpdate) => request<Property>(`/properties/${id}`, { method: 'PUT', body: data, token }),
    delete: (token: string, id: string) => request<{ status: string }>(`/properties/${id}`, { method: 'DELETE', token }),
  },

  suppliers: {
    list: (token: string, assignedOnly?: boolean) => request<Supplier[]>(`/suppliers${assignedOnly ? '?assigned_only=true' : ''}`, { token }),
    listForProperty: (token: string, propertyId: string) => request<PropertySupplier[]>('/properties/' + propertyId + '/suppliers', { token }),
    addToProperty: (token: string, propertyId: string, data: PropertySupplierCreate) => request<PropertySupplier>('/properties/' + propertyId + '/suppliers', { method: 'POST', body: data, token }),
    updateForProperty: (token: string, propertyId: string, propertySupplierId: string, data: PropertySupplierUpdate) => request<PropertySupplier>(`/properties/${propertyId}/suppliers/${propertySupplierId}`, { method: 'PUT', body: data, token }),
    removeFromProperty: (token: string, propertyId: string, propertySupplierId: string) => request<{ status: string }>(`/properties/${propertyId}/suppliers/${propertySupplierId}`, { method: 'DELETE', token }),
    sync: (token: string, propertyId: string) => request<{ status: string; property_id: string; bills_created: number; errors?: string[]; message?: string; multiple_contracts?: Record<string, { supplier_name: string; contracts: Array<{ contract_id: string; address?: string }> }>; progress?: Array<{ supplier_name: string; status: string; bills_found: number; bills_created: number; error?: string }> }>(`/suppliers/sync/${propertyId}`, { method: 'POST', token }),
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
    sync: (token: string) => request<{ 
      status: string; 
      message: string; 
      emails_processed: number; 
      bills_discovered: number;
      bills_created: number; 
      discovered_bills?: Array<any>;
      errors?: string[] 
    }>('/email/sync', { method: 'POST', token }),
    markRead: (token: string, emailIds: string[]) => 
      request<{ status: string; message: string }>('/email/mark-read', { 
        method: 'POST', 
        body: { email_ids: emailIds }, 
        token 
      }),
    delete: (token: string, emailIds: string[]) => 
      request<{ status: string; message: string }>('/email/delete', { 
        method: 'POST', 
        body: { email_ids: emailIds }, 
        token 
      }),
  },

  ebloc: {
    discover: (token: string, data: { username: string; password: string }) => request<{ status: string; properties: Array<{ page_id: string; name: string; address: string; url: string }> }>('/ebloc/discover', { method: 'POST', body: data, token }),
    configure: (token: string, data: EblocConfigCreate) => request<{ status: string; message: string }>('/ebloc/configure', { method: 'POST', body: data, token }),
    getConfig: (token: string) => request<{ username: string; password?: string; configured: boolean }>('/ebloc/config', { token }),
    sync: (token: string, propertyId: string, associationId?: string) => request<{ status: string; property_id: string; property_name: string; matches?: Array<{ id: string; nume: string; address: string; score: number }>; balance?: { outstanding_debt: number; last_payment_date?: string; oldest_debt_month?: string }; bills_created: number; payments_created: number }>(`/ebloc/sync/${propertyId}${associationId ? `?association_id=${associationId}` : ''}`, { method: 'POST', token }),
    setupSupplierForProperties: (token: string, propertyIds: string[]) => request<{ status: string; supplier_id: string; properties_updated: number }>('/ebloc/setup-supplier-for-properties', { method: 'POST', body: propertyIds, token }),
  },

  subscription: {
    status: (token: string) => request<SubscriptionStatus>('/subscription/status', { token }),
  },

  preferences: {
    get: (token: string) => request<Preferences>('/preferences', { token }),
    save: (token: string, data: Partial<Preferences>) => request<Preferences>('/preferences', { method: 'POST', body: data, token }),
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
    createFromPdf: (token: string, data: any) => request<{
      bill: Bill | null;
      duplicate: boolean;
      action: 'created' | 'skipped' | 'updated' | 'conflict';
      message?: string;
      existing_bill_id?: string;
      existing_amount?: number;
      new_amount?: number;
      bill_number?: string;
    }>('/bills/create-from-pdf', { method: 'POST', body: data, token }),
  },

  textPatterns: {
    list: (token: string) => request<{ patterns: TextPattern[] }>('/text-patterns/list-patterns', { token }),
  },
};

// Centralized Bill Type definition - single source of truth
export type BillType = 'rent' | 'utilities' | 'telecom' | 'ebloc' | 'other';
export const BILL_TYPES: readonly BillType[] = ['rent', 'utilities', 'telecom', 'ebloc', 'other'] as const;

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

export type Supplier = {
  id: string;
  name: string;
  has_api: boolean;
  bill_type: BillType;
  extraction_pattern_supplier?: string;
  created_at: string;
};

export type SupplierCreate = {
  name: string;
  has_api: boolean;
  bill_type: BillType;
  extraction_pattern_supplier?: string;
};

export type SupplierUpdate = {
  name?: string;
  has_api?: boolean;
  bill_type?: BillType;
  extraction_pattern_supplier?: string;
};

export type PropertySupplier = {
  id: string;
  supplier: Supplier;
  property_id: string;
  supplier_id: string;
  extraction_pattern_supplier?: string | null;
  contract_id?: string | null;
  direct_debit: boolean;
  has_credentials: boolean;
  created_at: string;
  updated_at: string;
};

export type PropertySupplierCreate = {
  supplier_id: string;
  extraction_pattern_supplier?: string | null;
  contract_id?: string | null;
  direct_debit?: boolean;
};

export type PropertySupplierUpdate = {
  contract_id?: string;
  direct_debit?: boolean;
};

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
  bill_type: BillType;
  description: string;
  amount: number;
  currency?: string;  // Currency for the bill: "EUR", "RON", or "USD"
  due_date: string;
  iban?: string;
  bill_number?: string;
  property_supplier_id?: string;  // Reference to PropertySupplier.id (links to property-supplier relationship)
  status: 'pending' | 'paid' | 'overdue';
  created_at: string;
};

export type BillCreate = {
  property_id: string;
  renter_id?: string;  // undefined/null means bill applies to all renters in the property
  bill_type: BillType;
  description: string;
  amount: number;
  currency?: string;  // Currency for the bill: "EUR", "RON", or "USD"
  due_date: string;
  iban?: string;
  bill_number?: string;
  property_supplier_id?: string;  // Reference to PropertySupplier.id
};

export type BillUpdate = {
  renter_id?: string;  // undefined/null means bill applies to all renters in the property
  bill_type?: BillType;
  description?: string;
  amount?: number;
  currency?: string;
  due_date?: string;
  iban?: string;
  bill_number?: string;
  status?: 'pending' | 'paid' | 'overdue';
  property_supplier_id?: string;  // Reference to PropertySupplier.id
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

export type Preferences = {
  language: string;
  view_mode: string;
  rent_warning_days: number;
  rent_currency: string;
  bill_currency: string;
  date_format: string;
  phone_number?: string | null;
  landlord_name?: string | null;
  personal_email?: string | null;
  iban?: string | null;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type RenterInfo = {
  renter: { id: string; name: string };
  property: { id: string; name: string; address: string } | null;
  date_format?: string;
};

export type RenterBill = {
  bill: Bill;
  paid_amount: number;
  remaining: number;
  is_direct_debit: boolean;  // Whether this bill's supplier has direct_debit enabled
};

export type RenterBalance = {
  total_due: number;
  total_paid: number;
  balance: number;
  currency: string; // Landlord's preferred currency
  exchange_rates?: {
    EUR: number;
    USD: number;
    RON: number;
  };
  total_due_ron?: number;
  total_paid_ron?: number;
  balance_ron?: number;
  eur_to_ron_rate?: number;
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

export type ExtractionResult = {
  iban?: string;
  contract_id?: string;
  bill_number?: string;
  amount?: number;
  due_date?: string;
  bill_date?: string;  // Date when bill was issued (from pattern)
  legal_name?: string;  // Legal name of supplier (from pattern)
  address?: string;
  consumption_location?: string;
  business_name?: string;
  all_addresses: string[];
  bank_accounts: Array<{bank: string; iban: string}>;
  matched_pattern_id?: string;
  matched_pattern_name?: string;
  matched_pattern_supplier?: string;
  matched_pattern_bill_type?: string;
  raw_text?: string;
  address_matches?: boolean;
  address_warning?: string;
  address_confidence?: number;
  property_address?: string;
  supplier_added?: boolean;
  supplier_message?: string;
};

export type TextPattern = {
  pattern_id: string;
  name: string;
  supplier?: string;
  bill_type: BillType;
  field_count: number;
  created_at: string;
  updated_at: string;
};
