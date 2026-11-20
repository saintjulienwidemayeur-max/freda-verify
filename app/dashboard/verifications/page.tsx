import DashShell from "@/components/DashShell";
import EmptyState from "@/components/EmptyState";

export const metadata = { title: "Verifications — Freda Verify" };

export default function Page() {
  return (
    <DashShell active="Verifications" sample={false}>
      <EmptyState title="Verifications" intro="People your customers have verified (KYC) will be listed here."
        body="No verifications yet. The verification engine and the verifications API are not released, and the hosted page does not upload anything, so there is nothing to show. Selfie videos, ID photos and decisions will appear here once real verifications are processed." />
    </DashShell>
  );
}
