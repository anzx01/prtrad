import type { Metadata } from "next"

import "./globals.css"
import { ConsoleNav } from "./components/console-nav"

export const metadata: Metadata = {
  title: "PRT 单页控制台",
  description: "面向小白的单页自动化 Polymarket 风控控制台。",
  other: {
    google: "notranslate",
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
    apple: "/favicon.svg",
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="zh-CN" translate="no" className="notranslate" suppressHydrationWarning>
      <body
        className="notranslate min-h-screen"
        translate="no"
        suppressHydrationWarning
      >
        <ConsoleNav>{children}</ConsoleNav>
      </body>
    </html>
  )
}
