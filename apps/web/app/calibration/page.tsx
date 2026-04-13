"use client"

import { useEffect, useState } from "react"

import { apiGet, apiPost } from "@/lib/api"
import { PageIntro } from "../components/page-intro"

type CalibrationUnit = {
  id: string
  price_bucket: string
  category_code: string
  time_bucket: string
  liquidity_tier: string
  window_type: string
  sample_count: number
  edge_estimate: number
  interval_low: number
  interval_high: number
  is_active: boolean
  disabled_reason: string | null
  computed_at: string
}

type RecomputeResponse = {
  window_type: string
  computed_at: string
  total_units: number
  active_units: number
  inactive_units: number
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message
  }
  if (error && typeof error === "object" && "message" in error) {
    const message = (error as { message?: unknown }).message
    if (typeof message === "string") {
      return message
    }
  }
  return "发生了未知错误，请稍后重试"
}

export default function CalibrationPage() {
  const [units, setUnits] = useState<CalibrationUnit[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const loadUnits = async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await apiGet<CalibrationUnit[]>("/calibration/units?include_inactive=true")
      setUnits(data ?? [])
    } catch (error) {
      setError(getErrorMessage(error))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadUnits()
  }, [])

  const handleRecompute = async () => {
    setRefreshing(true)
    setError(null)
    setNotice(null)

    try {
      const result = await apiPost<RecomputeResponse>("/calibration/recompute-all?window_type=long")
      setNotice(
        `已重算 ${result.total_units} 个长窗口校准单元，` +
          `其中 ${result.active_units} 个可用，${result.inactive_units} 个不可用。`
      )
      await loadUnits()
    } catch (error) {
      setError(getErrorMessage(error))
    } finally {
      setRefreshing(false)
    }
  }

  const activeUnits = units.filter((unit) => unit.is_active)
  const inactiveUnits = units.length - activeUnits.length

  if (loading) {
    return <div className="p-8 text-slate-300">正在加载校准单元...</div>
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-5 md:px-6">
      <PageIntro
        eyebrow="Calibration"
        title="校准单元"
        description="这页主要判断历史已结算样本是否足够支撑概率校准。若这里长期全 0，先检查 resolved 市场是否真的同步完整，以及重算是否真正执行。"
        stats={[
          { label: "全部单元", value: String(units.length) },
          { label: "活跃单元", value: String(activeUnits.length) },
        ]}
        guides={[
          {
            title: "先看什么",
            description: "先看单元总数和样本数，再看哪些单元被禁用以及禁用原因。",
          },
          {
            title: "什么时候算异常",
            description: "如果库里已经有大量 resolved 市场，但这里仍然空，才值得继续排查同步与回填链路。",
          },
          {
            title: "下一步怎么做",
            description: "先重算长窗口；若还为空，再回查 recent resolved markets 和 final_resolution 是否完整。",
          },
        ]}
      />

      <div className="mb-6 flex justify-end">
        <button
          className="rounded-2xl bg-cyan-500 px-4 py-3 text-sm font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-500"
          disabled={refreshing}
          onClick={handleRecompute}
        >
          {refreshing ? "重算中..." : "重算长窗口校准"}
        </button>
      </div>

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <MetricCard label="全部单元" value={units.length.toString()} tone="slate" />
        <MetricCard label="活跃单元" value={activeUnits.length.toString()} tone="emerald" />
        <MetricCard label="非活跃单元" value={inactiveUnits.toString()} tone="amber" />
      </div>

      {notice && (
        <div className="mb-6 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
          {notice}
        </div>
      )}

      {error && (
        <div className="mb-6 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          {error}
        </div>
      )}

      <div className="overflow-hidden rounded-2xl border border-white/10 bg-slate-950/60 shadow-2xl shadow-slate-950/30">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-white/10 text-sm">
            <thead className="bg-white/5 text-left text-xs uppercase tracking-[0.24em] text-slate-400">
              <tr>
                <th className="px-5 py-4">类别 / 价格桶</th>
                <th className="px-5 py-4">时间 / 流动性</th>
                <th className="px-5 py-4">样本数</th>
                <th className="px-5 py-4">边际估计</th>
                <th className="px-5 py-4">区间</th>
                <th className="px-5 py-4">状态</th>
                <th className="px-5 py-4">计算时间</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-200">
              {units.length > 0 ? (
                units.map((unit) => (
                  <tr key={unit.id} className="transition hover:bg-white/5">
                    <td className="px-5 py-4">
                      <div className="font-medium text-white">{unit.category_code}</div>
                      <div className="mt-1 text-xs text-slate-400">{unit.price_bucket}</div>
                    </td>
                    <td className="px-5 py-4">
                      <div>{unit.time_bucket}</div>
                      <div className="mt-1 text-xs text-slate-400">
                        {unit.liquidity_tier} / {unit.window_type}
                      </div>
                    </td>
                    <td className="px-5 py-4 text-slate-300">{unit.sample_count}</td>
                    <td
                      className={`px-5 py-4 font-semibold ${
                        unit.edge_estimate >= 0 ? "text-emerald-300" : "text-rose-300"
                      }`}
                    >
                      {(unit.edge_estimate * 100).toFixed(2)}%
                    </td>
                    <td className="px-5 py-4 text-slate-300">
                      [{(unit.interval_low * 100).toFixed(2)}%, {(unit.interval_high * 100).toFixed(2)}%]
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${
                          unit.is_active
                            ? "bg-emerald-500/15 text-emerald-200"
                            : "bg-amber-500/15 text-amber-100"
                        }`}
                      >
                        {unit.is_active ? "可用" : unit.disabled_reason ?? "不可用"}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-xs text-slate-400">
                      {new Date(unit.computed_at).toLocaleString()}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-slate-400">
                    当前还没有校准单元。先执行一次重算；若仍为空，再检查 resolved 市场是否真的已同步入库。
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  )
}

function MetricCard({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone: "slate" | "emerald" | "amber"
}) {
  const toneClassName = {
    slate: "border-white/10 bg-slate-900/60 text-white",
    emerald: "border-emerald-500/20 bg-emerald-500/10 text-emerald-50",
    amber: "border-amber-500/20 bg-amber-500/10 text-amber-50",
  }[tone]

  return (
    <div className={`rounded-2xl border p-5 ${toneClassName}`}>
      <div className="text-xs uppercase tracking-[0.24em] text-current/70">{label}</div>
      <div className="mt-3 text-3xl font-semibold">{value}</div>
    </div>
  )
}
