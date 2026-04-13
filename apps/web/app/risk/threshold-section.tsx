import type { FormEventHandler, ReactNode } from "react"

import {
  ConsoleButton,
  ConsoleEmpty,
  ConsoleInput,
  ConsolePanel,
  ConsoleSelect,
} from "../components/console-ui"
import { THRESHOLD_METRIC_OPTIONS, formatThresholdMetricLabel } from "./constants"
import type { ThresholdFormState, ThresholdItem, ThresholdMetric } from "./types"

function formatDate(value: string): string {
  return new Date(value).toLocaleString()
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-[#8b949e]">{label}</span>
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
    <ConsolePanel
      className="mb-8"
      title="阈值覆盖"
      description="这里显示当前生效的覆盖项；恢复默认后，系统会回退到预设阈值。"
    >
      <form onSubmit={onSubmit} className="mb-6 grid gap-4 rounded-xl border border-[#30363d] bg-[#0d1117] p-4 lg:grid-cols-4">
        <Field label="簇">
          <ConsoleInput
            value={thresholdForm.cluster_code}
            onChange={(event) => onFormChange({ cluster_code: event.target.value })}
            placeholder="global 或 category"
            required
          />
        </Field>

        <Field label="指标">
          <ConsoleSelect
            value={thresholdForm.metric_name}
            onChange={(event) => onMetricChange(event.target.value as ThresholdMetric)}
          >
            {THRESHOLD_METRIC_OPTIONS.map((metric) => (
              <option key={metric} value={metric}>
                {formatThresholdMetricLabel(metric)}
              </option>
            ))}
          </ConsoleSelect>
        </Field>

        <Field label="阈值">
          <ConsoleInput
            type="number"
            step="0.01"
            min="0.01"
            value={thresholdForm.threshold_value}
            onChange={(event) => onFormChange({ threshold_value: event.target.value })}
            required
          />
        </Field>

        <Field label="修改人">
          <ConsoleInput
            value={thresholdForm.created_by}
            onChange={(event) => onFormChange({ created_by: event.target.value })}
            placeholder="risk_ops"
            required
          />
        </Field>

        <div className="lg:col-span-3">
          <p className="text-xs text-[#8b949e]">
            `utilization_*` 建议使用 0-1 之间的小数；`max_exposure` 和 `max_positions` 使用正数。
          </p>
          <p className="mt-1 text-xs text-[#6e7681]">
            若想恢复已停用的覆盖项，重新在这里提交相同的 cluster 和 metric 即可。
          </p>
        </div>

        <div className="flex items-end justify-start lg:justify-end">
          <ConsoleButton
            type="submit"
            disabled={savingThreshold}
            tone="primary"
          >
            {savingThreshold ? "保存中..." : "保存阈值"}
          </ConsoleButton>
        </div>
      </form>
      {thresholds.length === 0 ? (
        <ConsoleEmpty title="当前没有显式阈值覆盖项" description="后端当前正在使用默认阈值，可按需新增覆盖项。" />
      ) : (
        <div className="overflow-x-auto">
          <table className="console-table min-w-full">
            <thead>
              <tr>
                <th>簇</th>
                <th>指标</th>
                <th className="text-right">阈值</th>
                <th>修改人</th>
                <th className="text-right">创建时间</th>
                <th className="text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              {thresholds.map((threshold) => (
                <tr key={threshold.id}>
                  <td className="font-mono text-xs text-[#c9d1d9]">{threshold.cluster_code}</td>
                  <td className="text-[#c9d1d9]">{formatThresholdMetricLabel(threshold.metric_name)}</td>
                  <td className="text-right text-[#c9d1d9]">{threshold.threshold_value.toFixed(4)}</td>
                  <td className="text-[#c9d1d9]">{threshold.created_by}</td>
                  <td className="text-right text-xs text-[#8b949e]">{formatDate(threshold.created_at)}</td>
                  <td className="text-right">
                    <ConsoleButton
                      type="button"
                      onClick={() => onDeactivate(threshold)}
                      disabled={deactivatingThresholdId === threshold.id}
                      size="sm"
                    >
                      {deactivatingThresholdId === threshold.id ? "停用中..." : "恢复默认"}
                    </ConsoleButton>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </ConsolePanel>
  )
}
