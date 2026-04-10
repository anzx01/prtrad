import { STATE_COLORS, STATE_PANEL_STYLES } from "./constants"
import type { StateEvent } from "./types"

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

export function RiskPageHeader({
  computing,
  onCompute,
}: {
  computing: boolean
  onCompute: () => void
}) {
  return (
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
        onClick={onCompute}
        disabled={computing}
        className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-500"
      >
        {computing ? "Computing..." : "Compute Exposures"}
      </button>
    </div>
  )
}

export function RiskSummaryGrid({
  currentState,
  exposureCount,
  breachedCount,
  pendingCount,
}: {
  currentState: string
  exposureCount: number
  breachedCount: number
  pendingCount: number
}) {
  return (
    <div className="mb-8 grid gap-4 md:grid-cols-4">
      <SummaryCard
        label="Current State"
        value={currentState}
        accent={STATE_COLORS[currentState] ?? "text-white"}
      />
      <SummaryCard label="Tracked Clusters" value={exposureCount.toString()} />
      <SummaryCard label="Breached Clusters" value={breachedCount.toString()} />
      <SummaryCard label="Pending Requests" value={pendingCount.toString()} />
    </div>
  )
}

export function RiskStatePanel({
  currentState,
  latestEvent,
}: {
  currentState: string
  latestEvent?: StateEvent
}) {
  return (
    <section
      className={`mb-8 rounded-2xl border p-6 ${STATE_PANEL_STYLES[currentState] ?? "border-white/10 bg-white/5"}`}
    >
      <p className="text-sm text-slate-200/80">Global risk state</p>
      <p className={`mt-2 text-4xl font-semibold ${STATE_COLORS[currentState] ?? "text-white"}`}>
        {currentState}
      </p>
      {latestEvent && (
        <p className="mt-3 text-xs text-slate-200/70">
          Last change at {new Date(latestEvent.created_at).toLocaleString()}
          {latestEvent.actor_id ? ` by ${latestEvent.actor_id}` : " via auto transition"}
        </p>
      )}
    </section>
  )
}
