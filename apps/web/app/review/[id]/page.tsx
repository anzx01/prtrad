"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"

import { apiGet, apiPost } from "@/lib/api"
import {
  canAutoRejectTask,
  formatReviewClassificationStatusDisplay,
  formatReviewPriorityDisplay,
  formatReviewReasonDisplay,
  getReviewReasonDescription,
  type ReviewTask,
  type ReviewTaskDetailResponse,
  type ReviewQueueStatus,
} from "@/lib/review"

import { PageIntro, SoftPanel } from "../../components/page-intro"

const STATUS_LABELS: Record<ReviewQueueStatus, string> = {
  pending: "待处理",
  in_progress: "处理中",
  approved: "已通过",
  rejected: "已退回",
  cancelled: "已取消",
}

function statusStyles(status: ReviewQueueStatus) {
  const styles: Record<ReviewQueueStatus, string> = {
    pending: "border-amber-400/30 bg-amber-500/10 text-amber-100",
    in_progress: "border-sky-400/30 bg-sky-500/10 text-sky-100",
    approved: "border-emerald-400/30 bg-emerald-500/10 text-emerald-100",
    rejected: "border-rose-400/30 bg-rose-500/10 text-rose-100",
    cancelled: "border-white/10 bg-white/5 text-slate-300",
  }
  return styles[status]
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
      <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm leading-6 text-slate-200">{value}</p>
    </div>
  )
}

function readString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null
}

function readNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null
}

function readStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return []
  }
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
}

function getReviewPayloadSummary(reviewPayload: Record<string, unknown> | null) {
  return {
    classificationStatus: readString(reviewPayload?.classification_status),
    primaryCategoryCode: readString(reviewPayload?.primary_category_code),
    admissionBucketCode: readString(reviewPayload?.admission_bucket_code),
    failureReasonCode: readString(reviewPayload?.failure_reason_code),
    confidence: readNumber(reviewPayload?.confidence),
    matchedRuleCodes: readStringList(reviewPayload?.matched_rule_codes),
  }
}

export default function ReviewTaskDetailPage() {
  const params = useParams()
  const router = useRouter()
  const taskId = params.id as string

  const [task, setTask] = useState<ReviewTask | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState("")
  const [showRejectForm, setShowRejectForm] = useState(false)
  const [actorId] = useState("reviewer_1")

  useEffect(() => {
    setLoading(true)
    apiGet<ReviewTaskDetailResponse>(`/review/${taskId}`)
      .then((data) => {
        setTask(data.task)
        setLoading(false)
      })
      .catch((fetchError) => {
        setError(fetchError instanceof Error ? fetchError.message : "加载审核任务失败")
        setLoading(false)
      })
  }, [taskId])

  async function startReview() {
    setActionLoading(true)
    setError(null)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/review/${taskId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ queue_status: "in_progress", assigned_to: actorId }),
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const data = (await response.json()) as ReviewTaskDetailResponse
      setTask(data.task)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "开始审核失败")
    } finally {
      setActionLoading(false)
    }
  }

  async function approveTask() {
    setActionLoading(true)
    setError(null)
    try {
      const data = await apiPost<ReviewTaskDetailResponse>(`/review/${taskId}/approve`, {
        actor_id: actorId,
        approval_notes: null,
      })
      setTask(data.task)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "批准失败")
    } finally {
      setActionLoading(false)
    }
  }

  async function rejectTask() {
    if (!rejectReason.trim() && !(task && canAutoRejectTask(task))) {
      setError("请先填写退回原因")
      return
    }

    setActionLoading(true)
    setError(null)
    try {
      const data = await apiPost<ReviewTaskDetailResponse>(`/review/${taskId}/reject`, {
        actor_id: actorId,
        rejection_reason: rejectReason.trim(),
        rejection_notes: null,
      })
      setTask(data.task)
      setShowRejectForm(false)
      setRejectReason("")
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "拒绝失败")
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return <div className="p-8 text-slate-400">正在加载审核任务详情...</div>
  }

  if (!task) {
    return <div className="p-8 text-slate-400">当前任务不存在，或已无法访问。</div>
  }

  const isTerminal = ["approved", "rejected", "cancelled"].includes(task.queue_status)
  const reviewPayloadSummary = getReviewPayloadSummary(task.review_payload)
  const reviewReasonDisplay = formatReviewReasonDisplay(task.review_reason_code)
  const reviewReasonDescription = getReviewReasonDescription(task.review_reason_code)
  const hasFormalClassificationResult = Boolean(task.classification_result)
  const hasFormalPrimaryCategory = Boolean(task.classification_result?.primary_category_code)
  const formalConflictCount = task.classification_result?.conflict_count ?? 0
  const formalClassificationNeedsReview = Boolean(task.classification_result?.requires_review)
  const hasFallbackClassificationContext =
    reviewPayloadSummary.classificationStatus !== null ||
    reviewPayloadSummary.primaryCategoryCode !== null ||
    reviewPayloadSummary.admissionBucketCode !== null ||
    reviewPayloadSummary.failureReasonCode !== null ||
    reviewPayloadSummary.confidence !== null ||
    reviewPayloadSummary.matchedRuleCodes.length > 0
  const canApproveTask = task.can_approve
  const canAutoRejectWithoutReason = canAutoRejectTask(task)
  const priorityDisplay = formatReviewPriorityDisplay(task.priority)
  const approvalGuideText = canApproveTask
    ? formalConflictCount > 0
      ? "只有在你已经人工确认最终主类别合理、冲突已被排除时，才应批准。"
      : formalClassificationNeedsReview
        ? "正式主类别已经产出，但仍需人工确认；核对市场信息、主类别和触发原因一致后，再批准。"
        : "正式主类别已经明确，且没有明显冲突时，通常可以批准。"
    : "当前没有正式主类别；若主类别为空、只有回退字段，或正式分类结果缺失，不建议直接批准。"
  const rejectGuideText = canApproveTask
    ? formalConflictCount > 0
      ? "若最终主类别仍无法裁决，或市场信息与候选类别明显冲突，应填写拒绝原因并驳回。"
      : "若类别明显错误、触发原因不合理，或市场信息本身异常，再填写拒绝原因并驳回。"
    : "当前没有可批准的分类依据时，应优先写明原因并退回，避免把“无结论”任务直接放行。"
  const classificationPanelDescription = hasFormalClassificationResult
    ? "这里展示正式 classification_result。只有存在正式主类别时，批准才有意义。"
    : hasFallbackClassificationContext
      ? "正式分类结果缺失，下面展示的是创建审核任务时写入的回退字段，只能作为排查参考。"
      : "当前既没有正式分类结果，也没有足够的回退字段，不建议直接批准。"

  return (
    <main className="mx-auto max-w-6xl px-4 py-5 md:px-6">
      <button
        type="button"
        onClick={() => router.push("/review")}
        className="mb-5 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-300 transition hover:bg-white/10"
      >
        返回审核队列
      </button>

      <PageIntro
        eyebrow="Review Detail"
        title="审核任务详情"
        description="先看系统已经给出的结论，再决定是批准还是退回。只有系统仍不确定时，才需要你继续看更细的分类字段。"
        stats={[
          { label: "当前状态", value: STATUS_LABELS[task.queue_status] },
          { label: "操作人", value: task.assigned_to ?? actorId },
        ]}
        guides={[
          {
            title: "先看系统结论",
            description: "先看系统结论和建议动作，再决定是否继续下钻看分类细节。",
          },
          {
            title: "什么时候批准",
            description: approvalGuideText,
          },
          {
            title: "什么时候退回",
            description: rejectGuideText,
          },
        ]}
      />

      <section className="mb-6 rounded-[28px] border border-white/10 bg-black/20 p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">审核任务</p>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <span className={`rounded-full border px-3 py-1.5 text-sm ${statusStyles(task.queue_status)}`}>
                {STATUS_LABELS[task.queue_status]}
              </span>
              <span className="text-sm text-slate-400">优先级：{priorityDisplay}</span>
              <span className="text-sm text-slate-400">触发原因：{reviewReasonDisplay}</span>
            </div>
            {reviewReasonDescription ? (
              <p className="mt-2 text-sm leading-6 text-slate-400">{reviewReasonDescription}</p>
            ) : null}
            <div className="mt-4 rounded-2xl border border-amber-400/20 bg-amber-500/10 p-4">
              <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">系统结论</p>
              <p className="mt-2 text-sm font-medium text-slate-100">{task.system_conclusion}</p>
              <p className="mt-2 text-sm leading-6 text-slate-300">{task.system_reason}</p>
              <p className="mt-2 text-xs text-sky-200">建议动作：{task.system_next_action_label}</p>
            </div>
          </div>

          {!isTerminal && task.queue_status === "pending" ? (
            <button
              type="button"
              onClick={startReview}
              disabled={actionLoading}
              className="rounded-full border border-sky-300/30 bg-sky-500/10 px-5 py-3 text-sm text-sky-100 transition hover:bg-sky-500/20 disabled:opacity-50"
            >
              {actionLoading ? "处理中..." : "开始审核"}
            </button>
          ) : null}

          {!isTerminal && task.queue_status === "in_progress" ? (
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={approveTask}
                disabled={actionLoading || !canApproveTask}
                className="rounded-full border border-emerald-300/30 bg-emerald-500/10 px-5 py-3 text-sm text-emerald-100 transition hover:bg-emerald-500/20 disabled:opacity-50"
              >
                {actionLoading && !showRejectForm ? "处理中..." : "批准"}
              </button>
              <button
                type="button"
                onClick={() => setShowRejectForm((current) => !current)}
                disabled={actionLoading}
                className="rounded-full border border-rose-300/30 bg-rose-500/10 px-5 py-3 text-sm text-rose-100 transition hover:bg-rose-500/20 disabled:opacity-50"
              >
                退回
              </button>
            </div>
          ) : null}
        </div>
      </section>

      {error ? (
        <div className="mb-6 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-100">
          {error}
        </div>
      ) : null}

      {!canApproveTask ? (
        <div className="mb-6 rounded-2xl border border-amber-400/30 bg-amber-500/10 p-4 text-sm text-amber-100">
          {task.system_reason}
        </div>
      ) : null}

      <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <SoftPanel title="市场信息" description="先确认任务对应的市场本身是否合理。">
          <div className="space-y-4">
            <InfoRow label="问题" value={task.market?.question ?? "-"} />
            <InfoRow label="描述" value={task.market?.description ?? "-"} />
            <div className="grid gap-4 md:grid-cols-2">
              <InfoRow label="市场状态" value={task.market?.market_status ?? "-"} />
              <InfoRow label="市场 ID" value={task.market?.market_id ?? task.market_ref_id} />
            </div>
          </div>
        </SoftPanel>

        <SoftPanel title="分类结果" description={classificationPanelDescription}>
          {task.classification_result ? (
            <div className="space-y-4">
              {!hasFormalPrimaryCategory ? (
                <div className="rounded-2xl border border-amber-400/20 bg-amber-500/10 p-4 text-sm text-amber-100">
                  当前虽然有正式 `classification_result` 记录，但主类别仍为空。这说明自动分类没有形成可接受的主类别结论，不能直接批准。
                </div>
              ) : null}
              {hasFormalPrimaryCategory && formalConflictCount > 0 ? (
                <div className="rounded-2xl border border-amber-400/20 bg-amber-500/10 p-4 text-sm text-amber-100">
                  当前正式分类结果里仍有 {formalConflictCount} 个冲突候选。批准前应先确认最终主类别是否正确。
                </div>
              ) : null}
              <div className="grid gap-4 md:grid-cols-2">
                <InfoRow
                  label="分类状态"
                  value={formatReviewClassificationStatusDisplay(task.classification_result.classification_status)}
                />
                <InfoRow label="主类别" value={task.classification_result.primary_category_code ?? "当前未产出"} />
                <InfoRow
                  label="置信度"
                  value={
                    task.classification_result.confidence != null
                      ? `${(task.classification_result.confidence * 100).toFixed(1)}%`
                      : "-"
                  }
                />
                <InfoRow label="冲突数" value={String(formalConflictCount)} />
                <InfoRow label="需要审核" value={task.classification_result.requires_review ? "是" : "否"} />
              </div>
            </div>
          ) : hasFallbackClassificationContext ? (
            <div className="space-y-4">
              <div className="rounded-2xl border border-amber-400/20 bg-amber-500/10 p-4 text-sm text-amber-100">
                当前缺少正式 `classification_result` 记录。下面这些字段来自审核任务创建时写入的回退信息，可用于判断为什么进人工审核，但不足以把“没有主类别”的任务直接批准。
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <InfoRow
                  label="分类状态（回退）"
                  value={formatReviewClassificationStatusDisplay(reviewPayloadSummary.classificationStatus)}
                />
                <InfoRow label="主类别（回退）" value={reviewPayloadSummary.primaryCategoryCode ?? "当前未产出"} />
                <InfoRow
                  label="置信度（回退）"
                  value={
                    reviewPayloadSummary.confidence != null
                      ? `${(reviewPayloadSummary.confidence * 100).toFixed(1)}%`
                      : "-"
                  }
                />
                <InfoRow label="准入桶（回退）" value={reviewPayloadSummary.admissionBucketCode ?? "-"} />
                <InfoRow
                  label="失败原因（回退）"
                  value={formatReviewReasonDisplay(reviewPayloadSummary.failureReasonCode ?? task.review_reason_code)}
                />
                <InfoRow label="匹配规则数" value={String(reviewPayloadSummary.matchedRuleCodes.length)} />
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400">
              当前没有分类结果，也没有足够的回退字段可供参考。就这个状态而言，不建议直接批准。
            </p>
          )}
        </SoftPanel>
      </section>

      {!isTerminal && task.queue_status === "in_progress" ? (
        <section className="mt-6">
          <SoftPanel
            title="审核操作"
            description={
              canApproveTask
                ? "批准代表接受当前分类结论；退回代表需要人工回退并给出原因。"
                : "当前缺少足够的分类依据，建议优先退回；若系统已明确不能批准，可直接退回而不必手填原因。"
            }
          >
            <div className="space-y-4 text-sm text-slate-300">
              <p>当前审核人：{task.assigned_to ?? actorId}</p>
              <p>
                {canApproveTask
                  ? "如果要退回，请尽量填写明确的原因码，方便后续回溯和统计。"
                  : "这条任务当前更像是“自动分类未产出可接受结论”，应优先退回，不建议直接批准。"}
              </p>
              {!canApproveTask ? (
                <p className="text-amber-200">
                  批准按钮已禁用：当前没有主类别或正式分类结果，系统不能把这条任务视为“已有可接受分类结论”。
                </p>
              ) : null}
              {canAutoRejectWithoutReason ? (
                <p className="text-sky-200">
                  如果你直接退回且不填写原因，系统会自动补全为：
                  {formatReviewReasonDisplay(task.auto_reject_reason_code)}
                </p>
              ) : null}
            </div>

            {showRejectForm ? (
              <div className="mt-4 rounded-2xl border border-rose-400/20 bg-rose-500/10 p-4">
                <label className="block text-sm text-slate-200">
                  退回原因
                  <input
                    type="text"
                    value={rejectReason}
                    onChange={(event) => setRejectReason(event.target.value)}
                    placeholder="可选；若系统已明确不能批准，可留空自动补全"
                    className="mt-2 w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none transition focus:border-rose-300/40"
                  />
                </label>
                <div className="mt-3 flex gap-3">
                  <button
                    type="button"
                    onClick={rejectTask}
                    disabled={actionLoading}
                    className="rounded-2xl border border-rose-300/30 bg-rose-500/10 px-4 py-2 text-sm text-rose-100 transition hover:bg-rose-500/20 disabled:opacity-50"
                  >
                    {actionLoading ? "处理中..." : "确认退回"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowRejectForm(false)
                      setRejectReason("")
                    }}
                    className="rounded-2xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-300 transition hover:bg-white/10"
                  >
                    取消
                  </button>
                </div>
              </div>
            ) : null}
          </SoftPanel>
        </section>
      ) : null}

      {isTerminal ? (
        <section className="mt-6">
          <SoftPanel title="审核结论" description="这条任务已经完成，不再接受新的操作。">
            <div className="flex flex-wrap items-center gap-3">
              <span className={`rounded-full border px-3 py-1.5 text-sm ${statusStyles(task.queue_status)}`}>
                {STATUS_LABELS[task.queue_status]}
              </span>
              <span className="text-sm text-slate-400">
                完成时间：{task.resolved_at ? new Date(task.resolved_at).toLocaleString("zh-CN", { hour12: false }) : "-"}
              </span>
            </div>
          </SoftPanel>
        </section>
      ) : null}
    </main>
  )
}
