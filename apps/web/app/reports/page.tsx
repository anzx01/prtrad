"use client"

import { useEffect, useMemo, useState } from "react"

import { apiGet, apiPost } from "@/lib/api"
import {
  ConsoleBadge,
  ConsoleButton,
  ConsoleEmpty,
  ConsoleField,
  ConsolePanel,
  ConsoleSelect,
} from "../components/console-ui"
import { PageIntro } from "../components/page-intro"
import { buildReportsDashboard } from "./report-dashboard"
import { describeReport } from "./report-insights"
import { ReportsOverview } from "./report-overview"
import { AuditEventCard, ReportArchiveCard, type AuditRecord, type ReportRecord } from "./report-sections"
import { STAGE_NAMES, formatDateTime, formatLabel, formatReportTitle } from "./report-primitives"

const REPORT_ACTIONS = [
  { report_type: "daily_summary", label: "生成日报" },
  { report_type: "weekly_summary", label: "生成周报" },
  { report_type: "stage_review", label: "生成阶段评审" },
] as const

const REPORT_FILTERS = [
  { key: "all", label: "全部" },
  { key: "daily", label: "日报" },
  { key: "weekly", label: "周报" },
  { key: "stage", label: "阶段评审" },
] as const

type ReportFilter = (typeof REPORT_FILTERS)[number]["key"]

function matchesFilter(report: ReportRecord, filter: ReportFilter) {
  if (filter === "all") {
    return true
  }
  if (filter === "daily") {
    return report.report_type === "daily_summary"
  }
  if (filter === "weekly") {
    return report.report_type === "weekly_summary"
  }
  return report.report_type.startsWith("stage_review:")
}

function baseTypeTone(reportType: string) {
  if (reportType === "daily_summary") {
    return "info" as const
  }
  if (reportType === "weekly_summary") {
    return "good" as const
  }
  if (reportType.startsWith("stage_review:")) {
    return "warn" as const
  }
  return "neutral" as const
}

function toTimestamp(value: string) {
  const parsed = Date.parse(value)
  return Number.isNaN(parsed) ? 0 : parsed
}

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportRecord[]>([])
  const [auditEvents, setAuditEvents] = useState<AuditRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [stageName, setStageName] = useState<(typeof STAGE_NAMES)[number]>("M6")
  const [reportFilter, setReportFilter] = useState<ReportFilter>("all")
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null)

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
      setError(fetchError instanceof Error ? fetchError.message : "加载报告失败，请稍后重试")
    } finally {
      setLoading(false)
      setSubmitting(null)
    }
  }

  useEffect(() => {
    void fetchAll()
  }, [])

  const orderedReports = useMemo(
    () => [...reports].sort((left, right) => toTimestamp(right.generated_at) - toTimestamp(left.generated_at)),
    [reports],
  )

  const orderedAuditEvents = useMemo(
    () => [...auditEvents].sort((left, right) => toTimestamp(right.created_at) - toTimestamp(left.created_at)),
    [auditEvents],
  )

  const dashboard = useMemo(
    () => buildReportsDashboard(orderedReports, orderedAuditEvents),
    [orderedAuditEvents, orderedReports],
  )

  const filteredReports = useMemo(
    () => orderedReports.filter((report) => matchesFilter(report, reportFilter)),
    [orderedReports, reportFilter],
  )

  useEffect(() => {
    if (filteredReports.length === 0) {
      setSelectedReportId(null)
      return
    }
    if (!selectedReportId || !filteredReports.some((report) => report.id === selectedReportId)) {
      setSelectedReportId(filteredReports[0].id)
    }
  }, [filteredReports, selectedReportId])

  const selectedReport =
    filteredReports.find((report) => report.id === selectedReportId) ?? filteredReports[0] ?? null

  const handleSelectReport = (reportId: string) => {
    setReportFilter("all")
    setSelectedReportId(reportId)
  }

  const handleGenerate = async (reportType: string) => {
    setSubmitting(reportType)
    setError(null)
    try {
      await apiPost("/reports/generate", {
        report_type: reportType,
        generated_by: "web_console",
        stage_name: reportType === "stage_review" ? stageName : null,
      })
      await fetchAll()
      setReportFilter("all")
    } catch (generateError) {
      setSubmitting(null)
      setError(generateError instanceof Error ? generateError.message : "生成报告失败，请稍后重试")
    }
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-5 md:px-6">
      <PageIntro
        eyebrow="Reports"
        title="日报、周报与阶段评审"
        description="先让系统告诉你现在该看哪份报告、为什么要看，再决定要不要继续下钻。0 并不总是故障，也可能只是该时间窗没有新动作。"
        stats={[
          { label: "报告归档", value: String(orderedReports.length) },
          { label: "审计事件", value: String(orderedAuditEvents.length) },
        ]}
        guides={[
          {
            title: "先看什么",
            description: "优先看顶部智能速读，它会先告诉你当前最关键的是回测、阶段评审还是日报拒绝原因。",
          },
          {
            title: "什么时候看周报",
            description: "当你想判断 NoGo 是偶发还是持续趋势时，看周报最有效。",
          },
          {
            title: "什么时候看阶段评审",
            description: "当你要做 Go/NoGo 决策时，阶段评审是最快的判断入口。",
          },
        ]}
      />

      {error ? (
        <div className="mb-6 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      <ReportsOverview
        dashboard={dashboard}
        selectedReportId={selectedReportId}
        onSelectReport={handleSelectReport}
      />

      <ConsolePanel
        className="mt-6"
        title="生成或刷新报告"
        description="先选阶段评审目标，再决定这次是补日报、补周报，还是刷新某个阶段的门槛结论。"
      >
        <div className="flex flex-wrap items-end gap-3">
          <ConsoleField label="阶段评审目标">
            <ConsoleSelect
              value={stageName}
              onChange={(event) => setStageName(event.target.value as (typeof STAGE_NAMES)[number])}
            >
              {STAGE_NAMES.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </ConsoleSelect>
          </ConsoleField>

          {REPORT_ACTIONS.map((action) => (
            <ConsoleButton
              key={action.report_type}
              type="button"
              onClick={() => void handleGenerate(action.report_type)}
              disabled={submitting !== null}
              tone="primary"
            >
              {submitting === action.report_type
                ? "生成中..."
                : action.report_type === "stage_review"
                  ? `生成 ${stageName} 阶段评审`
                  : action.label}
            </ConsoleButton>
          ))}
        </div>
      </ConsolePanel>

      <section className="mt-6 grid gap-6 lg:grid-cols-[340px_minmax(0,1fr)]">
        <ConsolePanel
          title="报告归档"
          description="左边按类型选报告，右边看结构化详情。需要追根溯源时，再展开原始 JSON。"
          actions={<ConsoleBadge label={`${filteredReports.length} / ${orderedReports.length} 份`} tone="neutral" />}
        >
          <div className="mb-4 flex flex-wrap gap-2">
            {REPORT_FILTERS.map((filter) => (
              <ConsoleButton
                key={filter.key}
                type="button"
                size="sm"
                tone={reportFilter === filter.key ? "primary" : "default"}
                onClick={() => setReportFilter(filter.key)}
              >
                {filter.label}
              </ConsoleButton>
            ))}
          </div>

          {loading ? <p className="text-sm text-[#8b949e]">正在加载报告...</p> : null}
          {!loading && filteredReports.length === 0 ? (
            <ConsoleEmpty title="当前筛选下没有报告" description="可以切换筛选，或先在上方生成一份最新报告。" />
          ) : null}

          <div className="space-y-3">
            {filteredReports.map((report) => {
              const insight = describeReport(report)
              const selected = report.id === selectedReport?.id
              return (
                <button
                  key={report.id}
                  type="button"
                  onClick={() => setSelectedReportId(report.id)}
                  className={`w-full rounded-lg border p-4 text-left transition ${
                    selected
                      ? "border-[#58a6ff]/45 bg-[#1f6feb]/10"
                      : "border-[#30363d] bg-[#0d1117] hover:border-[#58a6ff]/25 hover:bg-[#161b22]"
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-medium text-[#e6edf3]">{formatReportTitle(report.report_type)}</p>
                    <ConsoleBadge label={formatLabel(report.report_type.split(":")[0])} tone={baseTypeTone(report.report_type)} />
                  </div>
                  <p className="mt-2 text-xs uppercase tracking-[0.16em] text-[#8b949e]">
                    {formatDateTime(report.generated_at)}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-[#c9d1d9]">{insight.title}</p>
                </button>
              )
            })}
          </div>
        </ConsolePanel>

        <ConsolePanel
          title={selectedReport ? formatReportTitle(selectedReport.report_type) : "报告详情"}
          description={
            selectedReport
              ? `报告时间窗：${formatDateTime(selectedReport.report_period_start)} - ${formatDateTime(selectedReport.report_period_end)}`
              : "从左侧报告归档中选择一份报告后，这里会显示结构化详情。"
          }
          actions={
            selectedReport ? (
              <>
                <ConsoleBadge label={`生成者 ${selectedReport.generated_by ?? "system"}`} tone="neutral" />
                <ConsoleBadge label={formatDateTime(selectedReport.generated_at)} tone="info" />
              </>
            ) : null
          }
        >
          {!selectedReport ? (
            <ConsoleEmpty title="还没有选中报告" description="请先从左侧归档中选择一份日报、周报或阶段评审。" />
          ) : (
            <ReportArchiveCard report={selectedReport} embedded />
          )}
        </ConsolePanel>
      </section>

      <ConsolePanel
        className="mt-6"
        title="最近审计轨迹"
        description="这里不是让你读完所有日志，而是用来解释最近生成了什么、谁触发了它，以及结果是什么。"
        actions={<ConsoleBadge label={`${orderedAuditEvents.length} 条`} tone="neutral" />}
      >
        {loading ? <p className="text-sm text-[#8b949e]">正在加载审计轨迹...</p> : null}
        {!loading && orderedAuditEvents.length === 0 ? (
          <ConsoleEmpty title="当前还没有审计记录" description="一旦执行生成报告、审批或其他关键动作，这里会开始出现轨迹。" />
        ) : null}
        <div className="space-y-3">
          {orderedAuditEvents.map((event) => (
            <AuditEventCard key={event.id} event={event} />
          ))}
        </div>
      </ConsolePanel>
    </main>
  )
}
