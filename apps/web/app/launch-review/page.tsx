"use client"

import { FormEvent, useEffect, useState } from "react"

import { apiGet, apiPost } from "@/lib/api"
import {
  ConsoleMetric,
} from "../components/console-ui"
import { PageIntro } from "../components/page-intro"

import {
  STAGE_OPTIONS,
  formatChecklistLabel,
  formatRecommendationLabel,
  formatReviewStatusLabel,
  recommendationTone,
  reviewTone,
} from "./constants"
import { LaunchActionForms } from "./forms-section"
import { buildLaunchInsights, type LaunchJumpTarget } from "./insights"
import { LaunchReviewsPanel, ShadowRunsPanel } from "./record-panels"
import { LaunchSummaryPanels } from "./summary-panels"
import type {
  DecisionDraft,
  DecisionFeedback,
  LaunchReview,
  LaunchReviewResponse,
  ShadowRun,
} from "./types"

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "操作失败，请稍后重试"
}

export default function LaunchReviewPage() {
  const [shadowRuns, setShadowRuns] = useState<ShadowRun[]>([])
  const [reviews, setReviews] = useState<LaunchReview[]>([])
  const [loading, setLoading] = useState(true)
  const [runningShadow, setRunningShadow] = useState(false)
  const [creatingReview, setCreatingReview] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [decisionDraft, setDecisionDraft] = useState<DecisionDraft | null>(null)
  const [decisionFeedback, setDecisionFeedback] = useState<DecisionFeedback | null>(null)
  const [submittingDecision, setSubmittingDecision] = useState(false)
  const [shadowForm, setShadowForm] = useState({ run_name: "", executed_by: "" })
  const [reviewForm, setReviewForm] = useState<{
    title: string
    stage_name: (typeof STAGE_OPTIONS)[number]
    requested_by: string
    shadow_run_id: string
  }>({ title: "", stage_name: "M6", requested_by: "", shadow_run_id: "" })

  const fetchAll = async () => {
    try {
      const [shadowData, reviewData] = await Promise.all([
        apiGet<{ runs: ShadowRun[] }>("/shadow"),
        apiGet<{ reviews: LaunchReview[] }>("/launch-review"),
      ])
      setShadowRuns(shadowData.runs)
      setReviews(reviewData.reviews)
      setError(null)
    } catch (fetchError) {
      setError(getErrorMessage(fetchError))
    } finally {
      setLoading(false)
      setRunningShadow(false)
      setCreatingReview(false)
    }
  }

  useEffect(() => {
    void fetchAll()
  }, [])

  useEffect(() => {
    if (!decisionDraft) {
      return
    }
    const timer = window.setTimeout(() => {
      document
        .getElementById(`decision-editor-${decisionDraft.reviewId}`)
        ?.scrollIntoView({ behavior: "smooth", block: "nearest" })
    }, 40)
    return () => window.clearTimeout(timer)
  }, [decisionDraft])

  const jumpTo = (target: LaunchJumpTarget) => {
    document.getElementById(target)?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  const handleRunShadow = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setRunningShadow(true)
    setError(null)
    setNotice(null)
    try {
      await apiPost("/shadow/execute", {
        run_name: shadowForm.run_name,
        executed_by: shadowForm.executed_by || null,
      })
      setShadowForm({ run_name: "", executed_by: "" })
      setNotice("影子运行已执行完成，列表已刷新。")
      await fetchAll()
    } catch (runError) {
      setRunningShadow(false)
      setError(getErrorMessage(runError))
    }
  }

  const handleCreateReview = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setCreatingReview(true)
    setError(null)
    setNotice(null)
    try {
      const response = await apiPost<LaunchReviewResponse>("/launch-review", {
        title: reviewForm.title,
        stage_name: reviewForm.stage_name,
        requested_by: reviewForm.requested_by,
        shadow_run_id: reviewForm.shadow_run_id || null,
      })
      const failedChecklistItems = response.review.checklist.filter((item) => !item.passed)
      setReviewForm({ title: "", stage_name: "M6", requested_by: "", shadow_run_id: "" })
      setNotice(
        failedChecklistItems.length > 0
          ? `评审已创建为待决策。当前仍有 ${failedChecklistItems.length} 项检查项未通过，因此暂时不能提交 Go；可先补齐证据后再决策。`
          : "评审已创建为待决策，当前检查项已通过，可继续执行 Go/NoGo 决策。",
      )
      await fetchAll()
    } catch (createError) {
      setCreatingReview(false)
      setError(getErrorMessage(createError))
    }
  }

  const handleDecisionClick = (review: LaunchReview, decision: "go" | "nogo") => {
    const failedChecklistItems = review.checklist.filter((item) => !item.passed)
    if (decision === "go" && failedChecklistItems.length > 0) {
      setNotice(null)
      setError(null)
      setDecisionFeedback({
        reviewId: review.id,
        tone: "warn",
        message: `当前仍有 ${failedChecklistItems.length} 项 checklist 未通过，暂时不能提交 Go。`,
        details: failedChecklistItems.map((item) => formatChecklistLabel(item)),
      })
      setDecisionDraft(null)
      return
    }
    setError(null)
    setNotice(null)
    setDecisionFeedback({
      reviewId: review.id,
      tone: "info",
      message: decision === "go" ? "请在下方填写评审人 ID，然后确认提交 Go。" : "请在下方填写评审人 ID，然后确认提交 NoGo。",
    })
    setDecisionDraft({
      reviewId: review.id,
      decision,
      reviewedBy: "",
      notes: "",
    })
  }

  const handleDecisionSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!decisionDraft?.reviewedBy.trim()) {
      setError("请先填写评审人 ID。")
      return
    }

    setSubmittingDecision(true)
    setError(null)
    setNotice(null)
    try {
      await apiPost(`/launch-review/${decisionDraft.reviewId}/decide`, {
        decision: decisionDraft.decision,
        reviewed_by: decisionDraft.reviewedBy.trim(),
        notes: decisionDraft.notes,
      })
      setNotice(decisionDraft.decision === "go" ? "Go 决策已记录。" : "NoGo 决策已记录。")
      setDecisionDraft(null)
      setDecisionFeedback(null)
      await fetchAll()
    } catch (decisionError) {
      setError(getErrorMessage(decisionError))
    } finally {
      setSubmittingDecision(false)
    }
  }

  const pendingReviewCount = reviews.filter((review) => review.status === "pending").length
  const latestShadow = shadowRuns[0] ?? null
  const latestReview = reviews[0] ?? null
  const insights = buildLaunchInsights(shadowRuns, reviews)

  return (
    <main className="mx-auto max-w-6xl px-4 py-5 md:px-6">
      <PageIntro
        eyebrow="Launch Review"
        title="上线前门槛与 Go/NoGo 评审"
        description="这页回答的是“现在能不能上”。先跑 shadow run，再创建 review，把 backtest、shadow、stage review 和 kill-switch 证据一起看，最后再决定 Go / NoGo。"
        stats={[
          { label: "影子运行", value: String(shadowRuns.length) },
          { label: "待决策评审", value: String(pendingReviewCount) },
        ]}
        guides={[
          {
            title: "先看什么",
            description: "先看最新 shadow run，再创建 review，最后根据 checklist 和 evidence summary 判断能否 Go。",
          },
          {
            title: "什么时候别误判",
            description: "点击“创建评审”后如果 Go 被禁用，通常表示证据门槛未满足，而不是评审创建失败。",
          },
          {
            title: "下一步去哪",
            description: "若 checklist 不通过，优先回到 backtests、reports 或 risk 补齐证据，再重新评审。",
          },
        ]}
      />

      {error ? (
        <div className="mb-6 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      {notice ? (
        <div className="mb-6 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-100">
          {notice}
        </div>
      ) : null}

      <LaunchSummaryPanels insights={insights} onJump={jumpTo} />

      <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <ConsoleMetric label="影子运行" value={String(shadowRuns.length)} />
        <ConsoleMetric
          label="待决策评审"
          value={String(pendingReviewCount)}
          tone={pendingReviewCount > 0 ? "warn" : "good"}
        />
        <ConsoleMetric
          label="最近影子建议"
          value={latestShadow ? formatRecommendationLabel(latestShadow.recommendation) : "-"}
          tone={latestShadow ? recommendationTone(latestShadow.recommendation) : "neutral"}
        />
        <ConsoleMetric
          label="最近评审状态"
          value={latestReview ? formatReviewStatusLabel(latestReview.status) : "-"}
          tone={latestReview ? reviewTone(latestReview.status) : "neutral"}
        />
      </section>

      <LaunchActionForms
        shadowForm={shadowForm}
        reviewForm={reviewForm}
        shadowRuns={shadowRuns}
        runningShadow={runningShadow}
        creatingReview={creatingReview}
        onShadowFormChange={(patch) => setShadowForm((current) => ({ ...current, ...patch }))}
        onReviewFormChange={(patch) => setReviewForm((current) => ({ ...current, ...patch }))}
        onRunShadow={handleRunShadow}
        onCreateReview={handleCreateReview}
      />

      <section id="shadow-runs">
        <ShadowRunsPanel loading={loading} shadowRuns={shadowRuns} />
      </section>

      <section id="reviews">
        <LaunchReviewsPanel
          loading={loading}
          reviews={reviews}
          decisionDraft={decisionDraft}
          decisionFeedback={decisionFeedback}
          submittingDecision={submittingDecision}
          onDecisionClick={handleDecisionClick}
          onDecisionSubmit={handleDecisionSubmit}
          onDecisionDraftChange={(patch) =>
            setDecisionDraft((current) => (current ? { ...current, ...patch } : current))
          }
          onDecisionCancel={() => {
            setDecisionDraft(null)
            setDecisionFeedback(null)
          }}
        />
      </section>
    </main>
  )
}
