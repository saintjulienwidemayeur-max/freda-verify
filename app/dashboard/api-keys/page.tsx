import DashShell from "@/components/DashShell";
import ApiKeys from "@/components/ApiKeys";

export const metadata = { title: "API Keys — Freda Verify" };

export default function Page() {
  return <DashShell active="API Keys" sample={false}><ApiKeys /></DashShell>;
}
