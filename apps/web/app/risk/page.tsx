"use client"

import { useEffect, useState, type FormEvent } from "react"

import { apiGet, apiPost } from "@/lib/api"

import { DEFAULT_THRESHOLD_VALUES } from "./constants"
import {
  RiskPageHeader,
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
  ReviewAction,
  RiskStateData,
  ThresholdFormState,
  ThresholdItem,
  ThresholdMetric,
} from "./types"

const INITIAL_KILL_SWITCH_FORM: KillSwitchFormState = {
  request_type: "risk_off",
  target_scope: "global",
  requested_by: "",
  reason: "",
}

const INITIAL_THRESHOLD_FORM: ThresholdFormState = {
  cluster_code: "global",
  metric_name: "max_exposure",
  threshold_value: DEFAULT_THRESHOLD_VALUES.max_exposure,
  created_by: "",
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message
  }
  if (error && typeof error === "object" && "message" in error) {
    const message = (error as { message?: unknown }).message
    if (typeof message === "string") {
      return message
    }
  }
  return "Unexpected error"
}

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
      setError(getErrorMessage(fetchError))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void fetchAll()
  }, [])

  const updateKillSwitchForm = (patch: Partial<KillSwitchFormState>) => {
    setKillSwitchForm((current) => ({ ...current, ...patch }))
  }

  const updateThresholdForm = (patch: Partial<ThresholdFormState>) => {
    setThresholdForm((current) => ({ ...current, ...patch }))
  }

  const handleCompute = async () => {
    setComputing(true)
    setError(null)
    try {
      await apiPost("/risk/exposures/compute")
      await fetchAll()
    } catch (computeError) {
      setError(getErrorMessage(computeError))
    } finally {
      setComputing(false)
    }
  }

  const handleKillSwitchSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!killSwitchForm.requested_by || !killSwitchForm.reason) {
      return
    }

    setSubmitting(true)
    setError(null)
    try {
      await apiPost("/risk/kill-switch", killSwitchForm)
      setKillSwitchForm(INITIAL_KILL_SWITCH_FORM)
      await fetchAll()
    } catch (submitError) {
      setError(getErrorMessage(submitError))
    } finally {
      setSubmitting(false)
    }
  }

  const handleReview = async (id: string, action: ReviewAction) => {
    const reviewer = window.prompt("Reviewer ID")
    if (!reviewer) {
      return
    }
    const notes = window.prompt("Optional review notes") ?? ""

    setError(null)
    try {
      await apiPost(`/risk/kill-switch/${id}/${action}`, { reviewer, notes })
      await fetchAll()
    } catch (reviewError) {
      setError(getErrorMessage(reviewError))
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
      await fetchAll()
    } catch (submitError) {
      setError(getErrorMessage(submitError))
    } finally {
      setSavingThreshold(false)
    }
  }

  const handleDeactivateThreshold = async (threshold: ThresholdItem) => {
    const confirmed = window.confirm(
      `Disable override ${threshold.cluster_code} / ${threshold.metric_name} and fall back to default threshold?`,
    )
    if (!confirmed) {
      return
    }

    setDeactivatingThresholdId(threshold.id)
    setError(null)
    try {
      await apiPost(`/risk/thresholds/${threshold.id}/deactivate`)
      await fetchAll()
    } catch (deactivateError) {
      setError(getErrorMessage(deactivateError))
    } finally {
      setDeactivatingThresholdId(null)
    }
  }

  if (loading) {
    return <div className="p-8 text-slate-300">Loading risk controls...</div>
  }

  const currentState = riskState?.state ?? "Normal"
  const pendingRequests = killSwitchRequests.filter((request) => request.status === "pending")
  const reviewedRequests = killSwitchRequests.filter((request) => request.status !== "pending")
  const breachedClusters = exposures.filter((exposure) => exposure.is_breached)

  return (
    <main className="mx-auto max-w-7xl px-6 py-8 lg:px-10">
      <RiskPageHeader computing={computing} onCompute={handleCompute} />

      {error && (
        <div className="mb-6 rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
      )}

      <RiskSummaryGrid
        currentState={currentState}
        exposureCount={exposures.length}
        breachedCount={breachedClusters.length}
        pendingCount={pendingRequests.length}
      />

      <RiskStatePanel currentState={currentState} latestEvent={riskState?.history[0]} />

      <ExposuresSection exposures={exposures} />

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

      <StateHistorySection history={riskState?.history ?? []} />

      <KillSwitchSection
        killSwitchForm={killSwitchForm}
        pendingRequests={pendingRequests}
        submitting={submitting}
        onSubmit={handleKillSwitchSubmit}
        onFormChange={updateKillSwitchForm}
        onReview={handleReview}
      />

      <ReviewHistorySection requests={reviewedRequests} />
    </main>
  )
}
