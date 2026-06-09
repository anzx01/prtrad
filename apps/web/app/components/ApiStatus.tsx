"use client"

import { useEffect, useState } from "react"

type Status = "checking" | "connected" | "disconnected"

function RefreshIcon() {
  return (
    <svg
      aria-hidden="true"
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21 12a9 9 0 1 1-2.64-6.36" />
      <path d="M21 3v6h-6" />
    </svg>
  )
}

export default function ApiStatus({ compact = false }: { compact?: boolean }) {
  const [status, setStatus] = useState<Status>("checking")

  const check = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/health`, {
        signal: AbortSignal.timeout(3000),
      })
      setStatus(res.ok ? "connected" : "disconnected")
    } catch {
      setStatus("disconnected")
    }
  }

  useEffect(() => {
    void check()
    const timer = setInterval(() => {
      void check()
    }, 300000)

    return () => clearInterval(timer)
  }, [])

  const dot: Record<Status, string> = {
    checking: "bg-[color:var(--oa-gold)] animate-pulse",
    connected: "bg-[color:var(--oa-green)]",
    disconnected: "bg-[color:var(--oa-red)] animate-pulse",
  }

  const label: Record<Status, string> = {
    checking: "正在检查 API",
    connected: "API 已连接",
    disconnected: "API 未连接",
  }

  return (
    <div
      className={`flex items-center gap-2 border border-[color:var(--oa-border)] bg-[rgba(255,251,246,0.78)] text-[color:var(--oa-muted)] shadow-[0_12px_28px_rgba(52,34,20,0.06)] ${
        compact ? "rounded-full px-3 py-2 text-[12px]" : "rounded-full px-4 py-2 text-xs"
      }`}
    >
      <span className={`inline-block h-2.5 w-2.5 rounded-full ${dot[status]}`} />
      <span className="truncate">{label[status]}</span>
      <button
        type="button"
        onClick={() => void check()}
        className="ml-auto inline-flex h-6 w-6 items-center justify-center rounded-full text-[color:rgba(29,24,20,0.5)] transition-colors hover:bg-[rgba(181,72,47,0.08)] hover:text-[color:var(--oa-text)]"
        title="刷新 API 状态"
        aria-label="刷新 API 状态"
        suppressHydrationWarning
        translate="no"
      >
        <RefreshIcon />
      </button>
    </div>
  )
}
