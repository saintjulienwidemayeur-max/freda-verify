import Link from "next/link";
import type { ReactNode } from "react";

const NAV: [string, string][] = [
  ["Overview", "/dashboard"],
  ["Businesses", "/dashboard/businesses"],
];
const SOON = ["API Keys", "Logs", "Settings"];

export default function DashShell({ active, children }: { active: string; children: ReactNode }) {
  return (
    <div className="grid min-h-screen md:grid-cols-[200px_1fr]">
      <aside className="border-b border-black p-5 md:border-b-0 md:border-r">
        <Link href="/" className="font-bold tracking-tight">FREDA VERIFY</Link>
        <nav className="mt-6 flex flex-wrap gap-4 text-sm md:flex-col md:gap-2">
          {NAV.map(([n, href]) => (
            <Link key={n} href={href} className={n === active ? "font-bold underline" : "opacity-70 hover:opacity-100"}>{n}</Link>
          ))}
          {SOON.map((n) => <span key={n} className="opacity-40" title="Coming soon">{n}</span>)}
        </nav>
      </aside>
      <main className="min-w-0 p-6">{children}</main>
    </div>
  );
}
