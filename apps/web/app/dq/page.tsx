"use client"

import { useCallback, useEffect, useMemo, useState } from "react"

import { apiGet } from "@/lib/api"

import { PageIntro, SoftPanel } from "../components/page-intro"

interface DQReasonCount {
  reason_code: string
  count: number
}

interface DQSnapshotCapture {
  triggered_at: string | null
  audited_at: string
  task_id: string | null
  selected_markets: number | null
  created: number | null
  skipped_existing: number | null
  skipped_missing_mapping: number | null
  skipped_missing_order_books: number | null
  book_fetch_failed_tokens: number
  created_from_source_payload: number
  source_payload_fallback_enabled: boolean
}

interface DQSummary {
  total_checks: number
  status_distribution: Record<string, number>
  pass_rate: number
  latest_checked_at: string | null
  latest_snapshot_time: string | null
  snapshot_age_seconds: number | null
  freshness_status: string
  top_blocking_reasons: DQReasonCount[]
  latest_snapshot_capture: DQSnapshotCapture | null
}

interface DQResult {
  id: string
  market_ref_id: string
  market_id: string | null
  checked_at: string
  status: string
  score: number | null
  failure_count: number
  rule_version: string
  blocking_reason_codes: string[]
  warning_reason_codes: string[]
}

interface DQSummaryResponse {
  summary: DQSummary
  recent_results: DQResult[]
}

const STATUS_STYLES: Record<string, string> = {
  pass: "border-emerald-400/30 bg-emerald-500/10 text-emerald-100",
  warn: "border-amber-400/30 bg-amber-500/10 text-amber-100",
  fail: "border-rose-400/30 bg-rose-500/10 text-rose-100",
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`rounded-full border px-2.5 py-1 text-xs ${STATUS_STYLES[status] ?? "border-white/10 bg-white/5 text-slate-300"}`}>
      {status.toUpperCase()}
    </span>
  )
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
      <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-white">{value}</p>
      {sub ? <p className="mt-2 text-xs text-slate-400">{sub}</p> : null}
    </div>
  )
}

function formatTimestamp(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "-"
}

function formatAge(seconds: number | null) {
  if (seconds === null) return "未知"
  if (seconds < 60) return `${seconds} 秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟`
  return `${(seconds / 3600).toFixed(1)} 小时`
}

export default function DQPage() {
  const [data, setData] = useState<DQSummaryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null)

  const fetchDQ = useCallback(async (background = false) => {
    if (background) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }

    try {
      const json = await apiGet<DQSummaryResponse>("/dq/summary?limit=20")
      setData(json)
      setError(null)
      setLastRefreshedAt(new Date().toISOString())
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "加载 DQ 数据失败")
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void fetchDQ(false)
    const timer = window.setInterval(() => void fetchDQ(true), 30000)
    return () => window.clearInterval(timer)
  }, [fetchDQ])

  const summary = data?.summary
  const distribution = summary?.status_distribution ?? {}
  const snapshotCapture = summary?.latest_snapshot_capture ?? null

  const healthSummary = useMemo(() => {
    if (!summary) {
      return { label: "等待数据", tone: "neutral" as const, detail: "正在读取最近一批 DQ 结果。" }
    }
    if (summary.freshness_status === "stale") {
      return { label: "需要处理", tone: "warn" as const, detail: "快照已陈旧，DQ 结果可能失真，优先重跑 snapshot 和 DQ。" }
    }
    if ((distribution.fail ?? 0) > 0) {
      return { label: "有阻断项", tone: "warn" as const, detail: "本批次存在 fail，建议先看顶部阻断原因和最近结果。" }
    }
    return { label: "批次健康", tone: "good" as const, detail: "当前快照新鲜，且没有明显阻断堆积。" }
  }, [distribution.fail, summary])

  const healthToneClass =
    healthSummary.tone === "good"
      ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-100"
      : healthSummary.tone === "warn"
        ? "border-amber-400/30 bg-amber-500/10 text-amber-100"
        : "border-white/10 bg-white/5 text-slate-200"

  return (
    <main className="mx-auto max-w-7xl px-4 py-5 md:px-6">
      <PageIntro
        eyebrow="DQ"
        title="数据质量看板"
        description="这页主要回答两件事：最新一批 DQ 是否还新鲜，以及失败/告警到底是不是快照抓取问题引起的。先看顶部结论，再看阻断原因和最近结果。"
        stats={[
          { label: "最近刷新", value: formatTimestamp(lastRefreshedAt) },
          { label: "自动刷新", value: "30 秒" },
        ]}
        guides={[
          {
            title: "先看什么",
            description: "先看快照是否 stale，再看 fail 数量，最后看 blocking reason 和 snapshot capture 诊断。",
          },
          {
            title: "什么时候要处理",
            description: "freshness 变 stale、fail 明显增加、book fetch failed 持续升高时，就需要人工介入。",
          },
          {
            title: "0 或空值怎么理解",
            description: "不是所有 0 都是异常；如果最近根本没跑 DQ 或没抓到新快照，也会自然很平。",
          },
        ]}
      />

      <div className="mb-6 flex items-center gap-3">
        <button
          type="button"
          onClick={() => void fetchDQ(true)}
          className="rounded-2xl border border-sky-300/30 bg-sky-500/10 px-4 py-2.5 text-sm text-sky-100 transition hover:bg-sky-500/20"
        >
          {refreshing ? "刷新中..." : "立即刷新"}
        </button>
        <p className="text-sm text-slate-400">页面会每 30 秒自动刷新一次。</p>
      </div>

      {loading ? <div className="py-20 text-center text-slate-400">正在加载 DQ 数据...</div> : null}
      {error ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-5 text-sm text-rose-100">
          加载失败：{error}
        </div>
      ) : null}

      {!loading && !error && summary ? (
        <>
          <section className={`mb-6 rounded-[28px] border p-5 ${healthToneClass}`}>
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-[11px] uppercase tracking-[0.24em] text-white/70">当前判断</p>
                <h2 className="mt-2 text-xl font-semibold text-white">{healthSummary.label}</h2>
                <p className="mt-2 text-sm leading-6 text-white/80">{healthSummary.detail}</p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-white/15 bg-black/10 p-4">
                  <p className="text-xs text-white/70">最近检查时间</p>
                  <p className="mt-2 text-sm font-medium text-white">{formatTimestamp(summary.latest_checked_at)}</p>
                </div>
                <div className="rounded-2xl border border-white/15 bg-black/10 p-4">
                  <p className="text-xs text-white/70">快照年龄</p>
                  <p className="mt-2 text-sm font-medium text-white">{formatAge(summary.snapshot_age_seconds)}</p>
                </div>
              </div>
            </div>
          </section>

          <section className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="本批次检查数" value={String(summary.total_checks)} />
            <StatCard label="通过率" value={`${(summary.pass_rate * 100).toFixed(1)}%`} />
            <StatCard label="通过 / 告警" value={`${distribution.pass ?? 0} / ${distribution.warn ?? 0}`} />
            <StatCard label="失败数" value={String(distribution.fail ?? 0)} sub="fail 越高越值得优先排查" />
          </section>

          <section className="mb-6 grid gap-6 xl:grid-cols-[minmax(0,1.5fr),minmax(300px,0.9fr)]">
            <SoftPanel title="最近一次快照抓取诊断" description="这里用来判断是不是 CLOB 抓取抖动，或者 fallback 正在兜底。">
              {!snapshotCapture ? (
                <p className="text-sm text-slate-500">当前还没有 snapshot capture 审计记录。</p>
              ) : (
                <>
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    <StatCard label="选中市场数" value={String(snapshotCapture.selected_markets ?? 0)} />
                    <StatCard label="成功生成快照" value={String(snapshotCapture.created ?? 0)} />
                    <StatCard label="抓书失败 token" value={String(snapshotCapture.book_fetch_failed_tokens)} />
                    <StatCard label="fallback 快照" value={String(snapshotCapture.created_from_source_payload)} />
                    <StatCard label="缺少订单簿" value={String(snapshotCapture.skipped_missing_order_books ?? 0)} />
                    <StatCard label="缺少映射" value={String(snapshotCapture.skipped_missing_mapping ?? 0)} />
                  </div>
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-slate-300">
                      触发时间：{formatTimestamp(snapshotCapture.triggered_at)}
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-slate-300">
                      审计时间：{formatTimestamp(snapshotCapture.audited_at)}
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-slate-300">
                      Task ID：{snapshotCapture.task_id ?? "-"}
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-slate-300">
                      Source payload fallback：{snapshotCapture.source_payload_fallback_enabled ? "已开启" : "未开启"}
                    </div>
                  </div>
                </>
              )}
            </SoftPanel>

            <SoftPanel title="看板阅读指引" description="把这页当成一个排障入口，而不是纯展示页。">
              <div className="space-y-3 text-sm leading-6 text-slate-300">
                <p>1. 若 freshness 变 stale，优先重跑 snapshot sync 和 DQ。</p>
                <p>2. 若 `book_fetch_failed_tokens` 持续升高，优先怀疑外部抓取链路而不是 DQ 规则。</p>
                <p>3. 若 `created_from_source_payload` 上升，说明 fallback 在兜底，DQ 还能继续出数。</p>
                <p>4. 若 fail 明显堆积，再下钻看阻断原因和最近结果。</p>
              </div>
            </SoftPanel>
          </section>

          <SoftPanel title="顶部阻断原因" description="fail 多时先看这里，能最快知道批次被什么规则拦住。">
            {summary.top_blocking_reasons.length === 0 ? (
              <p className="text-sm text-slate-400">最新批次没有明显阻断原因。</p>
            ) : (
              <div className="flex flex-wrap gap-3">
                {summary.top_blocking_reasons.map((item) => (
                  <div key={item.reason_code} className="rounded-full border border-white/10 bg-black/20 px-3 py-1.5 text-sm text-slate-200">
                    {item.reason_code}
                    <span className="ml-2 text-xs text-slate-500">{item.count}</span>
                  </div>
                ))}
              </div>
            )}
          </SoftPanel>

          <div className="mt-6">
            <SoftPanel title="最近一批 DQ 结果" description="这里只放最近结果样本；如果你在这里看到了 fail，就继续结合原因字段往上追。">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[860px] text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-left text-slate-400">
                      <th className="px-4 py-3 font-medium">市场</th>
                      <th className="px-4 py-3 font-medium">检查时间</th>
                      <th className="px-4 py-3 font-medium">状态</th>
                      <th className="px-4 py-3 font-medium">分数</th>
                      <th className="px-4 py-3 font-medium">失败项</th>
                      <th className="px-4 py-3 font-medium">原因摘要</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent_results.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-4 py-12 text-center text-slate-500">
                          当前没有 DQ 结果。若你预期这里应有数据，优先检查 DQ 任务是否真的执行。
                        </td>
                      </tr>
                    ) : null}
                    {data.recent_results.map((result) => (
                      <tr key={result.id} className="border-b border-white/5 transition hover:bg-white/[0.03]">
                        <td className="px-4 py-3 font-mono text-xs text-slate-300">
                          {result.market_id ?? result.market_ref_id.slice(0, 8)}
                        </td>
                        <td className="px-4 py-3 text-slate-300">{formatTimestamp(result.checked_at)}</td>
                        <td className="px-4 py-3">
                          <StatusBadge status={result.status} />
                        </td>
                        <td className="px-4 py-3 text-slate-300">
                          {result.score !== null ? result.score.toFixed(3) : "-"}
                        </td>
                        <td className="px-4 py-3 text-slate-300">{result.failure_count}</td>
                        <td className="px-4 py-3 text-xs text-slate-400">
                          {[...result.blocking_reason_codes, ...result.warning_reason_codes].slice(0, 3).join("，") || "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </SoftPanel>
          </div>
        </>
      ) : null}
    </main>
  )
}
