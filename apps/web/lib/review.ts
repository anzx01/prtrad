export type ReviewQueueStatus =
  | "pending"
  | "in_progress"
  | "approved"
  | "rejected"
  | "cancelled"

export type ReviewPriority = "low" | "normal" | "high" | "urgent"
export type ReviewBulkAction = "start_review" | "approve" | "reject"

const REVIEW_REASON_LABELS: Record<string, string> = {
  TAG_NO_CATEGORY_MATCH: "未匹配到主类别",
  TAG_CATEGORY_CONFLICT: "主类别冲突",
  TAG_NO_BUCKET_MATCH: "未匹配到准入桶",
  TAG_BUCKET_CONFLICT: "准入桶冲突",
  TAG_LOW_CONFIDENCE: "分类置信度偏低",
  TAG_BLACKLIST_MATCH: "命中黑名单规则",
  TAG_EXPLICIT_REVIEW: "规则要求人工审核",
  TAG_MANUAL_REVIEW: "需要人工审核",
}

const REVIEW_REASON_DESCRIPTIONS: Record<string, string> = {
  TAG_NO_CATEGORY_MATCH: "自动分类没有找到足够可信的主类别，当前不应把这条任务视为“已有明确分类结论”。",
  TAG_CATEGORY_CONFLICT: "多个主类别候选同时命中，系统无法确定哪一个才是最终主类别，需要人工裁决。",
  TAG_NO_BUCKET_MATCH: "主类别或标签命中了部分规则，但准入桶没有稳定落位，说明规则覆盖仍不完整。",
  TAG_BUCKET_CONFLICT: "不同准入桶候选互相冲突，系统无法自动决定该进哪一档准入路径。",
  TAG_LOW_CONFIDENCE: "自动分类给出了候选，但整体置信度低于阈值，需要人工确认是否可信。",
  TAG_BLACKLIST_MATCH: "命中黑名单或强阻断规则，应重点核查是否需要直接拦截。",
  TAG_EXPLICIT_REVIEW: "规则明确要求进入人工审核，这不是“可自动放行”的场景。",
  TAG_MANUAL_REVIEW: "系统当前没有足够把握自动决策，需要人工补齐最终判断。",
}

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

export function getReviewReasonLabel(value: string | null | undefined): string {
  if (!value) {
    return "-"
  }
  return REVIEW_REASON_LABELS[value] ?? value
}

export function formatReviewReasonDisplay(value: string | null | undefined): string {
  if (!value) {
    return "-"
  }
  const label = getReviewReasonLabel(value)
  return label === value ? value : `${label}（${value}）`
}

export function getReviewReasonDescription(value: string | null | undefined): string | null {
  if (!value) {
    return null
  }
  return REVIEW_REASON_DESCRIPTIONS[value] ?? null
}
