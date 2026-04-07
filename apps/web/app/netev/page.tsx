"use client"

import { useEffect, useState } from "react"
import { apiGet, apiPost } from "@/lib/api"

type NetEVCandidate = {
  id: string
  market_ref_id: string
  market_id: string | null
  question: string | null
  category_code: string | null
  calibration_unit_id: string | null
  calibration_sample_count: number | null
  price_bucket: string | null
  time_bucket: string | null
  liquidity_tier: string | null
  window_type: string | null
  gross_edge: number
  fee_cost: number
  slippage_cost: number
  dispute_discount: number
  net_ev: number
  admission_decision: string
  rejection_reason_code: string | null
  rejection_reason_name: string | null
  rejection_reason_description: string | null
  scoring_recommendation: string | null
  dq_status: string | null
  rule_version: string
  evaluated_at: string
}

type NetEVBatchResponse = {
  total: number
  admitted: number
  rejected: number
  candidates: NetEVCandidate[]
}

export default function NetEVPage() {
  const [candidates, setCandidates] = useState<NetEVCandidate[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [filter, setFilter] = useState("")

  const loadCandidates = async (decision = filter) => {
    setLoading(true)
    setError(null)

    const endpoint = decision ? `/netev/candidates?decision=${decision}` : "/netev/candidates"
    try {
      const data = await apiGet<NetEVCandidate[]>(endpoint)
      setCandidates(data || [])
    } catch (err) {
      console.error("Failed to fetch NetEV candidates:", err)
      setError(err instanceof Error ? err.message : "Failed to fetch NetEV candidates")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadCandidates(filter)
  }, [filter])

  const handleBatchEvaluate = async () => {
    setRunning(true)
    setError(null)
    setNotice(null)

    try {
      const result = await apiPost<NetEVBatchResponse>("/netev/evaluate-batch?limit=20&window_type=long")
      setNotice(`本轮评估 ${result.total} 个候选，其中 ${result.admitted} 个通过，${result.rejected} 个拒绝。`)
      await loadCandidates(filter)
    } catch (err) {
      console.error("Failed to batch evaluate NetEV candidates:", err)
      setError(err instanceof Error ? err.message : "Failed to batch evaluate NetEV candidates")
    } finally {
      setRunning(false)
    }
  }

  const admitted = candidates.filter((candidate) => candidate.admission_decision === "admit").length
  const rejected = candidates.length - admitted

  return (
    <div className="mx-auto max-w-7xl px-6 py-8 lg:px-10">
      <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-cyan-300/80">Milestone 3</p>
          <h1 className="mt-2 text-3xl font-semibold text-white">NetEV 准入评估</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-300">
            将校准边际、交易费用、滑点和争议折扣收敛成统一决策，并输出通过/拒绝、原因码和规则版本。
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-500"
            disabled={running}
            onClick={handleBatchEvaluate}
          >
            {running ? "评估中..." : "评估最新 20 个候选"}
          </button>
          <button
            className={`rounded-lg px-4 py-2 text-sm transition ${
              !filter ? "bg-white text-slate-950" : "bg-white/10 text-slate-200 hover:bg-white/15"
            }`}
            onClick={() => setFilter("")}
          >
            全部
          </button>
          <button
            className={`rounded-lg px-4 py-2 text-sm transition ${
              filter === "admit" ? "bg-emerald-300 text-slate-950" : "bg-white/10 text-slate-200 hover:bg-white/15"
            }`}
            onClick={() => setFilter("admit")}
          >
            Admit
          </button>
          <button
            className={`rounded-lg px-4 py-2 text-sm transition ${
              filter === "reject" ? "bg-rose-300 text-slate-950" : "bg-white/10 text-slate-200 hover:bg-white/15"
            }`}
            onClick={() => setFilter("reject")}
          >
            Reject
          </button>
        </div>
      </div>

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-5 backdrop-blur">
          <div className="text-xs uppercase tracking-[0.24em] text-slate-400">候选总数</div>
          <div className="mt-3 text-3xl font-semibold text-white">{candidates.length}</div>
        </div>
        <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-5">
          <div className="text-xs uppercase tracking-[0.24em] text-emerald-200">通过</div>
          <div className="mt-3 text-3xl font-semibold text-emerald-50">{admitted}</div>
        </div>
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 p-5">
          <div className="text-xs uppercase tracking-[0.24em] text-rose-100">拒绝</div>
          <div className="mt-3 text-3xl font-semibold text-rose-50">{rejected}</div>
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

      {loading ? (
        <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-8 text-slate-300">加载 NetEV 评估中...</div>
      ) : candidates.length > 0 ? (
        <div className="grid grid-cols-1 gap-4">
          {candidates.map((candidate) => (
            <div
              key={candidate.id}
              className={`rounded-2xl border p-5 shadow-xl shadow-slate-950/20 ${
                candidate.admission_decision === "admit"
                  ? "border-emerald-500/30 bg-emerald-500/10"
                  : "border-rose-500/30 bg-rose-500/10"
              }`}
            >
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="max-w-3xl">
                  <div className="text-xs uppercase tracking-[0.24em] text-slate-300/80">
                    {candidate.category_code || "Uncategorized"} · {candidate.rule_version}
                  </div>
                  <h2 className="mt-2 text-lg font-semibold text-white">
                    {candidate.question || candidate.market_id || candidate.market_ref_id}
                  </h2>
                  <div className="mt-2 text-xs text-slate-300/80">
                    Market ID: <span className="font-mono">{candidate.market_id || candidate.market_ref_id}</span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-200">
                    {candidate.price_bucket && <span className="rounded-full bg-white/10 px-2.5 py-1">{candidate.price_bucket}</span>}
                    {candidate.time_bucket && <span className="rounded-full bg-white/10 px-2.5 py-1">{candidate.time_bucket}</span>}
                    {candidate.liquidity_tier && <span className="rounded-full bg-white/10 px-2.5 py-1">{candidate.liquidity_tier}</span>}
                    {candidate.calibration_sample_count !== null && (
                      <span className="rounded-full bg-white/10 px-2.5 py-1">样本 {candidate.calibration_sample_count}</span>
                    )}
                    {candidate.dq_status && <span className="rounded-full bg-white/10 px-2.5 py-1">DQ {candidate.dq_status}</span>}
                    {candidate.scoring_recommendation && (
                      <span className="rounded-full bg-white/10 px-2.5 py-1">Scoring {candidate.scoring_recommendation}</span>
                    )}
                  </div>
                </div>

                <div className="text-right">
                  <span
                    className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] ${
                      candidate.admission_decision === "admit"
                        ? "bg-emerald-200 text-emerald-950"
                        : "bg-rose-200 text-rose-950"
                    }`}
                  >
                    {candidate.admission_decision}
                  </span>
                  <div className="mt-2 text-xs text-slate-200/80">
                    {new Date(candidate.evaluated_at).toLocaleString()}
                  </div>
                </div>
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-4">
                <MetricCard label="Gross Edge" value={`${(candidate.gross_edge * 100).toFixed(2)}%`} tone="emerald" />
                <MetricCard label="Fee" value={`-${(candidate.fee_cost * 100).toFixed(2)}%`} tone="slate" />
                <MetricCard label="Slippage + Dispute" value={`-${((candidate.slippage_cost + candidate.dispute_discount) * 100).toFixed(2)}%`} tone="slate" />
                <MetricCard
                  label="Net EV"
                  value={`${(candidate.net_ev * 100).toFixed(2)}%`}
                  tone={candidate.net_ev >= 0 ? "emerald" : "rose"}
                />
              </div>

              {candidate.rejection_reason_code && (
                <div className="mt-4 rounded-xl bg-black/20 px-4 py-3 text-sm text-slate-100">
                  <div className="font-medium">
                    {candidate.rejection_reason_name || candidate.rejection_reason_code}
                  </div>
                  <div className="mt-1 text-xs text-slate-300">{candidate.rejection_reason_code}</div>
                  {candidate.rejection_reason_description && (
                    <div className="mt-2 text-xs text-slate-300/90">{candidate.rejection_reason_description}</div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-12 text-center text-slate-300">
          还没有评估记录，先执行一轮批量评估。
        </div>
      )}
    </div>
  )
}

function MetricCard({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone: "emerald" | "rose" | "slate"
}) {
  const toneClassName = {
    emerald: "border-emerald-500/20 bg-emerald-500/10 text-emerald-100",
    rose: "border-rose-500/20 bg-rose-500/10 text-rose-100",
    slate: "border-white/10 bg-white/5 text-slate-100",
  }[tone]

  return (
    <div className={`rounded-xl border p-4 ${toneClassName}`}>
      <div className="text-xs uppercase tracking-[0.24em] text-current/70">{label}</div>
      <div className="mt-3 text-xl font-semibold">{value}</div>
    </div>
  )
}
