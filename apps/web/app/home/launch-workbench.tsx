"use client"

import {
  ConsoleBadge,
  ConsoleButton,
  ConsoleCallout,
  ConsoleEmpty,
  ConsoleInset,
  ConsoleMetric,
  ConsolePanel,
} from "../components/console-ui"

export interface LaunchShadowRun {
  id: string
  run_name: string
  recommendation: "go" | "watch" | "block"
  risk_state: string
  created_at: string
}

export interface LaunchBacktestRun {
  id: string
  run_name: string
  recommendation: "go" | "watch" | "nogo"
  created_at: string
}

export interface LaunchKillSwitchRequest {
  id: string
  reason: string
  created_at: string
}

export interface LaunchReportRecord {
  id: string
  report_type: string
  generated_at: string
}

export interface TradingBlocker {
  code: string
  message: string
}

export interface TradingModeGuard {
  ready: boolean
  blockers: TradingBlocker[]
}

export interface TradingOrderRecord {
  id: string
  mode: "paper" | "live"
  status: string
  provider: string
  market_id: string
  question: string
  outcome_side: string
  price: number | null
  size: number | null
  notional: number | null
  net_ev: number | null
  requested_by: string | null
  provider_order_id: string | null
  failure_reason_code: string | null
  failure_reason_text: string | null
  created_at: string | null
  completed_at: string | null
}

export interface TradingRuntimeState {
  id: string
  status: "running" | "stopped"
  mode: "paper" | "live"
  started_by: string | null
  stopped_by: string | null
  last_started_at: string | null
  last_stopped_at: string | null
  last_stop_reason_code: string | null
  last_stop_reason_text: string | null
  last_stop_was_automatic: boolean
  paper: TradingModeGuard
  live: TradingModeGuard
  executable_market_count: number
  executable_markets: Array<{
    market_id: string
    question: string
    net_ev: number
    price: number
  }>
  latest_backtest: {
    id: string
    run_name: string
    recommendation: string
    created_at: string | null
  } | null
  latest_shadow: {
    id: string
    run_name: string
    recommendation: string
    risk_state: string | null
    created_at: string | null
  } | null
  risk_state: string
  pending_kill_switch_count: number
  live_mode_enabled: boolean
  headline: string
  description: string
  latest_order: TradingOrderRecord | null
  updated_at: string | null
}

function formatDateTime(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString("zh-CN") : "-"
}

function formatNumber(value: number | null | undefined, digits = 3) {
  return typeof value === "number" ? value.toFixed(digits) : "-"
}

function recommendationLabel(value: string | undefined) {
  if (value === "go") return "可继续"
  if (value === "watch") return "继续观察"
  if (value === "block" || value === "nogo") return "先暂停"
  return "等待结果"
}

function toneFromRecommendation(value: string | undefined) {
  if (value === "go") return "good" as const
  if (value === "watch") return "warn" as const
  if (value === "block" || value === "nogo") return "bad" as const
  return "neutral" as const
}

function tradingModeLabel(value: string | undefined) {
  if (value === "live") return "实盘闸门"
  if (value === "paper") return "纸交易"
  return "未选择"
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

function tradingBlockers(state: TradingRuntimeState | null) {
  if (!state) return []
  if (state.last_stop_was_automatic && state.last_stop_reason_text) {
    return [state.last_stop_reason_text]
  }
  if (!state.paper.ready) {
    return state.paper.blockers.map((item) => item.message)
  }
  if (!state.live.ready) {
    return state.live.blockers.map((item) => item.message)
  }
  return []
}

function orderStatusLabel(value: string | undefined) {
  if (value === "filled") return "已模拟成交"
  if (value === "failed") return "未成功"
  if (value === "submitted") return "已提交"
  if (value === "live") return "已挂单"
  if (value === "cancelled") return "已自动撤单"
  if (value === "matched" || value === "mined" || value === "confirmed") return "已成交"
  if (value === "pending") return "执行中"
  return "等待结果"
}

function orderTone(value: string | undefined) {
  if (value === "matched" || value === "mined" || value === "confirmed") return "good" as const
  if (value === "filled") return "good" as const
  if (value === "failed") return "bad" as const
  if (value === "cancelled") return "warn" as const
  if (value === "live") return "info" as const
  if (value === "submitted" || value === "pending") return "warn" as const
  return "neutral" as const
}

function launchSummary({
  tradingState,
  killSwitches,
  latestShadow,
  latestBacktest,
}: {
  tradingState: TradingRuntimeState | null
  killSwitches: LaunchKillSwitchRequest[]
  latestShadow: LaunchShadowRun | null
  latestBacktest: LaunchBacktestRun | null
}) {
  if (tradingState) {
    return {
      tone: tradingTone(tradingState),
      title: tradingState.headline,
      description: tradingState.description,
    }
  }

  if (killSwitches.length > 0) {
    return {
      tone: "bad" as const,
      title: "自动上线已暂停",
      description: `当前还有 ${killSwitches.length} 条待处理的暂停请求，系统会先停住。`,
    }
  }

  if (latestShadow?.recommendation === "block") {
    return {
      tone: "bad" as const,
      title: "影子验证建议暂停",
      description: "最新影子验证已经明确拦下当前推进动作，先不要继续。",
    }
  }

  if (latestBacktest?.recommendation === "nogo") {
    return {
      tone: "warn" as const,
      title: "回测结果偏保守",
      description: "最新回测不支持继续推进，系统会保持暂停，直到下一轮自动结果更新。",
    }
  }

  return {
    tone: "good" as const,
    title: "交易闸门处在可用档位",
    description: "系统会根据影子验证、回测和风控开关结果，自动决定继续推进还是暂停。",
  }
}

export function LaunchWorkbench({
  loading,
  shadowRuns,
  backtests,
  killSwitches,
  reports,
  tradingState,
  tradingBusy,
  onStartPaper,
  onStartLive,
  onStopTrading,
}: {
  loading: boolean
  shadowRuns: LaunchShadowRun[]
  backtests: LaunchBacktestRun[]
  killSwitches: LaunchKillSwitchRequest[]
  reports: LaunchReportRecord[]
  tradingState: TradingRuntimeState | null
  tradingBusy: boolean
  onStartPaper: () => void
  onStartLive: () => void
  onStopTrading: () => void
}) {
  const latestShadow = shadowRuns[0] ?? null
  const latestBacktest = backtests[0] ?? null
  const latestReport = reports[0] ?? null
  const summary = launchSummary({ tradingState, killSwitches, latestShadow, latestBacktest })
  const blockers = tradingBlockers(tradingState)
  const latestOrder = tradingState?.latest_order ?? null
  const paperActionLabel =
    tradingBusy
      ? "执行中..."
      : tradingState?.status === "running" && tradingState.mode === "paper"
        ? "再跑一笔纸交易"
        : "开始纸交易"

  const gateMetrics = [
    {
      label: "交易状态",
      value: tradingStatusLabel(tradingState),
      tone: tradingTone(tradingState),
      hint: tradingState?.status === "running" ? "系统正在自动执行" : "当前未在运行",
    },
    {
      label: "当前模式",
      value: tradingModeLabel(tradingState?.mode),
      tone: tradingState?.mode === "live" && tradingState?.status === "running" ? ("good" as const) : ("info" as const),
      hint: tradingState?.mode === "live" ? "真实闸门" : "模拟档位",
    },
    {
      label: "影子验证",
      value: recommendationLabel(latestShadow?.recommendation),
      tone: toneFromRecommendation(latestShadow?.recommendation),
      hint: latestShadow ? latestShadow.run_name : "等待结果",
    },
    {
      label: "回测结论",
      value: recommendationLabel(latestBacktest?.recommendation),
      tone: toneFromRecommendation(latestBacktest?.recommendation),
      hint: latestBacktest ? latestBacktest.run_name : "等待结果",
    },
  ]

  return (
    <section id="launch" className="space-y-6">
      <ConsoleCallout
        eyebrow="交易闸门"
        title={summary.title}
        description={summary.description}
        tone={summary.tone}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {gateMetrics.map((item) => (
          <ConsoleMetric key={item.label} label={item.label} value={item.value} tone={item.tone} hint={item.hint} />
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <ConsolePanel
          title="自动发单"
          description="这里只保留 3 个动作：开始纸交易、开始实盘、立即停止。系统会自动检查前置条件，不需要你再自己拼 Go/NoGo。"
        >
          <div className="grid gap-4 md:grid-cols-3">
            <ConsoleInset className="flex h-full flex-col justify-between gap-5">
              <div>
                <p className="text-lg font-semibold text-[color:var(--oa-text)] [font-family:var(--oa-font-display)]">
                  纸交易
                </p>
                <p className="mt-3 text-sm leading-7 text-[color:var(--oa-muted)]">
                  适合先确认链路闭环。系统会自动挑一个可执行市场，生成一笔模拟订单。
                </p>
              </div>
              <ConsoleButton
                tone="primary"
                onClick={onStartPaper}
                disabled={loading || tradingBusy || (!tradingState?.paper.ready && !(tradingState?.status === "running" && tradingState.mode === "paper"))}
                className="w-full justify-center"
              >
                {paperActionLabel}
              </ConsoleButton>
            </ConsoleInset>

            <ConsoleInset className="flex h-full flex-col justify-between gap-5">
              <div>
                <p className="text-lg font-semibold text-[color:var(--oa-text)] [font-family:var(--oa-font-display)]">
                  实盘
                </p>
                <p className="mt-3 text-sm leading-7 text-[color:var(--oa-muted)]">
                  适合前置条件都已经满足时。系统会按资金比例自动算下单额，并在超时后自动撤单。
                </p>
              </div>
              <ConsoleButton
                tone="success"
                onClick={onStartLive}
                disabled={loading || tradingBusy || !tradingState?.live.ready || (tradingState?.status === "running" && tradingState.mode === "live")}
                className="w-full justify-center"
              >
                {tradingBusy ? "执行中..." : tradingState?.status === "running" && tradingState.mode === "live" ? "实盘闸门已开启" : "开始实盘"}
              </ConsoleButton>
            </ConsoleInset>

            <ConsoleInset className="flex h-full flex-col justify-between gap-5">
              <div>
                <p className="text-lg font-semibold text-[color:var(--oa-text)] [font-family:var(--oa-font-display)]">
                  立即停止
                </p>
                <p className="mt-3 text-sm leading-7 text-[color:var(--oa-muted)]">
                  当你想立刻停住交易链路时，用这个按钮。系统会记录最后一次停机原因，方便回看。
                </p>
              </div>
              <ConsoleButton
                tone="danger"
                onClick={onStopTrading}
                disabled={loading || tradingBusy || tradingState?.status !== "running"}
                className="w-full justify-center"
              >
                {tradingBusy ? "执行中..." : "立即停止"}
              </ConsoleButton>
            </ConsoleInset>
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-[0.96fr_1.04fr]">
            {latestOrder ? (
              <ConsoleInset className="h-full">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--oa-muted)]">最近一笔结果</p>
                    <p className="mt-2 text-lg font-semibold text-[color:var(--oa-text)] [font-family:var(--oa-font-display)]">
                      {latestOrder.market_id}
                    </p>
                  </div>
                  <ConsoleBadge label={orderStatusLabel(latestOrder.status)} tone={orderTone(latestOrder.status)} />
                </div>
                <p className="mt-3 text-sm leading-7 text-[color:var(--oa-muted)]">{latestOrder.question}</p>

                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  <div className="rounded-[18px] border border-[color:rgba(91,68,48,0.1)] bg-[rgba(255,255,255,0.62)] p-3">
                    <p className="text-[11px] uppercase tracking-[0.16em] text-[color:var(--oa-muted)]">价格</p>
                    <p className="mt-2 text-sm text-[color:var(--oa-text)]">{formatNumber(latestOrder.price, 3)}</p>
                  </div>
                  <div className="rounded-[18px] border border-[color:rgba(91,68,48,0.1)] bg-[rgba(255,255,255,0.62)] p-3">
                    <p className="text-[11px] uppercase tracking-[0.16em] text-[color:var(--oa-muted)]">数量</p>
                    <p className="mt-2 text-sm text-[color:var(--oa-text)]">{formatNumber(latestOrder.size, 2)}</p>
                  </div>
                  <div className="rounded-[18px] border border-[color:rgba(91,68,48,0.1)] bg-[rgba(255,255,255,0.62)] p-3">
                    <p className="text-[11px] uppercase tracking-[0.16em] text-[color:var(--oa-muted)]">金额</p>
                    <p className="mt-2 text-sm text-[color:var(--oa-text)]">{formatNumber(latestOrder.notional, 3)}</p>
                  </div>
                </div>

                <p className="mt-4 text-xs leading-6 text-[color:var(--oa-muted)]">
                  {latestOrder.failure_reason_text
                    ? `失败原因：${latestOrder.failure_reason_text}`
                    : `完成时间：${formatDateTime(latestOrder.completed_at ?? latestOrder.created_at)}`}
                </p>
              </ConsoleInset>
            ) : (
              <ConsoleEmpty title="还没有交易记录" description="开始纸交易或实盘后，这里会自动展示最近一笔订单的结果。" />
            )}

            <ConsoleInset className="h-full">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--oa-muted)]">当前可执行市场</p>
                  <p className="mt-2 text-lg font-semibold text-[color:var(--oa-text)] [font-family:var(--oa-font-display)]">
                    {tradingState?.executable_market_count ?? 0} 个
                  </p>
                </div>
                <ConsoleBadge label={tradingState?.risk_state ?? "-"} tone={tradingState?.risk_state === "Normal" ? "good" : "warn"} />
              </div>

              <p className="mt-3 text-sm leading-7 text-[color:var(--oa-muted)]">
                这里只统计已经自动放行、DQ 通过、价格可用且能直接试跑的市场。
              </p>

              <div className="mt-4 space-y-3">
                {tradingState?.executable_markets.length ? (
                  tradingState.executable_markets.slice(0, 3).map((item) => (
                    <div
                      key={item.market_id}
                      className="rounded-[18px] border border-[color:rgba(91,68,48,0.1)] bg-[rgba(255,255,255,0.62)] p-3"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <span className="text-sm font-semibold text-[color:var(--oa-text)]">{item.market_id}</span>
                        <div className="flex flex-wrap gap-2">
                          <ConsoleBadge label={`价格 ${item.price.toFixed(3)}`} tone="info" />
                          <ConsoleBadge label={`NetEV ${item.net_ev.toFixed(4)}`} tone="good" />
                        </div>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-[color:var(--oa-muted)]">{item.question}</p>
                    </div>
                  ))
                ) : (
                  <ConsoleEmpty title="当前还没有可执行市场" description="先刷新自动证据包，等系统形成新的可执行市场后再启动交易。" />
                )}
              </div>
            </ConsoleInset>
          </div>
        </ConsolePanel>

        <ConsolePanel title="系统拦截项" description="这里只保留真正会让系统停住的因素，不再堆一整页内部字段。">
          {loading ? <div className="py-12 text-center text-sm text-[color:var(--oa-muted)]">正在加载交易状态...</div> : null}

          {!loading && blockers.length === 0 ? (
            <ConsoleEmpty
              title="当前没有明显拦截项"
              description="如果需要继续观察，可以先开纸交易；如果实盘按钮可用，说明当前前置条件也已经基本满足。"
            />
          ) : null}

          {!loading && blockers.length > 0 ? (
            <div className="space-y-3">
              {blockers.map((blocker, index) => (
                <ConsoleInset key={blocker}>
                  <div className="flex items-start gap-3">
                    <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-[color:rgba(177,63,51,0.16)] bg-[color:rgba(177,63,51,0.08)] text-sm font-semibold text-[color:var(--oa-red)]">
                      {index + 1}
                    </span>
                    <p className="text-sm leading-7 text-[color:var(--oa-text)]">{blocker}</p>
                  </div>
                </ConsoleInset>
              ))}
            </div>
          ) : null}

          <div className="mt-5 grid gap-3">
            <ConsoleInset>待处理暂停请求：{tradingState?.pending_kill_switch_count ?? killSwitches.length}</ConsoleInset>
            <ConsoleInset>最近影子验证：{recommendationLabel(latestShadow?.recommendation)}</ConsoleInset>
            <ConsoleInset>最近回测结论：{recommendationLabel(latestBacktest?.recommendation)}</ConsoleInset>
            <ConsoleInset>最近报告时间：{latestReport ? formatDateTime(latestReport.generated_at) : "-"}</ConsoleInset>
            <ConsoleInset>最近停机原因：{tradingState?.last_stop_reason_text ?? "暂无"}</ConsoleInset>
          </div>
        </ConsolePanel>
      </div>

      <ConsolePanel title="最近自动结果" description="这里只保留交易真正会用到的 3 类自动结果：影子验证、回测、报告。">
        {!loading && !latestShadow && !latestBacktest && !latestReport ? (
          <ConsoleEmpty title="还没有可展示的自动结果" description="先在上面的自动动作里刷新证据链，这里就会自动更新。" />
        ) : null}

        <div className="grid gap-4 lg:grid-cols-3">
          {latestShadow ? (
            <ConsoleInset>
              <div className="flex items-center justify-between gap-3">
                <p className="text-base font-semibold text-[color:var(--oa-text)] [font-family:var(--oa-font-display)]">
                  影子验证
                </p>
                <ConsoleBadge
                  label={recommendationLabel(latestShadow.recommendation)}
                  tone={toneFromRecommendation(latestShadow.recommendation)}
                />
              </div>
              <p className="mt-3 text-sm leading-7 text-[color:var(--oa-text)]">{latestShadow.run_name}</p>
              <p className="mt-2 text-xs leading-6 text-[color:var(--oa-muted)]">
                风险状态：{latestShadow.risk_state} / {formatDateTime(latestShadow.created_at)}
              </p>
            </ConsoleInset>
          ) : null}

          {latestBacktest ? (
            <ConsoleInset>
              <div className="flex items-center justify-between gap-3">
                <p className="text-base font-semibold text-[color:var(--oa-text)] [font-family:var(--oa-font-display)]">
                  回测结论
                </p>
                <ConsoleBadge
                  label={recommendationLabel(latestBacktest.recommendation)}
                  tone={toneFromRecommendation(latestBacktest.recommendation)}
                />
              </div>
              <p className="mt-3 text-sm leading-7 text-[color:var(--oa-text)]">{latestBacktest.run_name}</p>
              <p className="mt-2 text-xs leading-6 text-[color:var(--oa-muted)]">{formatDateTime(latestBacktest.created_at)}</p>
            </ConsoleInset>
          ) : null}

          {latestReport ? (
            <ConsoleInset>
              <p className="text-base font-semibold text-[color:var(--oa-text)] [font-family:var(--oa-font-display)]">
                最近报告
              </p>
              <p className="mt-3 text-sm leading-7 text-[color:var(--oa-text)]">{latestReport.report_type}</p>
              <p className="mt-2 text-xs leading-6 text-[color:var(--oa-muted)]">{formatDateTime(latestReport.generated_at)}</p>
            </ConsoleInset>
          ) : null}
        </div>
      </ConsolePanel>
    </section>
  )
}
