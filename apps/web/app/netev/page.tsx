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

export default function NetEVPage() {
  const [candidates, setCandidates] = useState<NetEVCandidate[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [filter, setFilter] = useState<"" | "admit" | "reject">("")

  const loadCandidates = async (decision: "" | "admit" | "reject" = filter) => {
    setLoading(true)
    setError(null)

    const endpoint = decision ? `/netev/candidates?decision=${decision}` : "/netev/candidates"
    try {
      const data = await apiGet<NetEVCandidate[]>(endpoint)
      setCandidates(data ?? [])
    } catch (error) {
      setError(getErrorMessage(error))
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
      setNotice(
        `Evaluated ${result.total} candidates. ` +
          `${result.admitted} admitted and ${result.rejected} rejected.`
      )
      await loadCandidates(filter)
    } catch (error) {
      setError(getErrorMessage(error))
    } finally {
      setRunning(false)
    }
  }

  const admitted = candidates.filter((candidate) => candidate.admission_decision === "admit").length
  const rejected = candidates.length - admitted

  return (
    <main className="mx-auto max-w-7xl px-6 py-8 lg:px-10">
      <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-cyan-300/80">Milestone 3</p>
          <h1 className="mt-2 text-3xl font-semibold text-white">NetEV Admission</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-300">
            Review cost-adjusted admission decisions built from calibration edge,
            fees, slippage, dispute discount, scoring, and DQ status.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-500"
            disabled={running}
            onClick={handleBatchEvaluate}
          >
            {running ? "Evaluating..." : "Evaluate Latest 20"}
          </button>
          <FilterButton active={!filter} label="All" onClick={() => setFilter("")} />
          <FilterButton active={filter === "admit"} label="Admit" onClick={() => setFilter("admit")} />
          <FilterButton active={filter === "reject"} label="Reject" onClick={() => setFilter("reject")} />
        </div>
      </div>

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <MetricCard label="Candidates" value={candidates.length.toString()} tone="slate" />
        <MetricCard label="Admitted" value={admitted.toString()} tone="emerald" />
        <MetricCard label="Rejected" value={rejected.toString()} tone="rose" />
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
        <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-8 text-slate-300">
          Loading NetEV candidates...
        </div>
      ) : candidates.length > 0 ? (
        <div className="grid grid-cols-1 gap-4">
          {candidates.map((candidate) => (
            <article
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
                    {candidate.category_code || "Uncategorized"} / {candidate.rule_version}
                  </div>
                  <h2 className="mt-2 text-lg font-semibold text-white">
                    {candidate.question || candidate.market_id || candidate.market_ref_id}
                  </h2>
                  <div className="mt-2 text-xs text-slate-300/80">
                    Market ID: <span className="font-mono">{candidate.market_id || candidate.market_ref_id}</span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-200">
                    {candidate.price_bucket && <Chip label={candidate.price_bucket} />}
                    {candidate.time_bucket && <Chip label={candidate.time_bucket} />}
                    {candidate.liquidity_tier && <Chip label={candidate.liquidity_tier} />}
                    {candidate.calibration_sample_count !== null && (
                      <Chip label={`Samples ${candidate.calibration_sample_count}`} />
                    )}
                    {candidate.dq_status && <Chip label={`DQ ${candidate.dq_status}`} />}
                    {candidate.scoring_recommendation && (
                      <Chip label={`Scoring ${candidate.scoring_recommendation}`} />
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
                <MetricCard
                  label="Gross Edge"
                  value={`${(candidate.gross_edge * 100).toFixed(2)}%`}
                  tone="emerald"
                />
                <MetricCard
                  label="Fee"
                  value={`-${(candidate.fee_cost * 100).toFixed(2)}%`}
                  tone="slate"
                />
                <MetricCard
                  label="Slippage + Dispute"
                  value={`-${((candidate.slippage_cost + candidate.dispute_discount) * 100).toFixed(2)}%`}
                  tone="slate"
                />
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
                    <div className="mt-2 text-xs text-slate-300/90">
                      {candidate.rejection_reason_description}
                    </div>
                  )}
                </div>
              )}
            </article>
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-12 text-center text-slate-300">
          No NetEV evaluations yet. Run a batch evaluation to populate this page.
        </div>
      )}
    </main>
  )
}

function FilterButton({
  active,
  label,
  onClick,
}: {
  active: boolean
  label: string
  onClick: () => void
}) {
  return (
    <button
      className={`rounded-lg px-4 py-2 text-sm transition ${
        active ? "bg-white text-slate-950" : "bg-white/10 text-slate-200 hover:bg-white/15"
      }`}
      onClick={onClick}
    >
      {label}
    </button>
  )
}

function Chip({ label }: { label: string }) {
  return <span className="rounded-full bg-white/10 px-2.5 py-1">{label}</span>
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
