import DashShell from "@/components/DashShell";
import Webhooks from "@/components/Webhooks";

export const metadata = { title: "Webhooks — Freda Verify" };

export default function Page() {
  return <DashShell active="Webhooks" sample={false}><Webhooks /></DashShell>;
}
