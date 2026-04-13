"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useState, type ReactNode } from "react"

import ApiStatus from "./ApiStatus"

interface NavItem {
  href: string
  label: string
  icon: ReactNode
}

interface NavSection {
  title: string
  items: NavItem[]
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: "主链路",
    items: [
      { href: "/", label: "总览", icon: <OverviewIcon /> },
      { href: "/markets", label: "市场总表", icon: <MarketIcon /> },
      { href: "/dq", label: "数据质量", icon: <PulseIcon /> },
      { href: "/tagging", label: "标签分类", icon: <TagIcon /> },
      { href: "/review", label: "审核队列", icon: <InboxIcon /> },
    ],
  },
  {
    title: "准入与研究",
    items: [
      { href: "/lists", label: "名单管理", icon: <ListIcon /> },
      { href: "/tag-quality", label: "标签质量", icon: <CheckIcon /> },
      { href: "/calibration", label: "校准单元", icon: <ScaleIcon /> },
      { href: "/netev", label: "NetEV 准入", icon: <SparkIcon /> },
      { href: "/backtests", label: "回测实验室", icon: <ChartIcon /> },
      { href: "/reports", label: "日报周报", icon: <ReportIcon /> },
    ],
  },
  {
    title: "风控与上线",
    items: [
      { href: "/risk", label: "组合风控", icon: <ShieldIcon /> },
      { href: "/state-alerts", label: "状态告警", icon: <AlertIcon /> },
      { href: "/launch-review", label: "上线评审", icon: <RocketIcon /> },
      { href: "/monitoring", label: "系统监控", icon: <SettingIcon /> },
    ],
  },
]

function isActive(pathname: string, href: string) {
  if (href === "/") {
    return pathname === "/"
  }
  return pathname === href || pathname.startsWith(`${href}/`)
}

function findActiveLabel(pathname: string) {
  for (const section of NAV_SECTIONS) {
    const item = section.items.find((entry) => isActive(pathname, entry.href))
    if (item) {
      return item.label
    }
  }
  return "主链路控制台"
}

export function ConsoleNav({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)
  const activeLabel = findActiveLabel(pathname)

  return (
    <div className="flex min-h-screen bg-[#0d1117] text-[#e6edf3]">
      <div
        className={`fixed inset-0 z-40 bg-black/55 transition-opacity md:hidden ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={() => setOpen(false)}
      />

      <aside
        className={`fixed left-0 top-0 z-50 flex h-full w-[220px] flex-col border-r border-[#30363d] bg-[#161b22] transition-transform duration-200 md:sticky md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center gap-3 px-5 py-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-[#30363d] bg-[#21262d] text-[#e6edf3]">
            <OverviewIcon />
          </div>
          <div className="notranslate" translate="no">
            <p className="text-sm font-semibold text-[#e6edf3]" suppressHydrationWarning>
              PRT Console
            </p>
            <p className="text-[11px] text-[#8b949e]" suppressHydrationWarning>
              Polymarket Tail Risk
            </p>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 pb-4">
          {NAV_SECTIONS.map((section) => (
            <div key={section.title} className="mt-4 first:mt-0">
              <p className="px-3 py-2 text-[11px] uppercase tracking-[0.18em] text-[#8b949e]/65">
                {section.title}
              </p>
              <div className="space-y-0.5">
                {section.items.map((item) => {
                  const active = isActive(pathname, item.href)

                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setOpen(false)}
                      className={`relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                        active
                          ? "bg-[#21262d] text-[#e6edf3]"
                          : "text-[#8b949e] hover:bg-[#21262d]/70 hover:text-[#e6edf3]"
                      }`}
                    >
                      <span
                        className={`absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-r-full bg-[#58a6ff] transition ${
                          active ? "opacity-100" : "opacity-0"
                        }`}
                      />
                      <span className="flex h-5 w-5 items-center justify-center">{item.icon}</span>
                      <span>{item.label}</span>
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="border-t border-[#30363d] px-4 py-3">
          <ApiStatus compact />
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col bg-[#0d1117]">
        <div className="flex items-center gap-3 border-b border-[#30363d] bg-[#161b22] px-4 py-3 md:hidden">
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="rounded-md border border-[#30363d] bg-[#21262d] p-2 text-[#8b949e] transition hover:text-[#e6edf3]"
            aria-label="打开导航"
          >
            <MenuIcon />
          </button>
          <div className="notranslate" translate="no">
            <p className="text-[11px] uppercase tracking-[0.16em] text-[#8b949e]" suppressHydrationWarning>
              PRT Console
            </p>
            <p className="text-sm font-semibold text-[#e6edf3]" suppressHydrationWarning>
              {activeLabel}
            </p>
          </div>
        </div>

        <div className="page-fade-in min-w-0 flex-1 overflow-y-auto">{children}</div>
      </div>
    </div>
  )
}

function IconFrame({ children }: { children: ReactNode }) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </svg>
  )
}

function MenuIcon() {
  return (
    <IconFrame>
      <path d="M3 6h18" />
      <path d="M3 12h18" />
      <path d="M3 18h18" />
    </IconFrame>
  )
}

function OverviewIcon() {
  return (
    <IconFrame>
      <rect x="3" y="4" width="18" height="14" rx="2" />
      <path d="M8 20h8" />
      <path d="M12 18v2" />
    </IconFrame>
  )
}

function MarketIcon() {
  return (
    <IconFrame>
      <path d="M4 19h16" />
      <path d="M6 15l4-4 3 3 5-6" />
      <path d="M18 8h-4" />
    </IconFrame>
  )
}

function PulseIcon() {
  return (
    <IconFrame>
      <path d="M3 12h4l2-5 4 10 2-5h6" />
    </IconFrame>
  )
}

function TagIcon() {
  return (
    <IconFrame>
      <path d="M20 10 12 2H4v8l8 8 8-8Z" />
      <circle cx="7.5" cy="7.5" r="1" fill="currentColor" stroke="none" />
    </IconFrame>
  )
}

function InboxIcon() {
  return (
    <IconFrame>
      <path d="M3 7h18v10H3z" />
      <path d="M7 12h10" />
      <path d="M9 16h6" />
    </IconFrame>
  )
}

function ListIcon() {
  return (
    <IconFrame>
      <path d="M8 6h12" />
      <path d="M8 12h12" />
      <path d="M8 18h12" />
      <circle cx="4" cy="6" r="1" fill="currentColor" stroke="none" />
      <circle cx="4" cy="12" r="1" fill="currentColor" stroke="none" />
      <circle cx="4" cy="18" r="1" fill="currentColor" stroke="none" />
    </IconFrame>
  )
}

function CheckIcon() {
  return (
    <IconFrame>
      <path d="m5 12 4 4L19 6" />
    </IconFrame>
  )
}

function ScaleIcon() {
  return (
    <IconFrame>
      <path d="M12 4v16" />
      <path d="M7 8h10" />
      <path d="m7 8-3 5h6l-3-5Z" />
      <path d="m17 8-3 5h6l-3-5Z" />
    </IconFrame>
  )
}

function SparkIcon() {
  return (
    <IconFrame>
      <path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8Z" />
    </IconFrame>
  )
}

function ChartIcon() {
  return (
    <IconFrame>
      <path d="M4 19h16" />
      <path d="M7 16v-5" />
      <path d="M12 16V8" />
      <path d="M17 16v-9" />
    </IconFrame>
  )
}

function ReportIcon() {
  return (
    <IconFrame>
      <path d="M6 3h9l4 4v14H6z" />
      <path d="M15 3v4h4" />
      <path d="M9 12h6" />
      <path d="M9 16h6" />
    </IconFrame>
  )
}

function ShieldIcon() {
  return (
    <IconFrame>
      <path d="M12 3 5 6v6c0 5 3 8 7 9 4-1 7-4 7-9V6l-7-3Z" />
    </IconFrame>
  )
}

function AlertIcon() {
  return (
    <IconFrame>
      <path d="M12 4 4 18h16L12 4Z" />
      <path d="M12 9v4" />
      <circle cx="12" cy="16" r="1" fill="currentColor" stroke="none" />
    </IconFrame>
  )
}

function RocketIcon() {
  return (
    <IconFrame>
      <path d="M6 14c0-4 3-7 7-7h2l3 3v2c0 4-3 7-7 7h-1l-4-4Z" />
      <path d="m7 17-2 2" />
      <circle cx="14" cy="10" r="1.4" fill="currentColor" stroke="none" />
    </IconFrame>
  )
}

function SettingIcon() {
  return (
    <IconFrame>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 0 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 0 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 0 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3 1.7 1.7 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 0 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8 1.7 1.7 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z" />
    </IconFrame>
  )
}
