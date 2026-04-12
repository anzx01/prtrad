import Link from "next/link"

import {
  ConsoleBadge,
  ConsoleButton,
  ConsoleCallout,
  ConsoleInset,
  ConsolePanel,
} from "../components/console-ui"
import type { ActionId, DashboardSnapshot, DashboardSummary, DashboardTone } from "./types"

export const RESOURCE_LABELS: Record<string, string> = {
  monitoring: "系统监控",
  dq: "DQ 摘要",
  reviewQueue: "Review Queue",
  riskState: "风险状态",
  exposures: "风险暴露",
  killSwitches: "Kill-switch",
  calibration: "校准单元",
  backtests: "回测",
  shadowRuns: "影子运行",
  launchReviews: "上线评审",
  reports: "报告归档",
}

export function toneToButton(tone: DashboardTone) {
  if (tone === "bad") {
    return "danger" as const
  }
  if (tone === "good") {
    return "success" as const
  }
  if (tone === "info") {
    return "primary" as const
  }
  return "default" as const
}

export function toneToClass(tone: DashboardTone) {
  if (tone === "bad") {
    return "border-[#f85149]/35 bg-[#da3633]/12"
  }
  if (tone === "good") {
    return "border-[#3fb950]/35 bg-[#238636]/12"
  }
  if (tone === "warn") {
    return "border-[#d29922]/35 bg-[#9e6a03]/15"
  }
  if (tone === "info") {
    return "border-[#58a6ff]/35 bg-[#1f6feb]/10"
  }
  return "border-[#30363d] bg-[#161b22]"
}

export function HeadlineSection({
  summary,
  refreshing,
  runningActionId,
  onRefresh,
  onAction,
}: {
  summary: DashboardSummary
  refreshing: boolean
  runningActionId: ActionId | null
  onRefresh: () => void
  onAction: (actionId: ActionId) => void
}) {
  return (
    <section className={`relative overflow-hidden rounded-2xl border px-5 py-5 ${toneToClass(summary.headline.tone)}`}>
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(88,166,255,0.18),transparent_32%),radial-gradient(circle_at_bottom_left,rgba(63,185,80,0.08),transparent_28%)]" />
      <div className="relative flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-4xl">
          <p className="text-[11px] uppercase tracking-[0.2em] text-[#8b949e]">系统当前判断</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-[#e6edf3]">
            {summary.headline.title}
          </h1>
          <p className="mt-3 text-sm leading-7 text-[#c9d1d9]">{summary.headline.description}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <ConsoleButton
            type="button"
            tone="primary"
            disabled={refreshing || runningActionId !== null}
            onClick={() => onAction("refreshEvidencePack")}
          >
            {runningActionId === "refreshEvidencePack" ? "执行中..." : "一键刷新证据包"}
          </ConsoleButton>
          <ConsoleButton
            type="button"
            disabled={refreshing || runningActionId !== null}
            onClick={onRefresh}
          >
            {refreshing ? "刷新中..." : "刷新看板"}
          </ConsoleButton>
        </div>
      </div>
    </section>
  )
}

export function ResourceErrorsCallout({
  snapshot,
  refreshing,
  runningActionId,
  onRefresh,
}: {
  snapshot: DashboardSnapshot
  refreshing: boolean
  runningActionId: ActionId | null
  onRefresh: () => void
}) {
  const resourceErrors = Object.entries(snapshot.errors)
  if (resourceErrors.length === 0) {
    return null
  }

  return (
    <ConsoleCallout
      eyebrow="部分数据缺失"
      title="有些接口这次没拿到，但首页仍会尽量给出可用判断"
      description={resourceErrors
        .map(([key, message]) => `${RESOURCE_LABELS[key] ?? key}：${message}`)
        .join("；")}
      tone="warn"
      actions={
        <ConsoleButton
          type="button"
          onClick={onRefresh}
          disabled={refreshing || runningActionId !== null}
        >
          重试读取
        </ConsoleButton>
      }
    />
  )
}

export function StorySection({
  summary,
  refreshing,
  runningActionId,
  onAction,
}: {
  summary: DashboardSummary
  refreshing: boolean
  runningActionId: ActionId | null
  onAction: (actionId: ActionId) => void
}) {
  return (
    <section className="mt-6 grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
      <ConsolePanel title="系统在想什么" description="这几条不是原始指标堆砌，而是系统根据当前数据自动整理出的可读结论。">
        <div className="space-y-3">
          {summary.narratives.map((item) => (
            <article key={item.id} className={`rounded-xl border p-4 ${toneToClass(item.tone)}`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-[#e6edf3]">{item.title}</p>
                  <p className="mt-2 text-sm leading-6 text-[#c9d1d9]">{item.body}</p>
                </div>
                {item.href ? (
                  <Link href={item.href} className="rounded-lg border border-[#30363d] px-3 py-2 text-sm text-[#e6edf3] transition hover:border-[#58a6ff]/40 hover:bg-[#21262d]">
                    去细页
                  </Link>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      </ConsolePanel>

      <ConsolePanel title="下一步建议" description="系统只把最值得现在做的动作推到前面，避免你自己去拼顺序。">
        <div className="space-y-3">
          {summary.nextActions.map((action) => (
            <article key={action.id} className={`rounded-xl border p-4 ${toneToClass(action.tone)}`}>
              <p className="text-sm font-medium text-[#e6edf3]">{action.title}</p>
              <p className="mt-2 text-sm leading-6 text-[#c9d1d9]">{action.body}</p>
              <div className="mt-4">
                {action.href ? (
                  <Link href={action.href} className="inline-flex rounded-lg border border-[#30363d] px-3 py-2 text-sm text-[#e6edf3] transition hover:border-[#58a6ff]/40 hover:bg-[#21262d]">
                    {action.cta}
                  </Link>
                ) : action.actionId ? (
                  <ConsoleButton
                    type="button"
                    tone={toneToButton(action.tone)}
                    disabled={refreshing || runningActionId !== null}
                    onClick={() => onAction(action.actionId!)}
                  >
                    {runningActionId === action.actionId ? "执行中..." : action.cta}
                  </ConsoleButton>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      </ConsolePanel>
    </section>
  )
}

export function WorkflowSection({
  summary,
  refreshing,
  runningActionId,
  onAction,
}: {
  summary: DashboardSummary
  refreshing: boolean
  runningActionId: ActionId | null
  onAction: (actionId: ActionId) => void
}) {
  return (
    <section className="mt-6 grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
      <ConsolePanel title="主链路状态" description="把整个项目拆成更容易理解的 6 个工作段，你不用自己再脑补它们怎么串。">
        <div className="grid gap-3 md:grid-cols-2">
          {summary.workflows.map((item) => (
            <Link key={item.id} href={item.href} className={`rounded-xl border p-4 transition hover:border-[#58a6ff]/35 hover:bg-[#21262d] ${toneToClass(item.tone)}`}>
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium text-[#e6edf3]">{item.label}</p>
                <ConsoleBadge
                  label={item.status}
                  tone={item.tone === "bad" ? "bad" : item.tone === "good" ? "good" : item.tone === "warn" ? "warn" : "info"}
                />
              </div>
              <p className="mt-3 text-sm leading-6 text-[#c9d1d9]">{item.detail}</p>
            </Link>
          ))}
        </div>
      </ConsolePanel>

      <ConsolePanel title="M4 / M5 / M6 一眼看懂" description="阶段评审不该是一堆散落的 JSON。这里直接告诉你缺、旧、还是已通过。">
        <div className="space-y-3">
          {summary.stages.map((stage) => (
            <ConsoleInset key={stage.stage} className={`border ${toneToClass(stage.tone)}`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-[11px] uppercase tracking-[0.18em] text-[#8b949e]">{stage.stage}</p>
                  <p className="mt-2 text-sm font-medium text-[#e6edf3]">{stage.title}</p>
                  <p className="mt-2 text-sm leading-6 text-[#c9d1d9]">{stage.detail}</p>
                </div>
                <ConsoleButton
                  type="button"
                  size="sm"
                  tone={toneToButton(stage.tone)}
                  disabled={refreshing || runningActionId !== null}
                  onClick={() => onAction(stage.actionId)}
                >
                  {runningActionId === stage.actionId ? "执行中..." : `生成 ${stage.stage}`}
                </ConsoleButton>
              </div>
            </ConsoleInset>
          ))}
        </div>
      </ConsolePanel>
    </section>
  )
}
