import { STATE_COLORS } from "./constants"
import type { ExposureItem, StateEvent } from "./types"

function formatDate(value: string): string {
  return new Date(value).toLocaleString()
}

export function ExposuresSection({ exposures }: { exposures: ExposureItem[] }) {
  return (
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
                  <td className="py-3 text-right text-xs text-slate-400">{formatDate(exposure.snapshot_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export function StateHistorySection({ history }: { history: StateEvent[] }) {
  if (history.length === 0) {
    return null
  }

  return (
    <section className="mb-8 rounded-2xl border border-white/10 bg-white/5 p-6">
      <h2 className="mb-4 text-xl font-medium text-white">State History</h2>
      <div className="space-y-3">
        {history.map((event, index) => (
          <div key={`${event.created_at}-${index}`} className="rounded-xl border border-white/10 bg-black/10 p-4">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className={STATE_COLORS[event.from_state] ?? "text-slate-200"}>{event.from_state}</span>
              <span className="text-slate-500">-&gt;</span>
              <span className={STATE_COLORS[event.to_state] ?? "text-slate-200"}>{event.to_state}</span>
              <span className="text-slate-500">[{event.trigger_type}]</span>
              <span className="font-mono text-xs text-slate-400">{event.trigger_metric}</span>
            </div>
            <div className="mt-2 text-xs text-slate-400">
              value={event.trigger_value.toFixed(4)} / {formatDate(event.created_at)}
            </div>
            {event.notes && <div className="mt-2 text-sm text-slate-300">{event.notes}</div>}
          </div>
        ))}
      </div>
    </section>
  )
}
