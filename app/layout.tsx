import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import localFont from "next/font/local";

// Fonts are self-hosted from npm packages (SIL OFL): the build no longer needs to reach Google Fonts.
const inter = localFont({ src: "../node_modules/@fontsource-variable/inter/files/inter-latin-wght-normal.woff2", weight: "100 900", variable: "--f", display: "swap" });
const jakarta = localFont({ src: "../node_modules/@fontsource-variable/plus-jakarta-sans/files/plus-jakarta-sans-latin-wght-normal.woff2", weight: "200 800", variable: "--h", display: "swap" });
const mono = localFont({
  src: [
    { path: "../node_modules/@fontsource/ibm-plex-mono/files/ibm-plex-mono-latin-400-normal.woff2", weight: "400" },
    { path: "../node_modules/@fontsource/ibm-plex-mono/files/ibm-plex-mono-latin-500-normal.woff2", weight: "500" },
  ],
  variable: "--m", display: "swap",
});

export const metadata = { metadataBase: new URL("https://fredaverify.com"), title: "Freda Verify — Automated identity verification" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${jakarta.variable} ${mono.variable}`}>
      <body className="overflow-x-hidden font-sans antialiased"><AuthProvider>{children}</AuthProvider></body>
    </html>
  );
}
