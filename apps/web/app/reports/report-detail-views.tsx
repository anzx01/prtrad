import type { ReactNode } from "react"

import { ConsoleEmpty, ConsoleInset } from "../components/console-ui"
import {
  asBoolean,
  asNumber,
  asRecord,
  asRecordList,
  asStringList,
  formatDateTime,
  formatLabel,
  formatMetric,
  formatValue,
  MetricTile,
  RawJsonDetails,
  SectionBlock,
  StatusChip,
  type JsonRecord,
  type ReportRecord,
} from "./report-primitives"
import { ReportSummaryBanner } from "./report-summary-banner"

function KeyValueList({
  items,
}: {
  items: Array<{ label: string; value: string }>
}) {
  return (
    <div className="space-y-2 text-sm text-[#c9d1d9]">
      {items.map((item) => (
        <div
          key={item.label}
          className="flex flex-wrap items-center justify-between gap-3 border-b border-[#30363d]/70 pb-2 last:border-b-0 last:pb-0"
        >
          <span className="text-[#8b949e]">{item.label}</span>
          <span className="font-medium text-[#e6edf3]">{item.value}</span>
        </div>
      ))}
    </div>
  )
}

function TimelineItem({
  title,
  subtitle,
  meta,
  badge,
}: {
  title: string
  subtitle: string
  meta?: string
  badge?: ReactNode
}) {
  return (
    <ConsoleInset>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-[#e6edf3]">{title}</p>
          <p className="mt-1 text-sm text-[#8b949e]">{subtitle}</p>
          {meta ? <p className="mt-2 text-xs uppercase tracking-[0.16em] text-[#6e7681]">{meta}</p> : null}
        </div>
        {badge}
      </div>
    </ConsoleInset>
  )
}

function DailySummaryView({ data }: { data: JsonRecord }) {
  const summary = asRecord(data.summary)
  const rejectionReasons = Object.entries(asRecord(data.rejection_reason_distribution))
  const riskEvents = asRecordList(data.risk_state_events)
  const exposures = asRecordList(data.current_exposures)
  const dqSnapshot = Object.entries(asRecord(data.dq_alert_snapshot))
  const missingSections = asStringList(data.missing_sections)
  const auditable = asBoolean(summary.auditable)

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <MetricTile label="候选市场" value={formatMetric(asNumber(summary.candidate_total))} />
        <MetricTile label="准入" value={formatMetric(asNumber(summary.admitted_count))} />
        <MetricTile label="拒绝" value={formatMetric(asNumber(summary.rejected_count))} />
        <MetricTile label="审计事件" value={formatMetric(asNumber(summary.audit_event_count))} />
      </div>
      <div className="flex flex-wrap gap-2">
        <StatusChip label={auditable ? "可审计" : "缺少审计"} tone={auditable ? "good" : "warn"} />
        {missingSections.map((item) => (
          <StatusChip key={item} label={`缺少${formatLabel(item)}`} tone="warn" />
        ))}
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <SectionBlock title="拒绝原因">
          {rejectionReasons.length === 0 ? (
            <ConsoleEmpty title="当前没有拒绝堆积" description="这份日报时间窗内没有出现明显的拒绝原因聚集。" />
          ) : (
            <div className="flex flex-wrap gap-2">
              {rejectionReasons.map(([reason, count]) => (
                <StatusChip key={reason} label={`${formatLabel(reason)} x${count}`} tone="neutral" />
              ))}
            </div>
          )}
        </SectionBlock>
        <SectionBlock title="DQ 快照">
          {dqSnapshot.length === 0 ? (
            <ConsoleEmpty title="未嵌入 DQ 快照" description="这份日报没有附带 DQ 快照，阅读时要把数据质量判断放回 DQ 页面。" />
          ) : (
            <KeyValueList
              items={dqSnapshot.map(([key, value]) => ({
                label: formatLabel(key),
                value: formatValue(value),
              }))}
            />
          )}
        </SectionBlock>
        <SectionBlock title="最近风险状态变化">
          {riskEvents.length === 0 ? (
            <ConsoleEmpty title="没有新的风险状态变化" description="当前时间窗里没有新的风险状态切换记录。" />
          ) : (
            <div className="space-y-3">
              {riskEvents.map((event, index) => (
                <TimelineItem
                  key={`${event.created_at ?? "event"}-${index}`}
                  title={String(event.to_state ?? "未知状态")}
                  subtitle={String(event.trigger_metric ?? "未知触发指标")}
                  meta={formatDateTime(String(event.created_at ?? ""))}
                />
              ))}
            </div>
          )}
        </SectionBlock>
        <SectionBlock title="当前暴露">
          {exposures.length === 0 ? (
            <ConsoleEmpty title="没有新的暴露快照" description="这份日报里没有记录新的暴露数据，可回到风险页查看最新计算结果。" />
          ) : (
            <div className="space-y-3">
              {exposures.map((exposure, index) => {
                const breached = asBoolean(exposure.is_breached)
                return (
                  <TimelineItem
                    key={`${exposure.cluster_code ?? "cluster"}-${index}`}
                    title={String(exposure.cluster_code ?? "未知簇")}
                    subtitle={`利用率 ${formatMetric(asNumber(exposure.utilization_rate), "percent")}`}
                    badge={<StatusChip label={breached ? "已越限" : "未越限"} tone={breached ? "bad" : "good"} />}
                  />
                )
              })}
            </div>
          )}
        </SectionBlock>
      </div>
    </div>
  )
}

function WeeklySummaryView({ data }: { data: JsonRecord }) {
  const summary = asRecord(data.summary)
  const recommendationBreakdown = asRecord(summary.recommendation_breakdown)
  const backtests = asRecordList(data.recent_backtests)
  const riskTimeline = asRecordList(data.risk_timeline)

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <MetricTile label="回测次数" value={formatMetric(asNumber(summary.backtest_run_count))} />
        <MetricTile label="风险事件" value={formatMetric(asNumber(summary.risk_event_count))} />
        <MetricTile label="Go" value={formatMetric(asNumber(recommendationBreakdown.go))} />
        <MetricTile label="观察" value={formatMetric(asNumber(recommendationBreakdown.watch))} />
        <MetricTile label="NoGo" value={formatMetric(asNumber(recommendationBreakdown.nogo))} />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <SectionBlock title="最近回测">
          {backtests.length === 0 ? (
            <ConsoleEmpty title="没有新的回测结果" description="这份周报时间窗里没有生成新的回测结论。" />
          ) : (
            <div className="space-y-3">
              {backtests.map((run, index) => {
                const recommendation = String(run.recommendation ?? "unknown").toLowerCase()
                const tone = recommendation === "go" ? "good" : recommendation === "watch" ? "warn" : "bad"
                return (
                  <TimelineItem
                    key={`${run.run_name ?? "backtest"}-${index}`}
                    title={String(run.run_name ?? "未命名回测")}
                    subtitle={formatDateTime(String(run.completed_at ?? ""))}
                    badge={<StatusChip label={formatLabel(String(run.recommendation ?? "unknown"))} tone={tone} />}
                  />
                )
              })}
            </div>
          )}
        </SectionBlock>
        <SectionBlock title="风险时间线">
          {riskTimeline.length === 0 ? (
            <ConsoleEmpty title="没有风险迁移记录" description="当前时间窗里没有风险状态迁移，可把这份周报理解为平稳观察窗口。" />
          ) : (
            <div className="space-y-3">
              {riskTimeline.map((event, index) => (
                <TimelineItem
                  key={`${event.created_at ?? "risk"}-${index}`}
                  title={String(event.to_state ?? "未知状态")}
                  subtitle="风险状态迁移"
                  meta={formatDateTime(String(event.created_at ?? ""))}
                />
              ))}
            </div>
          )}
        </SectionBlock>
      </div>
    </div>
  )
}

function StageReviewView({ data }: { data: JsonRecord }) {
  const decision = String(data.decision ?? "NoGo")
  const stageName = String(data.stage_name ?? "M6")
  const dod = Object.entries(asRecord(data.dod))
  const nogoReasons = asStringList(data.nogo_reasons)
  const latestBacktest = asRecord(data.latest_backtest)
  const latestShadowRun = asRecord(data.latest_shadow_run)

  return (
    <div className="space-y-4">
      <ConsoleInset>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-[11px] uppercase tracking-[0.2em] text-[#8b949e]">阶段门槛</p>
            <h4 className="mt-2 text-xl font-semibold text-[#e6edf3]">{stageName} 阶段结论</h4>
          </div>
          <StatusChip label={formatLabel(decision.toLowerCase())} tone={decision.toLowerCase() === "go" ? "good" : "bad"} />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {nogoReasons.length === 0 ? (
            <StatusChip label="无阻断项" tone="good" />
          ) : (
            nogoReasons.map((reason) => <StatusChip key={reason} label={formatLabel(reason)} tone="warn" />)
          )}
        </div>
      </ConsoleInset>
      <div className="grid gap-4 xl:grid-cols-2">
        <SectionBlock title="完成定义">
          <div className="space-y-3">
            {dod.map(([key, value]) => (
              <ConsoleInset key={key} className="flex items-center justify-between gap-3">
                <span className="text-sm text-[#c9d1d9]">{formatLabel(key)}</span>
                <StatusChip label={asBoolean(value) ? "已满足" : "缺失"} tone={asBoolean(value) ? "good" : "warn"} />
              </ConsoleInset>
            ))}
          </div>
        </SectionBlock>
        <SectionBlock title="关联证据">
          <div className="space-y-3">
            <ConsoleInset>
              <p className="text-sm text-[#8b949e]">最近回测</p>
              <p className="mt-1 font-medium text-[#e6edf3]">{String(latestBacktest.run_name ?? "暂无")}</p>
              <p className="mt-2 text-sm text-[#8b949e]">
                {formatValue(latestBacktest.recommendation)} · {formatDateTime(String(latestBacktest.created_at ?? ""))}
              </p>
            </ConsoleInset>
            <ConsoleInset>
              <p className="text-sm text-[#8b949e]">最近影子运行</p>
              <p className="mt-1 font-medium text-[#e6edf3]">{String(latestShadowRun.run_name ?? "暂无")}</p>
              <p className="mt-2 text-sm text-[#8b949e]">
                {formatValue(latestShadowRun.recommendation)} · {formatDateTime(String(latestShadowRun.created_at ?? ""))}
              </p>
            </ConsoleInset>
          </div>
        </SectionBlock>
      </div>
    </div>
  )
}

export function ReportArchiveContent({ report }: { report: ReportRecord }) {
  const baseType = report.report_type.split(":")[0]
  const reportData = asRecord(report.report_data)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs tracking-[0.16em] text-[#8b949e]">生成者：{report.generated_by ?? "system"}</p>
        </div>
      </div>

      <ReportSummaryBanner report={report} />

      <div className="mt-4">
        {baseType === "daily_summary" ? <DailySummaryView data={reportData} /> : null}
        {baseType === "weekly_summary" ? <WeeklySummaryView data={reportData} /> : null}
        {baseType === "stage_review" ? <StageReviewView data={reportData} /> : null}
        {!["daily_summary", "weekly_summary", "stage_review"].includes(baseType) ? (
          <SectionBlock title="报告数据">
            <p className="text-sm text-[#c9d1d9]">这类历史报告暂时没有专用视图，可先结合上方一句话结论阅读。</p>
          </SectionBlock>
        ) : null}
      </div>

      <RawJsonDetails data={report.report_data} />
    </div>
  )
}
