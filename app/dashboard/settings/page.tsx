import DashShell from "@/components/DashShell";
import Settings from "@/components/Settings";

export const metadata = { title: "Settings — Freda Verify" };

export default function Page() {
  return <DashShell active="Settings"><Settings /></DashShell>;
}
