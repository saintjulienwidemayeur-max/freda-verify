import "./globals.css";
import { Inter_Tight, IBM_Plex_Mono } from "next/font/google";

const inter = Inter_Tight({ subsets: ["latin"], variable: "--f" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--m" });

export const metadata = { title: "Freda Verify — Automated identity verification" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable}`}>
      <body className="overflow-x-hidden font-sans antialiased">{children}</body>
    </html>
  );
}
