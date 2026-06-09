"use client"

import ApiStatus from "./ApiStatus"

const NAV_ITEMS = [
  { href: "#actions", label: "自动动作" },
  { href: "#markets", label: "市场总表" },
  { href: "#launch", label: "交易闸门" },
]

export function ConsoleNav({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen text-[color:var(--oa-text)]">
      <header className="sticky top-0 z-40 border-b border-[color:var(--oa-border)] bg-[rgba(252,247,239,0.84)] backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1280px] items-center justify-between gap-4 px-4 py-3 md:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-[color:rgba(181,72,47,0.18)] bg-[linear-gradient(135deg,rgba(181,72,47,0.14),rgba(255,255,255,0.96))] text-sm font-semibold uppercase tracking-[0.2em] text-[color:var(--oa-accent-strong)] shadow-[0_12px_24px_rgba(123,56,33,0.1)]">
              PRT
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold tracking-[0.08em] text-[color:var(--oa-text)]">PRT 自动驾驶舱</p>
              <p className="mt-1 text-xs text-[color:var(--oa-muted)]">只保留一个入口，系统先给结论，你再决定要不要点按钮</p>
            </div>
          </div>

          <nav className="hidden items-center gap-2 lg:flex">
            {NAV_ITEMS.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="rounded-full border border-transparent px-4 py-2 text-sm text-[color:var(--oa-muted)] transition hover:border-[color:var(--oa-border)] hover:bg-[rgba(255,255,255,0.7)] hover:text-[color:var(--oa-text)]"
              >
                {item.label}
              </a>
            ))}
          </nav>

          <ApiStatus compact />
        </div>
      </header>

      <div className="min-w-0">{children}</div>
    </div>
  )
}
