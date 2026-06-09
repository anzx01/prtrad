"use client"

import { useEffect, useState, type FormEvent } from "react"

import { apiGet, apiPost } from "@/lib/api"
import { PageIntro } from "../components/page-intro"

import {
  buildSuggestedKillSwitchReason,
  DEFAULT_THRESHOLD_VALUES,
  formatRiskStateLabel,
  formatThresholdMetricLabel,
  getRiskErrorMessage,
  INITIAL_KILL_SWITCH_FORM,
  INITIAL_THRESHOLD_FORM,
} from "./constants"
import { buildRiskInsights, type RiskJumpTarget } from "./insights"
import {
  RiskPageHeader,
  RiskPrioritySection,
  RiskStatePanel,
  RiskSummaryGrid,
} from "./overview"
import {
  ExposuresSection,
  StateHistorySection,
} from "./exposure-sections"
import {
  ThresholdsSection,
} from "./threshold-section"
import {
  KillSwitchSection,
  ReviewHistorySection,
} from "./kill-switch-sections"
import type {
  ExposureItem,
  KillSwitchFormState,
  KillSwitchItem,
  KillSwitchReviewDraft,
  ReviewAction,
  RiskStateData,
  ThresholdFormState,
  ThresholdItem,
  ThresholdMetric,
} from "./types"

export default function RiskPage() {
  const [riskState, setRiskState] = useState<RiskStateData | null>(null)
  const [exposures, setExposures] = useState<ExposureItem[]>([])
  const [thresholds, setThresholds] = useState<ThresholdItem[]>([])
  const [killSwitchRequests, setKillSwitchRequests] = useState<KillSwitchItem[]>([])
  const [loading, setLoading] = useState(true)
  const [computing, setComputing] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [savingThreshold, setSavingThreshold] = useState(false)
  const [deactivatingThresholdId, setDeactivatingThresholdId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [reviewDraft, setReviewDraft] = useState<KillSwitchReviewDraft | null>(null)
  const [reviewSubmitting, setReviewSubmitting] = useState(false)

  const [killSwitchForm, setKillSwitchForm] = useState<KillSwitchFormState>(INITIAL_KILL_SWITCH_FORM)
  const [thresholdForm, setThresholdForm] = useState<ThresholdFormState>(INITIAL_THRESHOLD_FORM)

  const fetchAll = async () => {
    try {
      const [stateData, exposureData, thresholdData, requestData] = await Promise.all([
        apiGet<RiskStateData>("/risk/state"),
        apiGet<{ exposures: ExposureItem[] }>("/risk/exposures"),
        apiGet<{ thresholds: ThresholdItem[] }>("/risk/thresholds"),
        apiGet<{ requests: KillSwitchItem[] }>("/risk/kill-switch"),
      ])

      setRiskState(stateData)
      setExposures(exposureData.exposures)
      setThresholds(thresholdData.thresholds)
      setKillSwitchRequests(requestData.requests)
      setError(null)
    } catch (fetchError) {
      setError(getRiskErrorMessage(fetchError))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void fetchAll()
  }, [])

  const jumpTo = (target: RiskJumpTarget) => {
    document.getElementById(target)?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  const updateKillSwitchForm = (patch: Partial<KillSwitchFormState>) => {
    setKillSwitchForm((current) => ({ ...current, ...patch }))
  }

  const updateThresholdForm = (patch: Partial<ThresholdFormState>) => {
    setThresholdForm((current) => ({ ...current, ...patch }))
  }

  const handleCompute = async () => {
    setComputing(true)
    setError(null)
    setNotice(null)
    try {
      await apiPost("/risk/exposures/compute")
      setNotice("最新暴露快照已重算，页面数据已刷新。")
      await fetchAll()
    } catch (computeError) {
      setError(getRiskErrorMessage(computeError))
    } finally {
      setComputing(false)
    }
  }

  const handleKillSwitchSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!killSwitchForm.requested_by || !killSwitchForm.reason) {
      setError("请先填写申请人和原因")
      return
    }

    setSubmitting(true)
    setError(null)
    setNotice(null)
    try {
      await apiPost("/risk/kill-switch", killSwitchForm)
      setKillSwitchForm(INITIAL_KILL_SWITCH_FORM)
      setNotice("人工风险动作已提交，待审批区已刷新。")
      await fetchAll()
    } catch (submitError) {
      setError(getRiskErrorMessage(submitError))
    } finally {
      setSubmitting(false)
    }
  }

  const handleReviewStart = (request: KillSwitchItem, action: ReviewAction) => {
    setReviewDraft({
      requestId: request.id,
      action,
      reviewer: request.reviewed_by ?? "",
      notes: request.review_notes ?? "",
    })
    setError(null)
    setNotice(null)
  }

  const handleReviewSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!reviewDraft?.reviewer.trim()) {
      setError("请先填写审批人 ID")
      return
    }

    setReviewSubmitting(true)
    setError(null)
    setNotice(null)
    try {
      await apiPost(`/risk/kill-switch/${reviewDraft.requestId}/${reviewDraft.action}`, {
        reviewer: reviewDraft.reviewer.trim(),
        notes: reviewDraft.notes.trim() || null,
      })
      setNotice(reviewDraft.action === "approve" ? "风险动作已批准。" : "风险动作已拒绝。")
      setReviewDraft(null)
      await fetchAll()
    } catch (reviewError) {
      setError(getRiskErrorMessage(reviewError))
    } finally {
      setReviewSubmitting(false)
    }
  }

  const handleThresholdMetricChange = (metric: ThresholdMetric) => {
    setThresholdForm((current) => ({
      ...current,
      metric_name: metric,
      threshold_value: DEFAULT_THRESHOLD_VALUES[metric],
    }))
  }

  const handleThresholdSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const thresholdValue = Number.parseFloat(thresholdForm.threshold_value)
    if (!thresholdForm.cluster_code.trim() || !thresholdForm.created_by.trim()) {
      setError("请填写阈值簇和操作人")
      return
    }
    if (Number.isNaN(thresholdValue) || thresholdValue <= 0) {
      setError("阈值必须是大于 0 的数字")
      return
    }

    setSavingThreshold(true)
    setError(null)
    setNotice(null)
    try {
      await apiPost("/risk/thresholds", {
        cluster_code: thresholdForm.cluster_code.trim(),
        metric_name: thresholdForm.metric_name,
        threshold_value: thresholdValue,
        created_by: thresholdForm.created_by.trim(),
      })
      setThresholdForm((current) => ({
        ...current,
        created_by: "",
        threshold_value: DEFAULT_THRESHOLD_VALUES[current.metric_name],
      }))
      setNotice("阈值覆盖已保存。")
      await fetchAll()
    } catch (submitError) {
      setError(getRiskErrorMessage(submitError))
    } finally {
      setSavingThreshold(false)
    }
  }

  const handleDeactivateThreshold = async (threshold: ThresholdItem) => {
    const confirmed = window.confirm(
      `确认停用 ${threshold.cluster_code} / ${formatThresholdMetricLabel(threshold.metric_name)} 覆盖，并恢复为默认阈值吗？`,
    )
    if (!confirmed) {
      return
    }

    setDeactivatingThresholdId(threshold.id)
    setError(null)
    setNotice(null)
    try {
      await apiPost(`/risk/thresholds/${threshold.id}/deactivate`)
      setNotice("阈值覆盖已停用，系统已恢复默认阈值。")
      await fetchAll()
    } catch (deactivateError) {
      setError(getRiskErrorMessage(deactivateError))
    } finally {
      setDeactivatingThresholdId(null)
    }
  }

  if (loading) {
    return <div className="p-8 text-slate-300">正在加载风控数据...</div>
  }

  const currentState = riskState?.state ?? "Normal"
  const currentStateLabel = formatRiskStateLabel(currentState)
  const pendingRequests = killSwitchRequests.filter((request) => request.status === "pending")
  const reviewedRequests = killSwitchRequests.filter((request) => request.status !== "pending")
  const breachedClusters = exposures.filter((exposure) => exposure.is_breached)
  const pendingCount = pendingRequests.length
  const breachedCount = breachedClusters.length
  const suggestedKillSwitchReason = buildSuggestedKillSwitchReason({
    requestType: killSwitchForm.request_type,
    currentState,
    breachedClusters: breachedClusters.map((item) => item.cluster_code),
  })
  const insights = buildRiskInsights({
    riskState,
    exposures,
    thresholds,
    killSwitchRequests,
  })

  return (
    <main className="mx-auto max-w-7xl px-4 py-5 md:px-6">
      <PageIntro
        eyebrow="Risk"
        title="组合风控"
        description="这页回答的是“系统现在安不安全、要不要人工介入”。先看当前风险状态和越限簇，再看 kill-switch 审批与阈值覆盖，最后回看状态历史。"
        stats={[
          { label: "当前状态", value: currentStateLabel },
          { label: "待处理请求", value: String(pendingCount) },
        ]}
        guides={[
          {
            title: "先看什么",
            description: "先看系统当前判断，再按按钮跳到待审批请求、越限簇或阈值覆盖，不要自己在页面里来回找。",
          },
          {
            title: "什么时候要动作",
            description: "系统停在 RiskOff / 冻结、存在越限簇、或有待审批请求挂起时，都意味着这里不是只看一眼就能离开。",
          },
          {
            title: "下一步去哪",
            description: "需要看告警概览去 state-alerts；需要判断能否上线则继续去 launch-review。",
          },
        ]}
      />

      <RiskPageHeader
        computing={computing}
        onCompute={handleCompute}
        actions={insights.headline.actions}
        onJump={jumpTo}
        title={insights.headline.title}
        summary={insights.headline.description}
        tone={insights.headline.tone}
      />

      {error && (
        <div className="mb-6 rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
      )}
      {notice && (
        <div className="mb-6 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-100">
          {notice}
        </div>
      )}

      <RiskSummaryGrid
        currentState={currentState}
        exposureCount={exposures.length}
        breachedCount={breachedCount}
        pendingCount={pendingCount}
      />

      <RiskPrioritySection priorities={insights.priorities} spotlight={insights.spotlight} onJump={jumpTo} />

      <section id="state">
        <RiskStatePanel currentState={currentState} latestEvent={riskState?.history[0]} />
      </section>

      <section id="exposures">
        <ExposuresSection exposures={exposures} />
      </section>

      <section id="thresholds">
        <ThresholdsSection
          thresholdForm={thresholdForm}
          savingThreshold={savingThreshold}
          thresholds={thresholds}
          deactivatingThresholdId={deactivatingThresholdId}
          onSubmit={handleThresholdSubmit}
          onFormChange={updateThresholdForm}
          onMetricChange={handleThresholdMetricChange}
          onDeactivate={handleDeactivateThreshold}
        />
      </section>

      <section id="history">
        <StateHistorySection history={riskState?.history ?? []} />
      </section>

      <KillSwitchSection
        killSwitchForm={killSwitchForm}
        suggestedReason={suggestedKillSwitchReason}
        pendingRequests={pendingRequests}
        submitting={submitting}
        reviewDraft={reviewDraft}
        reviewSubmitting={reviewSubmitting}
        onSubmit={handleKillSwitchSubmit}
        onFormChange={updateKillSwitchForm}
        onUseSuggestedReason={() => updateKillSwitchForm({ reason: suggestedKillSwitchReason })}
        onReviewStart={handleReviewStart}
        onReviewDraftChange={(patch) =>
          setReviewDraft((current) => (current ? { ...current, ...patch } : current))
        }
        onReviewSubmit={handleReviewSubmit}
        onReviewCancel={() => setReviewDraft(null)}
      />

      <ReviewHistorySection requests={reviewedRequests} />
    </main>
  )
}
