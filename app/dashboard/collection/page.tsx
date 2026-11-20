import DashShell from "@/components/DashShell";
import Collection from "@/components/Collection";

export const metadata = { title: "Collection — Freda Verify" };

export default function Page() {
  return <DashShell active="Collection" sample={false}><Collection /></DashShell>;
}
