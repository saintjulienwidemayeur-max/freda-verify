// Typed client for the Freda Verify API (backend/). The access token lives in memory only; the refresh token is kept in localStorage
// ("remember me") or sessionStorage. The backend rotates refresh tokens and revokes every session if an old one is replayed, so refreshes
// are serialised across browser tabs (Web Locks) to avoid a harmless race looking like a theft.

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details: { field: string; message: string }[] = [], public requestId?: string) {
    super(message);
  }
}

export type User = { id: string; email: string; full_name: string; mfa_enabled: boolean };
export type Org = { id: string; name: string; slug: string; role: string | null; created_at: string };
export type Tokens = { access_token: string; refresh_token: string; expires_in: number; user: User };

const RT = "fv.refresh";
let access: string | null = null;
let onSignedOut: (() => void) | null = null;

export const tokenStore = {
  get: (): string | null => { try { return localStorage.getItem(RT) ?? sessionStorage.getItem(RT); } catch { return null; } },
  set: (t: string, remember: boolean) => { try { localStorage.removeItem(RT); sessionStorage.removeItem(RT); (remember ? localStorage : sessionStorage).setItem(RT, t); } catch { /* storage blocked */ } },
  clear: () => { try { localStorage.removeItem(RT); sessionStorage.removeItem(RT); } catch { /* ignore */ } },
  remembered: (): boolean => { try { return localStorage.getItem(RT) !== null; } catch { return true; } },
};
export const setAccessToken = (t: string | null) => { access = t; };
export const setSignedOutHandler = (fn: (() => void) | null) => { onSignedOut = fn; };

async function raw(path: string, init: RequestInit & { json?: unknown; auth?: boolean; blob?: Blob }): Promise<Response> {
  if (!API_URL) throw new ApiError(0, "not_configured", "The API address is not configured (NEXT_PUBLIC_API_URL).");
  const headers: Record<string, string> = { Accept: "application/json" };
  if (init.json !== undefined) headers["Content-Type"] = "application/json";
  if (init.blob) headers["Content-Type"] = init.blob.type;
  if (init.auth !== false && access) headers.Authorization = `Bearer ${access}`;
  try {
    return await fetch(`${API_URL}/api/v1${path}`, { method: init.method ?? "GET", headers, body: init.blob ?? (init.json !== undefined ? JSON.stringify(init.json) : undefined), credentials: "omit", signal: init.signal });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError(0, "network", "Cannot reach the server. Check your connection and try again.");
  }
}

async function parse<T>(r: Response): Promise<T> {
  if (r.status === 204) return undefined as T;
  let body: unknown = null;
  try { body = await r.json(); } catch { /* empty body */ }
  if (r.ok) return body as T;
  const e = (body as { error?: { code?: string; message?: string; details?: { field: string; message: string }[]; request_id?: string } } | null)?.error;
  throw new ApiError(r.status, e?.code ?? "http_error", e?.message ?? `Request failed (${r.status})`, e?.details ?? [], e?.request_id);
}

let inflight: Promise<boolean> | null = null;
/** Exchanges the stored refresh token for new tokens. Serialised inside the tab and across tabs. */
export function refreshSession(): Promise<boolean> {
  inflight ??= (async () => {
    const run = async (): Promise<boolean> => {
      const rt = tokenStore.get();                                   // read AFTER taking the lock: another tab may have rotated it
      if (!rt) return false;
      try {
        const r = await raw("/auth/refresh", { method: "POST", json: { refresh_token: rt }, auth: false });
        if (!r.ok) { if (r.status === 401) { tokenStore.clear(); access = null; } return false; }
        const t = (await r.json()) as Tokens;
        access = t.access_token;
        tokenStore.set(t.refresh_token, tokenStore.remembered());
        return true;
      } catch { return false; }
    };
    try { return navigator.locks ? await navigator.locks.request("fv-refresh", run) : await run(); } finally { inflight = null; }
  })();
  return inflight;
}

type Opts = { method?: string; json?: unknown; blob?: Blob; auth?: boolean; signal?: AbortSignal };
export async function api<T = unknown>(path: string, opts: Opts = {}): Promise<T> {
  let r = await raw(path, opts);
  if (r.status === 401 && opts.auth !== false && tokenStore.get()) {
    if (await refreshSession()) r = await raw(path, opts);
    else onSignedOut?.();
  }
  return parse<T>(r);
}

/** Authenticated download of binary data (e.g. the logo). Returns null on 404. */
export async function apiBlob(path: string): Promise<Blob | null> {
  let r = await raw(path, {});
  if (r.status === 401 && tokenStore.get()) { if (await refreshSession()) r = await raw(path, {}); else onSignedOut?.(); }
  if (r.status === 404) return null;
  if (!r.ok) return parse<never>(r);
  return r.blob();
}

/** Only same-site relative paths are accepted as a post-login destination (no open redirect). */
export const safeNext = (v: string | null | undefined, fallback = "/dashboard"): string => (v && v.startsWith("/") && !v.startsWith("//") && !v.includes("\\") ? v : fallback);
