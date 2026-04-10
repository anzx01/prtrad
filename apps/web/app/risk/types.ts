export interface StateEvent {
  from_state: string
  to_state: string
  trigger_type: string
  trigger_metric: string
  trigger_value: number
  actor_id: string | null
  notes: string | null
  created_at: string
}

export interface RiskStateData {
  state: string
  history: StateEvent[]
}

export interface ExposureItem {
  cluster_code: string
  gross_exposure: number
  net_exposure: number
  position_count: number
  limit_value: number
  utilization_rate: number
  is_breached: boolean
  snapshot_at: string
}

export interface ThresholdItem {
  id: string
  cluster_code: string
  metric_name: string
  threshold_value: number
  is_active: boolean
  created_by: string
  created_at: string
}

export type ThresholdMetric =
  | "utilization_caution"
  | "utilization_risk_off"
  | "max_exposure"
  | "max_positions"

export interface ThresholdFormState {
  cluster_code: string
  metric_name: ThresholdMetric
  threshold_value: string
  created_by: string
}

export interface KillSwitchItem {
  id: string
  request_type: string
  target_scope: string
  requested_by: string
  reason: string
  status: string
  reviewed_by: string | null
  reviewed_at: string | null
  review_notes: string | null
  created_at: string
}

export interface KillSwitchFormState {
  request_type: string
  target_scope: string
  requested_by: string
  reason: string
}

export type ReviewAction = "approve" | "reject"
