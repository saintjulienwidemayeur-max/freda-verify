import Link from "next/link";

type Status = "APPROVED" | "REJECTED" | "PENDING";
const ROWS: [string, string, string, Status, number][] = [
  ["Marc Jean-Baptiste", "KYC", "ID card", "APPROVED", 99.8],
  ["Kafe Lakay SARL", "KYB", "Company registry", "APPROVED", 97.2],
  ["Nadège Pierre", "KYC", "Passport", "PENDING", 88.4],
  ["Sunrise Trading", "KYB", "Company registry", "REJECTED", 41.0],
  ["Jonas Étienne", "KYC", "ID card", "APPROVED", 98.6],
];
const BADGE: Record<Status, string> = {
  APPROVED: "bg-black text-white",
  REJECTED: "border border-black bg-white line-through",
  PENDING: "border border-dashed border-black",
};
const BARS = [42, 58, 51, 74, 66, 88, 79];
const NAV = ["Overview", "Verifications", "API Keys", "Logs", "Settings"];

export default function Dashboard() {
  return (
    <div className="grid min-h-screen md:grid-cols-[200px_1fr]">
      <aside className="border-b border-black p-5 md:border-b-0 md:border-r">
        <Link href="/" className="font-bold tracking-tight">FREDA VERIFY</Link>
        <nav className="mt-6 flex gap-4 text-sm md:flex-col md:gap-2">
          {NAV.map((n, i) => <a key={n} href="#" className={i === 0 ? "font-bold underline" : "opacity-70"}>{n}</a>)}
        </nav>
      </aside>
      <main className="min-w-0 p-6">
        <h1 className="text-3xl font-extrabold tracking-tighter">Overview</h1>
        <div className="mt-5 grid grid-cols-2 gap-px border border-black bg-black md:grid-cols-4">
          {[["12,480", "Total checks"], ["96.4%", "Success rate"], ["1.2s", "Avg response"], ["37", "Active requests"]].map(([v, l]) => (
            <div key={l} className="bg-[#e8e8e6] p-4"><div className="text-2xl font-bold">{v}</div><div className="text-xs opacity-60">{l}</div></div>
          ))}
        </div>
        <div className="mt-6 border border-black p-4">
          <div className="mb-3 text-sm font-bold">Checks per day (last 7 days)</div>
          <div className="flex h-32 items-end gap-2" role="img" aria-label="Bar chart of checks per day">
            {BARS.map((h, i) => <div key={i} className="flex-1 bg-black" style={{ height: `${h}%` }} />)}
          </div>
        </div>
        <div className="mt-6 overflow-x-auto border border-black">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-black font-mono text-xs"><tr>{["Name", "Type", "Document", "Status", "Match"].map((h) => <th key={h} className="p-3 font-medium">{h}</th>)}</tr></thead>
            <tbody>
              {ROWS.map(([n, t, d, s, m]) => (
                <tr key={n} className="border-b border-black/20 last:border-0">
                  <td className="p-3">{n}</td><td className="p-3">{t}</td><td className="p-3">{d}</td>
                  <td className="p-3"><span className={`rounded-full px-3 py-1 font-mono text-xs ${BADGE[s]}`}>{s}</span></td>
                  <td className="p-3 font-mono">{m.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
