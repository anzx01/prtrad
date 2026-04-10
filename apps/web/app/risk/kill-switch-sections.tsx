import type { FormEventHandler, ReactNode } from "react"

import { STATUS_BADGE_STYLES } from "./constants"
import type { KillSwitchFormState, KillSwitchItem, ReviewAction } from "./types"

function formatDate(value: string): string {
  return new Date(value).toLocaleString()
}

function Field({ label, children }: { label: string; children: ReactNode }) {
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
  tone: ReviewAction
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

interface KillSwitchSectionProps {
  killSwitchForm: KillSwitchFormState
  pendingRequests: KillSwitchItem[]
  submitting: boolean
  onSubmit: FormEventHandler<HTMLFormElement>
  onFormChange: (patch: Partial<KillSwitchFormState>) => void
  onReview: (id: string, action: ReviewAction) => void
}

export function KillSwitchSection({
  killSwitchForm,
  pendingRequests,
  submitting,
  onSubmit,
  onFormChange,
  onReview,
}: KillSwitchSectionProps) {
  return (
    <section className="grid gap-6 lg:grid-cols-2">
      <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
        <h2 className="mb-4 text-xl font-medium text-white">Submit Kill-Switch Request</h2>
        <form onSubmit={onSubmit} className="space-y-4">
          <Field label="Request Type">
            <select
              value={killSwitchForm.request_type}
              onChange={(event) => onFormChange({ request_type: event.target.value })}
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
              onChange={(event) => onFormChange({ target_scope: event.target.value })}
              placeholder="global or cluster code"
              className="w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500"
              required
            />
          </Field>

          <Field label="Requested By">
            <input
              value={killSwitchForm.requested_by}
              onChange={(event) => onFormChange({ requested_by: event.target.value })}
              placeholder="ops_user"
              className="w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500"
              required
            />
          </Field>

          <Field label="Reason">
            <textarea
              value={killSwitchForm.reason}
              onChange={(event) => onFormChange({ reason: event.target.value })}
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
                    <div className="text-sm font-medium uppercase text-slate-100">{request.request_type}</div>
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
                  <ActionButton label="Approve" tone="approve" onClick={() => onReview(request.id, "approve")} />
                  <ActionButton label="Reject" tone="reject" onClick={() => onReview(request.id, "reject")} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

export function ReviewHistorySection({ requests }: { requests: KillSwitchItem[] }) {
  if (requests.length === 0) {
    return null
  }

  return (
    <section className="mt-8 rounded-2xl border border-white/10 bg-white/5 p-6">
      <h2 className="mb-4 text-xl font-medium text-white">Review History</h2>
      <div className="space-y-3">
        {requests.map((request) => (
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
              <div className="mt-2 text-xs text-slate-400">{formatDate(request.created_at)}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
