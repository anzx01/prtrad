import type { LaunchChecklistItem, LaunchReview, ShadowRun } from "./types"

export const STAGE_OPTIONS = ["M4", "M5", "M6"] as const

const CHECKLIST_LABELS: Record<string, string> = {
  latest_backtest_go: "最新回测结论为 Go / Watch",
  shadow_not_blocked: "最新 shadow 没有给出阻断结论",
  shadow_risk_state_safe: "shadow 运行时风险状态不是 RiskOff / Frozen",
  latest_stage_review_go: "最新阶段评审结论为 Go",
  kill_switch_queue_clear: "当前没有待审批 kill-switch",
  risk_state_safe: "当前风险状态不是 RiskOff / Frozen",
  cluster_limits_clean: "当前没有越限暴露簇",
  dq_alerts_clean: "最近没有新增 DQ 失败告警",
}

export function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "-"
}

export function formatRecommendationLabel(value: ShadowRun["recommendation"] | string | undefined) {
  return value === "go" ? "Go" : value === "watch" ? "观察" : value === "block" ? "阻断" : "-"
}

export function recommendationTone(value: ShadowRun["recommendation"] | string | undefined) {
  return value === "go" ? "good" : value === "watch" ? "warn" : value === "block" ? "bad" : "neutral"
}

export function reviewTone(value: LaunchReview["status"] | string | undefined) {
  return value === "go" ? "good" : value === "nogo" ? "bad" : value === "pending" ? "warn" : "neutral"
}

export function formatReviewStatusLabel(value: LaunchReview["status"] | string | undefined) {
  return value === "go" ? "Go" : value === "nogo" ? "NoGo" : value === "pending" ? "待决策" : "-"
}

export function formatChecklistLabel(item: LaunchChecklistItem) {
  return CHECKLIST_LABELS[item.code] ?? item.label
}

export function formatChecklistLabels(items: LaunchChecklistItem[]) {
  return items.map((item) => formatChecklistLabel(item))
}

export function formatEvidenceRecommendation(value?: string | null) {
  switch (value?.toLowerCase()) {
    case "go":
      return "Go，可继续"
    case "watch":
      return "观察"
    case "block":
    case "nogo":
      return "阻断"
    default:
      return "-"
  }
}

export function formatDecisionLabel(value?: string | null) {
  switch (value?.toLowerCase()) {
    case "go":
      return "Go，可进入上线决策"
    case "nogo":
      return "NoGo，暂不上线"
    case "pending":
      return "待决策"
    default:
      return value ?? "-"
  }
}

export function formatReportTypeLabel(value?: string | null) {
  if (!value) {
    return "尚未关联阶段评审"
  }
  if (value === "daily_summary") {
    return "日报"
  }
  if (value === "weekly_summary") {
    return "周报"
  }
  if (value.startsWith("stage_review")) {
    const stageName = value.split(":")[1]
    return stageName ? `${stageName} 阶段评审` : "阶段评审"
  }
  return value
}
