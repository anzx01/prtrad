import { ConsoleBadge, ConsoleInset, ConsolePanel } from "../components/console-ui"
import {
  asRecord,
  formatDateTime,
  formatLabel,
  formatRange,
  formatReportTitle,
  formatValue,
  RawJsonDetails,
  StatusChip,
  type AuditRecord,
  type ReportRecord,
} from "./report-primitives"
import { ReportArchiveContent } from "./report-detail-views"

function shortenAuditLabel(value: string | null | undefined) {
  if (!value) {
    return "-"
  }
  const normalized = value.replaceAll("_", " ").replaceAll(".", " / ").trim()
  if (normalized.length <= 42) {
    return normalized
  }
  return `${normalized.slice(0, 39)}...`
}

export function ReportArchiveCard({
  report,
  embedded = false,
}: {
  report: ReportRecord
  embedded?: boolean
}) {
  if (embedded) {
    return <ReportArchiveContent report={report} />
  }

  return (
    <ConsolePanel
      className="bg-[#0d1117]"
      bodyClassName="space-y-4"
      title={formatReportTitle(report.report_type)}
      description={formatRange(report.report_period_start, report.report_period_end)}
      actions={
        <>
          <ConsoleBadge label={formatLabel(report.report_type.split(":")[0])} tone="neutral" />
          <ConsoleBadge label={formatDateTime(report.generated_at)} tone="info" />
        </>
      }
    >
      <ReportArchiveContent report={report} />
    </ConsolePanel>
  )
}

export function AuditEventCard({ event }: { event: AuditRecord }) {
  const payloadEntries = Object.entries(asRecord(event.event_payload)).slice(0, 4)
  const normalizedResult = event.result.toLowerCase()
  const resultTone =
    normalizedResult === "success" || normalizedResult === "go"
      ? "good"
      : normalizedResult === "watch" || normalizedResult === "pending" || normalizedResult === "queued"
        ? "warn"
        : "bad"

  return (
    <ConsolePanel
      className="bg-[#0d1117]"
      bodyClassName="space-y-3"
      title={shortenAuditLabel(event.object_type)}
      description={`${event.object_id ?? "-"} · ${formatDateTime(event.created_at)}`}
      actions={
        <>
          <StatusChip label={shortenAuditLabel(event.action)} tone="neutral" />
          <StatusChip label={formatLabel(event.result.toLowerCase())} tone={resultTone} />
          <ConsoleBadge label={shortenAuditLabel(event.actor_id ?? event.actor_type ?? "system")} tone="info" />
        </>
      }
    >
      <div className="space-y-2">
        <p className="text-sm text-[#8b949e]">用于解释最近一次动作的审计轨迹。</p>
        <div className="grid gap-2 md:grid-cols-2">
          <ConsoleInset>
            <p className="console-kicker">对象类型</p>
            <p className="mt-2 break-all text-sm text-[#c9d1d9]">{event.object_type}</p>
          </ConsoleInset>
          <ConsoleInset>
            <p className="console-kicker">对象 ID</p>
            <p className="mt-2 break-all text-sm text-[#c9d1d9]">{event.object_id ?? "-"}</p>
          </ConsoleInset>
        </div>
      </div>

      {payloadEntries.length > 0 ? (
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {payloadEntries.map(([key, value]) => (
            <ConsoleInset key={key}>
              <p className="text-[11px] uppercase tracking-[0.18em] text-[#8b949e]">{formatLabel(key)}</p>
              <p className="mt-2 break-all text-sm text-[#c9d1d9]">{formatValue(value)}</p>
            </ConsoleInset>
          ))}
        </div>
      ) : null}

      {event.event_payload ? <RawJsonDetails data={event.event_payload} label="查看 payload 原文" /> : null}
    </ConsolePanel>
  )
}

export type { AuditRecord, ReportRecord } from "./report-primitives"
