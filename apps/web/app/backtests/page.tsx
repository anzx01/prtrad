"use client"

import { FormEvent, useEffect, useState } from "react"

import { apiGet, apiPost } from "@/lib/api"

interface BacktestRun {
  id: string
  run_name: string
  recommendation: "go" | "watch" | "nogo"
  status: string
  window_start: string
  window_end: string
  strategy_version: string | null
  executed_by: string | null
  summary: {
    totals?: {
      candidate_count?: number
      admitted_count?: number
      rejected_count?: number
      resolved_ratio?: number
      avg_admit_net_ev?: number
    }
    cluster_breakdown?: Record<string, number>
    stress_tests?: Record<string, { positive_count: number; avg_net_ev: number }>
  }
  completed_at: string
}

function formatDate(value: string) {
  return new Date(value).toLocaleString()
}

export default function BacktestsPage() {
  const [runs, setRuns] = useState<BacktestRun[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState({
    run_name: "",
    window_days: "30",
    executed_by: "",
    strategy_version: "baseline-v1",
  })

  const fetchRuns = async () => {
    try {
      const data = await apiGet<{ runs: BacktestRun[] }>("/backtests")
      setRuns(data.runs)
      setError(null)
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Failed to load backtests")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void fetchRuns()
  }, [])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await apiPost("/backtests/run", {
        run_name: form.run_name,
        window_days: Number.parseInt(form.window_days, 10),
        executed_by: form.executed_by || null,
        strategy_version: form.strategy_version || null,
      })
      setForm((current) => ({ ...current, run_name: "", executed_by: "" }))
      await fetchRuns()
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to create backtest run")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-8 lg:px-10">
      <section className="mb-8 rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur">
        <p className="text-sm uppercase tracking-[0.2em] text-sky-200">M5 Backtest Lab</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Structured replay and validation</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
          Submit a lightweight research replay using the latest NetEV decisions, current clustering logic, and recent risk-state history.
        </p>
      </section>

      {error ? (
        <div className="mb-6 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      <section className="mb-8 rounded-3xl border border-white/10 bg-slate-950/50 p-6">
        <h2 className="text-xl font-medium text-white">Run a backtest</h2>
        <form className="mt-4 grid gap-4 md:grid-cols-2" onSubmit={handleSubmit}>
          <label className="space-y-2">
            <span className="text-sm text-slate-300">Run name</span>
            <input
              value={form.run_name}
              onChange={(event) => setForm((current) => ({ ...current, run_name: event.target.value }))}
              className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none"
              placeholder="backtest-20260410"
            />
          </label>
          <label className="space-y-2">
            <span className="text-sm text-slate-300">Window days</span>
            <input
              type="number"
              min={1}
              max={365}
              value={form.window_days}
              onChange={(event) => setForm((current) => ({ ...current, window_days: event.target.value }))}
              className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none"
            />
          </label>
          <label className="space-y-2">
            <span className="text-sm text-slate-300">Operator</span>
            <input
              value={form.executed_by}
              onChange={(event) => setForm((current) => ({ ...current, executed_by: event.target.value }))}
              className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none"
              placeholder="researcher_a"
            />
          </label>
          <label className="space-y-2">
            <span className="text-sm text-slate-300">Strategy version</span>
            <input
              value={form.strategy_version}
              onChange={(event) => setForm((current) => ({ ...current, strategy_version: event.target.value }))}
              className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none"
            />
          </label>
          <button
            type="submit"
            disabled={submitting}
            className="w-fit rounded-full border border-sky-400/40 bg-sky-500/10 px-5 py-2 text-sm text-sky-100 transition hover:bg-sky-500/20 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? "Running..." : "Run Backtest"}
          </button>
        </form>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-medium text-white">Recent runs</h2>
          <span className="text-xs uppercase tracking-[0.2em] text-slate-400">{runs.length} runs</span>
        </div>

        {loading ? <p className="text-slate-300">Loading backtests...</p> : null}

        {!loading && runs.length === 0 ? (
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6 text-sm text-slate-400">
            No backtest runs yet.
          </div>
        ) : null}

        {runs.map((run) => (
          <article key={run.id} className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h3 className="text-xl font-medium text-white">{run.run_name}</h3>
                <p className="mt-2 text-sm text-slate-400">
                  {formatDate(run.window_start)} to {formatDate(run.window_end)}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-slate-200">{run.status}</span>
                <span className={`rounded-full px-3 py-1 text-xs ${run.recommendation === "go" ? "bg-emerald-500/15 text-emerald-200" : run.recommendation === "watch" ? "bg-amber-500/15 text-amber-200" : "bg-rose-500/15 text-rose-200"}`}>
                  {run.recommendation}
                </span>
              </div>
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-5">
              <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Candidates</p>
                <p className="mt-2 text-2xl font-semibold text-white">{run.summary.totals?.candidate_count ?? 0}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Admitted</p>
                <p className="mt-2 text-2xl font-semibold text-white">{run.summary.totals?.admitted_count ?? 0}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Rejected</p>
                <p className="mt-2 text-2xl font-semibold text-white">{run.summary.totals?.rejected_count ?? 0}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Resolved Ratio</p>
                <p className="mt-2 text-2xl font-semibold text-white">
                  {(((run.summary.totals?.resolved_ratio ?? 0) as number) * 100).toFixed(1)}%
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Avg Admit NetEV</p>
                <p className="mt-2 text-2xl font-semibold text-white">{(run.summary.totals?.avg_admit_net_ev ?? 0).toFixed(4)}</p>
              </div>
            </div>

            <div className="mt-5 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
              <div>
                <h4 className="text-sm font-medium text-slate-200">Cluster breakdown</h4>
                <div className="mt-3 space-y-2">
                  {Object.entries(run.summary.cluster_breakdown ?? {}).length === 0 ? (
                    <p className="text-sm text-slate-400">No cluster data.</p>
                  ) : (
                    Object.entries(run.summary.cluster_breakdown ?? {}).map(([cluster, count]) => (
                      <div key={cluster} className="flex items-center justify-between rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm">
                        <span className="text-slate-200">{cluster}</span>
                        <span className="text-white">{count}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>
              <div>
                <h4 className="text-sm font-medium text-slate-200">Stress tests</h4>
                <div className="mt-3 space-y-2">
                  {Object.entries(run.summary.stress_tests ?? {}).map(([scenario, result]) => (
                    <div key={scenario} className="rounded-2xl border border-white/10 bg-slate-950/50 p-4 text-sm">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-slate-200">{scenario}</span>
                        <span className="text-white">{result.positive_count} positive</span>
                      </div>
                      <p className="mt-2 text-slate-400">Average net EV {result.avg_net_ev.toFixed(4)}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </article>
        ))}
      </section>
    </main>
  )
}
