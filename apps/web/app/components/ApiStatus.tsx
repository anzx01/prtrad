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
    checking: "bg-yellow-400 animate-pulse",
    connected: "bg-green-400",
    disconnected: "bg-red-500 animate-pulse",
  }

  const label: Record<Status, string> = {
    checking: "正在检查 API",
    connected: "API 已连接",
    disconnected: "API 未连接",
  }

  return (
    <div
      className={`flex items-center gap-2 border border-[#30363d] bg-[#0d1117] text-[#8b949e] ${
        compact ? "rounded-md px-2.5 py-1.5 text-[12px]" : "rounded-full px-3 py-1.5 text-xs"
      }`}
    >
      <span className={`inline-block h-2 w-2 rounded-full ${dot[status]}`} />
      <span className="truncate">{label[status]}</span>
      <button
        type="button"
        onClick={() => void check()}
        className="ml-auto inline-flex h-5 w-5 items-center justify-center text-[#8b949e]/60 transition-colors hover:text-[#e6edf3]"
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
