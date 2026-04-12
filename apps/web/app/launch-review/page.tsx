"use client"

import { FormEvent, useEffect, useState } from "react"

import { apiGet, apiPost } from "@/lib/api"
import {
  ConsoleBadge,
  ConsoleButton,
  ConsoleCallout,
  ConsoleEmpty,
  ConsoleField,
  ConsoleInput,
  ConsoleInset,
  ConsoleMetric,
  ConsolePanel,
  ConsoleSelect,
  ConsoleTextarea,
} from "../components/console-ui"
import { PageIntro } from "../components/page-intro"
import { formatRiskStateLabel } from "../risk/constants"

import { LaunchEvidenceSection, type LaunchEvidenceSummary } from "./evidence-section"

interface ShadowRun {
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
  checklist: Array<{ code: string; label: string; passed: boolean }>
  created_at: string
}

interface LaunchReview {
  id: string
  title: string
  stage_name: string
  shadow_run_id: string | null
  requested_by: string
  reviewed_by: string | null
  status: "pending" | "go" | "nogo"
  checklist: Array<{ code: string; label: string; passed: boolean }>
  evidence_summary: LaunchEvidenceSummary | null
  review_notes: string | null
  decided_at: string | null
  created_at: string
}

interface LaunchReviewResponse {
  review: LaunchReview
}

interface DecisionDraft {
  reviewId: string
  decision: "go" | "nogo"
  reviewedBy: string
  notes: string
}

interface DecisionFeedback {
  reviewId: string
  tone: "info" | "warn" | "bad"
  message: string
  details?: string[]
}

const STAGE_OPTIONS = ["M4", "M5", "M6"] as const

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString("zh-CN") : "-"
}

function formatRecommendationLabel(value: ShadowRun["recommendation"]) {
  return value === "go" ? "Go" : value === "watch" ? "观察" : "阻断"
}

function recommendationTone(value: ShadowRun["recommendation"]) {
  return value === "go" ? "good" : value === "watch" ? "warn" : "bad"
}

function reviewTone(value: LaunchReview["status"]) {
  return value === "go" ? "good" : value === "nogo" ? "bad" : "warn"
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
      setError(fetchError instanceof Error ? fetchError.message : "加载上线评审数据失败，请稍后重试")
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
      setError(runError instanceof Error ? runError.message : "执行影子运行失败，请稍后重试")
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
      setError(createError instanceof Error ? createError.message : "创建上线评审失败，请稍后重试")
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
        details: failedChecklistItems.map((item) => item.label),
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
      setError(decisionError instanceof Error ? decisionError.message : "记录评审决策失败，请稍后重试")
    } finally {
      setSubmittingDecision(false)
    }
  }

  const pendingReviewCount = reviews.filter((review) => review.status === "pending").length

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

      <ConsoleCallout
        title="Go 被禁用时，通常是门槛没过，不是页面创建失败。"
        description="如果创建 review 后 `Go` 不可点，优先看 checklist 里缺的是哪一块证据，然后回到 backtests、reports 或 risk 补齐。"
        tone="info"
      />

      <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <ConsoleMetric label="影子运行" value={String(shadowRuns.length)} />
        <ConsoleMetric
          label="待决策评审"
          value={String(pendingReviewCount)}
          tone={pendingReviewCount > 0 ? "warn" : "good"}
        />
        <ConsoleMetric
          label="最近影子建议"
          value={shadowRuns[0] ? formatRecommendationLabel(shadowRuns[0].recommendation) : "-"}
          tone={shadowRuns[0] ? recommendationTone(shadowRuns[0].recommendation) : "neutral"}
        />
        <ConsoleMetric
          label="最近评审状态"
          value={reviews[0] ? (reviews[0].status === "pending" ? "待决策" : reviews[0].status === "go" ? "Go" : "NoGo") : "-"}
          tone={reviews[0] ? reviewTone(reviews[0].status) : "neutral"}
        />
      </section>

      <section className="mt-6 grid gap-6 lg:grid-cols-2">
        <ConsolePanel
          className="bg-[#0d1117]"
          title="执行影子运行"
          description="先用 shadow run 确认当前风险状态和核心检查项，再决定是否进入正式评审。"
        >
          <form className="space-y-4" onSubmit={handleRunShadow}>
            <ConsoleField label="运行名称">
              <ConsoleInput
                value={shadowForm.run_name}
                onChange={(event) => setShadowForm((current) => ({ ...current, run_name: event.target.value }))}
                placeholder="shadow-20260410"
              />
            </ConsoleField>
            <ConsoleField label="执行人">
              <ConsoleInput
                value={shadowForm.executed_by}
                onChange={(event) => setShadowForm((current) => ({ ...current, executed_by: event.target.value }))}
                placeholder="ops_lead"
              />
            </ConsoleField>
            <ConsoleButton type="submit" disabled={runningShadow} tone="primary">
              {runningShadow ? "执行中..." : "执行影子运行"}
            </ConsoleButton>
          </form>
        </ConsolePanel>

        <ConsolePanel
          className="bg-[#0d1117]"
          title="创建上线评审"
          description="把当前阶段、申请人和关联的 shadow run 固定下来，形成一条可追溯的 Go/NoGo 决策记录。"
        >
          <form className="space-y-4" onSubmit={handleCreateReview}>
            <ConsoleField label="评审标题">
              <ConsoleInput
                value={reviewForm.title}
                onChange={(event) => setReviewForm((current) => ({ ...current, title: event.target.value }))}
                placeholder="M6 上线准备评审"
              />
            </ConsoleField>
            <div className="grid gap-4 md:grid-cols-2">
              <ConsoleField label="阶段">
                <ConsoleSelect
                  value={reviewForm.stage_name}
                  onChange={(event) =>
                    setReviewForm((current) => ({
                      ...current,
                      stage_name: event.target.value as (typeof STAGE_OPTIONS)[number],
                    }))
                  }
                >
                  {STAGE_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </ConsoleSelect>
              </ConsoleField>
              <ConsoleField label="申请人">
                <ConsoleInput
                  value={reviewForm.requested_by}
                  onChange={(event) => setReviewForm((current) => ({ ...current, requested_by: event.target.value }))}
                  required
                />
              </ConsoleField>
            </div>
            <ConsoleField label="关联影子运行" hint="如不指定，将默认使用最近一次影子运行。">
              <ConsoleSelect
                value={reviewForm.shadow_run_id}
                onChange={(event) => setReviewForm((current) => ({ ...current, shadow_run_id: event.target.value }))}
              >
                <option value="">使用最近一次影子运行</option>
                {shadowRuns.map((run) => (
                  <option key={run.id} value={run.id}>
                    {run.run_name} / {formatRecommendationLabel(run.recommendation)}
                  </option>
                ))}
              </ConsoleSelect>
            </ConsoleField>
            <ConsoleButton type="submit" disabled={creatingReview} tone="primary">
              {creatingReview ? "创建中..." : "创建评审"}
            </ConsoleButton>
          </form>
        </ConsolePanel>
      </section>

      <ConsolePanel
        className="mt-8"
        title="最近影子运行"
        description="优先看建议结论、运行时风险状态，以及还有没有越限簇没解释清楚。"
        actions={<ConsoleBadge label={`${shadowRuns.length} 条`} tone="neutral" />}
      >
        {loading ? <p className="text-sm text-[#8b949e]">正在加载影子运行...</p> : null}
        {!loading && shadowRuns.length === 0 ? (
          <ConsoleEmpty
            title="当前还没有影子运行记录"
            description="先执行一次 shadow run，才能让后续上线评审拥有足够证据。"
          />
        ) : null}
        <div className="space-y-4">
          {shadowRuns.map((run) => (
            <ConsoleInset key={run.id}>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h3 className="text-lg font-medium text-[#e6edf3]">{run.run_name}</h3>
                  <p className="mt-1 text-sm text-[#8b949e]">
                    {formatDate(run.created_at)} / 风险状态 {formatRiskStateLabel(run.risk_state)}
                  </p>
                  <p className="mt-2 text-sm text-[#c9d1d9]">
                    {(run.summary.exposure_summary?.breached_clusters?.length ?? 0) > 0
                      ? `仍有 ${run.summary.exposure_summary?.breached_clusters?.length ?? 0} 个越限簇待解释：${run.summary.exposure_summary?.breached_clusters?.slice(0, 3).join("、")}${(run.summary.exposure_summary?.breached_clusters?.length ?? 0) > 3 ? " 等" : ""}`
                      : "当前影子运行未看到越限簇，可继续结合 checklist 判断是否进入评审。"}
                  </p>
                </div>
                <ConsoleBadge
                  label={formatRecommendationLabel(run.recommendation)}
                  tone={recommendationTone(run.recommendation)}
                />
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {run.checklist.map((item) => (
                  <ConsoleInset key={item.code}>
                    <p className="text-sm text-[#c9d1d9]">{item.label}</p>
                    <p className={`mt-2 font-medium ${item.passed ? "text-[#3fb950]" : "text-[#f85149]"}`}>
                      {item.passed ? "通过" : "未通过"}
                    </p>
                  </ConsoleInset>
                ))}
              </div>
            </ConsoleInset>
          ))}
        </div>
      </ConsolePanel>

      <ConsolePanel
        className="mt-8"
        title="上线评审记录"
        description="每一条评审都应该能解释：现在能不能 Go、为什么不能 Go、缺的是哪块证据。"
        actions={<ConsoleBadge label={`${reviews.length} 条`} tone="neutral" />}
      >
        {loading ? <p className="text-sm text-[#8b949e]">正在加载评审记录...</p> : null}
        {!loading && reviews.length === 0 ? (
          <ConsoleEmpty
            title="当前还没有上线评审记录"
            description="在完成 shadow run 后创建一条 review，这里就会开始沉淀真正的 Go/NoGo 决策链。"
          />
        ) : null}
        <div className="space-y-4">
          {reviews.map((review) => {
            const hasFailedChecklist = review.checklist.some((item) => !item.passed)
            const failedChecklistItems = review.checklist.filter((item) => !item.passed)

            return (
              <ConsoleInset key={review.id}>
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h3 className="text-lg font-medium text-[#e6edf3]">{review.title}</h3>
                    <p className="mt-1 text-sm text-[#8b949e]">
                      {review.stage_name} / 申请人 {review.requested_by} / {formatDate(review.created_at)}
                    </p>
                  </div>
                <div className="flex items-center gap-2">
                  <ConsoleBadge
                    label={review.status === "go" ? "Go" : review.status === "nogo" ? "NoGo" : "待决策"}
                    tone={reviewTone(review.status)}
                  />
                    {review.status === "pending" ? (
                      <>
                        <ConsoleButton
                          type="button"
                          onClick={() => handleDecisionClick(review, "go")}
                          tone="success"
                          size="sm"
                        >
                          Go
                        </ConsoleButton>
                        <ConsoleButton
                          type="button"
                          onClick={() => handleDecisionClick(review, "nogo")}
                          tone="danger"
                          size="sm"
                        >
                          NoGo
                        </ConsoleButton>
                      </>
                    ) : null}
                  </div>
                </div>

                {decisionFeedback?.reviewId === review.id ? (
                  <div
                    id={`decision-editor-${review.id}`}
                    className={`mt-4 rounded-xl border p-4 text-sm ${
                      decisionFeedback.tone === "bad"
                        ? "border-[#f85149]/35 bg-[#da3633]/12 text-[#ffd8d3]"
                        : decisionFeedback.tone === "warn"
                          ? "border-[#d29922]/35 bg-[#9e6a03]/15 text-[#f2cc60]"
                          : "border-[#58a6ff]/30 bg-[#1f6feb]/10 text-[#c9d1d9]"
                    }`}
                  >
                    <p className="font-medium text-[#e6edf3]">{decisionFeedback.message}</p>
                    {decisionFeedback.details && decisionFeedback.details.length > 0 ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {decisionFeedback.details.map((detail) => (
                          <ConsoleBadge key={detail} label={detail} tone="warn" />
                        ))}
                      </div>
                    ) : null}
                  </div>
                ) : null}

                {decisionDraft?.reviewId === review.id ? (
                  <div className="mt-4 rounded-xl border border-[#58a6ff]/30 bg-[#1f6feb]/10 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="console-kicker">确认决策</p>
                        <p className="mt-2 text-sm text-[#e6edf3]">
                          你将为这条评审提交
                          {decisionDraft.decision === "go" ? " Go " : " NoGo "}
                          决策。
                        </p>
                      </div>
                      <ConsoleBadge
                        label={decisionDraft.decision === "go" ? "准备提交 Go" : "准备提交 NoGo"}
                        tone={decisionDraft.decision === "go" ? "good" : "bad"}
                      />
                    </div>
                    <form className="mt-4 grid gap-4 md:grid-cols-2" onSubmit={handleDecisionSubmit}>
                      <ConsoleField label="评审人 ID">
                        <ConsoleInput
                          value={decisionDraft.reviewedBy}
                          onChange={(event) =>
                            setDecisionDraft((current) =>
                              current
                                ? { ...current, reviewedBy: event.target.value }
                                : current,
                            )
                          }
                          placeholder="reviewer_a"
                          required
                        />
                      </ConsoleField>
                      <ConsoleField label="备注">
                        <ConsoleTextarea
                          value={decisionDraft.notes}
                          onChange={(event) =>
                            setDecisionDraft((current) =>
                              current
                                ? { ...current, notes: event.target.value }
                                : current,
                            )
                          }
                          rows={3}
                          placeholder="可选，补充这次 Go/NoGo 的背景说明"
                        />
                      </ConsoleField>
                      <div className="flex flex-wrap gap-2 md:col-span-2">
                        <ConsoleButton type="submit" tone={decisionDraft.decision === "go" ? "success" : "danger"} disabled={submittingDecision}>
                          {submittingDecision
                            ? "提交中..."
                            : decisionDraft.decision === "go"
                              ? "确认提交 Go"
                              : "确认提交 NoGo"}
                        </ConsoleButton>
                        <ConsoleButton
                          type="button"
                          onClick={() => {
                            setDecisionDraft(null)
                            setDecisionFeedback(null)
                          }}
                          disabled={submittingDecision}
                        >
                          取消
                        </ConsoleButton>
                      </div>
                    </form>
                  </div>
                ) : null}

                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {review.checklist.map((item) => (
                    <ConsoleInset key={item.code}>
                      <p className="text-sm text-[#c9d1d9]">{item.label}</p>
                      <p className={`mt-2 font-medium ${item.passed ? "text-[#3fb950]" : "text-[#f85149]"}`}>
                        {item.passed ? "通过" : "未通过"}
                      </p>
                    </ConsoleInset>
                  ))}
                </div>

                <LaunchEvidenceSection evidence={review.evidence_summary} />

                {review.status === "pending" && hasFailedChecklist ? (
                  <div className="mt-4 rounded-xl border border-[#d29922]/35 bg-[#9e6a03]/15 p-4 text-sm text-[#f2cc60]">
                    <p className="font-medium text-[#fff2c9]">
                      该 review 已创建成功，但当前仍有未通过的 checklist，因此暂时不能提交 Go。
                    </p>
                    <p className="mt-2">
                      可先补齐 backtest / shadow / stage review 证据，或清空待处理 kill-switch；在所有门槛通过前，仍可保持 pending 或提交 NoGo。
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {failedChecklistItems.map((item) => (
                        <ConsoleBadge key={item.code} label={`未通过: ${item.label}`} tone="warn" />
                      ))}
                    </div>
                  </div>
                ) : null}

                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  <ConsoleInset>
                    <p className="console-kicker">评审人</p>
                    <p className="mt-2 text-sm text-[#e6edf3]">{review.reviewed_by ?? "-"}</p>
                  </ConsoleInset>
                  <ConsoleInset>
                    <p className="console-kicker">决策时间</p>
                    <p className="mt-2 text-sm text-[#e6edf3]">{formatDate(review.decided_at)}</p>
                  </ConsoleInset>
                  <ConsoleInset>
                    <p className="console-kicker">备注</p>
                    <p className="mt-2 text-sm text-[#e6edf3]">{review.review_notes ?? "-"}</p>
                  </ConsoleInset>
                </div>
              </ConsoleInset>
            )
          })}
        </div>
      </ConsolePanel>
    </main>
  )
}
