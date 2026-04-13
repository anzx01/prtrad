import { ConsoleBadge, ConsoleButton, ConsoleCallout, ConsoleInset, ConsoleMetric, ConsolePanel } from "../components/console-ui"
import { describeReport } from "./report-insights"
import { type ReportsDashboard } from "./report-dashboard"
import { formatDateTime, formatLabel, formatReportTitle, type ReportRecord } from "./report-primitives"

function toneForReport(report: ReportRecord) {
  const insight = describeReport(report)
  return insight.tone === "neutral" ? "info" : insight.tone
}

function StageEvidenceSummary({
  label,
  value,
}: {
  label: string
  value: string | null
}) {
  return (
    <div className="rounded-lg border border-[#30363d] bg-[#0d1117] px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.18em] text-[#8b949e]">{label}</p>
      <p className="mt-2 text-sm text-[#e6edf3]">{value ?? "暂无"}</p>
    </div>
  )
}

export function ReportsOverview({
  dashboard,
  selectedReportId,
  onSelectReport,
}: {
  dashboard: ReportsDashboard
  selectedReportId: string | null
  onSelectReport: (reportId: string) => void
}) {
  return (
    <section className="space-y-6">
      <ConsoleCallout
        eyebrow="智能速读"
        title={dashboard.headline.title}
        description={dashboard.headline.description}
        tone={dashboard.headline.tone}
        actions={
          <>
            {dashboard.primaryStage ? (
              <ConsoleButton
                type="button"
                size="sm"
                tone="primary"
                onClick={() => onSelectReport(dashboard.primaryStage!.report.id)}
              >
                打开最新阶段评审
              </ConsoleButton>
            ) : null}
            {dashboard.latestWeekly ? (
              <ConsoleButton
                type="button"
                size="sm"
                onClick={() => onSelectReport(dashboard.latestWeekly!.id)}
              >
                打开最新周报
              </ConsoleButton>
            ) : null}
            {dashboard.latestDaily ? (
              <ConsoleButton
                type="button"
                size="sm"
                onClick={() => onSelectReport(dashboard.latestDaily!.id)}
              >
                打开最新日报
              </ConsoleButton>
            ) : null}
          </>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {dashboard.metrics.map((metric) => (
          <ConsoleMetric
            key={metric.label}
            label={metric.label}
            value={metric.value}
            hint={metric.hint}
            tone={metric.tone}
          />
        ))}
      </div>

      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <ConsolePanel
          title="系统建议先看这里"
          description="这不是字段说明，而是系统根据最新报告整理出的阅读顺序。"
        >
          <div className="space-y-3">
            {dashboard.priorities.map((priority, index) => (
              <ConsoleInset key={`${priority.title}-${index}`} className="space-y-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-[#e6edf3]">{priority.title}</p>
                    <p className="mt-2 text-sm leading-6 text-[#8b949e]">{priority.description}</p>
                  </div>
                  <ConsoleBadge
                    label={priority.tone === "bad" ? "高优先级" : priority.tone === "warn" ? "建议先看" : "补齐即可"}
                    tone={priority.tone}
                  />
                </div>
                {priority.reportId ? (
                  <ConsoleButton type="button" size="sm" onClick={() => onSelectReport(priority.reportId!)}>
                    打开相关报告
                  </ConsoleButton>
                ) : null}
              </ConsoleInset>
            ))}
          </div>
        </ConsolePanel>

        <ConsolePanel
          title="最新关键报告"
          description="如果你只打算快速扫一遍，先看这几份。"
        >
          <div className="space-y-3">
            {dashboard.quickReports.map((report) => {
              const insight = describeReport(report)
              const selected = report.id === selectedReportId
              return (
                <button
                  key={report.id}
                  type="button"
                  onClick={() => onSelectReport(report.id)}
                  className={`w-full rounded-xl border p-4 text-left transition ${
                    selected
                      ? "border-[#58a6ff]/45 bg-[#1f6feb]/10"
                      : "border-[#30363d] bg-[#0d1117] hover:border-[#58a6ff]/25 hover:bg-[#111823]"
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold text-[#e6edf3]">{formatReportTitle(report.report_type)}</p>
                    <ConsoleBadge label={formatDateTime(report.generated_at)} tone="neutral" />
                    <ConsoleBadge label={insight.tone === "good" ? "偏正向" : insight.tone === "bad" ? "需处理" : "建议关注"} tone={toneForReport(report)} />
                  </div>
                  <p className="mt-3 text-sm leading-6 text-[#c9d1d9]">{insight.title}</p>
                </button>
              )
            })}
          </div>
        </ConsolePanel>
      </section>

      <ConsolePanel
        title="M4 / M5 / M6 门槛概览"
        description="看这里是为了快速分辨：当前是“没报告”，还是“有报告但真没过门槛”。"
      >
        {dashboard.stageSnapshots.length === 0 ? (
          <ConsoleInset>
            <p className="text-sm text-[#c9d1d9]">当前还没有阶段评审，先生成 M4 / M5 / M6 报告后再看这里。</p>
          </ConsoleInset>
        ) : (
          <div className="grid gap-4 lg:grid-cols-3">
            {dashboard.stageSnapshots.map((snapshot) => (
              <ConsoleInset key={snapshot.stage} className="space-y-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.2em] text-[#8b949e]">{snapshot.stage}</p>
                    <h3 className="mt-2 text-lg font-semibold text-[#e6edf3]">{snapshot.stage} 阶段评审</h3>
                    <p className="mt-2 text-sm text-[#8b949e]">{formatDateTime(snapshot.generatedAt)}</p>
                  </div>
                  <ConsoleBadge label={formatLabel(snapshot.decision.toLowerCase())} tone={snapshot.tone} />
                </div>

                <div className="flex flex-wrap gap-2">
                  <ConsoleBadge label={`DoD ${snapshot.dodReady}/${snapshot.dodTotal}`} tone={snapshot.dodReady === snapshot.dodTotal ? "good" : "warn"} />
                  {snapshot.reasons.length > 0 ? (
                    snapshot.reasons.map((reason) => (
                      <ConsoleBadge key={reason} label={formatLabel(reason)} tone="warn" />
                    ))
                  ) : (
                    <ConsoleBadge label="无阻断项" tone="good" />
                  )}
                </div>

                <div className="grid gap-3">
                  <StageEvidenceSummary
                    label="最近回测"
                    value={
                      snapshot.backtestName
                        ? `${snapshot.backtestName} · ${formatLabel(snapshot.backtestRecommendation ?? "unknown")}`
                        : null
                    }
                  />
                  <StageEvidenceSummary
                    label="最近影子运行"
                    value={
                      snapshot.shadowName
                        ? `${snapshot.shadowName} · ${formatLabel(snapshot.shadowRecommendation ?? "unknown")}`
                        : null
                    }
                  />
                </div>

                <ConsoleButton type="button" size="sm" onClick={() => onSelectReport(snapshot.report.id)}>
                  打开 {snapshot.stage} 报告
                </ConsoleButton>
              </ConsoleInset>
            ))}
          </div>
        )}
      </ConsolePanel>
    </section>
  )
}
