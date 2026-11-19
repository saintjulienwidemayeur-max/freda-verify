"use client";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, ApiError, refreshSession, setAccessToken, setSignedOutHandler, tokenStore, type Org, type Tokens, type User } from "./api";

type Status = "loading" | "anon" | "authed";
type LoginResult = { mfaToken: string } | { ok: true };

type Ctx = {
  status: Status; user: User | null; orgs: Org[]; org: Org | null;
  login: (email: string, password: string, remember: boolean) => Promise<LoginResult>;
  verifyMfa: (mfaToken: string, code: string, remember: boolean) => Promise<void>;
  register: (v: { email: string; password: string; full_name: string; organization_name: string }, remember: boolean) => Promise<void>;
  logout: () => Promise<void>;
  setOrg: (id: string) => void;
  reload: () => Promise<void>;
};

const AuthCtx = createContext<Ctx | null>(null);
const ORG = "fv.org";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [user, setUser] = useState<User | null>(null);
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [orgId, setOrgId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [me, list] = await Promise.all([api<User>("/auth/me"), api<Org[]>("/organizations")]);
    setUser(me); setOrgs(list);
    let saved: string | null = null;
    try { saved = localStorage.getItem(ORG); } catch { /* ignore */ }
    setOrgId(list.find((o) => o.id === saved)?.id ?? list[0]?.id ?? null);
    setStatus("authed");
  }, []);

  const signedOut = useCallback(() => { setAccessToken(null); tokenStore.clear(); setUser(null); setOrgs([]); setOrgId(null); setStatus("anon"); }, []);

  useEffect(() => {
    setSignedOutHandler(signedOut);
    (async () => {
      if (!tokenStore.get()) return setStatus("anon");
      try { if (await refreshSession()) await load(); else signedOut(); } catch (e) { if (e instanceof ApiError && e.code === "network") setStatus("anon"); else signedOut(); }
    })();
    return () => setSignedOutHandler(null);
  }, [load, signedOut]);

  const accept = useCallback(async (t: Tokens, remember: boolean) => { setAccessToken(t.access_token); tokenStore.set(t.refresh_token, remember); await load(); }, [load]);

  const value = useMemo<Ctx>(() => ({
    status, user, orgs, org: orgs.find((o) => o.id === orgId) ?? null,
    login: async (email, password, remember) => {
      const r = await api<Tokens | { mfa_required: true; mfa_token: string }>("/auth/login", { method: "POST", json: { email, password }, auth: false });
      if ("mfa_required" in r) return { mfaToken: r.mfa_token };
      await accept(r, remember); return { ok: true };
    },
    verifyMfa: async (mfaToken, code, remember) => { await accept(await api<Tokens>("/auth/mfa/verify", { method: "POST", json: { mfa_token: mfaToken, code }, auth: false }), remember); },
    register: async (v, remember) => { await accept(await api<Tokens>("/auth/register", { method: "POST", json: v, auth: false }), remember); },
    logout: async () => {
      const rt = tokenStore.get();
      try { if (rt) await api("/auth/logout", { method: "POST", json: { refresh_token: rt }, auth: false }); } catch { /* the local session is cleared either way */ }
      signedOut();
    },
    setOrg: (id) => { setOrgId(id); try { localStorage.setItem(ORG, id); } catch { /* ignore */ } },
    reload: load,
  }), [status, user, orgs, orgId, accept, load, signedOut]);

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): Ctx {
  const c = useContext(AuthCtx);
  if (!c) throw new Error("useAuth must be used inside <AuthProvider>");
  return c;
}

/** Role helpers used by the UI (the API enforces the same rules: the UI only hides what would be refused). */
export const can = {
  manageKeys: (o: Org | null) => o?.role === "owner" || o?.role === "admin",
  readKeys: (o: Org | null) => !!o && o.role !== "viewer",
  manageMembers: (o: Org | null) => o?.role === "owner" || o?.role === "admin",
  rename: (o: Org | null) => o?.role === "owner" || o?.role === "admin",
  audit: (o: Org | null) => o?.role === "owner" || o?.role === "admin",
};
