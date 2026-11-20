import Contribute from "@/components/Contribute";

export const metadata = {
  title: "Help us test fraud detection",
  description: "Donate a few photos to help test face anti-fraud detection.",
  robots: { index: false, follow: false },
};

export default function Page() {
  return <Contribute />;
}
