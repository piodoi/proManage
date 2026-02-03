// API URL: use env variable, or fallback to localhost for dev
// For tunneled access, set VITE_API_URL to the backend tunnel URL
const getApiUrl = () => {
  // If explicitly set via env, use that
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  // Default to localhost for local development
  return 'http://localhost:8000';
};

const API_URL = getApiUrl();

type RequestOptions = {
  method?: string;
  body?: unknown;
  token?: string | null;
};

import {
  SupplierMatch,
  BalanceRequest,
  BalanceResponse,
  PaymentRequest,
  TransactionResponse,
  SupplierInfo,
  ProductInfo,
} from './utils/utility';

// Utility Payment API Functions

export async function matchBarcodeAPI(barcode: string): Promise<SupplierMatch[]> {
  const response = await fetch(`${API_URL}/api/utility/match-barcode?barcode=${encodeURIComponent(barcode)}`, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${localStorage.getItem('token')}`,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to match barcode');
  }

  return response.json();
}

export async function getUtilityBalanceAPI(request: BalanceRequest): Promise<BalanceResponse> {
  const response = await fetch(`${API_URL}/api/utility/balance`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('token')}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get utility balance');
  }

  return response.json();
}

export async function payUtilityBillAPI(request: PaymentRequest): Promise<TransactionResponse> {
  const response = await fetch(`${API_URL}/api/utility/pay`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('token')}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Payment failed');
  }

  return response.json();
}

export async function getSuppliersAPI(): Promise<SupplierInfo[]> {
  const response = await fetch(`${API_URL}/api/utility/suppliers`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem('token')}`,
    },
  });

  if (!response.ok) {
    throw new Error('Failed to fetch suppliers');
  }

  return response.json();
}

export async function getSupplierAPI(supplierUid: string): Promise<SupplierInfo> {
  const response = await fetch(`${API_URL}/api/utility/suppliers/${supplierUid}`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem('token')}`,
    },
  });

  if (!response.ok) {
    throw new Error('Failed to fetch supplier details');
  }

  return response.json();
}

export async function getSupplierProductsAPI(supplierUid: string): Promise<ProductInfo[]> {
  const response = await fetch(`${API_URL}/api/utility/suppliers/${supplierUid}/products`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem('token')}`,
    },
  });

  if (!response.ok) {
    throw new Error('Failed to fetch supplier products');
  }

  return response.json();
}

export async function getAllProductsAPI(): Promise<ProductInfo[]> {
  const response = await fetch(`${API_URL}/api/utility/products`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem('token')}`,
    },
  });

  if (!response.ok) {
    throw new Error('Failed to fetch products');
  }

  return response.json();
}

export interface BarcodeExtractionResult {
  primary_barcode: string | null;
  all_barcodes: Array<{
    data: string;
    type: string;
    page: number;
    rect: { x: number; y: number; width: number; height: number };
  }>;
  bill_id: string;
  bill_number: string | null;
}

export async function extractBarcodeFromBillAPI(billId: string): Promise<BarcodeExtractionResult> {
  const response = await fetch(`${API_URL}/api/utility/extract-barcode/${billId}`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem('token')}`,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to extract barcode' }));
    throw new Error(error.detail || 'Failed to extract barcode');
  }

  return response.json();
}

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
    userPatterns: {
      list: (token: string) => request<UserPatternInfo[]>('/admin/user-patterns', { token }),
      copyToAdmin: (token: string, data: { user_id: string; filename: string; new_pattern_id: string; new_name?: string }) =>
        request<{ status: string; pattern_id: string; message: string }>('/admin/copy-user-pattern', { method: 'POST', body: data, token }),
    },
    env: {
      getVariables: (token: string) => 
        request<{ backend: EnvVariable[]; frontend: EnvVariable[] }>('/admin/env/variables', { token }),
      updateVariables: (token: string, variables: Record<string, string>, source: 'backend' | 'frontend') =>
        request<{ status: string; message: string }>('/admin/env/variables', { method: 'PUT', body: { variables, source }, token }),
      getFeatureFlags: (token: string) =>
        request<Record<string, boolean>>('/admin/env/feature-flags', { token }),
      updateFeatureFlags: (token: string, flags: Record<string, boolean>) =>
        request<{ status: string; message: string }>('/admin/env/feature-flags', { method: 'PUT', body: flags, token }),
      restart: (token: string, service: 'backend' | 'frontend') =>
        request<{ status: string; message: string }>('/admin/env/restart', { method: 'POST', body: { service }, token }),
      getStatus: (token: string) =>
        request<{ backend: { running: boolean; env_file_exists: boolean; python_version: string }; frontend: { env_file_exists: boolean } }>('/admin/env/status', { token }),
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
    listByProperty: (token: string, propertyId: string) => request<Bill[]>(`/bills/property/${propertyId}`, { token }),
    create: (token: string, data: BillCreate) => request<Bill>('/bills', { method: 'POST', body: data, token }),
    get: (token: string, id: string) => request<Bill>(`/bills/${id}`, { token }),
    update: (token: string, id: string, data: BillUpdate) => request<Bill>(`/bills/${id}`, { method: 'PUT', body: data, token }),
    delete: (token: string, id: string) => request<{ status: string }>(`/bills/${id}`, { method: 'DELETE', token }),
    downloadPdf: async (token: string, billId: string): Promise<void> => {
      // Fetch PDF with auth header and open in new tab
      const response = await fetch(`${API_URL}/bills/${billId}/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Download failed' }));
        throw new Error(error.detail || 'Download failed');
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
      // Clean up the URL after a delay
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    },
  },

  renter: {
    info: (token: string) => request<RenterInfo>(`/renter/${token}`),
    bills: (token: string) => request<RenterBill[]>(`/renter/${token}/bills`),
    balance: (token: string) => request<RenterBalance>(`/renter/${token}/balance`),
    notifyPayment: (token: string, data: PaymentNotificationCreate) =>
      request<PaymentNotificationResponse>(`/renter/${token}/notify-payment`, { method: 'POST', body: data }),
    createAccount: (token: string, data: RenterAccountCreate) =>
      request<{ message: string; renter: { id: string; name: string; email?: string; has_account: boolean } }>(`/renter/${token}/create-account`, { method: 'POST', body: data }),
    login: (token: string, password: string) =>
      request<{ message: string; renter: { id: string; name: string; email?: string; language: string; email_notifications: boolean } }>(`/renter/${token}/login`, { method: 'POST', body: { password } }),
    updatePreferences: (token: string, data: RenterPreferencesUpdate) =>
      request<{ message: string; renter: { id: string; name: string; email?: string; language: string; email_notifications: boolean } }>(`/renter/${token}/preferences`, { method: 'PUT', body: data }),
    updateEmail: (token: string, email: string) =>
      request<{ message: string; email: string }>(`/renter/${token}/email?email=${encodeURIComponent(email)}`, { method: 'PUT' }),
  },

  paymentNotifications: {
    list: (token: string, status?: string) =>
      request<PaymentNotificationWithDetails[]>(`/payment-notifications/${status ? `?status=${status}` : ''}`, { token }),
    count: (token: string) => request<{ count: number }>('/payment-notifications/count', { token }),
    get: (token: string, id: string) => request<PaymentNotificationWithDetails>(`/payment-notifications/${id}`, { token }),
    confirm: (token: string, id: string, note?: string) =>
      request<PaymentNotificationActionResponse>(`/payment-notifications/${id}/confirm`, {
        method: 'POST',
        body: { landlord_note: note },
        token
      }),
    reject: (token: string, id: string, note?: string) =>
      request<PaymentNotificationActionResponse>(`/payment-notifications/${id}/reject`, {
        method: 'POST',
        body: { landlord_note: note },
        token
      }),
    clearAll: (token: string, status?: string, propertyId?: string) => {
      const params = new URLSearchParams();
      if (status) params.append('status', status);
      if (propertyId) params.append('property_id', propertyId);
      const queryString = params.toString();
      return request<{ status: string; deleted_count: number; message: string }>(`/payment-notifications/clear-all${queryString ? `?${queryString}` : ''}`, {
        method: 'DELETE',
        token
      });
    },
    clearSelected: (token: string, notificationIds: string[]) =>
      request<{ status: string; deleted_count: number; message: string }>('/payment-notifications/clear-selected', {
        method: 'POST',
        body: { notification_ids: notificationIds },
        token
      }),
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
    setupSupplierForProperties: (token: string, propertyIds: string[]) => request<{ status: string; supplier_id: string; properties_updated: number }>('/ebloc/setup-supplier-for-properties', { method: 'POST', body: propertyIds, token }),
  },

  subscription: {
    status: (token: string) => request<SubscriptionStatus>('/subscription/status', { token }),
  },

  stripe: {
    config: (token: string) => request<StripeConfig>('/stripe/config', { token }),
    createCheckout: (token: string, quantity: number, successUrl: string, cancelUrl: string) => 
      request<StripeCheckoutSession>('/stripe/create-checkout-session', { 
        method: 'POST', 
        body: { quantity, success_url: successUrl, cancel_url: cancelUrl }, 
        token 
      }),
    createPortal: (token: string, returnUrl: string, checkoutQuantity: number = 1) => 
      request<StripePortalSession>('/stripe/create-portal-session', { 
        method: 'POST', 
        body: { return_url: returnUrl, checkout_quantity: checkoutQuantity }, 
        token 
      }),
    subscription: (token: string) => request<StripeSubscription>('/stripe/subscription', { token }),
  },

  preferences: {
    get: (token: string) => request<Preferences>('/preferences', { token }),
    save: (token: string, data: Partial<Preferences>) => request<Preferences>('/preferences', { method: 'POST', body: data, token }),
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

export type EnvVariable = {
  key: string;
  value: string;
  source: 'backend' | 'frontend';
  category: string;
  description?: string;
  is_secret: boolean;
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
  rent_amount?: number;  // Rent amount
  rent_currency?: string;  // Currency for rent: "EUR", "RON", or "USD"
  access_token: string;
  password_hash?: string;  // Not sent to frontend, but presence indicates account exists
  language?: string;  // Language preference: "en" or "ro"
  email_notifications?: boolean;  // Whether to receive email notifications
  created_at: string;
};

export type RenterCreate = {
  name: string;
  email?: string;
  phone?: string;
  rent_day?: number;  // Day of month (1-28) for recurring rent
  start_contract_date?: string;  // Optional start date of contract
  rent_amount?: number;  // Rent amount
  rent_currency?: string;  // Currency for rent: "EUR", "RON", or "USD"
  password?: string;  // Optional password (landlord can set for renter)
  language?: string;  // Language preference: "en" or "ro"
};
export type RenterUpdate = {
  name?: string;
  email?: string;
  phone?: string;
  rent_day?: number;  // Day of month (1-28) for recurring rent
  start_contract_date?: string;  // Optional start date of contract
  rent_amount?: number;  // Rent amount
  rent_currency?: string;  // Currency for rent: "EUR", "RON", or "USD"
  password?: string;  // Optional password (landlord can update for renter)
  language?: string;  // Language preference: "en" or "ro"
};

export type RenterAccountCreate = {
  password: string;
  password_confirm: string;
  email?: string;
};

export type RenterPreferencesUpdate = {
  language?: string;
  email_notifications?: boolean;
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
  legal_name?: string;  // Legal name of the supplier/company for payment
  bill_number?: string;
  contract_id?: string;  // Contract/client ID for payment reference
  payment_details?: Record<string, unknown>;  // Additional payment details
  property_supplier_id?: string;  // Reference to PropertySupplier.id (links to property-supplier relationship)
  status: 'pending' | 'paid' | 'overdue';
  created_at: string;
  has_pdf?: boolean;  // Whether a PDF file is available for download
};

// Helper function to get PDF download URL for landlord view
export const getBillPdfUrl = (_token: string, billId: string): string => {
  return `${API_URL}/bills/${billId}/pdf`;
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
  iban?: string | null;  // RON IBAN
  iban_eur?: string | null;  // EUR IBAN
  iban_usd?: string | null;  // USD IBAN
  property_order?: string[] | null;  // Ordered list of property IDs for display preference
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type RenterInfo = {
  renter: {
    id: string;
    name: string;
    email?: string | null;
    has_account: boolean;  // Whether renter has created account (password set)
    language: string;  // Language preference: "en" or "ro"
    email_notifications: boolean;  // Whether email notifications are enabled
    email_set_by_landlord: boolean;  // Whether email was set by landlord (renter can't change)
  };
  property: { id: string; name: string; address: string } | null;
  date_format?: string;
  landlord_iban?: string | null;  // Landlord's RON IBAN for rent payments
  landlord_iban_eur?: string | null;  // Landlord's EUR IBAN for rent payments
  landlord_iban_usd?: string | null;  // Landlord's USD IBAN for rent payments
  landlord_name?: string | null;  // Landlord's name for rent payments
  rent_currency?: string;  // Landlord's preferred rent currency
  rent_warning_days?: number;  // Number of days before due date to include bills in balance
};

export type RenterBill = {
  bill: Bill;
  paid_amount: number;
  remaining: number;
  is_direct_debit: boolean;  // Whether this bill's supplier has direct_debit enabled
  has_pdf: boolean;  // Whether a PDF file is available for download
  has_pending_notification?: boolean;  // Whether renter has a pending payment notification for this bill
  notifications?: PaymentNotificationSummary[];  // Payment notifications for this bill from this renter
};

export type PaymentNotificationSummary = {
  id: string;
  status: 'pending' | 'confirmed' | 'rejected';
  amount: number;
  currency: string;
  created_at: string;
  renter_note?: string;
  landlord_note?: string;
  confirmed_at?: string;
};

// Helper function to get PDF download URL for renter view
export const getRenterBillPdfUrl = (renterToken: string, billId: string): string => {
  return `${API_URL}/renter/${renterToken}/bill/${billId}/pdf`;
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

export type PaymentNotificationCreate = {
  bill_id: string;
  amount: number;
  currency?: string;
  renter_note?: string;
};

export type PaymentNotificationResponse = {
  notification: PaymentNotification;
  message: string;
  bank_transfer_info?: {
    iban: string;
    bill_number: string;
    amount: number;
    reference: string;
  };
};

export type PaymentNotification = {
  id: string;
  bill_id: string;
  renter_id: string;
  landlord_id: string;
  amount: number;
  currency: string;
  status: 'pending' | 'confirmed' | 'rejected';
  renter_note?: string;
  landlord_note?: string;
  created_at: string;
  confirmed_at?: string;
};

export type PaymentNotificationWithDetails = {
  notification: PaymentNotification;
  bill: {
    id: string;
    description: string;
    amount: number;
    currency: string;
    due_date: string;
    status: string;
    bill_number?: string;
    iban?: string;
  } | null;
  renter: {
    id: string;
    name: string;
    email?: string;
    phone?: string;
  } | null;
  property: {
    id: string;
    name: string;
    address: string;
  } | null;
};

export type PaymentNotificationActionResponse = {
  notification: PaymentNotification;
  message: string;
  bill_status?: string;
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

export type SubscriptionStatus = {
  status: 'active' | 'expired' | 'none';
  expires?: string;
  subscription_tier: number;
  is_free_tier: boolean;
  
  // Current usage
  property_count: number;
  supplier_count: number;
  renter_count: number;
  
  // Limits based on tier
  limits: {
    max_properties: number;
    max_suppliers: number;
    max_suppliers_per_property: number;
    max_renters: number;
    max_renters_per_property: number;
    email_sync_enabled: boolean;
  };
  
  // Action permissions
  can_add_property: boolean;
  can_add_supplier: boolean;
  can_add_renter: boolean;
  can_use_email_sync: boolean;
  
  // Deprecated
  needs_subscription?: boolean;
};

export type StripeConfig = {
  public_key: string;
  enabled: boolean;
  price_id: string;
};

export type StripeCheckoutSession = {
  session_id: string;
  url: string;
};

export type StripePortalSession = {
  url: string;
  type?: 'portal' | 'checkout';  // 'checkout' when no subscription exists
};

export type StripeSubscription = {
  has_subscription: boolean;
  stripe_enabled: boolean;
  subscription_tier: number;
  subscription_id?: string;
  status?: string;
  quantity?: number;
  current_period_end?: number;
  cancel_at_period_end?: boolean;
  error?: string;
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

export type UserPatternInfo = {
  user_id: string;
  user_email: string;
  user_name: string;
  subscription_tier: number;
  pattern_id: string;
  pattern_name: string;
  supplier?: string;
  bill_type: BillType;
  field_count: number;
  created_at: string;
  filename: string;
};
