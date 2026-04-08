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
  return "Unexpected error"
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
        `Recomputed ${result.total_units} long-window units. ` +
          `${result.active_units} are active and ${result.inactive_units} are inactive.`
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
    return <div className="p-8 text-slate-300">Loading calibration units...</div>
  }

  return (
    <main className="mx-auto max-w-7xl px-6 py-8 lg:px-10">
      <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-cyan-300/80">Milestone 3</p>
          <h1 className="mt-2 text-3xl font-semibold text-white">Calibration Units</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-300">
            Historical resolved markets are grouped into reusable calibration units by
            category, price bucket, time bucket, and liquidity tier.
          </p>
        </div>

        <button
          className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-500"
          disabled={refreshing}
          onClick={handleRecompute}
        >
          {refreshing ? "Recomputing..." : "Recompute Long Window"}
        </button>
      </div>

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <MetricCard label="All Units" value={units.length.toString()} tone="slate" />
        <MetricCard label="Active Units" value={activeUnits.length.toString()} tone="emerald" />
        <MetricCard label="Inactive Units" value={inactiveUnits.toString()} tone="amber" />
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
                <th className="px-5 py-4">Category / Price</th>
                <th className="px-5 py-4">Time / Liquidity</th>
                <th className="px-5 py-4">Samples</th>
                <th className="px-5 py-4">Edge</th>
                <th className="px-5 py-4">Interval</th>
                <th className="px-5 py-4">Status</th>
                <th className="px-5 py-4">Computed</th>
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
                        {unit.is_active ? "Active" : unit.disabled_reason ?? "Inactive"}
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
                    No calibration units yet. Run a recompute to create the first batch.
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
