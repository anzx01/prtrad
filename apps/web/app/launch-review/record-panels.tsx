import type { FormEventHandler } from "react"

import {
  ConsoleBadge,
  ConsoleButton,
  ConsoleEmpty,
  ConsoleField,
  ConsoleInput,
  ConsoleInset,
  ConsolePanel,
  ConsoleTextarea,
} from "../components/console-ui"
import { formatRiskStateLabel } from "../risk/constants"

import {
  formatChecklistLabel,
  formatDate,
  formatRecommendationLabel,
  formatReviewStatusLabel,
  recommendationTone,
  reviewTone,
} from "./constants"
import { buildLaunchReviewGuidance } from "./guidance"
import { LaunchEvidenceSection } from "./evidence-section"
import type { DecisionDraft, DecisionFeedback, LaunchReview, ShadowRun } from "./types"

export function ShadowRunsPanel({
  loading,
  shadowRuns,
}: {
  loading: boolean
  shadowRuns: ShadowRun[]
}) {
  return (
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
                  <p className="text-sm text-[#c9d1d9]">{formatChecklistLabel(item)}</p>
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
  )
}

export function LaunchReviewsPanel({
  loading,
  reviews,
  decisionDraft,
  decisionFeedback,
  submittingDecision,
  onDecisionClick,
  onDecisionSubmit,
  onDecisionDraftChange,
  onDecisionCancel,
}: {
  loading: boolean
  reviews: LaunchReview[]
  decisionDraft: DecisionDraft | null
  decisionFeedback: DecisionFeedback | null
  submittingDecision: boolean
  onDecisionClick: (review: LaunchReview, decision: "go" | "nogo") => void
  onDecisionSubmit: FormEventHandler<HTMLFormElement>
  onDecisionDraftChange: (patch: Partial<Pick<DecisionDraft, "reviewedBy" | "notes">>) => void
  onDecisionCancel: () => void
}) {
  return (
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
          const guidance = buildLaunchReviewGuidance(review)

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
                  <ConsoleBadge label={formatReviewStatusLabel(review.status)} tone={reviewTone(review.status)} />
                  {review.status === "pending" ? (
                    <>
                      <ConsoleButton type="button" onClick={() => onDecisionClick(review, "go")} tone="success" size="sm">
                        Go
                      </ConsoleButton>
                      <ConsoleButton type="button" onClick={() => onDecisionClick(review, "nogo")} tone="danger" size="sm">
                        NoGo
                      </ConsoleButton>
                    </>
                  ) : null}
                </div>
              </div>

              <div
                className={`mt-4 rounded-xl border p-4 text-sm ${
                  guidance.tone === "bad"
                    ? "border-[#f85149]/35 bg-[#da3633]/12 text-[#ffd8d3]"
                    : guidance.tone === "warn"
                      ? "border-[#d29922]/35 bg-[#9e6a03]/15 text-[#f2cc60]"
                      : guidance.tone === "good"
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-100"
                        : "border-[#58a6ff]/30 bg-[#1f6feb]/10 text-[#c9d1d9]"
                }`}
              >
                <p className="text-[11px] uppercase tracking-[0.22em] text-[#8b949e]">系统结论</p>
                <p className="mt-2 font-medium text-[#e6edf3]">{guidance.conclusion}</p>
                <p className="mt-2 leading-6">{guidance.reason}</p>
                <p className="mt-2 text-xs text-sky-200">建议动作：{guidance.nextActionLabel}</p>
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
                  <form className="mt-4 grid gap-4 md:grid-cols-2" onSubmit={onDecisionSubmit}>
                    <ConsoleField label="评审人 ID">
                      <ConsoleInput
                        value={decisionDraft.reviewedBy}
                        onChange={(event) => onDecisionDraftChange({ reviewedBy: event.target.value })}
                        placeholder="reviewer_a"
                        required
                      />
                    </ConsoleField>
                    <ConsoleField label="备注">
                      <ConsoleTextarea
                        value={decisionDraft.notes}
                        onChange={(event) => onDecisionDraftChange({ notes: event.target.value })}
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
                      <ConsoleButton type="button" onClick={onDecisionCancel} disabled={submittingDecision}>
                        取消
                      </ConsoleButton>
                    </div>
                  </form>
                </div>
              ) : null}

              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {review.checklist.map((item) => (
                  <ConsoleInset key={item.code}>
                    <p className="text-sm text-[#c9d1d9]">{formatChecklistLabel(item)}</p>
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
                      <ConsoleBadge key={item.code} label={`未通过: ${formatChecklistLabel(item)}`} tone="warn" />
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
  )
}
