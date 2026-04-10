import type { FormEventHandler, ReactNode } from "react"

import { THRESHOLD_METRIC_OPTIONS } from "./constants"
import type { ThresholdFormState, ThresholdItem, ThresholdMetric } from "./types"

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

interface ThresholdsSectionProps {
  thresholdForm: ThresholdFormState
  savingThreshold: boolean
  thresholds: ThresholdItem[]
  deactivatingThresholdId: string | null
  onSubmit: FormEventHandler<HTMLFormElement>
  onFormChange: (patch: Partial<ThresholdFormState>) => void
  onMetricChange: (metric: ThresholdMetric) => void
  onDeactivate: (threshold: ThresholdItem) => void
}

export function ThresholdsSection({
  thresholdForm,
  savingThreshold,
  thresholds,
  deactivatingThresholdId,
  onSubmit,
  onFormChange,
  onMetricChange,
  onDeactivate,
}: ThresholdsSectionProps) {
  return (
    <section className="mb-8 rounded-2xl border border-white/10 bg-white/5 p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-medium text-white">Thresholds</h2>
        <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Active overrides</p>
      </div>
      <form onSubmit={onSubmit} className="mb-6 grid gap-4 rounded-xl border border-white/10 bg-black/10 p-4 lg:grid-cols-4">
        <Field label="Cluster">
          <input
            value={thresholdForm.cluster_code}
            onChange={(event) => onFormChange({ cluster_code: event.target.value })}
            placeholder="global or category"
            className="w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500"
            required
          />
        </Field>

        <Field label="Metric">
          <select
            value={thresholdForm.metric_name}
            onChange={(event) => onMetricChange(event.target.value as ThresholdMetric)}
            className="w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm text-slate-100"
          >
            {THRESHOLD_METRIC_OPTIONS.map((metric) => (
              <option key={metric} value={metric}>
                {metric}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Threshold Value">
          <input
            type="number"
            step="0.01"
            min="0.01"
            value={thresholdForm.threshold_value}
            onChange={(event) => onFormChange({ threshold_value: event.target.value })}
            className="w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm text-slate-100"
            required
          />
        </Field>

        <Field label="Changed By">
          <input
            value={thresholdForm.created_by}
            onChange={(event) => onFormChange({ created_by: event.target.value })}
            placeholder="risk_ops"
            className="w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500"
            required
          />
        </Field>

        <div className="lg:col-span-3">
          <p className="text-xs text-slate-400">
            `utilization_*` 建议使用 0-1 之间的小数；`max_exposure` 和 `max_positions` 使用正数。
          </p>
          <p className="mt-1 text-xs text-slate-500">
            To restore an override after disabling it, submit the same cluster and metric here again.
          </p>
        </div>

        <div className="flex items-end justify-start lg:justify-end">
          <button
            type="submit"
            disabled={savingThreshold}
            className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-500"
          >
            {savingThreshold ? "Saving..." : "Save Threshold"}
          </button>
        </div>
      </form>
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
                <th className="pb-3 pr-4 text-right">Created At</th>
                <th className="pb-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-200">
              {thresholds.map((threshold) => (
                <tr key={threshold.id}>
                  <td className="py-3 pr-4 font-mono text-xs">{threshold.cluster_code}</td>
                  <td className="py-3 pr-4">{threshold.metric_name}</td>
                  <td className="py-3 pr-4 text-right">{threshold.threshold_value.toFixed(4)}</td>
                  <td className="py-3 pr-4">{threshold.created_by}</td>
                  <td className="py-3 pr-4 text-right text-xs text-slate-400">{formatDate(threshold.created_at)}</td>
                  <td className="py-3 text-right">
                    <button
                      type="button"
                      onClick={() => onDeactivate(threshold)}
                      disabled={deactivatingThresholdId === threshold.id}
                      className="rounded-lg bg-white/5 px-3 py-1.5 text-xs font-medium text-slate-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {deactivatingThresholdId === threshold.id ? "Disabling..." : "Use Default"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
