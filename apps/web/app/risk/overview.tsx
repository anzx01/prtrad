import { ConsoleButton, ConsoleCallout, ConsoleMetric, ConsolePanel } from "../components/console-ui"
import { STATE_COLORS, STATE_PANEL_STYLES, formatRiskStateLabel } from "./constants"
import type { StateEvent } from "./types"

export function RiskPageHeader({
  computing,
  onCompute,
  summary,
  tone,
}: {
  computing: boolean
  onCompute: () => void
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
      title={tone === "danger" ? "优先处理风险阻断" : tone === "warning" ? "先处理待办风险项" : "当前链路相对稳定"}
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
