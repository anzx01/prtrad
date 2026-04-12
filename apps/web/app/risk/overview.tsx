import {
  ConsoleBadge,
  ConsoleButton,
  ConsoleCallout,
  ConsoleInset,
  ConsoleMetric,
  ConsolePanel,
} from "../components/console-ui"
import { STATE_COLORS, STATE_PANEL_STYLES, formatRiskStateLabel } from "./constants"
import type { RiskPriority, RiskSpotlight } from "./insights"
import type { StateEvent } from "./types"

export function RiskPageHeader({
  computing,
  onCompute,
  title,
  summary,
  tone,
}: {
  computing: boolean
  onCompute: () => void
  title: string
  summary: string
  tone: "safe" | "warning" | "danger"
}) {
  const toneClassName = {
    safe: "good",
    warning: "warn",
    danger: "bad",
  }[tone]

  return (
    <ConsoleCallout
      eyebrow="当前优先事项"
      title={title}
      description={summary}
      tone={toneClassName as "good" | "warn" | "bad"}
      actions={
        <ConsoleButton
          onClick={onCompute}
          disabled={computing}
          tone="primary"
          type="button"
        >
          {computing ? "计算中..." : "重算暴露"}
        </ConsoleButton>
      }
    />
  )
}

function priorityToneLabel(tone: "info" | "good" | "warn" | "bad") {
  if (tone === "bad") {
    return "优先处理"
  }
  if (tone === "warn") {
    return "建议先看"
  }
  if (tone === "good") {
    return "当前稳定"
  }
  return "补充判断"
}

export function RiskPrioritySection({
  priorities,
  spotlight,
}: {
  priorities: RiskPriority[]
  spotlight: RiskSpotlight
}) {
  return (
    <section className="mb-8 grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
      <ConsolePanel
        title="系统建议先看这里"
        description="这不是字段罗列，而是把当前更值得先处理的风险项排了顺序。"
      >
        <div className="space-y-3">
          {priorities.map((priority) => (
            <ConsoleInset key={priority.id} className="space-y-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-[#e6edf3]">{priority.title}</p>
                  <p className="mt-2 text-sm leading-6 text-[#8b949e]">{priority.description}</p>
                </div>
                <ConsoleBadge label={priorityToneLabel(priority.tone)} tone={priority.tone} />
              </div>
              <ConsoleBadge label={priority.badge} tone={priority.tone} />
            </ConsoleInset>
          ))}
        </div>
      </ConsolePanel>

      <ConsolePanel
        title={spotlight.title}
        description={spotlight.description}
      >
        {spotlight.items.length === 0 ? (
          <ConsoleInset>
            <p className="text-sm leading-6 text-[#c9d1d9]">{spotlight.emptyState}</p>
          </ConsoleInset>
        ) : (
          <div className="space-y-3">
            {spotlight.items.map((item) => (
              <ConsoleInset key={item}>
                <p className="text-sm leading-6 text-[#c9d1d9]">{item}</p>
              </ConsoleInset>
            ))}
          </div>
        )}
      </ConsolePanel>
    </section>
  )
}

export function RiskSummaryGrid({
  currentState,
  exposureCount,
  breachedCount,
  pendingCount,
}: {
  currentState: string
  exposureCount: number
  breachedCount: number
  pendingCount: number
}) {
  return (
    <div className="mb-8 grid gap-4 md:grid-cols-4">
      <ConsoleMetric label="当前状态" value={formatRiskStateLabel(currentState)} />
      <ConsoleMetric label="跟踪簇数" value={exposureCount.toString()} />
      <ConsoleMetric label="越限簇数" value={breachedCount.toString()} tone={breachedCount > 0 ? "warn" : "good"} />
      <ConsoleMetric label="待处理请求" value={pendingCount.toString()} tone={pendingCount > 0 ? "warn" : "good"} />
    </div>
  )
}

export function RiskStatePanel({
  currentState,
  latestEvent,
}: {
  currentState: string
  latestEvent?: StateEvent
}) {
  return (
    <ConsolePanel className={`mb-8 ${STATE_PANEL_STYLES[currentState] ?? "border-[#30363d] bg-[#161b22]"}`}>
      <p className="text-sm text-[#c9d1d9]">全局风险状态</p>
      <p className={`mt-2 text-4xl font-semibold ${STATE_COLORS[currentState] ?? "text-white"}`}>
        {formatRiskStateLabel(currentState)}
      </p>
      <p className="mt-1 text-xs text-[#8b949e]">状态码：{currentState}</p>
      {latestEvent && (
        <p className="mt-3 text-xs text-[#8b949e]">
          最近一次变化：{new Date(latestEvent.created_at).toLocaleString("zh-CN", { hour12: false })}
          {latestEvent.actor_id ? ` / 操作人 ${latestEvent.actor_id}` : " / 自动切换"}
        </p>
      )}
    </ConsolePanel>
  )
}
