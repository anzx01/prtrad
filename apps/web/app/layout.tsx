import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import ApiStatus from "./components/ApiStatus";

export const metadata: Metadata = {
  title: "Polymarket Tail Risk",
  description: "Research and risk control console for Polymarket tail risk management.",
};

const navLinks = [
  { href: "/", label: "Home" },
  { href: "/markets", label: "Markets" },
  { href: "/dq", label: "Data Quality" },
  { href: "/tagging", label: "Tagging" },
];

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[radial-gradient(circle_at_top,#0f2744,transparent_45%),linear-gradient(180deg,#06101b,#0c1724)] text-slate-100">
        <nav className="border-b border-white/10 bg-slate-950/60 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3 lg:px-10">
            <span className="text-sm font-semibold tracking-wide text-white">
              PRT Console
            </span>
            <div className="flex gap-4">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="text-sm text-slate-300 hover:text-white transition-colors"
                >
                  {link.label}
                </Link>
              ))}
            </div>
            <div className="ml-auto">
              <ApiStatus />
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
