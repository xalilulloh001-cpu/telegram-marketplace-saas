export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

// The CSRF cookie is deliberately readable by JavaScript — copying it into a header is
// what a cross-site attacker cannot do, since it cannot read our cookies.
function readCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)mp_csrf=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

// Sessions ride in an httpOnly cookie, so every call must include credentials
// and no session token is ever readable from JavaScript.
export async function apiFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) headers.set("Content-Type", "application/json");

  const method = (init.method ?? "GET").toUpperCase();
  if (!SAFE_METHODS.has(method)) {
    const csrf = readCsrfToken();
    if (csrf) headers.set("X-CSRF-Token", csrf);
  }

  return fetch(`${API_BASE}${path}`, { ...init, headers, credentials: "include" });
}

export async function apiJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await apiFetch(path, init);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<T>;
}

export type Page<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
};

export type Category = {
  id: number;
  name: string;
  slug: string;
  parent_id: number | null;
  is_active: boolean;
};

export type Product = {
  id: number;
  name: string;
  slug: string;
  price: string;
  discount_price: string | null;
  stock: number;
  is_active: boolean;
  category_id: number | null;
};

export type Shop = {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  contact_phone: string | null;
  city: string | null;
};

export type OrderItem = {
  id: number;
  product_id: number | null;
  product_name: string;
  unit_price: string;
  quantity: number;
  line_total: string;
};

export type Order = {
  id: number;
  order_number: string;
  status: string;
  subtotal: string;
  total: string;
  total_items: number;
  created_at: string;
};

export type SellerOrderDetail = Order & {
  customer_id: number;
  items: OrderItem[];
  address_snapshot: string | null;
  phone_snapshot: string | null;
  customer_name_snapshot: string | null;
  comment: string | null;
};

export const ORDER_STATUS_LABELS: Record<string, string> = {
  pending: "Kutilmoqda",
  confirmed: "Tasdiqlangan",
  processing: "Tayyorlanmoqda",
  shipped: "Yo'lda",
  delivered: "Yetkazilgan",
  cancelled: "Bekor qilingan",
};

// Mirrors the server-side state machine so the UI only offers legal moves; the server
// remains the authority and rejects anything else with 409.
export const NEXT_STATUSES: Record<string, string[]> = {
  pending: ["confirmed", "cancelled"],
  confirmed: ["processing", "cancelled"],
  processing: ["shipped", "cancelled"],
  shipped: ["delivered"],
  delivered: [],
  cancelled: [],
};

export function formatPrice(value: string): string {
  const number = Number(value);
  if (Number.isNaN(number)) return value;
  return new Intl.NumberFormat("uz-UZ", { maximumFractionDigits: 0 }).format(number);
}
