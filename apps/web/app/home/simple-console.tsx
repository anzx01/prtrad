"use client"

import { useEffect, useMemo, useState } from "react"

import { apiGet, apiPost } from "@/lib/api"

import {
  ConsoleBadge,
  ConsoleButton,
  ConsoleCallout,
  ConsoleInset,
  ConsoleMetric,
  ConsolePanel,
} from "../components/console-ui"
import { PageIntro } from "../components/page-intro"
import {
  LaunchWorkbench,
  type LaunchBacktestRun,
  type LaunchKillSwitchRequest,
  type LaunchReportRecord,
  type LaunchShadowRun,
  type TradingOrderRecord,
  type TradingRuntimeState,
} from "./launch-workbench"
import { MarketWorkbench } from "./market-workbench"

interface MonitoringResponse {
  metrics?: {
    tag_quality?: { open_anomalies?: number }
    dq?: { recent_failures?: number }
  }
}

interface MarketDecisionPreview {
  classification_status: string
  admission_bucket_code: string | null
}

interface MarketPreviewResponse {
  markets: Array<{
    id: string
    latest_classification: MarketDecisionPreview | null
  }>
  total: number
}

interface TradingStateResponse {
  state: TradingRuntimeState
}

interface TradingExecuteResponse {
  state: TradingRuntimeState
  order: TradingOrderRecord
}

interface Snapshot {
  monitoring: MonitoringResponse["metrics"] | null
  markets: MarketPreviewResponse | null
  shadowRuns: LaunchShadowRun[]
  backtests: LaunchBacktestRun[]
  reports: LaunchReportRecord[]
  killSwitches: LaunchKillSwitchRequest[]
  trading: TradingRuntimeState | null
}

function createEmptySnapshot(): Snapshot {
  return {
    monitoring: null,
    markets: null,
    shadowRuns: [],
    backtests: [],
    reports: [],
    killSwitches: [],
    trading: null,
  }
}

function formatDateTime(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString("zh-CN") : "-"
}

function recommendationLabel(value: string | undefined) {
  if (value === "go") return "可继续"
  if (value === "watch") return "继续观察"
  if (value === "block" || value === "nogo") return "先暂停"
  return "等待结果"
}

function tradingStatusLabel(state: TradingRuntimeState | null) {
  if (!state) return "加载中"
  return state.status === "running" ? "运行中" : "已停止"
}

function tradingTone(state: TradingRuntimeState | null) {
  if (!state) return "neutral" as const
  if (state.status === "running" && state.mode === "live") return "good" as const
  if (state.status === "running") return "info" as const
  if (state.last_stop_was_automatic) return "warn" as const
  if (state.paper.ready || state.live.ready) return "info" as const
  return "neutral" as const
}

function buildRunName(prefix: string) {
  const now = new Date()
  const pad = (value: number) => String(value).padStart(2, "0")
  return `${prefix}-${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`
}

function buildPaperTradeMessage(order: TradingOrderRecord, startedNewRun: boolean) {
  if (order.status === "filled") {
    return startedNewRun ? "纸交易已启动，并自动生成了第一笔模拟订单。" : "已按当前最优市场再生成一笔模拟订单。"
  }
  return `纸交易已启动，但这笔模拟订单没有成功：${order.failure_reason_text ?? "请稍后重试。"}`
}

function buildLiveTradeMessage(order: TradingOrderRecord) {
  if (order.status === "live" || order.status === "submitted") {
    return "实盘已启动，第一笔真实订单已经发出。"
  }
  if (order.status === "matched" || order.status === "mined" || order.status === "confirmed") {
    return "实盘已启动，第一笔真实订单已经成交。"
  }
  if (order.status === "cancelled") {
    return "实盘已启动，但挂单在等待后仍未成交，系统已经自动撤单。"
  }
  if (order.status === "failed") {
    return `实盘已启动，但真实订单没有成功：${order.failure_reason_text ?? "请检查资金、授权和私钥配置。"}`
  }
  return "实盘已启动，并已尝试发出第一笔真实订单。"
}

async function loadSnapshot(): Promise<Snapshot> {
  const [monitoring, markets, shadow, backtests, reports, killSwitches, trading] = await Promise.all([
    apiGet<MonitoringResponse>("/monitoring/metrics"),
    apiGet<MarketPreviewResponse>("/markets?page=1&page_size=6&only_allowed=true"),
    apiGet<{ runs: LaunchShadowRun[] }>("/shadow"),
    apiGet<{ runs: LaunchBacktestRun[] }>("/backtests"),
    apiGet<{ reports: LaunchReportRecord[] }>("/reports"),
    apiGet<{ requests: LaunchKillSwitchRequest[] }>("/risk/kill-switch?status=pending"),
    apiGet<TradingStateResponse>("/trading/state"),
  ])

  return {
    monitoring: monitoring.metrics ?? null,
    markets,
    shadowRuns: shadow.runs ?? [],
    backtests: backtests.runs ?? [],
    reports: reports.reports ?? [],
    killSwitches: killSwitches.requests ?? [],
    trading: trading.state ?? null,
  }
}

export function SimpleConsolePage() {
  const [snapshot, setSnapshot] = useState<Snapshot>(createEmptySnapshot())
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = async () => {
    setLoading(true)
    setError(null)
    try {
      setSnapshot(await loadSnapshot())
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "加载单页控制台失败")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
  }, [])

  const latestShadow = snapshot.shadowRuns[0] ?? null
  const latestBacktest = snapshot.backtests[0] ?? null
  const latestReport = snapshot.reports[0] ?? null
  const allowedPreviewCount = snapshot.markets?.markets.length ?? 0

  const overview = useMemo(() => {
    if (snapshot.trading?.status === "running" || snapshot.trading?.last_stop_was_automatic) {
      return {
        tone: tradingTone(snapshot.trading),
        title: snapshot.trading.headline,
        description: snapshot.trading.description,
      }
    }

    if (snapshot.killSwitches.length > 0) {
      return {
        tone: "bad" as const,
        title: "系统已自动暂停推进",
        description: `当前还有 ${snapshot.killSwitches.length} 条待处理的暂停请求，系统会先停住，等风控条件恢复后再继续。`,
      }
    }

    if (latestShadow?.recommendation === "block" || latestBacktest?.recommendation === "nogo") {
      return {
        tone: "warn" as const,
        title: "系统建议先暂停",
        description: "当前至少有一条自动结果不支持继续推进。你只需要看这页给出的结论，不需要再去别的页面自己拼判断。",
      }
    }

    return {
      tone: "good" as const,
      title: "系统处在可继续观察的自动档位",
      description: "市场、数据质量、自动分类和交易开关都已经收在这一页。默认只展示已自动放行的市场，让注意力始终留在真正能继续推进的对象上。",
    }
  }, [latestBacktest?.recommendation, latestShadow?.recommendation, snapshot.killSwitches.length, snapshot.trading])

  const signalDeck = [
    {
      title: "当前交易状态",
      value: tradingStatusLabel(snapshot.trading),
      tone: tradingTone(snapshot.trading),
      note: snapshot.trading?.mode === "live" ? "正在使用实盘闸门" : "当前不是实盘运行",
    },
    {
      title: "待处理暂停请求",
      value: String(snapshot.killSwitches.length),
      tone: snapshot.killSwitches.length > 0 ? ("bad" as const) : ("good" as const),
      note: snapshot.killSwitches.length > 0 ? "有待处理风险动作" : "当前没有待处理暂停",
    },
    {
      title: "最近回测",
      value: recommendationLabel(latestBacktest?.recommendation),
      tone:
        latestBacktest?.recommendation === "go"
          ? ("good" as const)
          : latestBacktest?.recommendation === "watch"
            ? ("warn" as const)
            : latestBacktest?.recommendation
              ? ("bad" as const)
              : ("neutral" as const),
      note: latestBacktest ? latestBacktest.run_name : "等待第一轮结果",
    },
    {
      title: "最近影子验证",
      value: recommendationLabel(latestShadow?.recommendation),
      tone:
        latestShadow?.recommendation === "go"
          ? ("good" as const)
          : latestShadow?.recommendation === "watch"
            ? ("warn" as const)
            : latestShadow?.recommendation
              ? ("bad" as const)
              : ("neutral" as const),
      note: latestShadow ? latestShadow.run_name : "等待第一轮结果",
    },
    {
      title: "最近报告时间",
      value: latestReport ? formatDateTime(latestReport.generated_at) : "暂无",
      tone: latestReport ? ("info" as const) : ("neutral" as const),
      note: latestReport ? latestReport.report_type : "尚未生成",
    },
  ]

  const actionCards = [
    {
      key: "refreshPack",
      title: "刷新整套证据",
      description: "按顺序重算暴露、校准、回测、影子验证与报告，适合你想把系统重新拉回最新状态时使用。",
      buttonLabel: running === "refreshPack" ? "执行中..." : "刷新自动证据包",
      tone: "primary" as const,
    },
    {
      key: "runShadow",
      title: "只重跑影子验证",
      description: "不动整套链路，只重新演练一轮影子运行，适合验证策略动作是否仍然稳定。",
      buttonLabel: running === "runShadow" ? "执行中..." : "仅重跑影子",
      tone: "default" as const,
    },
    {
      key: "generateReports",
      title: "只更新报告",
      description: "当你只想看新的摘要和周报，而不想重新跑重型任务时，用这一项最快。",
      buttonLabel: running === "generateReports" ? "执行中..." : "重新生成报告",
      tone: "default" as const,
    },
  ]

  const coreMetrics = [
    {
      label: "可用市场总数",
      value: String(snapshot.markets?.total ?? 0),
      tone: (snapshot.markets?.total ?? 0) > 0 ? ("good" as const) : ("neutral" as const),
      hint: "系统已先过滤拦截项",
    },
    {
      label: "首屏可用市场",
      value: String(allowedPreviewCount),
      tone: allowedPreviewCount > 0 ? ("good" as const) : ("neutral" as const),
      hint: "当前页面直接能看的数量",
    },
    {
      label: "交易状态",
      value: tradingStatusLabel(snapshot.trading),
      tone: tradingTone(snapshot.trading),
      hint: snapshot.trading?.mode === "live" ? "实盘闸门" : "纸交易或停止中",
    },
    {
      label: "最近 DQ 异常",
      value: String(snapshot.monitoring?.dq?.recent_failures ?? 0),
      tone: (snapshot.monitoring?.dq?.recent_failures ?? 0) > 0 ? ("bad" as const) : ("good" as const),
      hint: "越低越省心",
    },
  ]

  const handleAction = async (action: "refreshPack" | "runShadow" | "generateReports") => {
    setRunning(action)
    setError(null)
    setMessage(null)

    try {
      if (action === "refreshPack") {
        await apiPost("/risk/exposures/compute")
        await apiPost("/calibration/recompute-all?window_type=long")
        await apiPost("/backtests/run", {
          run_name: buildRunName("auto-backtest"),
          window_days: 30,
          executed_by: "console_autopilot",
          strategy_version: "baseline-v1",
        })
        await apiPost("/shadow/execute", {
          run_name: buildRunName("auto-shadow"),
          executed_by: "console_autopilot",
        })
        await apiPost("/reports/generate", { report_type: "daily_summary", generated_by: "console_autopilot" })
        await apiPost("/reports/generate", { report_type: "weekly_summary", generated_by: "console_autopilot" })
        setMessage("自动证据包已刷新完成。")
      } else if (action === "runShadow") {
        await apiPost("/shadow/execute", {
          run_name: buildRunName("auto-shadow"),
          executed_by: "console_autopilot",
        })
        setMessage("新的影子运行已触发。")
      } else {
        await apiPost("/reports/generate", { report_type: "daily_summary", generated_by: "console_autopilot" })
        await apiPost("/reports/generate", { report_type: "weekly_summary", generated_by: "console_autopilot" })
        setMessage("报告已重新生成。")
      }

      await refresh()
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "自动动作执行失败")
    } finally {
      setRunning(null)
    }
  }

  const handleTradingAction = async (action: "startPaper" | "startLive" | "stopTrading") => {
    setRunning(action)
    setError(null)
    setMessage(null)

    try {
      if (action === "startPaper") {
        const paperAlreadyRunning = snapshot.trading?.status === "running" && snapshot.trading.mode === "paper"
        if (!paperAlreadyRunning) {
          await apiPost("/trading/start", {
            mode: "paper",
            actor_id: "console_autopilot",
          })
        }
        const executeResult = await apiPost<TradingExecuteResponse>("/trading/execute-next", {
          actor_id: "console_autopilot",
        })
        setMessage(buildPaperTradeMessage(executeResult.order, !paperAlreadyRunning))
      } else if (action === "startLive") {
        await apiPost("/trading/start", {
          mode: "live",
          actor_id: "console_autopilot",
        })
        const executeResult = await apiPost<TradingExecuteResponse>("/trading/execute-next", {
          actor_id: "console_autopilot",
        })
        setMessage(buildLiveTradeMessage(executeResult.order))
      } else {
        await apiPost("/trading/stop", {
          actor_id: "console_autopilot",
          reason: "控制台手动停止",
        })
        setMessage("交易已经停止。")
      }

      await refresh()
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "交易控制执行失败")
    } finally {
      setRunning(null)
    }
  }

  return (
    <main className="page-fade-in mx-auto max-w-[1280px] px-4 pb-16 pt-6 md:px-6 lg:px-8">
      <PageIntro
        eyebrow="Auto Console"
        title="一页接管现在的判断、动作和交易"
        description="这不是开发者后台，而是给你看的自动驾驶舱。系统先替你过滤掉不能继续的对象，再把真正需要你点的动作和能直接关注的市场摆到前面。"
        stats={[
          { label: "入口页面", value: "1 个" },
          { label: "自动方式", value: "默认全自动" },
          { label: "当前可用市场", value: String(snapshot.markets?.total ?? 0) },
        ]}
        guides={[
          { title: "先看系统总判断", description: "先确认系统现在是继续、观察还是暂停，不必先研究内部缩写。" },
          { title: "再点自动动作", description: "如果你想更新状态，只点本页按钮。系统会替你跑完整顺序，不需要多页跳转。" },
          { title: "最后看市场和交易", description: "当系统已经放行市场，再去看市场卡片和交易闸门，注意力不会被拦截项打散。" },
        ]}
      />

      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <ConsoleCallout
          eyebrow="系统总判断"
          title={overview.title}
          description={overview.description}
          tone={overview.tone}
        />

        <ConsolePanel title="即时信号" description="这 5 个信号足够你快速判断系统目前卡在哪。">
          <div className="grid gap-3">
            {signalDeck.map((item) => (
              <ConsoleInset key={item.title} className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--oa-muted)]">{item.title}</p>
                  <p className="mt-2 text-sm leading-6 text-[color:var(--oa-muted)]">{item.note}</p>
                </div>
                <ConsoleBadge label={item.value} tone={item.tone} className="shrink-0" />
              </ConsoleInset>
            ))}
          </div>
        </ConsolePanel>
      </section>

      {message ? (
        <div className="mt-4">
          <ConsoleCallout eyebrow="动作反馈" title="最新动作已完成" description={message} tone="good" />
        </div>
      ) : null}
      {error ? (
        <div className="mt-4">
          <ConsoleCallout eyebrow="需要处理" title="这一步没有成功" description={error} tone="bad" />
        </div>
      ) : null}

      <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {coreMetrics.map((item) => (
          <ConsoleMetric key={item.label} label={item.label} value={item.value} tone={item.tone} hint={item.hint} />
        ))}
      </section>

      <section id="actions" className="mt-8 grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
        <ConsolePanel
          title="自动动作"
          description="按钮刻意不多，只保留真正会影响整体状态的 3 个动作。需要更新时，系统会自己跑顺序。"
        >
          <div className="grid gap-4 lg:grid-cols-3">
            {actionCards.map((item) => (
              <ConsoleInset key={item.key} className="flex h-full flex-col justify-between gap-5">
                <div>
                  <p className="text-lg font-semibold tracking-tight text-[color:var(--oa-text)] [font-family:var(--oa-font-display)]">
                    {item.title}
                  </p>
                  <p className="mt-3 text-sm leading-7 text-[color:var(--oa-muted)]">{item.description}</p>
                </div>
                <ConsoleButton
                  tone={item.tone}
                  onClick={() => void handleAction(item.key as "refreshPack" | "runShadow" | "generateReports")}
                  disabled={Boolean(running)}
                  className="w-full justify-center"
                >
                  {item.buttonLabel}
                </ConsoleButton>
              </ConsoleInset>
            ))}
          </div>

          <ConsoleInset className="mt-5">
            <div className="flex flex-wrap items-center gap-2">
              <ConsoleBadge label="自动顺序" tone="info" />
              <span className="text-sm text-[color:var(--oa-muted)]">
                风险暴露 → 校准 → 回测 → 影子验证 → 报告
              </span>
            </div>
            <p className="mt-3 text-sm leading-7 text-[color:var(--oa-muted)]">
              你不需要记内部链路，系统已经把动作顺序固定好了。想要“全量刷新”就点第一项，只想快速看结果则用后两项。
            </p>
          </ConsoleInset>
        </ConsolePanel>

        <ConsolePanel title="本页使用顺序" description="如果你完全不想研究术语，就按这个顺序看。">
          <div className="space-y-3">
            {[
              { title: "先扫总判断", description: "确认系统现在是继续、观察还是暂停。" },
              { title: "再决定要不要刷新", description: "需要更新证据链时，只点一个自动动作按钮。" },
              { title: "最后看市场和交易", description: "确认已放行市场，再决定是否打开纸交易或实盘。" },
            ].map((item, index) => (
              <ConsoleInset key={item.title}>
                <div className="flex items-start gap-3">
                  <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-[color:rgba(181,72,47,0.16)] bg-[color:rgba(181,72,47,0.08)] text-sm font-semibold text-[color:var(--oa-accent-strong)]">
                    {index + 1}
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-[color:var(--oa-text)]">{item.title}</p>
                    <p className="mt-1 text-sm leading-6 text-[color:var(--oa-muted)]">{item.description}</p>
                  </div>
                </div>
              </ConsoleInset>
            ))}
          </div>
        </ConsolePanel>
      </section>

      <div className="mt-8">
        <MarketWorkbench />
      </div>

      <div className="mt-8">
        <LaunchWorkbench
          loading={loading}
          shadowRuns={snapshot.shadowRuns}
          backtests={snapshot.backtests}
          killSwitches={snapshot.killSwitches}
          reports={snapshot.reports}
          tradingState={snapshot.trading}
          tradingBusy={running === "startPaper" || running === "startLive" || running === "stopTrading"}
          onStartPaper={() => void handleTradingAction("startPaper")}
          onStartLive={() => void handleTradingAction("startLive")}
          onStopTrading={() => void handleTradingAction("stopTrading")}
        />
      </div>
    </main>
  )
}
