import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Polymarket Tail Risk",
  description: "Wave 1 scaffold for the research and risk control console."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

