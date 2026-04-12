"use client"

import { useCallback, useEffect, useMemo, useState } from "react"

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
import { PageIntro } from "../components/page-intro"

interface Market {
  id: string
  market_id: string
  question: string
  description: string | null
  market_status: string | null
  category_raw: string | null
  close_time: string | null
  created_at: string
  updated_at: string
}

interface MarketListResponse {
  markets: Market[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

const STATUS_LABELS: Record<string, string> = {
  active_accepting_orders: "活跃可下单",
  active_not_accepting_orders: "活跃不可下单",
  closed: "已关闭",
  resolved: "已结算",
}

function statusBadge(status: string | null) {
  if (!status) {
    return <ConsoleBadge label="未知" tone="neutral" />
  }
  const tone = status === "resolved" ? "info" : status === "closed" ? "neutral" : status === "active_not_accepting_orders" ? "warn" : "good"
  return <ConsoleBadge label={STATUS_LABELS[status] ?? status} tone={tone} />
}

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleDateString("zh-CN") : "-"
}

export default function MarketsPage() {
  const [data, setData] = useState<MarketListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState("")
  const [searchInput, setSearchInput] = useState("")
  const [statusFilter, setStatusFilter] = useState("")

  const fetchMarkets = useCallback(async () => {
    setLoading(true)
    setError(null)

    const params = new URLSearchParams({ page: String(page), page_size: "20" })
    if (search) params.set("search", search)
    if (statusFilter) params.set("status", statusFilter)

    try {
      const json = await apiGet<MarketListResponse>(`/markets?${params.toString()}`)
      setData(json)
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "加载市场失败")
    } finally {
      setLoading(false)
    }
  }, [page, search, statusFilter])

  useEffect(() => {
    void fetchMarkets()
  }, [fetchMarkets])

  const statusSummary = useMemo(() => {
    const summary = { active: 0, closed: 0, resolved: 0 }
    for (const market of data?.markets ?? []) {
      if (market.market_status === "closed") {
        summary.closed += 1
      } else if (market.market_status === "resolved") {
        summary.resolved += 1
      } else {
        summary.active += 1
      }
    }
    return summary
  }, [data])

  const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / (data?.page_size ?? 20)))

  function handleSearchSubmit(event: React.FormEvent) {
    event.preventDefault()
    setPage(1)
    setSearch(searchInput.trim())
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-5 md:px-6">
      <PageIntro
        eyebrow="Markets"
        title="市场总表"
        description="先用这页确认市场是否真的已接入，再继续看 DQ、分类和审核。如果这里都没有你预期的市场，后面的页面大概率也不会有正确结果。"
        stats={[
          { label: "当前页市场数", value: String(data?.markets.length ?? 0) },
          { label: "筛选后总数", value: String(data?.total ?? 0) },
        ]}
        guides={[
          {
            title: "先看什么",
            description: "先看 question、状态和关闭时间，确认是不是你期望的市场批次。",
          },
          {
            title: "什么时候算异常",
            description: "你明明知道某批市场已经同步过，但这里搜不到，才值得继续排查 ingest 或筛选条件。",
          },
          {
            title: "下一步去哪",
            description: "市场确认存在后，继续去看数据质量、标签分类和审核队列是否也同步出数。",
          },
        ]}
      />

      <section className="mb-6 grid gap-4 md:grid-cols-3">
        <ConsoleMetric label="当前页活跃市场" value={String(statusSummary.active)} hint="按当前筛选条件统计，不是全库总量。" />
        <ConsoleMetric label="当前页已关闭" value={String(statusSummary.closed)} hint="适合确认是否进入后续历史链路。" />
        <ConsoleMetric label="当前页已结算" value={String(statusSummary.resolved)} hint="若 calibration 长期为 0，可优先确认这里是否有已结算市场。" />
      </section>

      <ConsolePanel title="筛选与搜索" description="先缩小范围，再判断数据是否缺失。">
        <div className="flex flex-wrap gap-3">
          <form onSubmit={handleSearchSubmit} className="flex min-w-[280px] flex-1 gap-2">
            <ConsoleInput
              type="text"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="按问题关键词搜索市场"
              className="flex-1"
            />
            <ConsoleButton type="submit" tone="primary">
              搜索
            </ConsoleButton>
          </form>
          <ConsoleField label="状态过滤">
            <ConsoleSelect
              value={statusFilter}
              onChange={(event) => {
                setStatusFilter(event.target.value)
                setPage(1)
              }}
              className="min-w-48"
            >
              <option value="">全部状态</option>
              <option value="active_accepting_orders">活跃可下单</option>
              <option value="active_not_accepting_orders">活跃不可下单</option>
              <option value="closed">已关闭</option>
              <option value="resolved">已结算</option>
            </ConsoleSelect>
          </ConsoleField>
          {(search || statusFilter) && (
            <ConsoleButton
              type="button"
              onClick={() => {
                setSearch("")
                setSearchInput("")
                setStatusFilter("")
                setPage(1)
              }}
            >
              清空条件
            </ConsoleButton>
          )}
        </div>
        <p className="mt-3 text-sm text-[#8b949e]">
          {data ? `当前共命中 ${data.total} 个市场，正在看第 ${data.page} 页。` : "可以先按状态或关键词缩小范围。"}
        </p>
      </ConsolePanel>

      <section className="mt-6">
        {loading ? <div className="py-20 text-center text-[#8b949e]">正在加载市场数据...</div> : null}
        {error ? (
          <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-5 text-sm text-rose-100">
            加载失败：{error}
          </div>
        ) : null}

        {!loading && !error && data ? (
          <ConsolePanel title="市场列表" description="先看问题、状态和关闭时间；如果这里没问题，再继续往下游页面看。">
            <div className="overflow-x-auto">
              <table className="console-table">
                <thead>
                  <tr>
                    <th>市场问题</th>
                    <th>类别</th>
                    <th>状态</th>
                    <th>关闭时间</th>
                    <th>更新时间</th>
                  </tr>
                </thead>
                <tbody>
                  {data.markets.length === 0 ? (
                    <tr>
                      <td colSpan={5}>
                        <ConsoleEmpty
                          title="当前条件下没有命中市场"
                          description="如果你本来预期这里应该有数据，先检查筛选条件，再检查 ingest 是否真的跑过。"
                        />
                      </td>
                    </tr>
                  ) : null}
                  {data.markets.map((market) => (
                    <tr key={market.id}>
                      <td>
                        <p className="max-w-xl text-sm leading-6 text-[#e6edf3]">{market.question}</p>
                        <p className="mt-2 text-xs text-[#8b949e]">{market.market_id}</p>
                      </td>
                      <td className="text-[#c9d1d9]">{market.category_raw ?? "-"}</td>
                      <td>{statusBadge(market.market_status)}</td>
                      <td className="text-[#c9d1d9]">{formatDate(market.close_time)}</td>
                      <td className="text-[#8b949e]">{formatDate(market.updated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-4 flex items-center justify-between">
              <ConsoleButton
                type="button"
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                disabled={page === 1}
              >
                上一页
              </ConsoleButton>
              <span className="text-sm text-[#8b949e]">
                第 {page} / {totalPages} 页
              </span>
              <ConsoleButton
                type="button"
                onClick={() => setPage((current) => current + 1)}
                disabled={!data.has_more}
              >
                下一页
              </ConsoleButton>
            </div>
          </ConsolePanel>
        ) : null}
      </section>
    </main>
  )
}
