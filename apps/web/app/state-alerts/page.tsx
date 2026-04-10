"use client"

import { useEffect, useState } from "react"

import { apiGet, apiPost } from "@/lib/api"

interface RiskStateEvent {
  id?: string
  to_state: string
  trigger_type: string
  trigger_metric: string
  trigger_value: number
  threshold_value?: number
  actor_id: string | null
  notes: string | null
  created_at: string
}

interface ExposureItem {
  cluster_code: string
  utilization_rate: number
  limit_value: number
  is_breached: boolean
  position_count: number
  net_exposure: number
}

interface KillSwitchItem {
  id: string
  request_type: string
  target_scope: string
  status: string
  requested_by: string
  created_at: string
}

interface MonitoringMetrics {
  review_queue: {
    pending: number
  }
  dq: {
    recent_failures: number
  }
  tag_quality: {
    open_anomalies: number
  }
}

function formatDate(value: string) {
  return new Date(value).toLocaleString()
}

export default function StateAlertsPage() {
  const [state, setState] = useState<string>("Normal")
  const [history, setHistory] = useState<RiskStateEvent[]>([])
  const [exposures, setExposures] = useState<ExposureItem[]>([])
  const [requests, setRequests] = useState<KillSwitchItem[]>([])
  const [metrics, setMetrics] = useState<MonitoringMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchAll = async () => {
    try {
      const [stateData, exposureData, requestData, metricData] = await Promise.all([
        apiGet<{ state: string }>("/risk/state"),
        apiGet<{ exposures: ExposureItem[] }>("/risk/exposures"),
        apiGet<{ requests: KillSwitchItem[] }>("/risk/kill-switch?status=pending"),
        apiGet<{ metrics: MonitoringMetrics }>("/monitoring/metrics"),
      ])

      const historyData = await apiGet<{ events: RiskStateEvent[] }>("/risk/state/history?limit=20")
      setState(stateData.state)
      setHistory(historyData.events)
      setExposures(exposureData.exposures)
      setRequests(requestData.requests)
      setMetrics(metricData.metrics)
      setError(null)
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Failed to load state & alerts")
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    void fetchAll()
  }, [])

  const handleRefresh = async () => {
    setRefreshing(true)
    setError(null)
    try {
      await apiPost("/risk/exposures/compute")
      await fetchAll()
    } catch (refreshError) {
      setRefreshing(false)
      setError(refreshError instanceof Error ? refreshError.message : "Failed to refresh alerts")
    }
  }

  if (loading) {
    return <main className="mx-auto max-w-6xl px-6 py-8 lg:px-10 text-slate-300">Loading state & alerts...</main>
  }

  const breached = exposures.filter((item) => item.is_breached)

  return (
    <main className="mx-auto max-w-6xl px-6 py-8 lg:px-10">
      <section className="mb-8 flex flex-col gap-4 rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-2">
          <p className="text-sm uppercase tracking-[0.2em] text-sky-200">M4 State & Alerts</p>
          <h1 className="text-3xl font-semibold text-white">Global state machine and alert handling</h1>
          <p className="max-w-3xl text-sm leading-6 text-slate-300">
            Watch the current risk state, breached clusters, pending kill-switch requests, and monitoring alerts in one place.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void handleRefresh()}
          disabled={refreshing}
          className="rounded-full border border-sky-400/40 bg-sky-500/10 px-5 py-2 text-sm text-sky-100 transition hover:bg-sky-500/20 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {refreshing ? "Refreshing..." : "Recompute Exposure"}
        </button>
      </section>

      {error && (
        <div className="mb-6 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
      )}

      <section className="mb-8 grid gap-4 md:grid-cols-4">
        <article className="rounded-3xl border border-white/10 bg-slate-950/50 p-5">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Current State</p>
          <p className="mt-3 text-3xl font-semibold text-white">{state}</p>
        </article>
        <article className="rounded-3xl border border-white/10 bg-slate-950/50 p-5">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Breached Clusters</p>
          <p className="mt-3 text-3xl font-semibold text-white">{breached.length}</p>
        </article>
        <article className="rounded-3xl border border-white/10 bg-slate-950/50 p-5">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Pending Kill-Switch</p>
          <p className="mt-3 text-3xl font-semibold text-white">{requests.length}</p>
        </article>
        <article className="rounded-3xl border border-white/10 bg-slate-950/50 p-5">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">DQ Failures 24h</p>
          <p className="mt-3 text-3xl font-semibold text-white">{metrics?.dq.recent_failures ?? 0}</p>
        </article>
      </section>

      <section className="mb-8 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <article className="rounded-3xl border border-white/10 bg-white/5 p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-medium text-white">Exposure Alerts</h2>
            <span className="text-xs uppercase tracking-[0.2em] text-slate-400">{exposures.length} clusters</span>
          </div>
          <div className="space-y-3">
            {exposures.length === 0 ? (
              <p className="text-sm text-slate-400">No exposure snapshots yet. Recompute once to populate the dashboard.</p>
            ) : (
              exposures.map((item) => (
                <div
                  key={item.cluster_code}
                  className="rounded-2xl border border-white/10 bg-slate-950/50 p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-white">{item.cluster_code}</p>
                      <p className="mt-1 text-sm text-slate-400">
                        Positions {item.position_count} · Net exposure {item.net_exposure.toFixed(2)} / limit {item.limit_value.toFixed(2)}
                      </p>
                    </div>
                    <span className={`rounded-full px-3 py-1 text-xs ${item.is_breached ? "bg-rose-500/20 text-rose-200" : "bg-emerald-500/15 text-emerald-200"}`}>
                      {(item.utilization_rate * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </article>

        <article className="rounded-3xl border border-white/10 bg-white/5 p-6">
          <h2 className="text-xl font-medium text-white">Active Alerts</h2>
          <div className="mt-4 space-y-3">
            <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
              <p className="text-sm text-slate-300">Pending review queue</p>
              <p className="mt-2 text-2xl font-semibold text-white">{metrics?.review_queue.pending ?? 0}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
              <p className="text-sm text-slate-300">Open tag anomalies</p>
              <p className="mt-2 text-2xl font-semibold text-white">{metrics?.tag_quality.open_anomalies ?? 0}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
              <p className="text-sm text-slate-300">Pending kill-switch requests</p>
              <div className="mt-3 space-y-2">
                {requests.length === 0 ? (
                  <p className="text-sm text-slate-400">No pending kill-switch requests.</p>
                ) : (
                  requests.map((request) => (
                    <div key={request.id} className="rounded-2xl border border-white/10 bg-white/5 p-3 text-sm text-slate-200">
                      <p className="font-medium text-white">{request.request_type} · {request.target_scope}</p>
                      <p className="mt-1 text-slate-400">Requested by {request.requested_by} at {formatDate(request.created_at)}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </article>
      </section>

      <section className="rounded-3xl border border-white/10 bg-white/5 p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-medium text-white">State Transition Timeline</h2>
          <span className="text-xs uppercase tracking-[0.2em] text-slate-400">{history.length} events</span>
        </div>
        <div className="space-y-3">
          {history.length === 0 ? (
            <p className="text-sm text-slate-400">No state changes recorded yet.</p>
          ) : (
            history.map((event) => (
              <div key={event.id ?? `${event.created_at}-${event.to_state}`} className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-medium text-white">{event.to_state}</p>
                    <p className="mt-1 text-sm text-slate-400">
                      {event.trigger_type} · {event.trigger_metric} · {formatDate(event.created_at)}
                    </p>
                  </div>
                  <div className="text-right text-sm text-slate-300">
                    <p>Trigger {event.trigger_value.toFixed(3)}</p>
                    {"threshold_value" in event && event.threshold_value !== undefined ? (
                      <p className="text-slate-400">Threshold {event.threshold_value.toFixed(3)}</p>
                    ) : null}
                  </div>
                </div>
                {event.notes ? <p className="mt-3 text-sm text-slate-300">{event.notes}</p> : null}
              </div>
            ))
          )}
        </div>
      </section>
    </main>
  )
}
