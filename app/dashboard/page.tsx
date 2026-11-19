import DashShell from "@/components/DashShell";

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
const BARS = [42, 58, 51, 74, 66, 88, 79];

export default function Dashboard() {
  return (
    <DashShell active="Overview">
        <h1 className="text-3xl font-extrabold tracking-tighter">Overview</h1>
        <div className="mt-5 grid grid-cols-2 gap-px border border-navy/80 bg-navy md:grid-cols-4">
          {[["12,480", "Total checks"], ["96.4%", "Success rate"], ["1.2s", "Avg response"], ["37", "Active requests"]].map(([v, l]) => (
            <div key={l} className="bg-ice p-4"><div className="text-2xl font-bold">{v}</div><div className="text-xs opacity-60">{l}</div></div>
          ))}
        </div>
        <div className="mt-6 border border-navy/80 p-4">
          <div className="mb-3 text-sm font-bold">Checks per day (last 7 days)</div>
          <div className="flex h-32 items-end gap-2" role="img" aria-label="Bar chart of checks per day">
            {BARS.map((h, i) => <div key={i} className="flex-1 bg-blue" style={{ height: `${h}%` }} />)}
          </div>
        </div>
        <div className="mt-6 overflow-x-auto border border-navy/80">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-navy/80 font-mono text-xs"><tr>{["Name", "Type", "Document", "Status", "Match"].map((h) => <th key={h} className="p-3 font-medium">{h}</th>)}</tr></thead>
            <tbody>
              {ROWS.map(([n, t, d, s, m]) => (
                <tr key={n} className="border-b border-blue/15 last:border-0">
                  <td className="p-3">{n}</td><td className="p-3">{t}</td><td className="p-3">{d}</td>
                  <td className="p-3"><span className={`rounded-full px-3 py-1 font-mono text-xs ${BADGE[s]}`}>{s}</span></td>
                  <td className="p-3 font-mono">{m.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
    </DashShell>
  );
}
