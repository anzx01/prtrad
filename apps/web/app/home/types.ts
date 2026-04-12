export type DashboardTone = "neutral" | "info" | "good" | "warn" | "bad"

export type StageName = "M4" | "M5" | "M6"

export type ActionId =
  | "refreshEvidencePack"
  | "recomputeRisk"
  | "recomputeCalibration"
  | "runBacktest"
  | "runShadow"
  | "generateDaily"
  | "generateWeekly"
  | "generateStageBundle"
  | "generateStageM4"
  | "generateStageM5"
  | "generateStageM6"

export type DashboardResourceKey =
  | "monitoring"
  | "dq"
  | "reviewQueue"
  | "riskState"
  | "exposures"
  | "killSwitches"
  | "calibration"
  | "backtests"
  | "shadowRuns"
  | "launchReviews"
  | "reports"

export interface MonitoringMetrics {
  review_queue?: {
    pending?: number
    in_progress?: number
    approved_today?: number
    rejected_today?: number
  }
  tag_quality?: {
    latest_total?: number
    latest_success_rate?: number
    latest_avg_confidence?: number
    open_anomalies?: number
  }
  dq?: {
    recent_failures?: number
  }
}

export interface DQSummaryResponse {
  summary: {
    total_checks: number
    status_distribution: Record<string, number>
    pass_rate: number
    latest_checked_at: string | null
    latest_snapshot_time: string | null
    snapshot_age_seconds: number | null
    freshness_status: string
  }
  recent_results: Array<{
    id: string
    market_id: string | null
    status: string
    score: number | null
  }>
}

export interface ReviewQueueResponse {
  tasks: Array<{
    id: string
    review_reason_code: string | null
    priority: string
    queue_status: string
    created_at: string
    market?: {
      market_id: string
      question: string
    } | null
  }>
  total: number
  page: number
  page_size: number
}

export interface RiskStateData {
  state: string
  history: Array<{
    created_at?: string
    to_state?: string
    trigger_metric?: string
  }>
}

export interface ExposureItem {
  cluster_code?: string
  is_breached?: boolean
  utilization_rate?: number
}

export interface KillSwitchRequest {
  id: string
  status: string
  request_type: string
  target_scope: string
  requested_by: string
  reason: string
  created_at: string
}

export interface CalibrationUnit {
  id: string
  category_code: string
  price_bucket: string
  time_bucket: string
  liquidity_tier: string
  window_type: string
  sample_count: number
  edge_estimate: number
  is_active: boolean
  disabled_reason: string | null
  computed_at: string
}

export interface BacktestRun {
  id: string
  run_name: string
  recommendation: "go" | "watch" | "nogo"
  status: string
  created_at: string
  completed_at: string
  summary: {
    totals?: {
      candidate_count?: number
      admitted_count?: number
      rejected_count?: number
      resolved_ratio?: number
    }
  }
}

export interface ShadowRun {
  id: string
  run_name: string
  risk_state: string
  recommendation: "go" | "watch" | "block"
  created_at: string
  checklist: Array<{ code: string; label: string; passed: boolean }>
}

export interface LaunchReview {
  id: string
  title: string
  stage_name: string
  requested_by: string
  reviewed_by: string | null
  status: "pending" | "go" | "nogo"
  checklist: Array<{ code: string; label: string; passed: boolean }>
  review_notes: string | null
  decided_at: string | null
  created_at: string
}

export interface ReportRecord {
  id: string
  report_type: string
  report_period_start: string
  report_period_end: string
  generated_at: string
  generated_by: string | null
  report_data: Record<string, unknown>
}

export interface DashboardSnapshot {
  monitoring: MonitoringMetrics | null
  dq: DQSummaryResponse | null
  reviewQueue: ReviewQueueResponse | null
  riskState: RiskStateData | null
  exposures: ExposureItem[]
  killSwitches: KillSwitchRequest[]
  calibration: CalibrationUnit[]
  backtests: BacktestRun[]
  shadowRuns: ShadowRun[]
  launchReviews: LaunchReview[]
  reports: ReportRecord[]
  errors: Partial<Record<DashboardResourceKey, string>>
}

export interface DashboardMetric {
  label: string
  value: string
  hint?: string
  tone?: DashboardTone
}

export interface DashboardNarrative {
  id: string
  title: string
  body: string
  tone: DashboardTone
  href?: string
}

export interface DashboardActionSuggestion {
  id: string
  title: string
  body: string
  tone: DashboardTone
  cta: string
  actionId?: ActionId
  href?: string
}

export interface WorkflowCard {
  id: string
  label: string
  status: string
  detail: string
  tone: DashboardTone
  href: string
}

export interface StageCard {
  stage: StageName
  title: string
  detail: string
  tone: DashboardTone
  actionId: ActionId
}

export interface DashboardSummary {
  headline: {
    title: string
    description: string
    tone: DashboardTone
  }
  metrics: DashboardMetric[]
  narratives: DashboardNarrative[]
  nextActions: DashboardActionSuggestion[]
  workflows: WorkflowCard[]
  stages: StageCard[]
}
