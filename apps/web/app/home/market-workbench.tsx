"use client"

import { useEffect, useMemo, useState } from "react"

import { apiGet } from "@/lib/api"

import {
  ConsoleBadge,
  ConsoleButton,
  ConsoleEmpty,
  ConsoleField,
  ConsoleInput,
  ConsoleMetric,
  ConsolePanel,
  ConsoleSelect,
} from "../components/console-ui"

interface MarketDecision {
  classification_status: string
  primary_category_code: string | null
  admission_bucket_code: string | null
  confidence: number | null
  failure_reason_code: string | null
  classified_at: string
}

interface MarketDQ {
  status: string
  score: number | null
  checked_at: string
}

interface MarketItem {
  id: string
  market_id: string
  question: string
  market_status: string | null
  close_time: string | null
  updated_at: string
  latest_classification: MarketDecision | null
  latest_dq: MarketDQ | null
}

interface MarketResponse {
  markets: MarketItem[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

const STATUS_LABELS: Record<string, string> = {
  active_accepting_orders: "可交易",
  active_not_accepting_orders: "暂停下单",
  active_open: "开放中",
  active_paused: "已暂停",
  closed: "已关闭",
  resolved: "已结算",
}

const REASON_LABELS: Record<string, string> = {
  TAG_NO_CATEGORY_MATCH: "系统没有识别出可信主类别",
  TAG_LOW_CONFIDENCE: "自动判断置信度不足",
  TAG_CATEGORY_CONFLICT: "分类规则互相冲突",
  TAG_BUCKET_CONFLICT: "放行桶判断冲突",
  TAG_NO_BUCKET_MATCH: "没有命中可放行规则",
  TAG_BLACKLIST_MATCH: "命中自动拦截规则",
}

function formatDateTime(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString("zh-CN") : "-"
}

function statusLabel(value: string | null) {
  return value ? STATUS_LABELS[value] ?? value : "未知状态"
}

function dqLabel(dq: MarketDQ | null) {
  if (!dq) return "等待检测"
  if (dq.status === "pass") return "通过"
  if (dq.status === "warn") return "注意"
  if (dq.status === "fail") return "失败"
  return dq.status
}

function dqTone(dq: MarketDQ | null) {
  if (!dq) return "warn" as const
  if (dq.status === "pass") return "good" as const
  if (dq.status === "warn") return "warn" as const
  return "bad" as const
}

function decisionLabel(decision: MarketDecision | null) {
  if (!decision) return "等待自动判断"
  if (decision.classification_status === "Blocked" || decision.admission_bucket_code === "LIST_BLACK") {
    return "已自动拦截"
  }
  if (decision.classification_status === "Tagged" && decision.admission_bucket_code === "LIST_WHITE") {
    return "已自动放行"
  }
  return "系统处理中"
}

function decisionTone(decision: MarketDecision | null) {
  if (!decision) return "warn" as const
  if (decision.classification_status === "Blocked" || decision.admission_bucket_code === "LIST_BLACK") {
    return "bad" as const
  }
  if (decision.classification_status === "Tagged" && decision.admission_bucket_code === "LIST_WHITE") {
    return "good" as const
  }
  return "warn" as const
}

function reasonLabel(decision: MarketDecision | null) {
  if (!decision) return "系统还在形成正式结论"
  if (decision.classification_status === "Tagged" && decision.admission_bucket_code === "LIST_WHITE") {
    return "已满足自动放行条件"
  }
  if (!decision.failure_reason_code) return "没有额外阻断原因"
  return REASON_LABELS[decision.failure_reason_code] ?? decision.failure_reason_code
}

export function MarketWorkbench() {
  const [data, setData] = useState<MarketResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState("")
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("")

  useEffect(() => {
    const params = new URLSearchParams({ page: String(page), page_size: "8", only_allowed: "true" })
    if (search) params.set("search", search)
    if (statusFilter) params.set("status", statusFilter)

    setLoading(true)
    setError(null)

    apiGet<MarketResponse>(`/markets?${params.toString()}`)
      .then((response) => setData(response))
      .catch((fetchError) => {
        setError(fetchError instanceof Error ? fetchError.message : "加载市场列表失败")
      })
      .finally(() => setLoading(false))
  }, [page, search, statusFilter])

  const summary = useMemo(() => {
    const markets = data?.markets ?? []
    return markets.reduce(
      (result, market) => {
        result.allowed += 1
        if (market.market_status === "active_accepting_orders") {
          result.tradable += 1
        }
        if (market.latest_dq?.status !== "pass") {
          result.dqAttention += 1
        }
        return result
      },
      { allowed: 0, tradable: 0, dqAttention: 0 },
    )
  }, [data?.markets])

  const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / (data?.page_size ?? 8)))

  return (
    <section id="markets" className="space-y-6">
      <ConsolePanel
        title="市场总表"
        description="这里只看已自动放行的市场。系统已经把明显不该继续看的对象挡在外面，所以你看到的是能继续往下看的候选池。"
      >
        <div className="grid gap-5 xl:grid-cols-[0.72fr_1.28fr]">
          <div className="grid gap-4 sm:grid-cols-3 xl:grid-cols-1">
            <ConsoleMetric label="当前页已放行" value={String(summary.allowed)} tone={summary.allowed > 0 ? "good" : "neutral"} hint="系统已先过滤拦截项" />
            <ConsoleMetric label="当前页可交易" value={String(summary.tradable)} tone={summary.tradable > 0 ? "good" : "neutral"} hint="状态允许继续下单" />
            <ConsoleMetric label="DQ 需留意" value={String(summary.dqAttention)} tone={summary.dqAttention > 0 ? "warn" : "good"} hint="不是失败，只是提醒" />
          </div>

          <div className="rounded-[26px] border border-[color:var(--oa-border)] bg-[rgba(255,255,255,0.7)] p-4">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end">
              <form
                className="flex min-w-[280px] flex-1 gap-2"
                onSubmit={(event) => {
                  event.preventDefault()
                  setPage(1)
                  setSearch(searchInput.trim())
                }}
              >
                <ConsoleInput
                  value={searchInput}
                  onChange={(event) => setSearchInput(event.target.value)}
                  placeholder="搜索市场问题"
                  className="flex-1"
                />
                <ConsoleButton type="submit" tone="primary">
                  搜索
                </ConsoleButton>
              </form>

              <ConsoleField label="市场状态">
                <ConsoleSelect
                  value={statusFilter}
                  onChange={(event) => {
                    setStatusFilter(event.target.value)
                    setPage(1)
                  }}
                  className="min-w-44"
                >
                  <option value="">全部状态</option>
                  <option value="active_accepting_orders">可交易</option>
                  <option value="active_not_accepting_orders">暂停下单</option>
                  <option value="closed">已关闭</option>
                  <option value="resolved">已结算</option>
                </ConsoleSelect>
              </ConsoleField>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-2">
              <ConsoleBadge label="默认只看已放行" tone="good" />
              <ConsoleBadge label={search ? `关键词：${search}` : "未设置关键词"} tone={search ? "info" : "neutral"} />
              <ConsoleBadge
                label={statusFilter ? `状态：${statusLabel(statusFilter)}` : "全部状态"}
                tone={statusFilter ? "info" : "neutral"}
              />
              {(search || statusFilter) ? (
                <ConsoleButton
                  type="button"
                  onClick={() => {
                    setSearch("")
                    setSearchInput("")
                    setStatusFilter("")
                    setPage(1)
                  }}
                  size="sm"
                >
                  清空条件
                </ConsoleButton>
              ) : null}
            </div>
          </div>
        </div>
      </ConsolePanel>

      <ConsolePanel title="优先市场" description="卡片里只保留你最需要知道的 4 件事：能不能交易、系统为什么放行、属于哪类、什么时候结束。">
        {loading ? <div className="py-16 text-center text-sm text-[color:var(--oa-muted)]">正在加载市场...</div> : null}
        {error ? (
          <div className="rounded-[22px] border border-[color:rgba(177,63,51,0.2)] bg-[color:rgba(177,63,51,0.1)] px-4 py-4 text-sm text-[color:var(--oa-red)]">
            {error}
          </div>
        ) : null}
        {!loading && !error && (data?.markets.length ?? 0) === 0 ? (
          <ConsoleEmpty title="当前没有可用市场" description="可以先清空筛选条件，或稍后等系统放行新的市场。" />
        ) : null}

        {!loading && !error && (data?.markets.length ?? 0) > 0 ? (
          <div className="grid gap-4 xl:grid-cols-2">
            {data?.markets.map((market) => {
              const decision = market.latest_classification
              const tone = decisionTone(decision)

              return (
                <article
                  key={market.id}
                  className="relative overflow-hidden rounded-[26px] border border-[color:var(--oa-border)] bg-[linear-gradient(180deg,rgba(255,255,255,0.9),rgba(247,239,229,0.74))] p-5 shadow-[0_18px_42px_rgba(49,31,20,0.05)]"
                >
                  <div
                    className={`absolute inset-x-0 top-0 h-1 ${
                      tone === "good"
                        ? "bg-[linear-gradient(90deg,rgba(47,125,81,0.75),rgba(47,125,81,0.08))]"
                        : tone === "warn"
                          ? "bg-[linear-gradient(90deg,rgba(155,106,36,0.75),rgba(155,106,36,0.08))]"
                          : "bg-[linear-gradient(90deg,rgba(177,63,51,0.75),rgba(177,63,51,0.08))]"
                    }`}
                  />

                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-xs uppercase tracking-[0.18em] text-[color:var(--oa-muted)]">{market.market_id}</p>
                      <h3 className="mt-2 text-xl font-semibold leading-8 tracking-tight text-[color:var(--oa-text)] [font-family:var(--oa-font-display)]">
                        {market.question}
                      </h3>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <ConsoleBadge label={statusLabel(market.market_status)} tone="neutral" />
                      <ConsoleBadge label={dqLabel(market.latest_dq)} tone={dqTone(market.latest_dq)} />
                      <ConsoleBadge label={decisionLabel(decision)} tone={tone} />
                    </div>
                  </div>

                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-[20px] border border-[color:rgba(91,68,48,0.1)] bg-[rgba(255,251,246,0.78)] p-4">
                      <p className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--oa-muted)]">系统原因</p>
                      <p className="mt-2 text-sm leading-7 text-[color:var(--oa-text)]">{reasonLabel(decision)}</p>
                    </div>
                    <div className="rounded-[20px] border border-[color:rgba(91,68,48,0.1)] bg-[rgba(255,251,246,0.78)] p-4">
                      <p className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--oa-muted)]">正式主类别</p>
                      <p className="mt-2 text-sm leading-7 text-[color:var(--oa-text)]">{decision?.primary_category_code ?? "暂无"}</p>
                    </div>
                    <div className="rounded-[20px] border border-[color:rgba(91,68,48,0.1)] bg-[rgba(255,251,246,0.78)] p-4">
                      <p className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--oa-muted)]">最近更新时间</p>
                      <p className="mt-2 text-sm leading-7 text-[color:var(--oa-text)]">{formatDateTime(market.updated_at)}</p>
                    </div>
                    <div className="rounded-[20px] border border-[color:rgba(91,68,48,0.1)] bg-[rgba(255,251,246,0.78)] p-4">
                      <p className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--oa-muted)]">收盘时间</p>
                      <p className="mt-2 text-sm leading-7 text-[color:var(--oa-text)]">{formatDateTime(market.close_time)}</p>
                    </div>
                  </div>
                </article>
              )
            })}
          </div>
        ) : null}

        {!loading && !error && data ? (
          <div className="mt-5 flex items-center justify-between gap-3">
            <ConsoleButton onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={page === 1}>
              上一页
            </ConsoleButton>
            <span className="text-sm text-[color:var(--oa-muted)]">
              第 {page} / {totalPages} 页
            </span>
            <ConsoleButton onClick={() => setPage((current) => current + 1)} disabled={!data.has_more}>
              下一页
            </ConsoleButton>
          </div>
        ) : null}
      </ConsolePanel>
    </section>
  )
}
