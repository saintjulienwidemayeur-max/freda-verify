import DashShell from "@/components/DashShell";
import Businesses from "@/components/Businesses";

export const metadata = { title: "Businesses — Freda Verify" };

export default function Page() {
  return <DashShell active="Businesses"><Businesses /></DashShell>;
}
