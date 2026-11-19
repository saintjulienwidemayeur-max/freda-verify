"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { useAuth } from "@/lib/auth";

const I = ({ children }: { children: ReactNode }) => (
  <svg viewBox="0 0 24 24" className="h-[18px] w-[18px] shrink-0" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>{children}</svg>
);
const ICONS = {
  overview: <I><rect x="3.5" y="3.5" width="7" height="7" rx="2" /><rect x="13.5" y="3.5" width="7" height="7" rx="2" /><rect x="3.5" y="13.5" width="7" height="7" rx="2" /><rect x="13.5" y="13.5" width="7" height="7" rx="2" /></I>,
  people: <I><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20c.5-3.6 3.2-5.5 6.5-5.5s6 1.900 6.500 5.500M16 4.800a3.500 3.500 0 0 1 0 6.400M18 14.800c1.900.7 3.200 2.300 3.500 5.200" /></I>,
  brand: <I><path d="M12 3a9 9 0 1 0 0 18c1.400 0 2-.900 2-1.800 0-1.200-1-1.500-1-2.700 0-1 .800-1.500 1.800-1.500H17a4 4 0 0 0 4-4c0-4.200-4-8-9-8z" /><circle cx="7.500" cy="11" r="1" /><circle cx="10" cy="7.500" r="1" /><circle cx="14.500" cy="7.500" r="1" /></I>,
  business: <I><path d="M4 20V6.5A1.5 1.5 0 0 1 5.5 5H13a1.5 1.5 0 0 1 1.5 1.5V20M14.5 10H18.5A1.5 1.5 0 0 1 20 11.5V20M2.5 20h19M8 9h2.5M8 12.5h2.5M8 16h2.5" /></I>,
  key: <I><circle cx="8" cy="15" r="3.5" /><path d="M10.5 12.5L20 3M16 7l3 3M13.5 9.5l2 2" /></I>,
  logs: <I><path d="M5 4.5h14M5 9.5h14M5 14.5h9M5 19.5h6" /></I>,
  settings: <I><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" /></I>,
  help: <I><circle cx="12" cy="12" r="9" /><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.4-1 .9-1 1.7M12 17h.01" /></I>,
};

const MAIN: [keyof typeof ICONS, string, string | null][] = [
  ["overview", "Overview", "/dashboard"],
  ["people", "Verifications", "/dashboard/verifications"],
  ["business", "Businesses", "/dashboard/businesses"],
  ["brand", "White label", "/dashboard/white-label"],
  ["key", "API Keys", "/dashboard/api-keys"],
  ["logs", "Logs", "/dashboard/logs"],
];
const SETTING: [keyof typeof ICONS, string, string][] = [["settings", "Settings", "/dashboard/settings"], ["help", "Support & Help", "/dashboard/support"]];

export default function DashShell({ active, children, sample = true }: { active: string; children: ReactNode; sample?: boolean }) {
  const [mini, setMini] = useState(false);
  const { status, user, orgs, org, setOrg, logout } = useAuth();
  const router = useRouter();
  const path = usePathname();
  // UX guard only: the API itself refuses every request without a valid session
  useEffect(() => { if (status === "anon") router.replace(`/login?next=${encodeURIComponent(path || "/dashboard")}`); }, [status, router, path]);
  if (status !== "authed") {
    return (
      <div className="grid min-h-screen place-items-center bg-[#F6F8FC]" role="status" aria-label="Loading">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-[#d6e2ff] border-t-blue" />
      </div>
    );
  }
  const initials = (user?.full_name || user?.email || "?").split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  const label = (t: string) => <span className={mini ? "md:hidden" : ""}>{t}</span>;
  const item = "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm";

  return (
    <div className="min-h-screen bg-[#F6F8FC] md:flex">
      <aside className={`flex flex-col border-b border-[#e3eaf8] bg-white md:sticky md:top-0 md:h-screen md:border-b-0 md:border-r ${mini ? "md:w-[76px]" : "md:w-64"} transition-[width] duration-200`}>
        <div className="flex items-center justify-between p-4">
          <Link href="/" className="flex items-center gap-2 font-display font-extrabold tracking-tight">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo-mark.svg" alt="" className="h-8 w-8" />
            {label("Freda Verify")}
          </Link>
          <button onClick={() => setMini(!mini)} aria-label={mini ? "Expand menu" : "Collapse menu"} aria-pressed={mini}
            className="hidden h-8 w-8 place-items-center rounded-lg border border-[#e3eaf8] text-navy/60 hover:bg-ice md:grid">
            <svg viewBox="0 0 24 24" className={`h-4 w-4 transition-transform ${mini ? "rotate-180" : ""}`} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M15 6l-6 6 6 6" /></svg>
          </button>
        </div>

        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto px-3 pb-3" aria-label="Dashboard">
          <p className={`px-3 pb-1 pt-3 font-mono text-[10px] uppercase tracking-widest text-navy/50 ${mini ? "md:invisible" : ""}`}>Main menu</p>
          <div className="flex flex-wrap gap-1 md:flex-col">
            {MAIN.map(([ic, n, href]) =>
              href ? (
                <Link key={n} href={href} title={n} aria-current={n === active ? "page" : undefined}
                  className={`${item} ${n === active ? "border border-[#d6e2ff] bg-ice font-semibold text-blue" : "border border-transparent text-navy/80 hover:bg-ice"}`}>
                  {ICONS[ic]}{label(n)}
                </Link>
              ) : (
                <span key={n} title={`${n} — coming soon`} className={`${item} cursor-not-allowed border border-transparent text-navy/35`}>
                  {ICONS[ic]}{label(n)}
                </span>
              ),
            )}
          </div>
          <p className={`mt-4 px-3 pb-1 pt-3 font-mono text-[10px] uppercase tracking-widest text-navy/50 ${mini ? "md:invisible" : ""}`}>Setting</p>
          <div className="flex flex-wrap gap-1 md:flex-col">
            {SETTING.map(([ic, n, href]) => (
              <Link key={n} href={href} title={n} aria-current={n === active ? "page" : undefined}
                className={`${item} ${n === active ? "border border-[#d6e2ff] bg-ice font-semibold text-blue" : "border border-transparent text-navy/80 hover:bg-ice"}`}>{ICONS[ic]}{label(n)}</Link>
            ))}
          </div>
        </nav>

        <div className="hidden p-3 md:block">
          <div className="rounded-2xl border border-[#e3eaf8] p-2.5">
            <div className="flex items-center gap-3">
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-navy text-xs font-bold text-white" title={user?.email}>{initials}</span>
              {!mini && <div className="min-w-0 flex-1 text-xs"><div className="truncate font-semibold">{user?.full_name}</div><div className="truncate text-navy/50">{org?.name ?? "No organization"}{org?.role ? ` · ${org.role}` : ""}</div></div>}
              <button onClick={() => void logout().then(() => router.replace("/login"))} aria-label="Sign out" title="Sign out" className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-navy/60 hover:bg-ice hover:text-navy">
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M9 4H5.5A1.5 1.5 0 0 0 4 5.500v13A1.5 1.5 0 0 0 5.500 20H9M16 16l4-4-4-4M20 12H9" /></svg>
              </button>
            </div>
            {!mini && orgs.length > 1 && (
              <select value={org?.id ?? ""} onChange={(e) => setOrg(e.target.value)} aria-label="Switch organization" className="mt-2.5 w-full rounded-lg border border-[#e3eaf8] bg-white px-2 py-1.5 text-xs">
                {orgs.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
              </select>
            )}
          </div>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="flex items-center justify-between border-b border-[#e3eaf8] bg-white px-6 py-4 text-sm">
          <div className="flex items-center gap-2"><span className="text-navy/45">Main menu</span><span className="text-navy/30">/</span><span className="flex items-center gap-1.5 font-medium">{ICONS[([...MAIN, ...SETTING].find((m) => m[1] === active) ?? MAIN[0])[0]]}{active}</span></div>
          {sample
            ? <span className="rounded-full border border-[#d6e2ff] bg-ice px-3 py-1 font-mono text-[10px] uppercase tracking-widest text-blue">Sample data</span>
            : <span className="rounded-full border border-[#b7e8cf] bg-[#E7F7EF] px-3 py-1 font-mono text-[10px] uppercase tracking-widest text-[#067647]">Live data</span>}
        </header>
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
