export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// The session token lives in module memory for the lifetime of the Mini App view.
// It is never written to localStorage or sessionStorage.
let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export async function apiFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  headers.set("Content-Type", "application/json");
  return fetch(`${API_BASE}${path}`, { ...init, headers });
}

export async function apiJson<T>(path: string): Promise<T> {
  const res = await apiFetch(path);
  if (res.status === 404) throw new NotFoundError();
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json() as Promise<T>;
}

export class NotFoundError extends Error {
  constructor() {
    super("not found");
    this.name = "NotFoundError";
  }
}

export type Page<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
};

export type Shop = {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  logo_url: string | null;
};

export type ShopDetail = Shop & {
  contact_phone: string | null;
  contact_email: string | null;
  address_line: string | null;
  city: string | null;
};

export type Category = {
  id: number;
  name: string;
  slug: string;
  parent_id: number | null;
};

export type Product = {
  id: number;
  name: string;
  slug: string;
  price: string;
  discount_price: string | null;
  display_price: string;
  category_id: number | null;
  image_url: string | null;
  in_stock: boolean;
};

export type ProductDetail = Product & {
  description: string | null;
  images: { id: number; url: string }[];
  category: Category | null;
};

export function formatPrice(value: string): string {
  const number = Number(value);
  if (Number.isNaN(number)) return value;
  return new Intl.NumberFormat("uz-UZ", { maximumFractionDigits: 0 }).format(number);
}

export type CartItem = {
  item_id: number;
  product_id: number;
  product_name: string;
  image_url: string | null;
  quantity: number;
  unit_price: string;
  display_price: string;
  line_total: string;
  in_stock: boolean;
  available: boolean;
};

export type Cart = {
  cart_id: number | null;
  shop_id: number;
  items: CartItem[];
  subtotal: string;
  total_items: number;
};

export type Favorite = {
  product_id: number;
  shop_id: number;
  product_name: string;
  image_url: string | null;
  price: string;
  discount_price: string | null;
  display_price: string;
  in_stock: boolean;
  is_available: boolean;
};

export async function apiSend<T>(path: string, method: string, body?: unknown): Promise<T> {
  const res = await apiFetch(path, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 404) throw new NotFoundError();
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `Request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export type OrderItem = {
  id: number;
  product_id: number | null;
  product_name: string;
  list_price: string | null;
  unit_price: string;
  quantity: number;
  line_total: string;
};

export type Order = {
  id: number;
  order_number: string;
  shop_id: number;
  shop_name: string | null;
  status: string;
  subtotal: string;
  total: string;
  total_items: number;
  created_at: string;
};

export type OrderDetail = Order & {
  items: OrderItem[];
  address_snapshot: string | null;
  phone_snapshot: string | null;
  customer_name_snapshot: string | null;
  comment: string | null;
};

export type CheckoutConflict = {
  message: string;
  items: {
    product_id: number;
    product_name: string;
    reason: string;
    available_stock: number | null;
  }[];
};

export const ORDER_STATUS_LABELS: Record<string, string> = {
  pending: "Kutilmoqda",
  confirmed: "Tasdiqlangan",
  processing: "Tayyorlanmoqda",
  shipped: "Yo'lda",
  delivered: "Yetkazilgan",
  cancelled: "Bekor qilingan",
};

export class ConflictError extends Error {
  detail: CheckoutConflict | string;
  constructor(detail: CheckoutConflict | string) {
    super(typeof detail === "string" ? detail : detail.message);
    this.name = "ConflictError";
    this.detail = detail;
  }
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await apiFetch(path, {
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 404) throw new NotFoundError();
  if (res.status === 409) {
    const payload = await res.json().catch(() => null);
    throw new ConflictError(payload?.detail ?? "Amal bajarilmadi");
  }
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
