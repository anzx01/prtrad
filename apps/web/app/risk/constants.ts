import type { KillSwitchFormState, ThresholdFormState, ThresholdMetric } from "./types"

export const STATE_COLORS: Record<string, string> = {
  Normal: "text-emerald-300",
  Caution: "text-yellow-300",
  RiskOff: "text-orange-300",
  Frozen: "text-rose-300",
}

export const STATE_PANEL_STYLES: Record<string, string> = {
  Normal: "border-emerald-500/30 bg-emerald-500/10",
  Caution: "border-yellow-500/30 bg-yellow-500/10",
  RiskOff: "border-orange-500/30 bg-orange-500/10",
  Frozen: "border-rose-500/30 bg-rose-500/10",
}

export const STATUS_BADGE_STYLES: Record<string, string> = {
  pending: "bg-yellow-500/10 text-yellow-300",
  approved: "bg-emerald-500/10 text-emerald-300",
  rejected: "bg-rose-500/10 text-rose-300",
}

export const STATE_LABELS: Record<string, string> = {
  Normal: "正常",
  Caution: "关注",
  RiskOff: "风险关闭",
  Frozen: "冻结",
}

export const KILL_SWITCH_TYPE_LABELS: Record<string, string> = {
  risk_off: "切到 RiskOff",
  freeze: "冻结交易",
  unfreeze: "解除冻结",
}

export const REVIEW_STATUS_LABELS: Record<string, string> = {
  pending: "待审批",
  approved: "已批准",
  rejected: "已拒绝",
}

export const THRESHOLD_METRIC_LABELS: Record<ThresholdMetric, string> = {
  max_exposure: "净暴露上限",
  max_positions: "持仓数上限",
  utilization_caution: "关注利用率阈值",
  utilization_risk_off: "RiskOff 利用率阈值",
}

export const DEFAULT_THRESHOLD_VALUES: Record<ThresholdMetric, string> = {
  utilization_caution: "0.60",
  utilization_risk_off: "0.80",
  max_exposure: "10.00",
  max_positions: "50",
}

export const INITIAL_KILL_SWITCH_FORM: KillSwitchFormState = {
  request_type: "risk_off",
  target_scope: "global",
  requested_by: "",
  reason: "",
}

export const INITIAL_THRESHOLD_FORM: ThresholdFormState = {
  cluster_code: "global",
  metric_name: "max_exposure",
  threshold_value: DEFAULT_THRESHOLD_VALUES.max_exposure,
  created_by: "",
}

export const THRESHOLD_METRIC_OPTIONS: ThresholdMetric[] = [
  "max_exposure",
  "max_positions",
  "utilization_caution",
  "utilization_risk_off",
]

export function formatRiskStateLabel(value: string): string {
  return STATE_LABELS[value] ?? value
}

export function formatKillSwitchTypeLabel(value: string): string {
  return KILL_SWITCH_TYPE_LABELS[value] ?? value
}

export function formatReviewStatusLabel(value: string): string {
  return REVIEW_STATUS_LABELS[value] ?? value
}

export function formatThresholdMetricLabel(value: ThresholdMetric | string): string {
  return THRESHOLD_METRIC_LABELS[value as ThresholdMetric] ?? value
}

export function getRiskErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message
  }
  if (error && typeof error === "object" && "message" in error) {
    const message = (error as { message?: unknown }).message
    if (typeof message === "string") {
      return message
    }
  }
  return "发生了未知错误，请稍后重试"
}
