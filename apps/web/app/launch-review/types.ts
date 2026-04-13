export interface LaunchChecklistItem {
  code: string
  label: string
  passed: boolean
}

export interface ShadowRun {
  id: string
  run_name: string
  risk_state: string
  recommendation: "go" | "watch" | "block"
  executed_by: string | null
  summary: {
    exposure_summary?: {
      breached_clusters?: string[]
    }
  }
  checklist: LaunchChecklistItem[]
  created_at: string
}

export interface LinkedEvidence {
  id: string
  run_name?: string
  report_type?: string
  created_at?: string
  window_end?: string
  generated_at?: string
  recommendation?: string
  risk_state?: string
  decision?: string
  report_period_end?: string
}

export interface LaunchEvidenceSummary {
  latest_backtest?: LinkedEvidence | null
  latest_shadow_run?: LinkedEvidence | null
  latest_stage_review?: LinkedEvidence | null
}

export interface LaunchReview {
  id: string
  title: string
  stage_name: string
  shadow_run_id: string | null
  requested_by: string
  reviewed_by: string | null
  status: "pending" | "go" | "nogo"
  checklist: LaunchChecklistItem[]
  evidence_summary: LaunchEvidenceSummary | null
  review_notes: string | null
  decided_at: string | null
  created_at: string
}

export interface LaunchReviewResponse {
  review: LaunchReview
}

export interface DecisionDraft {
  reviewId: string
  decision: "go" | "nogo"
  reviewedBy: string
  notes: string
}

export interface DecisionFeedback {
  reviewId: string
  tone: "info" | "warn" | "bad"
  message: string
  details?: string[]
}
