import DashShell from "@/components/DashShell";
import WhiteLabel from "@/components/WhiteLabel";

export const metadata = { title: "White label — Freda Verify" };

export default function Page() {
  return <DashShell active="White label" sample={false}><WhiteLabel /></DashShell>;
}
