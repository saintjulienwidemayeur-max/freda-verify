import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { Inter, Plus_Jakarta_Sans, IBM_Plex_Mono } from "next/font/google";

const inter = Inter({ subsets: ["latin"], variable: "--f" });
const jakarta = Plus_Jakarta_Sans({ subsets: ["latin"], weight: ["500", "600", "700", "800"], variable: "--h" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--m" });

export const metadata = { title: "Freda Verify — Automated identity verification" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${jakarta.variable} ${mono.variable}`}>
      <body className="overflow-x-hidden font-sans antialiased"><AuthProvider>{children}</AuthProvider></body>
    </html>
  );
}
