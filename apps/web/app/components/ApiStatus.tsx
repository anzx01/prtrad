"use client"

import { useEffect, useState } from "react"

type Status = "checking" | "connected" | "disconnected"

export default function ApiStatus() {
  const [status, setStatus] = useState<Status>("checking")

  const check = async () => {
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/health`,
        { signal: AbortSignal.timeout(3000) }
      )
      setStatus(res.ok ? "connected" : "disconnected")
    } catch {
      setStatus("disconnected")
    }
  }

  useEffect(() => {
    check()
    const timer = setInterval(check, 300000)
    return () => clearInterval(timer)
  }, [])

  const dot: Record<Status, string> = {
    checking: "bg-yellow-400 animate-pulse",
    connected: "bg-green-400",
    disconnected: "bg-red-500 animate-pulse",
  }

  const label: Record<Status, string> = {
    checking: "Connecting...",
    connected: "API Connected",
    disconnected: "API Disconnected",
  }

  return (
    <div className="flex items-center gap-1.5 text-xs text-slate-400">
      <span className={`inline-block h-2 w-2 rounded-full ${dot[status]}`} />
      {label[status]}
      <button
        onClick={check}
        className="ml-1 text-slate-500 hover:text-slate-300 transition-colors"
        title="刷新连接状态"
      >
        ↻
      </button>
    </div>
  )
}
