import DashShell from "@/components/DashShell";
import EmptyState from "@/components/EmptyState";

export const metadata = { title: "Businesses — Freda Verify" };

export default function Page() {
  return (
    <DashShell active="Businesses" sample={false}>
      <EmptyState title="Businesses" intro="Companies verified through KYB will be listed here."
        body="No business verifications yet. KYB (company registry checks, beneficial owners) is not built, so there is nothing to show." />
    </DashShell>
  );
}
