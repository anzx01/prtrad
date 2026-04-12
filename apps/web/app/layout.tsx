import type { Metadata } from "next"
import "./globals.css"
import { ConsoleNav } from "./components/console-nav"

export const metadata: Metadata = {
  title: "PRT 风控控制台",
  description: "用于研究、准入、风控、回测、影子运行与上线评审的控制台。",
  other: {
    google: "notranslate",
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
    apple: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="zh-CN" translate="no" className="notranslate" suppressHydrationWarning>
      <body
        className="notranslate min-h-screen bg-[#0d1117] text-[#e6edf3]"
        translate="no"
        suppressHydrationWarning
      >
        <ConsoleNav>{children}</ConsoleNav>
      </body>
    </html>
  )
}
