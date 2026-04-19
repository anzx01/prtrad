"use client"

import Link from "next/link"
import { useEffect, useState } from "react"

import { apiGet, apiPost } from "@/lib/api"

import { PageIntro, SoftPanel } from "../components/page-intro"

type NetEVCandidate = {
  id: string
  market_ref_id: string
  market_id: string | null
  question: string | null
  category_code: string | null
  calibration_sample_count: number | null
  price_bucket: string | null
  time_bucket: string | null
  liquidity_tier: string | null
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
  dq_checked_at: string | null
  dq_blocking_reason_codes: string[]
  dq_warning_reason_codes: string[]
  dq_primary_reason_code: string | null
  dq_primary_reason_name: string | null
  dq_primary_reason_description: string | null
  rule_version: string
  evaluated_at: string
}

type NetEVBatchResponse = {
  total: number
  admitted: number
  rejected: number
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

const DQ_STATUS_LABELS: Record<string, string> = {
  pass: "通过",
  warn: "告警",
  fail: "失败",
}

const DQ_STATUS_STYLES: Record<string, string> = {
  pass: "border-emerald-400/30 bg-emerald-500/10 text-emerald-50",
  warn: "border-amber-400/30 bg-amber-500/10 text-amber-50",
  fail: "border-rose-400/30 bg-rose-500/10 text-rose-50",
}

function MetricCard({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone: "slate" | "emerald" | "rose"
}) {
  const toneClassName = {
    slate: "border-white/10 bg-slate-900/60 text-white",
    emerald: "border-emerald-500/20 bg-emerald-500/10 text-emerald-50",
    rose: "border-rose-500/20 bg-rose-500/10 text-rose-50",
  }[tone]

  return (
    <div className={`rounded-2xl border p-4 ${toneClassName}`}>
      <div className="text-[11px] uppercase tracking-[0.22em] text-current/70">{label}</div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
    </div>
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
      type="button"
      onClick={onClick}
      className={`rounded-full border px-4 py-2 text-sm transition ${
        active
          ? "border-cyan-300/40 bg-cyan-500/15 text-cyan-50"
          : "border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
      }`}
    >
      {label}
    </button>
  )
}

function Chip({ label }: { label: string }) {
  return <span className="rounded-full border border-white/10 bg-black/20 px-2.5 py-1 text-xs text-slate-200">{label}</span>
}

function formatTimestamp(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "-"
}

function getDQStatusLabel(value: string | null | undefined) {
  if (!value) {
    return "-"
  }
  return DQ_STATUS_LABELS[value] ?? value
}

function isBlockedByDQ(candidate: NetEVCandidate) {
  return Boolean(candidate.dq_status && candidate.dq_status !== "pass")
}

function DQStatusChip({ status }: { status: string }) {
  return (
    <span
      className={`rounded-full border px-2.5 py-1 text-xs ${
        DQ_STATUS_STYLES[status] ?? "border-white/10 bg-black/20 text-slate-200"
      }`}
    >
      {`DQ ${getDQStatusLabel(status)}`}
    </span>
  )
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

    try {
      const endpoint = decision ? `/netev/candidates?decision=${decision}` : "/netev/candidates"
      const data = await apiGet<NetEVCandidate[]>(endpoint)
      setCandidates(data ?? [])
    } catch (fetchError) {
      setError(getErrorMessage(fetchError))
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
      setNotice(`已评估 ${result.total} 个候选，其中 ${result.admitted} 个准入，${result.rejected} 个拒绝。`)
      await loadCandidates(filter)
    } catch (submitError) {
      setError(getErrorMessage(submitError))
    } finally {
      setRunning(false)
    }
  }

  const admitted = candidates.filter((candidate) => candidate.admission_decision === "admit").length
  const rejected = candidates.length - admitted

  return (
    <main className="mx-auto max-w-7xl px-4 py-5 md:px-6">
      <PageIntro
        eyebrow="NetEV"
        title="NetEV 准入"
        description="这页用来回答“这个市场值不值得进”。不要只看最终准入/拒绝，还要一起看 gross edge、费用、滑点、争议折扣，以及 DQ 和 scoring 的约束。"
        stats={[
          { label: "当前候选数", value: String(candidates.length) },
          { label: "准入 / 拒绝", value: `${admitted} / ${rejected}` },
        ]}
        guides={[
          {
            title: "先看什么",
            description: "先看最终 admit / reject，再分清是 NetEV 本身不够，还是先被 DQ / scoring 闸门挡住。",
          },
          {
            title: "什么时候算异常",
            description: "如果你明明已经跑过批量评估，但这里仍长期为空，才值得继续排查任务执行链路。",
          },
          {
            title: "下一步去哪",
            description: "若是 DQ 挡住，先去 `/dq` 看板；若是 NetEV 本身不足，再看 calibration、scoring 和成本项。",
          },
        ]}
      />

      <div className="mb-6 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={handleBatchEvaluate}
          disabled={running}
          className="rounded-2xl bg-cyan-500 px-4 py-3 text-sm font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-500"
        >
          {running ? "评估中..." : "评估最近 20 个"}
        </button>
        <FilterButton active={!filter} label="全部" onClick={() => setFilter("")} />
        <FilterButton active={filter === "admit"} label="仅准入" onClick={() => setFilter("admit")} />
        <FilterButton active={filter === "reject"} label="仅拒绝" onClick={() => setFilter("reject")} />
      </div>

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <MetricCard label="候选数" value={String(candidates.length)} tone="slate" />
        <MetricCard label="准入" value={String(admitted)} tone="emerald" />
        <MetricCard label="拒绝" value={String(rejected)} tone="rose" />
      </div>

      {notice ? (
        <div className="mb-6 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
          {notice}
        </div>
      ) : null}
      {error ? (
        <div className="mb-6 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-8 text-slate-300">
          正在加载 NetEV 候选...
        </div>
      ) : null}

      {!loading && candidates.length === 0 ? (
        <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-12 text-center text-slate-300">
          当前还没有 NetEV 评估结果。先执行一次批量评估，再回来判断哪些市场值得准入。
        </div>
      ) : null}

      {!loading && candidates.length > 0 ? (
        <div className="space-y-4">
          {candidates.map((candidate) => (
            <SoftPanel
              key={candidate.id}
              title={candidate.question || candidate.market_id || candidate.market_ref_id}
              description={`${candidate.category_code || "未分类"} / ${candidate.rule_version} / ${new Date(candidate.evaluated_at).toLocaleString("zh-CN", { hour12: false })}`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <Chip label={candidate.admission_decision === "admit" ? "准入" : "拒绝"} />
                {candidate.price_bucket ? <Chip label={candidate.price_bucket} /> : null}
                {candidate.time_bucket ? <Chip label={candidate.time_bucket} /> : null}
                {candidate.liquidity_tier ? <Chip label={candidate.liquidity_tier} /> : null}
                {candidate.calibration_sample_count !== null ? <Chip label={`样本 ${candidate.calibration_sample_count}`} /> : null}
                {candidate.dq_status ? <DQStatusChip status={candidate.dq_status} /> : null}
                {candidate.scoring_recommendation ? <Chip label={`评分 ${candidate.scoring_recommendation}`} /> : null}
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-4">
                <MetricCard label="毛边际" value={`${(candidate.gross_edge * 100).toFixed(2)}%`} tone="emerald" />
                <MetricCard label="手续费" value={`-${(candidate.fee_cost * 100).toFixed(2)}%`} tone="slate" />
                <MetricCard
                  label="滑点 + 争议折扣"
                  value={`-${((candidate.slippage_cost + candidate.dispute_discount) * 100).toFixed(2)}%`}
                  tone="slate"
                />
                <MetricCard label="NetEV" value={`${(candidate.net_ev * 100).toFixed(2)}%`} tone={candidate.net_ev >= 0 ? "emerald" : "rose"} />
              </div>

              {isBlockedByDQ(candidate) ? (
                <div className="mt-4 rounded-2xl border border-amber-400/20 bg-amber-500/10 p-4 text-sm text-slate-200">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                      <p className="font-medium text-amber-100">DQ 闸门已拦截本次 NetEV 准入</p>
                      <p className="mt-2 leading-6 text-slate-300">
                        最新 DQ 状态是 {getDQStatusLabel(candidate.dq_status)}，而当前 NetEV 只接受 `pass`。
                        这表示市场先被 DQ 挡住了，还没进入真正的自动准入判断。
                      </p>
                    </div>
                    <Link
                      href="/dq"
                      className="inline-flex items-center justify-center rounded-full border border-amber-300/30 bg-amber-500/10 px-4 py-2 text-sm text-amber-100 transition hover:bg-amber-500/20"
                    >
                      去 DQ 看板排查
                    </Link>
                  </div>

                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                      <p className="text-xs text-slate-400">最新 DQ 时间</p>
                      <p className="mt-2 text-sm text-slate-200">{formatTimestamp(candidate.dq_checked_at)}</p>
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                      <p className="text-xs text-slate-400">市场 ID</p>
                      <p className="mt-2 text-sm text-slate-200">{candidate.market_id ?? candidate.market_ref_id}</p>
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                      <p className="text-xs text-slate-400">首要 DQ 原因</p>
                      <p className="mt-2 text-sm text-slate-200">
                        {candidate.dq_primary_reason_name || candidate.dq_primary_reason_code || "当前未记录"}
                      </p>
                      {candidate.dq_primary_reason_code ? (
                        <p className="mt-1 text-xs text-slate-500">{candidate.dq_primary_reason_code}</p>
                      ) : null}
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                      <p className="text-xs text-slate-400">DQ 原因摘要</p>
                      <p className="mt-2 text-sm text-slate-200">
                        {[...candidate.dq_blocking_reason_codes, ...candidate.dq_warning_reason_codes].slice(0, 3).join("，") || "-"}
                      </p>
                    </div>
                  </div>

                  {candidate.dq_primary_reason_description ? (
                    <p className="mt-3 text-sm leading-6 text-slate-300">{candidate.dq_primary_reason_description}</p>
                  ) : null}
                </div>
              ) : null}

              {candidate.rejection_reason_code ? (
                <div className="mt-4 rounded-2xl border border-rose-400/20 bg-rose-500/10 p-4 text-sm text-slate-200">
                  <p className="font-medium">{candidate.rejection_reason_name || candidate.rejection_reason_code}</p>
                  <p className="mt-1 text-xs text-slate-400">{candidate.rejection_reason_code}</p>
                  {candidate.rejection_reason_description ? (
                    <p className="mt-2 text-sm leading-6 text-slate-300">{candidate.rejection_reason_description}</p>
                  ) : null}
                </div>
              ) : null}
            </SoftPanel>
          ))}
        </div>
      ) : null}
    </main>
  )
}
