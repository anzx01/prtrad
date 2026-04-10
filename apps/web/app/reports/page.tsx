"use client"

import { useEffect, useState } from "react"

import { apiGet, apiPost } from "@/lib/api"

interface ReportRecord {
  id: string
  report_type: string
  report_period_start: string
  report_period_end: string
  generated_at: string
  generated_by: string | null
  report_data: Record<string, unknown>
}

interface AuditRecord {
  id: string
  actor_id: string | null
  object_type: string
  action: string
  result: string
  created_at: string
  event_payload: Record<string, unknown> | null
}

function formatDate(value: string) {
  return new Date(value).toLocaleString()
}

const REPORT_ACTIONS = [
  { report_type: "daily_summary", label: "Generate Daily Summary" },
  { report_type: "weekly_summary", label: "Generate Weekly Summary" },
  { report_type: "stage_review", label: "Generate Stage Review" },
] as const

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportRecord[]>([])
  const [auditEvents, setAuditEvents] = useState<AuditRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchAll = async () => {
    try {
      const [reportData, auditData] = await Promise.all([
        apiGet<{ reports: ReportRecord[] }>("/reports"),
        apiGet<{ audit_events: AuditRecord[] }>("/reports/audit?limit=20"),
      ])
      setReports(reportData.reports)
      setAuditEvents(auditData.audit_events)
      setError(null)
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Failed to load reports")
    } finally {
      setLoading(false)
      setSubmitting(null)
    }
  }

  useEffect(() => {
    void fetchAll()
  }, [])

  const handleGenerate = async (reportType: string) => {
    setSubmitting(reportType)
    setError(null)
    try {
      await apiPost("/reports/generate", {
        report_type: reportType,
        generated_by: "web_console",
        stage_name: reportType === "stage_review" ? "M6" : null,
      })
      await fetchAll()
    } catch (generateError) {
      setSubmitting(null)
      setError(generateError instanceof Error ? generateError.message : "Failed to generate report")
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-8 lg:px-10">
      <section className="mb-8 rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur">
        <p className="text-sm uppercase tracking-[0.2em] text-sky-200">M5 Reports & Audit</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Daily, weekly, and stage-level reporting</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
          Generate structured reports from decisions, risk-state events, backtests, and audit records. Reports are marked auditable when the required logs are present.
        </p>
      </section>

      {error ? (
        <div className="mb-6 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      <section className="mb-8 flex flex-wrap gap-3">
        {REPORT_ACTIONS.map((action) => (
          <button
            key={action.report_type}
            type="button"
            onClick={() => void handleGenerate(action.report_type)}
            disabled={submitting !== null}
            className="rounded-full border border-sky-400/40 bg-sky-500/10 px-5 py-2 text-sm text-sky-100 transition hover:bg-sky-500/20 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting === action.report_type ? "Generating..." : action.label}
          </button>
        ))}
      </section>

      <section className="mb-8 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <article className="rounded-3xl border border-white/10 bg-white/5 p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-medium text-white">Report archive</h2>
            <span className="text-xs uppercase tracking-[0.2em] text-slate-400">{reports.length} items</span>
          </div>
          {loading ? <p className="text-sm text-slate-300">Loading reports...</p> : null}
          {!loading && reports.length === 0 ? <p className="text-sm text-slate-400">No reports generated yet.</p> : null}
          <div className="space-y-4">
            {reports.map((report) => (
              <div key={report.id} className="rounded-2xl border border-white/10 bg-slate-950/50 p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="font-medium text-white">{report.report_type}</h3>
                    <p className="mt-1 text-sm text-slate-400">
                      {formatDate(report.report_period_start)} to {formatDate(report.report_period_end)}
                    </p>
                  </div>
                  <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-slate-200">
                    {formatDate(report.generated_at)}
                  </span>
                </div>
                <pre className="mt-4 overflow-x-auto rounded-2xl border border-white/10 bg-black/20 p-4 text-xs text-slate-300">
                  {JSON.stringify(report.report_data, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        </article>

        <article className="rounded-3xl border border-white/10 bg-white/5 p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-medium text-white">Recent audit events</h2>
            <span className="text-xs uppercase tracking-[0.2em] text-slate-400">{auditEvents.length} items</span>
          </div>
          {loading ? <p className="text-sm text-slate-300">Loading audit trail...</p> : null}
          {!loading && auditEvents.length === 0 ? <p className="text-sm text-slate-400">No audit records yet.</p> : null}
          <div className="space-y-3">
            {auditEvents.map((event) => (
              <div key={event.id} className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-medium text-white">{event.object_type}</p>
                    <p className="mt-1 text-sm text-slate-400">
                      {event.action} · {event.result} · {formatDate(event.created_at)}
                    </p>
                  </div>
                  <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-slate-200">
                    {event.actor_id ?? "system"}
                  </span>
                </div>
                {event.event_payload ? (
                  <pre className="mt-3 overflow-x-auto rounded-2xl border border-white/10 bg-black/20 p-3 text-xs text-slate-300">
                    {JSON.stringify(event.event_payload, null, 2)}
                  </pre>
                ) : null}
              </div>
            ))}
          </div>
        </article>
      </section>
    </main>
  )
}
