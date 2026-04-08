"use client"

import { useEffect, useState } from "react"

import { apiGet, apiPost } from "@/lib/api"

interface StateEvent {
  from_state: string
  to_state: string
  trigger_type: string
  trigger_metric: string
  trigger_value: number
  actor_id: string | null
  notes: string | null
  created_at: string
}

interface RiskStateData {
  state: string
  history: StateEvent[]
}

interface ExposureItem {
  cluster_code: string
  gross_exposure: number
  net_exposure: number
  position_count: number
  limit_value: number
  utilization_rate: number
  is_breached: boolean
  snapshot_at: string
}

interface ThresholdItem {
  id: string
  cluster_code: string
  metric_name: string
  threshold_value: number
  is_active: boolean
  created_by: string
  created_at: string
}

interface KillSwitchItem {
  id: string
  request_type: string
  target_scope: string
  requested_by: string
  reason: string
  status: string
  reviewed_by: string | null
  reviewed_at: string | null
  review_notes: string | null
  created_at: string
}

const STATE_COLORS: Record<string, string> = {
  Normal: "text-emerald-300",
  Caution: "text-yellow-300",
  RiskOff: "text-orange-300",
  Frozen: "text-rose-300",
}

const STATE_PANEL_STYLES: Record<string, string> = {
  Normal: "border-emerald-500/30 bg-emerald-500/10",
  Caution: "border-yellow-500/30 bg-yellow-500/10",
  RiskOff: "border-orange-500/30 bg-orange-500/10",
  Frozen: "border-rose-500/30 bg-rose-500/10",
}

const STATUS_BADGE_STYLES: Record<string, string> = {
  pending: "bg-yellow-500/10 text-yellow-300",
  approved: "bg-emerald-500/10 text-emerald-300",
  rejected: "bg-rose-500/10 text-rose-300",
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
  const [error, setError] = useState<string | null>(null)

  const [killSwitchForm, setKillSwitchForm] = useState({
    request_type: "risk_off",
    target_scope: "global",
    requested_by: "",
    reason: "",
  })

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

  const handleKillSwitchSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!killSwitchForm.requested_by || !killSwitchForm.reason) {
      return
    }

    setSubmitting(true)
    setError(null)
    try {
      await apiPost("/risk/kill-switch", killSwitchForm)
      setKillSwitchForm({
        request_type: "risk_off",
        target_scope: "global",
        requested_by: "",
        reason: "",
      })
      await fetchAll()
    } catch (submitError) {
      setError(getErrorMessage(submitError))
    } finally {
      setSubmitting(false)
    }
  }

  const handleReview = async (id: string, action: "approve" | "reject") => {
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

  if (loading) {
    return <div className="p-8 text-slate-300">Loading risk controls...</div>
  }

  const currentState = riskState?.state ?? "Normal"
  const pendingRequests = killSwitchRequests.filter((request) => request.status === "pending")
  const breachedClusters = exposures.filter((exposure) => exposure.is_breached)

  return (
    <main className="mx-auto max-w-7xl px-6 py-8 lg:px-10">
      <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-cyan-300/80">Milestone 4</p>
          <h1 className="mt-2 text-3xl font-semibold text-white">Portfolio Risk</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-300">
            Monitor cluster exposure, global risk state, active thresholds, and
            manual kill-switch approvals in one place.
          </p>
        </div>

        <button
          onClick={handleCompute}
          disabled={computing}
          className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-500"
        >
          {computing ? "Computing..." : "Compute Exposures"}
        </button>
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
      )}

      <div className="mb-8 grid gap-4 md:grid-cols-4">
        <SummaryCard label="Current State" value={currentState} accent={STATE_COLORS[currentState] ?? "text-white"} />
        <SummaryCard label="Tracked Clusters" value={exposures.length.toString()} />
        <SummaryCard label="Breached Clusters" value={breachedClusters.length.toString()} />
        <SummaryCard label="Pending Requests" value={pendingRequests.length.toString()} />
      </div>

      <section className={`mb-8 rounded-2xl border p-6 ${STATE_PANEL_STYLES[currentState] ?? "border-white/10 bg-white/5"}`}>
        <p className="text-sm text-slate-200/80">Global risk state</p>
        <p className={`mt-2 text-4xl font-semibold ${STATE_COLORS[currentState] ?? "text-white"}`}>{currentState}</p>
        {riskState?.history[0] && (
          <p className="mt-3 text-xs text-slate-200/70">
            Last change at {new Date(riskState.history[0].created_at).toLocaleString()}
            {riskState.history[0].actor_id ? ` by ${riskState.history[0].actor_id}` : " via auto transition"}
          </p>
        )}
      </section>

      <section className="mb-8 rounded-2xl border border-white/10 bg-white/5 p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-medium text-white">Cluster Exposures</h2>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Latest snapshot per cluster</p>
        </div>
        {exposures.length === 0 ? (
          <p className="text-sm text-slate-400">
            No exposure snapshots yet. Run "Compute Exposures" to populate this section.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-white/10 text-sm">
              <thead className="text-left text-xs uppercase tracking-[0.24em] text-slate-400">
                <tr>
                  <th className="pb-3 pr-4">Cluster</th>
                  <th className="pb-3 pr-4 text-right">Gross</th>
                  <th className="pb-3 pr-4 text-right">Net</th>
                  <th className="pb-3 pr-4 text-right">Positions</th>
                  <th className="pb-3 pr-4 text-right">Limit</th>
                  <th className="pb-3 pr-4 text-right">Utilization</th>
                  <th className="pb-3 text-right">Snapshot</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-slate-200">
                {exposures.map((exposure) => (
                  <tr key={exposure.cluster_code} className={exposure.is_breached ? "bg-rose-500/5" : ""}>
                    <td className="py-3 pr-4 font-mono text-xs">{exposure.cluster_code}</td>
                    <td className="py-3 pr-4 text-right">{exposure.gross_exposure.toFixed(4)}</td>
                    <td className="py-3 pr-4 text-right">{exposure.net_exposure.toFixed(4)}</td>
                    <td className="py-3 pr-4 text-right">{exposure.position_count}</td>
                    <td className="py-3 pr-4 text-right">{exposure.limit_value.toFixed(2)}</td>
                    <td className="py-3 pr-4 text-right">
                      <span className={exposure.is_breached ? "text-rose-300" : "text-slate-200"}>
                        {(exposure.utilization_rate * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-3 text-right text-xs text-slate-400">
                      {new Date(exposure.snapshot_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="mb-8 rounded-2xl border border-white/10 bg-white/5 p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-medium text-white">Thresholds</h2>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Active overrides</p>
        </div>
        {thresholds.length === 0 ? (
          <p className="text-sm text-slate-400">
            No explicit threshold overrides found. The backend is currently using default values.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-white/10 text-sm">
              <thead className="text-left text-xs uppercase tracking-[0.24em] text-slate-400">
                <tr>
                  <th className="pb-3 pr-4">Cluster</th>
                  <th className="pb-3 pr-4">Metric</th>
                  <th className="pb-3 pr-4 text-right">Value</th>
                  <th className="pb-3 pr-4">Created By</th>
                  <th className="pb-3 text-right">Created At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-slate-200">
                {thresholds.map((threshold) => (
                  <tr key={threshold.id}>
                    <td className="py-3 pr-4 font-mono text-xs">{threshold.cluster_code}</td>
                    <td className="py-3 pr-4">{threshold.metric_name}</td>
                    <td className="py-3 pr-4 text-right">{threshold.threshold_value.toFixed(4)}</td>
                    <td className="py-3 pr-4">{threshold.created_by}</td>
                    <td className="py-3 text-right text-xs text-slate-400">
                      {new Date(threshold.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {riskState && riskState.history.length > 0 && (
        <section className="mb-8 rounded-2xl border border-white/10 bg-white/5 p-6">
          <h2 className="mb-4 text-xl font-medium text-white">State History</h2>
          <div className="space-y-3">
            {riskState.history.map((event, index) => (
              <div key={`${event.created_at}-${index}`} className="rounded-xl border border-white/10 bg-black/10 p-4">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className={STATE_COLORS[event.from_state] ?? "text-slate-200"}>{event.from_state}</span>
                  <span className="text-slate-500">-&gt;</span>
                  <span className={STATE_COLORS[event.to_state] ?? "text-slate-200"}>{event.to_state}</span>
                  <span className="text-slate-500">[{event.trigger_type}]</span>
                  <span className="font-mono text-xs text-slate-400">{event.trigger_metric}</span>
                </div>
                <div className="mt-2 text-xs text-slate-400">
                  value={event.trigger_value.toFixed(4)} / {new Date(event.created_at).toLocaleString()}
                </div>
                {event.notes && <div className="mt-2 text-sm text-slate-300">{event.notes}</div>}
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
          <h2 className="mb-4 text-xl font-medium text-white">Submit Kill-Switch Request</h2>
          <form onSubmit={handleKillSwitchSubmit} className="space-y-4">
            <Field label="Request Type">
              <select
                value={killSwitchForm.request_type}
                onChange={(event) =>
                  setKillSwitchForm({ ...killSwitchForm, request_type: event.target.value })
                }
                className="w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm text-slate-100"
              >
                <option value="risk_off">RiskOff</option>
                <option value="freeze">Freeze</option>
                <option value="unfreeze">Unfreeze</option>
              </select>
            </Field>

            <Field label="Target Scope">
              <input
                value={killSwitchForm.target_scope}
                onChange={(event) =>
                  setKillSwitchForm({ ...killSwitchForm, target_scope: event.target.value })
                }
                placeholder="global or cluster code"
                className="w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500"
                required
              />
            </Field>

            <Field label="Requested By">
              <input
                value={killSwitchForm.requested_by}
                onChange={(event) =>
                  setKillSwitchForm({ ...killSwitchForm, requested_by: event.target.value })
                }
                placeholder="ops_user"
                className="w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500"
                required
              />
            </Field>

            <Field label="Reason">
              <textarea
                value={killSwitchForm.reason}
                onChange={(event) =>
                  setKillSwitchForm({ ...killSwitchForm, reason: event.target.value })
                }
                placeholder="Describe why this action is needed"
                rows={4}
                className="w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500"
                required
              />
            </Field>

            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-orange-400 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-orange-300 disabled:cursor-not-allowed disabled:bg-slate-500"
            >
              {submitting ? "Submitting..." : "Submit Request"}
            </button>
          </form>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
          <h2 className="mb-4 text-xl font-medium text-white">Pending Approvals</h2>
          {pendingRequests.length === 0 ? (
            <p className="text-sm text-slate-400">No pending kill-switch requests.</p>
          ) : (
            <div className="space-y-3">
              {pendingRequests.map((request) => (
                <div key={request.id} className="rounded-xl border border-yellow-500/20 bg-yellow-500/5 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-sm font-medium uppercase text-slate-100">
                        {request.request_type}
                      </div>
                      <div className="mt-1 text-xs text-slate-400">
                        {request.target_scope} / requested by {request.requested_by}
                      </div>
                      <p className="mt-2 text-sm text-slate-300">{request.reason}</p>
                    </div>
                    <span className="rounded-full bg-yellow-500/15 px-2.5 py-1 text-xs text-yellow-200">
                      pending
                    </span>
                  </div>
                  <div className="mt-4 flex gap-2">
                    <ActionButton label="Approve" tone="approve" onClick={() => handleReview(request.id, "approve")} />
                    <ActionButton label="Reject" tone="reject" onClick={() => handleReview(request.id, "reject")} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {killSwitchRequests.some((request) => request.status !== "pending") && (
        <section className="mt-8 rounded-2xl border border-white/10 bg-white/5 p-6">
          <h2 className="mb-4 text-xl font-medium text-white">Review History</h2>
          <div className="space-y-3">
            {killSwitchRequests
              .filter((request) => request.status !== "pending")
              .map((request) => (
                <div key={request.id} className="flex flex-col gap-2 rounded-xl border border-white/10 bg-black/10 p-4 md:flex-row md:items-start md:justify-between">
                  <div>
                    <div className="text-sm font-medium uppercase text-slate-100">
                      {request.request_type} / {request.target_scope}
                    </div>
                    <div className="mt-1 text-xs text-slate-400">
                      Requested by {request.requested_by}
                      {request.reviewed_by ? ` / reviewed by ${request.reviewed_by}` : ""}
                    </div>
                    <div className="mt-2 text-sm text-slate-300">{request.reason}</div>
                    {request.review_notes && (
                      <div className="mt-2 text-xs text-slate-400">Notes: {request.review_notes}</div>
                    )}
                  </div>
                  <div className="text-right">
                    <span
                      className={`inline-flex rounded-full px-2.5 py-1 text-xs ${
                        STATUS_BADGE_STYLES[request.status] ?? "bg-white/10 text-slate-200"
                      }`}
                    >
                      {request.status}
                    </span>
                    <div className="mt-2 text-xs text-slate-400">
                      {new Date(request.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </section>
      )}
    </main>
  )
}

function SummaryCard({
  label,
  value,
  accent = "text-white",
}: {
  label: string
  value: string
  accent?: string
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
      <div className="text-xs uppercase tracking-[0.24em] text-slate-400">{label}</div>
      <div className={`mt-3 text-3xl font-semibold ${accent}`}>{value}</div>
    </div>
  )
}

function Field({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs uppercase tracking-[0.2em] text-slate-400">{label}</span>
      {children}
    </label>
  )
}

function ActionButton({
  label,
  tone,
  onClick,
}: {
  label: string
  tone: "approve" | "reject"
  onClick: () => void
}) {
  const className =
    tone === "approve"
      ? "bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20"
      : "bg-rose-500/10 text-rose-300 hover:bg-rose-500/20"

  return (
    <button
      className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${className}`}
      onClick={onClick}
      type="button"
    >
      {label}
    </button>
  )
}
