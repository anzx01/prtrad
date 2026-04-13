import type { ActionId, DashboardSnapshot, ReportRecord, StageName } from "./types"

const numberFormatter = new Intl.NumberFormat("zh-CN")

export function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}

export function asStrings(value: unknown) {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : []
}

export function formatCount(value: number | null | undefined) {
  return numberFormatter.format(value ?? 0)
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "-"
  }
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false })
}

export function formatRecommendation(value: string | null | undefined) {
  if (value === "go") {
    return "Go"
  }
  if (value === "watch") {
    return "观察"
  }
  if (value === "block") {
    return "阻断"
  }
  if (value === "nogo") {
    return "NoGo"
  }
  return value ?? "-"
}

export function formatRiskState(value: string | null | undefined) {
  if (value === "Normal") {
    return "正常"
  }
  if (value === "Caution") {
    return "关注"
  }
  if (value === "RiskOff") {
    return "风险关闭"
  }
  if (value === "Frozen") {
    return "冻结"
  }
  return value ?? "-"
}

export function latestStageReport(reports: ReportRecord[], stage: StageName) {
  return reports.find((report) => report.report_type === `stage_review:${stage}`) ?? null
}

export function reportDecision(report: ReportRecord | null) {
  return String(asRecord(report?.report_data).decision ?? "").toLowerCase()
}

export function reportReasons(report: ReportRecord | null) {
  return asStrings(asRecord(report?.report_data).nogo_reasons)
}

export function stageActionId(stage: StageName): ActionId {
  if (stage === "M4") {
    return "generateStageM4"
  }
  if (stage === "M5") {
    return "generateStageM5"
  }
  return "generateStageM6"
}

export function latestEvidenceTime(snapshot: DashboardSnapshot) {
  const timestamps = [
    snapshot.backtests[0]?.created_at,
    snapshot.shadowRuns[0]?.created_at,
    snapshot.launchReviews[0]?.created_at,
  ]
    .filter(Boolean)
    .map((value) => new Date(value as string).getTime())
    .filter((value) => Number.isFinite(value))

  return timestamps.length > 0 ? Math.max(...timestamps) : null
}
