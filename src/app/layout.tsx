import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import "./globals.css";

const ibmPlexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-ibm-plex-sans",
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-ibm-plex-mono",
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
    <html
      lang="en"
      data-theme="aurora"
      className={`${ibmPlexSans.variable} ${ibmPlexMono.variable}`}
    >
      <body
        className={`${ibmPlexSans.className} antialiased`}
        data-theme="aurora"
      >
        {children}
      </body>
    </html>
  );
}
