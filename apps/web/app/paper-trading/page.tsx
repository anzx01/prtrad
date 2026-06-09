"use client"

import { useEffect, useState } from "react"

import { apiGet, apiPost } from "@/lib/api"
import {
  ConsoleBadge,
  ConsoleButton,
  ConsoleCallout,
  ConsoleEmpty,
  ConsoleInset,
  ConsoleMetric,
  ConsolePanel,
} from "../components/console-ui"
import { PageIntro } from "../components/page-intro"

interface PaperSummary {
  open_count: number
  closed_count: number
  total_count: number
  entry_notional: number
  unrealized_pnl: number
  realized_pnl: number
  total_pnl: number
  win_rate: number
}

interface PaperPosition {
  id: string
  market_id: string | null
  question: string | null
  market_status: string | null
  final_resolution: string | null
  strategy_version: string | null
  side: "yes" | "no"
  status: "open" | "closed"
  opened_at: string
  entry_price: number
  size: number
  entry_notional: number
  mark_price: number | null
  mark_time: string | null
  unrealized_pnl: number
  closed_at: string | null
  exit_price: number | null
  exit_reason: string | null
  realized_pnl: number | null
  net_ev: number | null
}

const EMPTY_SUMMARY: PaperSummary = {
  open_count: 0,
  closed_count: 0,
  total_count: 0,
  entry_notional: 0,
  unrealized_pnl: 0,
  realized_pnl: 0,
  total_pnl: 0,
  win_rate: 0,
}
function formatNumber(value: number, digits = 3) {
  return value.toFixed(digits)
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`
}

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "-"
}

function pnlTone(value: number) {
  if (value > 0) return "good" as const
  if (value < 0) return "bad" as const
  return "neutral" as const
}

function sideLabel(value: PaperPosition["side"]) {
  return value === "yes" ? "YES" : "NO"
}

function exitReasonLabel(value: string | null) {
  if (value === "resolved") return "已结算"
  if (value === "market_closed") return "市场关闭"
  if (value === "expired") return "到期"
  return value ?? "-"
}

function PositionList({ positions, closed }: { positions: PaperPosition[]; closed?: boolean }) {
  if (positions.length === 0) {
    return (
      <ConsoleEmpty
        title={closed ? "还没有已平仓记录" : "当前没有开放持仓"}
        description={closed ? "当市场结算或关闭后，模拟持仓会沉淀到这里。" : "先评估准入候选，系统会把可执行机会转成模拟持仓。"}
      />
    )
  }

  return (
    <div className="space-y-3">
      {positions.map((position) => {
        const pnl = closed ? position.realized_pnl ?? 0 : position.unrealized_pnl
        return (
          <ConsoleInset key={position.id}>
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap gap-2">
                  <ConsoleBadge label={sideLabel(position.side)} tone={position.side === "no" ? "info" : "neutral"} />
                  <ConsoleBadge label={position.status === "open" ? "开放" : "已平仓"} tone={position.status === "open" ? "good" : "neutral"} />
                  {position.net_ev !== null ? <ConsoleBadge label={`NetEV ${formatNumber(position.net_ev, 4)}`} tone="info" /> : null}
                </div>
                <h3 className="mt-3 text-base font-semibold leading-6 text-[color:var(--oa-text)]">
                  {position.question ?? position.market_id ?? position.id}
                </h3>
                <p className="mt-2 text-sm leading-6 text-[color:var(--oa-muted)]">
                  {position.market_id ?? "-"} · {position.strategy_version ?? "-"} · {formatDate(position.opened_at)}
                </p>
              </div>
              <div className="grid min-w-[280px] grid-cols-2 gap-3 text-sm">
                <ConsoleInset>
                  <p className="console-kicker">入场</p>
                  <p className="mt-2 font-semibold text-[color:var(--oa-text)]">
                    {formatNumber(position.entry_price)} × {formatNumber(position.size, 2)}
                  </p>
                </ConsoleInset>
                <ConsoleInset>
                  <p className="console-kicker">{closed ? "退出" : "标记"}</p>
                  <p className="mt-2 font-semibold text-[color:var(--oa-text)]">
                    {formatNumber((closed ? position.exit_price : position.mark_price) ?? 0)}
                  </p>
                </ConsoleInset>
                <ConsoleInset>
                  <p className="console-kicker">{closed ? "实现 PnL" : "未实现 PnL"}</p>
                  <p
                    className={`mt-2 font-semibold ${
                      pnl > 0
                        ? "text-[color:var(--oa-green)]"
                        : pnl < 0
                          ? "text-[color:var(--oa-red)]"
                          : "text-[color:var(--oa-text)]"
                    }`}
                  >
                    {formatNumber(pnl)}
                  </p>
                </ConsoleInset>
                <ConsoleInset>
                  <p className="console-kicker">{closed ? "原因" : "状态"}</p>
                  <p className="mt-2 font-semibold text-[color:var(--oa-text)]">
                    {closed ? exitReasonLabel(position.exit_reason) : position.market_status ?? "-"}
                  </p>
                </ConsoleInset>
              </div>
            </div>
          </ConsoleInset>
        )
      })}
    </div>
  )
}

export default function PaperTradingPage() {
  const [summary, setSummary] = useState<PaperSummary>(EMPTY_SUMMARY)
  const [openPositions, setOpenPositions] = useState<PaperPosition[]>([])
  const [closedPositions, setClosedPositions] = useState<PaperPosition[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const refresh = async () => {
    setLoading(true)
    setError(null)
    try {
      const [summaryResult, openResult, closedResult] = await Promise.all([
        apiGet<{ summary: PaperSummary }>("/paper-trading/summary"),
        apiGet<{ positions: PaperPosition[] }>("/paper-trading/positions?status=open&limit=100"),
        apiGet<{ positions: PaperPosition[] }>("/paper-trading/positions?status=closed&limit=100"),
      ])
      setSummary(summaryResult.summary)
      setOpenPositions(openResult.positions)
      setClosedPositions(closedResult.positions)
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "加载模拟交易数据失败")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
  }, [])

  const evaluate = async () => {
    setRunning("evaluate")
    setNotice(null)
    setError(null)
    try {
      const result = await apiPost<{ result: { created_count: number; skipped_count: number } }>("/paper-trading/evaluate", {
        limit: 20,
        strategy_version: "paper-noshare-v1",
      })
      setNotice(`已新开 ${result.result.created_count} 个模拟持仓，跳过 ${result.result.skipped_count} 个候选。`)
      await refresh()
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "评估候选失败")
    } finally {
      setRunning(null)
    }
  }

  const mark = async () => {
    setRunning("mark")
    setNotice(null)
    setError(null)
    try {
      const result = await apiPost<{ result: { updated_count: number; closed_count: number } }>("/paper-trading/mark", {
        auto_close: true,
      })
      setNotice(`已更新 ${result.result.updated_count} 个开放持仓，平仓 ${result.result.closed_count} 个。`)
      await refresh()
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "刷新盯市失败")
    } finally {
      setRunning(null)
    }
  }

  return (
    <main className="page-fade-in mx-auto max-w-[1280px] px-4 pb-16 pt-6 md:px-6 lg:px-8">
      <PageIntro
        eyebrow="Paper Trading"
        title="模拟交易验证"
        description="这里直接回答策略有没有被市场价格验证。NetEV 准入候选会转成模拟持仓，后续用最新快照更新 PnL，市场结算后沉淀为已实现收益。"
        stats={[
          { label: "开放持仓", value: String(summary.open_count) },
          { label: "总 PnL", value: formatNumber(summary.total_pnl) },
          { label: "胜率", value: formatPercent(summary.win_rate) },
        ]}
        guides={[
          { title: "先看总 PnL", description: "如果未实现和已实现 PnL 长期为负，先回到 NetEV 阈值和滑点假设。" },
          { title: "再看开放持仓", description: "开放持仓显示当前还在承受价格波动的机会。" },
          { title: "最后看平仓结果", description: "已平仓记录才是策略捕获 edge 的直接证据。" },
        ]}
      />

      {error ? (
        <div className="mb-5 rounded-[22px] border border-[color:rgba(177,63,51,0.24)] bg-[color:rgba(177,63,51,0.1)] p-4 text-sm text-[color:var(--oa-red)]">
          {error}
        </div>
      ) : null}
      {notice ? (
        <div className="mb-5 rounded-[22px] border border-[color:rgba(47,125,81,0.22)] bg-[color:rgba(47,125,81,0.1)] p-4 text-sm text-[color:var(--oa-green)]">
          {notice}
        </div>
      ) : null}

      <ConsoleCallout
        title={summary.total_count > 0 ? "模拟交易闭环已经开始积累证据" : "还没有模拟持仓"}
        description={
          summary.total_count > 0
            ? "继续刷新盯市，观察开放持仓的未实现 PnL；市场结算后再用已实现 PnL 复盘策略质量。"
            : "先把当前 NetEV 准入候选转成模拟持仓，再用快照价格验证这批机会是否真的有收益。"
        }
        tone={summary.total_count > 0 ? pnlTone(summary.total_pnl) : "info"}
        actions={
          <>
            <ConsoleButton type="button" tone="primary" disabled={running !== null} onClick={() => void evaluate()}>
              {running === "evaluate" ? "评估中..." : "评估准入候选"}
            </ConsoleButton>
            <ConsoleButton type="button" disabled={running !== null} onClick={() => void mark()}>
              {running === "mark" ? "刷新中..." : "刷新盯市"}
            </ConsoleButton>
          </>
        }
      />

      <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <ConsoleMetric label="开放持仓" value={loading ? "-" : String(summary.open_count)} tone={summary.open_count > 0 ? "info" : "neutral"} />
        <ConsoleMetric label="已平仓" value={loading ? "-" : String(summary.closed_count)} tone={summary.closed_count > 0 ? "good" : "neutral"} />
        <ConsoleMetric label="未实现 PnL" value={loading ? "-" : formatNumber(summary.unrealized_pnl)} tone={pnlTone(summary.unrealized_pnl)} />
        <ConsoleMetric label="已实现 PnL" value={loading ? "-" : formatNumber(summary.realized_pnl)} tone={pnlTone(summary.realized_pnl)} />
        <ConsoleMetric label="胜率" value={loading ? "-" : formatPercent(summary.win_rate)} tone={summary.win_rate >= 0.5 && summary.closed_count > 0 ? "good" : "neutral"} />
      </section>

      <section className="mt-8 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <ConsolePanel title="开放持仓" description="这些仓位仍在用最新快照标记价格，未实现 PnL 会随盘口变化。">
          {loading ? <p className="text-sm text-[color:var(--oa-muted)]">正在加载开放持仓...</p> : <PositionList positions={openPositions} />}
        </ConsolePanel>
        <ConsolePanel title="已平仓记录" description="这些记录已经有退出价和 realized PnL，更适合用来复盘策略质量。">
          {loading ? (
            <p className="text-sm text-[color:var(--oa-muted)]">正在加载已平仓记录...</p>
          ) : (
            <PositionList positions={closedPositions} closed />
          )}
        </ConsolePanel>
      </section>
    </main>
  )
}
