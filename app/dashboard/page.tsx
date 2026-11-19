import Link from "next/link";
import DashShell from "@/components/DashShell";
import OverviewChart from "@/components/OverviewChart";

type Status = "APPROVED" | "REJECTED" | "PENDING";
const ROWS: [string, string, string, Status, number][] = [
  ["Marc Jean-Baptiste", "KYC", "ID card", "APPROVED", 99.8],
  ["Kafe Lakay SARL", "KYB", "Company registry", "APPROVED", 97.2],
  ["Nadège Pierre", "KYC", "Passport", "PENDING", 88.4],
  ["Sunrise Trading", "KYB", "Company registry", "REJECTED", 41.0],
  ["Jonas Étienne", "KYC", "ID card", "APPROVED", 98.6],
];
const BADGE: Record<Status, string> = {
  APPROVED: "bg-[#E7F7EF] text-[#067647]",
  REJECTED: "bg-[#FDECEA] text-[#B42318]",
  PENDING: "bg-[#FEF3E2] text-[#B54708]",
};
const WHEN = ["2 min ago", "14 min ago", "31 min ago", "1 h ago", "2 h ago"];

const Svg = ({ children }: { children: React.ReactNode }) => (
  <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>{children}</svg>
);
const STATS: { label: string; value: string; delta: string; up: boolean; icon: React.ReactNode; spark: number[] }[] = [
  { label: "Total checks", value: "12,480", delta: "+21%", up: true, icon: <Svg><path d="M9 12l2 2 4-4M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z" /></Svg>, spark: [3, 5, 4, 7, 6, 9, 8] },
  { label: "Success rate", value: "96.4%", delta: "+1.8%", up: true, icon: <Svg><circle cx="12" cy="12" r="9" /><path d="M8 12.5l2.5 2.5L16 9.5" /></Svg>, spark: [5, 4, 6, 6, 7, 8, 9] },
  { label: "Avg response", value: "1.2s", delta: "-0.3s", up: true, icon: <Svg><circle cx="12" cy="13" r="8" /><path d="M12 9v4l2.5 1.5M9.5 2.5h5" /></Svg>, spark: [8, 7, 8, 6, 5, 5, 4] },
  { label: "Active requests", value: "37", delta: "-4", up: false, icon: <Svg><path d="M4 12h4l3 7 4-14 3 7h2" /></Svg>, spark: [6, 7, 5, 8, 6, 5, 4] },
];

function Spark({ d, up }: { d: number[]; up: boolean }) {
  const max = Math.max(...d), min = Math.min(...d);
  const pts = d.map((v, i) => `${(i / (d.length - 1)) * 80},${26 - ((v - min) / (max - min || 1)) * 22}`).join(" ");
  return (
    <svg viewBox="0 0 80 28" className="h-8 w-20" aria-hidden>
      <polyline points={pts} fill="none" stroke={up ? "#12B76A" : "#D92D20"} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Dashboard() {
  return (
    <DashShell active="Overview">
      <h1 className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">Welcome to Freda Verify 👋</h1>
      <p className="mt-1 text-sm text-navy/60">Track verifications, review decisions and monitor your API — all in one place.</p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {STATS.map((s) => (
          <div key={s.label} className="rounded-2xl border border-[#e3eaf8] bg-white p-4">
            <div className="flex items-center gap-2 text-sm font-medium"><span className="grid h-8 w-8 place-items-center rounded-lg border border-[#e3eaf8] text-blue">{s.icon}</span>{s.label}</div>
            <div className="mt-4 flex items-end justify-between">
              <div>
                <div className="font-display text-3xl font-bold tabular-nums">{s.value}</div>
                <div className="mt-1 text-xs"><span className={`font-semibold ${s.up ? "text-[#067647]" : "text-[#B42318]"}`}>{s.delta}</span> <span className="text-navy/50">vs last week</span></div>
              </div>
              <Spark d={s.spark} up={s.up} />
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_340px]">
        <div className="min-w-0 space-y-4">
          <OverviewChart />
          <section className="rounded-2xl border border-[#e3eaf8] bg-white p-5" aria-label="Recent verifications">
            <div className="flex items-center justify-between"><h2 className="font-display text-lg font-bold">Recent verifications</h2><Link href="/dashboard/verifications" className="text-sm font-medium text-blue hover:underline">View all →</Link></div>
            <div className="mt-3 overflow-x-auto rounded-xl border border-[#e3eaf8]">
              <table className="w-full text-left text-sm">
                <thead className="bg-[#F6F8FC] font-mono text-[11px] text-navy/60"><tr>{["Name", "Type", "Document", "Status", "Match"].map((h) => <th key={h} className="p-3 font-medium">{h}</th>)}</tr></thead>
                <tbody>
                  {ROWS.map(([n, t, d, s, m]) => (
                    <tr key={n} className="border-t border-[#e3eaf8]">
                      <td className="p-3 font-medium">{n}</td><td className="p-3">{t}</td><td className="p-3 text-navy/70">{d}</td>
                      <td className="p-3"><span className={`rounded-full px-3 py-1 font-mono text-xs ${BADGE[s]}`}>{s}</span></td>
                      <td className="p-3 font-mono">{m.toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <section className="rounded-2xl border border-[#e3eaf8] bg-white p-5" aria-label="Recent activity">
          <h2 className="font-display text-lg font-bold">Recent activity</h2>
          <ul className="mt-4 divide-y divide-[#e3eaf8]">
            {ROWS.map(([n, t, d, s, m], i) => (
              <li key={n} className="flex items-start gap-3 py-3.5">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-ice font-mono text-[11px] font-semibold text-blue">{t}</span>
                <div className="min-w-0 flex-1 text-sm">
                  <div className="truncate font-semibold">{n}</div>
                  <div className="mt-0.5 flex items-center gap-2 text-xs text-navy/55"><span className={`rounded-full px-2 py-0.5 font-mono text-[10px] ${BADGE[s]}`}>{s}</span>{d}</div>
                  <div className="mt-1 text-xs text-navy/45">Match {m.toFixed(1)}% · {WHEN[i]}</div>
                </div>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </DashShell>
  );
}
