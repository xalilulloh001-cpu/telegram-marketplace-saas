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
