import DashShell from "@/components/DashShell";
import Logs from "@/components/Logs";

export const metadata = { title: "Logs — Freda Verify" };

export default function Page() {
  return <DashShell active="Logs" sample={false}><Logs /></DashShell>;
}
