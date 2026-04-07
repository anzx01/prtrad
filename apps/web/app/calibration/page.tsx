"use client"

import { useEffect, useState } from "react"
import { apiGet, apiPost } from "@/lib/api"

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
      setUnits(data || [])
    } catch (err) {
      console.error("Failed to fetch calibration units:", err)
      setError(err instanceof Error ? err.message : "Failed to fetch calibration units")
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
        `已完成 ${result.window_type} 窗口重算，生成 ${result.total_units} 个单元，其中 ${result.active_units} 个可用。`,
      )
      await loadUnits()
    } catch (err) {
      console.error("Failed to recompute calibration units:", err)
      setError(err instanceof Error ? err.message : "Failed to recompute calibration units")
    } finally {
      setRefreshing(false)
    }
  }

  const activeUnits = units.filter((unit) => unit.is_active)
  const inactiveUnits = units.length - activeUnits.length

  if (loading) {
    return <div className="p-8 text-slate-300">加载校准单元中...</div>
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-8 lg:px-10">
      <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-cyan-300/80">Milestone 3</p>
          <h1 className="mt-2 text-3xl font-semibold text-white">概率校准单元</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-300">
            基于已结算市场和历史快照聚合价格桶、期限桶和流动性桶，供 NetEV 准入直接复用。
          </p>
        </div>

        <button
          className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-500"
          disabled={refreshing}
          onClick={handleRecompute}
        >
          {refreshing ? "重算中..." : "重算 long 窗口"}
        </button>
      </div>

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-5 backdrop-blur">
          <div className="text-xs uppercase tracking-[0.24em] text-slate-400">全部单元</div>
          <div className="mt-3 text-3xl font-semibold text-white">{units.length}</div>
        </div>
        <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-5">
          <div className="text-xs uppercase tracking-[0.24em] text-emerald-200">可用单元</div>
          <div className="mt-3 text-3xl font-semibold text-emerald-50">{activeUnits.length}</div>
        </div>
        <div className="rounded-2xl border border-amber-500/20 bg-amber-500/10 p-5">
          <div className="text-xs uppercase tracking-[0.24em] text-amber-100">停用单元</div>
          <div className="mt-3 text-3xl font-semibold text-amber-50">{inactiveUnits}</div>
        </div>
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
                <th className="px-5 py-4">分类 / 价格桶</th>
                <th className="px-5 py-4">期限 / 流动性</th>
                <th className="px-5 py-4">样本数</th>
                <th className="px-5 py-4">校准边际</th>
                <th className="px-5 py-4">95% 区间</th>
                <th className="px-5 py-4">状态</th>
                <th className="px-5 py-4">更新时间</th>
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
                    <td className={`px-5 py-4 font-semibold ${unit.edge_estimate >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
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
                        {unit.is_active ? "可用" : unit.disabled_reason || "停用"}
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
                    还没有校准单元，先执行一次全量重算。
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
