import type { Metadata } from "next";
import { IBM_Plex_Sans } from "next/font/google";
import "./globals.css";

const ibmPlexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-ibm-plex-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "TheDiffNews",
  description: "Independent AI coverage — multi-outlet story clusters.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-theme="signal" className={ibmPlexSans.variable}>
      <body className={`${ibmPlexSans.className} antialiased`} data-theme="signal">
        {children}
      </body>
    </html>
  );
}
