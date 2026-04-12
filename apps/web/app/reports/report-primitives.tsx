import {
  ConsoleBadge,
  ConsoleInset,
  ConsoleMetric,
  ConsolePanel,
} from "../components/console-ui"

export interface ReportRecord {
  id: string
  report_type: string
  report_period_start: string
  report_period_end: string
  generated_at: string
  generated_by: string | null
  report_data: Record<string, unknown>
}

export interface AuditRecord {
  id: string
  actor_id: string | null
  actor_type?: string | null
  object_type: string
  object_id?: string | null
  action: string
  result: string
  created_at: string
  event_payload: Record<string, unknown> | null
}

export type JsonRecord = Record<string, unknown>

export const STAGE_NAMES = ["M4", "M5", "M6"] as const
export type StageName = (typeof STAGE_NAMES)[number]

const integerFormatter = new Intl.NumberFormat("zh-CN")
const percentFormatter = new Intl.NumberFormat("zh-CN", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})
const LABEL_OVERRIDES: Record<string, string> = {
  daily_summary: "日报",
  weekly_summary: "周报",
  stage_review: "阶段评审",
  tagging_quality: "标签质量报告",
  risk_assessment: "风险评估",
  candidate_total: "候选市场数",
  admitted_count: "准入数",
  rejected_count: "拒绝数",
  audit_event_count: "审计事件数",
  auditable: "可审计",
  rejection_reason_distribution: "拒绝原因分布",
  risk_state_events: "风险状态变更",
  current_exposures: "当前暴露",
  dq_alert_snapshot: "DQ 快照",
  missing_sections: "缺失章节",
  backtest_run_count: "回测次数",
  risk_event_count: "风险事件数",
  recent_backtests: "最近回测",
  risk_timeline: "风险时间线",
  recommendation_breakdown: "建议分布",
  stage_name: "阶段",
  dod: "完成定义",
  decision: "结论",
  nogo_reasons: "阻断原因",
  latest_backtest: "最近回测",
  latest_shadow_run: "最近影子运行",
  state_alerts_available: "状态与告警证据",
  backtest_available: "回测证据",
  shadow_run_available: "影子运行证据",
  audit_available: "审计日志",
  latest_backtest_not_ready: "最新回测未达放行条件",
  latest_shadow_run_blocked: "最新影子运行未达放行条件",
  audit_log_missing: "缺少审计日志",
  total_markets: "市场总数",
  high_risk_markets: "高风险市场",
  medium_risk_markets: "中风险市场",
  low_risk_markets: "低风险市场",
  reviewed_count: "已审核",
  approved_count: "已通过",
  total_tagged: "总打标量",
  accuracy_rate: "准确率",
  conflicts_detected: "冲突数",
  manual_reviews: "人工复核",
  categories: "分类表现",
  assessment_date: "评估时间",
  critical_alerts: "严重告警",
  warning_alerts: "预警",
  info_alerts: "提示",
  top_risks: "重点风险",
  recent_failures: "最近 DQ 失败",
  go: "Go",
  watch: "观察",
  nogo: "NoGo",
  success: "成功",
  failure: "失败",
  pending: "待处理",
  approved: "已通过",
  rejected: "已拒绝",
  in_progress: "处理中",
  block: "阻断",
  unknown: "未知",
}

export function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

export function asRecord(value: unknown): JsonRecord {
  return isRecord(value) ? value : {}
}

export function asRecordList(value: unknown): JsonRecord[] {
  return Array.isArray(value) ? value.filter(isRecord) : []
}

export function asStringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
    : []
}

export function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value
  }
  if (typeof value === "string" && value.trim().length > 0) {
    const numeric = Number(value)
    return Number.isFinite(numeric) ? numeric : null
  }
  return null
}

export function asBoolean(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "-"
  }
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false })
}

export function formatRange(start: string, end: string) {
  return `${formatDateTime(start)} - ${formatDateTime(end)}`
}

export function formatMetric(value: number | null, variant: "number" | "percent" = "number") {
  if (value === null) {
    return "-"
  }
  return variant === "percent" ? percentFormatter.format(value) : integerFormatter.format(value)
}

export function formatLabel(value: string) {
  if (LABEL_OVERRIDES[value]) {
    return LABEL_OVERRIDES[value]
  }
  return value.replaceAll("_", " ").replaceAll(":", " / ")
}

export function formatReportTitle(reportType: string) {
  if (reportType.startsWith("stage_review:")) {
    return `${reportType.split(":")[1] ?? "M6"} 阶段评审`
  }
  if (reportType === "daily_summary") {
    return "日报"
  }
  if (reportType === "weekly_summary") {
    return "周报"
  }
  return LABEL_OVERRIDES[reportType] ?? formatLabel(reportType)
}

export function formatValue(value: unknown): string {
  if (typeof value === "boolean") {
    return value ? "是" : "否"
  }
  if (typeof value === "number") {
    return Number.isInteger(value) ? integerFormatter.format(value) : value.toFixed(3)
  }
  if (typeof value === "string") {
    return value
  }
  if (Array.isArray(value)) {
    return value.length === 0 ? "[]" : value.map((item) => formatValue(item)).join(", ")
  }
  if (isRecord(value)) {
    return JSON.stringify(value)
  }
  return "-"
}

export function StatusChip({
  label,
  tone,
}: {
  label: string
  tone: "neutral" | "good" | "warn" | "bad"
}) {
  const normalizedTone = tone === "neutral" ? "neutral" : tone === "good" ? "good" : tone === "warn" ? "warn" : "bad"
  return <ConsoleBadge label={label} tone={normalizedTone} />
}

export function MetricTile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return <ConsoleMetric label={label} value={value} hint={hint} />
}

export function SectionBlock({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <ConsolePanel title={title} bodyClassName="pt-4">
      {children}
    </ConsolePanel>
  )
}

export function RawJsonDetails({ data, label = "查看原始 JSON" }: { data: unknown; label?: string }) {
  return (
    <details className="mt-4 rounded-xl border border-[#30363d] bg-[#0d1117] p-4">
      <summary className="cursor-pointer text-xs uppercase tracking-[0.18em] text-[#8b949e]">{label}</summary>
      <ConsoleInset className="mt-3 overflow-x-auto">
        <pre className="text-xs leading-6 text-[#c9d1d9]">{JSON.stringify(data, null, 2)}</pre>
      </ConsoleInset>
    </details>
  )
}
