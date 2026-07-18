// Strip any trailing slash(es): if NEXT_PUBLIC_API_BASE_URL is set with a
// trailing slash (an easy mistake when copy-pasting a URL from a browser
// bar), naively concatenating "/api/..." onto it produces a double slash
// (e.g. "https://x.onrender.com//api/apps"), which FastAPI's router treats
// as a different, non-existent path and 404s on every request.
const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");
   const WS_BASE = API_BASE.replace(/^http/, "ws");

export type Store = "apple_app_store" | "google_play";

export interface AppSummary {
  id: string;
  store: Store;
  store_id: string;
  country: string;
  name: string | null;
  developer: string | null;
  category: string | null;
  icon_url: string | null;
  price: string | null;
  version: string | null;
  is_favorite: boolean;
  is_archived: boolean;
  tags: string[];
  updated_at: string | null;
}

export interface Snapshot {
  rating: number | null;
  rating_count: number | null;
  review_count: number | null;
  install_bucket_min: number | null;
  install_bucket_max: number | null;
  category_rank: number | null;
  overall_rank: number | null;
  chart_type: string | null;
  sources: string[];
  fetched_at: string;
}

export interface Milestone {
  source: string;
  source_url: string | null;
  reported_downloads: number | null;
  context: string | null;
  found_at: string;
}

export interface Estimate {
  estimated_daily_downloads: number | null;
  low_bound: number | null;
  high_bound: number | null;
  confidence_pct: number | null;
  method: string | null;
  notes: string | null;
  created_at: string;
}

export interface AppDetail extends AppSummary {
  latest_snapshot: Snapshot | null;
  latest_estimate: Estimate | null;
  history: Snapshot[];
  milestones: Milestone[];
}

export interface Kpis {
  total_apps_tracked: number;
  today_estimated_downloads: number;
  yesterday_estimated_downloads: number;
  thirty_day_estimated_downloads: number;
  average_rating: number | null;
  reviews_today: number;
  countries_monitored: number;
  alerts_triggered_today: number;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  if (res.status === 204) return undefined as unknown as T;
  return res.json();
}

export const api = {
  listApps: (params: { q?: string; favorite?: boolean; archived?: boolean } = {}) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.favorite !== undefined) qs.set("favorite", String(params.favorite));
    if (params.archived !== undefined) qs.set("archived", String(params.archived));
    return req<AppSummary[]>(`/api/apps?${qs.toString()}`);
  },
  addApp: (payload: { store: Store; store_id: string; country?: string }) =>
    req<AppSummary>(`/api/apps`, { method: "POST", body: JSON.stringify(payload) }),
  getApp: (id: string, days = 30) => req<AppDetail>(`/api/apps/${id}?days=${days}`),
  updateApp: (id: string, patch: { is_favorite?: boolean; is_archived?: boolean; tags?: string[] }) => {
    const qs = new URLSearchParams();
    Object.entries(patch).forEach(([k, v]) => {
      if (v !== undefined) qs.set(k, Array.isArray(v) ? v.join(",") : String(v));
    });
    return req<AppSummary>(`/api/apps/${id}?${qs.toString()}`, { method: "PATCH" });
  },
  deleteApp: (id: string) => req<void>(`/api/apps/${id}`, { method: "DELETE" }),
  refreshApp: (id: string) => req<AppDetail>(`/api/apps/${id}/refresh`, { method: "POST" }),
  getKpis: () => req<Kpis>(`/api/dashboard/kpis`),
  getAlerts: () => req<{ id: string; app_id: string; type: string; message: string; is_read: boolean; created_at: string }[]>(
    `/api/dashboard/alerts`
  ),
};

export function wsUrl() {
  return `${WS_BASE}/ws`;
}
