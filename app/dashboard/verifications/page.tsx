import DashShell from "@/components/DashShell";
import Verifications from "@/components/Verifications";

export const metadata = { title: "Verifications — Freda Verify" };

export default function Page() {
  return <DashShell active="Verifications" sample={false}><Verifications /></DashShell>;
}
