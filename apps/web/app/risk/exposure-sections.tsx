import { ConsoleEmpty, ConsoleInset, ConsolePanel } from "../components/console-ui"
import { STATE_COLORS, formatRiskStateLabel } from "./constants"
import type { ExposureItem, StateEvent } from "./types"

function formatDate(value: string): string {
  return new Date(value).toLocaleString()
}

export function ExposuresSection({ exposures }: { exposures: ExposureItem[] }) {
  return (
    <ConsolePanel
      className="mb-8"
      title="簇暴露"
      description="每个簇只显示最新一条快照，用于快速判断哪些簇已经越限。"
    >
      {exposures.length === 0 ? (
        <ConsoleEmpty title="当前还没有暴露快照" description="先执行一次“重算暴露”，再回来判断哪些簇进入了风险区间。" />
      ) : (
        <div className="overflow-x-auto">
          <table className="console-table min-w-full">
            <thead>
              <tr>
                <th>簇</th>
                <th className="text-right">毛暴露</th>
                <th className="text-right">净暴露</th>
                <th className="text-right">持仓数</th>
                <th className="text-right">限额</th>
                <th className="text-right">利用率</th>
                <th className="text-right">快照时间</th>
              </tr>
            </thead>
            <tbody>
              {exposures.map((exposure) => (
                <tr key={exposure.cluster_code} className={exposure.is_breached ? "bg-[#da3633]/10" : ""}>
                  <td className="font-mono text-xs text-[#c9d1d9]">{exposure.cluster_code}</td>
                  <td className="text-right text-[#c9d1d9]">{exposure.gross_exposure.toFixed(4)}</td>
                  <td className="text-right text-[#c9d1d9]">{exposure.net_exposure.toFixed(4)}</td>
                  <td className="text-right text-[#c9d1d9]">{exposure.position_count}</td>
                  <td className="text-right text-[#c9d1d9]">{exposure.limit_value.toFixed(2)}</td>
                  <td className="text-right">
                    <span className={exposure.is_breached ? "text-[#f85149]" : "text-[#e6edf3]"}>
                      {(exposure.utilization_rate * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="text-right text-xs text-[#8b949e]">{formatDate(exposure.snapshot_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </ConsolePanel>
  )
}

export function StateHistorySection({ history }: { history: StateEvent[] }) {
  if (history.length === 0) {
    return null
  }

  return (
    <ConsolePanel className="mb-8" title="状态历史" description="回看最近的状态切换，确认是自动触发还是人工动作。">
      <div className="space-y-3">
        {history.map((event, index) => (
          <ConsoleInset key={`${event.created_at}-${index}`}>
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className={STATE_COLORS[event.from_state] ?? "text-slate-200"}>{formatRiskStateLabel(event.from_state)}</span>
              <span className="text-[#8b949e]">-&gt;</span>
              <span className={STATE_COLORS[event.to_state] ?? "text-slate-200"}>{formatRiskStateLabel(event.to_state)}</span>
              <span className="text-[#8b949e]">[{event.trigger_type}]</span>
              <span className="font-mono text-xs text-[#8b949e]">{event.trigger_metric}</span>
            </div>
            <div className="mt-2 text-xs text-[#8b949e]">
              触发值={event.trigger_value.toFixed(4)} / {formatDate(event.created_at)}
            </div>
            {event.notes && <div className="mt-2 text-sm text-[#c9d1d9]">{event.notes}</div>}
          </ConsoleInset>
        ))}
      </div>
    </ConsolePanel>
  )
}
