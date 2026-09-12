import type { Metadata } from "next";
import "./globals.css";

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
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
