export type ReviewQueueStatus =
  | "pending"
  | "in_progress"
  | "approved"
  | "rejected"
  | "cancelled"

export type ReviewPriority = "low" | "normal" | "high" | "urgent"
export type ReviewBulkAction = "start_review" | "approve" | "reject"

export interface ReviewMarketSummary {
  market_id: string
  question: string
}

export interface ReviewMarketInfo extends ReviewMarketSummary {
  id: string
  description: string | null
  market_status: string
}

export interface ReviewClassificationResult {
  id: string
  classification_status: string
  primary_category_code: string | null
  confidence: number | null
  requires_review: boolean
  conflict_count: number | null
}

export interface ReviewTaskSummary {
  id: string
  market_ref_id: string
  classification_result_id: string
  queue_status: ReviewQueueStatus
  review_reason_code: string | null
  priority: ReviewPriority
  assigned_to: string | null
  review_payload: Record<string, unknown> | null
  resolved_at: string | null
  created_at: string
  updated_at: string
  market: ReviewMarketSummary | null
}

export interface ReviewTask extends Omit<ReviewTaskSummary, "market"> {
  market: ReviewMarketInfo | null
  classification_result: ReviewClassificationResult | null
}

export interface ReviewQueueResponse {
  tasks: ReviewTaskSummary[]
  total: number
  page: number
  page_size: number
}

export interface ReviewTaskDetailResponse {
  task: ReviewTask
}

export interface ReviewBulkActionResponse {
  tasks: ReviewTaskSummary[]
  updated_count: number
}
