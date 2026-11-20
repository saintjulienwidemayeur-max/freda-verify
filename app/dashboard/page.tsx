import DashShell from "@/components/DashShell";
import Overview from "@/components/Overview";

export default function Dashboard() {
  return (
    <DashShell active="Overview" sample={false}>
      <Overview />
    </DashShell>
  );
}
