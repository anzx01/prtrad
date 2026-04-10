import type { ThresholdMetric } from "./types"

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

export const DEFAULT_THRESHOLD_VALUES: Record<ThresholdMetric, string> = {
  utilization_caution: "0.60",
  utilization_risk_off: "0.80",
  max_exposure: "10.00",
  max_positions: "50",
}

export const THRESHOLD_METRIC_OPTIONS: ThresholdMetric[] = [
  "max_exposure",
  "max_positions",
  "utilization_caution",
  "utilization_risk_off",
]
