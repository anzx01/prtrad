import {
  asBoolean,
  asNumber,
  asRecord,
  asStringList,
  type AuditRecord,
  type ReportRecord,
  type StageName,
  STAGE_NAMES,
} from "./report-primitives"

export type DashboardTone = "info" | "good" | "warn" | "bad"

export interface DashboardMetric {
  label: string
  value: string
  hint: string
  tone: DashboardTone
}

export interface DashboardHeadline {
  title: string
  description: string
  tone: DashboardTone
}

export interface DashboardPriority {
  title: string
  description: string
  tone: DashboardTone
  reportId?: string
}

export interface StageSnapshot {
  stage: StageName
  report: ReportRecord
  decision: string
  tone: DashboardTone
  reasons: string[]
  generatedAt: string
  dodReady: number
  dodTotal: number
  backtestName: string | null
  backtestRecommendation: string | null
  shadowName: string | null
  shadowRecommendation: string | null
}

export interface ReportsDashboard {
  headline: DashboardHeadline
  metrics: DashboardMetric[]
  priorities: DashboardPriority[]
  primaryStage: StageSnapshot | null
  quickReports: ReportRecord[]
  stageSnapshots: StageSnapshot[]
  latestDaily: ReportRecord | null
  latestWeekly: ReportRecord | null
  latestAuditTime: string | null
}

function toTimestamp(value: string) {
  const parsed = Date.parse(value)
  return Number.isNaN(parsed) ? 0 : parsed
}

function sortReports(reports: ReportRecord[]) {
  return [...reports].sort((left, right) => toTimestamp(right.generated_at) - toTimestamp(left.generated_at))
}

function latestReport(reports: ReportRecord[], predicate: (report: ReportRecord) => boolean) {
  return reports.find(predicate) ?? null
}

function toneFromDecision(decision: string): DashboardTone {
  const normalized = decision.toLowerCase()
  if (normalized === "go") {
    return "good"
  }
  if (normalized === "watch") {
    return "warn"
  }
  return "bad"
}

function summarizeDailyReport(report: ReportRecord | null) {
  if (!report) {
    return null
  }

  const summary = asRecord(asRecord(report.report_data).summary)
  const candidateTotal = asNumber(summary.candidate_total) ?? 0
  const admittedCount = asNumber(summary.admitted_count) ?? 0
  const rejectedCount = asNumber(summary.rejected_count) ?? 0
  const auditCount = asNumber(summary.audit_event_count) ?? 0
  const reasons = Object.entries(asRecord(asRecord(report.report_data).rejection_reason_distribution))
    .slice(0, 2)
    .map(([reason]) => reason)

  return { candidateTotal, admittedCount, rejectedCount, auditCount, reasons }
}

function summarizeWeeklyReport(report: ReportRecord | null) {
  if (!report) {
    return null
  }

  const summary = asRecord(asRecord(report.report_data).summary)
  const recommendationBreakdown = asRecord(summary.recommendation_breakdown)

  return {
    backtestCount: asNumber(summary.backtest_run_count) ?? 0,
    riskEventCount: asNumber(summary.risk_event_count) ?? 0,
    goCount: asNumber(recommendationBreakdown.go) ?? 0,
    watchCount: asNumber(recommendationBreakdown.watch) ?? 0,
    nogoCount: asNumber(recommendationBreakdown.nogo) ?? 0,
  }
}

function buildStageSnapshot(report: ReportRecord | null, stage: StageName): StageSnapshot | null {
  if (!report) {
    return null
  }

  const reportData = asRecord(report.report_data)
  const dodEntries = Object.entries(asRecord(reportData.dod))
  const latestBacktest = asRecord(reportData.latest_backtest)
  const latestShadowRun = asRecord(reportData.latest_shadow_run)
  const decision = String(reportData.decision ?? "unknown")

  return {
    stage,
    report,
    decision,
    tone: toneFromDecision(decision),
    reasons: asStringList(reportData.nogo_reasons),
    generatedAt: report.generated_at,
    dodReady: dodEntries.filter(([, value]) => asBoolean(value)).length,
    dodTotal: dodEntries.length,
    backtestName: typeof latestBacktest.run_name === "string" ? latestBacktest.run_name : null,
    backtestRecommendation:
      typeof latestBacktest.recommendation === "string" ? latestBacktest.recommendation : null,
    shadowName: typeof latestShadowRun.run_name === "string" ? latestShadowRun.run_name : null,
    shadowRecommendation:
      typeof latestShadowRun.recommendation === "string" ? latestShadowRun.recommendation : null,
  }
}

function buildHeadline(stageSnapshots: StageSnapshot[], latestWeekly: ReportRecord | null, latestDaily: ReportRecord | null): DashboardHeadline {
  const primaryStage = stageSnapshots.find((snapshot) => snapshot.stage === "M6") ?? stageSnapshots[0] ?? null
  const daily = summarizeDailyReport(latestDaily)
  const weekly = summarizeWeeklyReport(latestWeekly)

  if (stageSnapshots.length > 0 && stageSnapshots.every((snapshot) => snapshot.decision.toLowerCase() === "nogo")) {
    const blockingBacktest = primaryStage?.backtestRecommendation?.toLowerCase() === "nogo"
    if (blockingBacktest) {
      const backtestName = primaryStage.backtestName ?? "最近一次回测"
      const shadowText =
        primaryStage.shadowRecommendation?.toLowerCase() === "go"
          ? "影子运行虽然是 Go，但还不足以抵消回测 NoGo。"
          : "影子运行也还没有提供足够的放行信号。"
      return {
        title: "最新阶段评审仍然不建议推进上线",
        description: `M4/M5/M6 最新评审全部是 NoGo。直接阻断点不是页面故障，而是 ${backtestName} 给出了 NoGo；${shadowText}`,
        tone: "bad",
      }
    }

    return {
      title: "阶段门槛尚未通过",
      description: "M4/M5/M6 最新评审都还没有放行，先看阶段卡点，再决定是否继续推进 Go/NoGo。",
      tone: "warn",
    }
  }

  if (weekly && weekly.nogoCount > 0) {
    return {
      title: "本周回测结论偏保守，建议先看周报",
      description: `最近周报里累计 ${weekly.backtestCount} 次回测，其中 NoGo 有 ${weekly.nogoCount} 次。阶段评审前，先确认这些 NoGo 是否已经被处理。`,
      tone: "warn",
    }
  }

  if (daily && daily.rejectedCount > 0 && daily.admittedCount === 0) {
    return {
      title: "最新日报显示候选以拒绝为主",
      description: `最新日报里 ${daily.candidateTotal} 个候选全部被拒，当前更适合先复盘拒绝原因，而不是继续扩大放行范围。`,
      tone: "warn",
    }
  }

  return {
    title: "报告链路当前可读，但仍建议先看最新阶段评审",
    description: "如果你只打算读一份报告，请先看最新阶段评审；它最直接决定当前是否能继续推进上线决策。",
    tone: "info",
  }
}

function buildPriorities(stageSnapshots: StageSnapshot[], latestWeekly: ReportRecord | null, latestDaily: ReportRecord | null) {
  const priorities: DashboardPriority[] = []
  const primaryStage = stageSnapshots.find((snapshot) => snapshot.stage === "M6") ?? stageSnapshots[0] ?? null
  const daily = summarizeDailyReport(latestDaily)
  const weekly = summarizeWeeklyReport(latestWeekly)

  if (primaryStage?.backtestRecommendation?.toLowerCase() === "nogo") {
    priorities.push({
      title: "先处理回测结论",
      description: `${primaryStage.stage} 最新评审引用的回测 ${primaryStage.backtestName ?? "未命名回测"} 是 NoGo。先复盘策略、阈值或样本，再重新生成阶段评审。`,
      tone: "bad",
      reportId: primaryStage.report.id,
    })
  }

  if (daily && daily.rejectedCount > 0) {
    const reasons = daily.reasons.length > 0 ? `，主要集中在 ${daily.reasons.join("、")}` : ""
    priorities.push({
      title: "复盘最新日报的拒绝原因",
      description: `最新日报里拒绝了 ${daily.rejectedCount} 个候选${reasons}。如果你想知道“今天为什么没有新增准入”，先看这份日报。`,
      tone: daily.admittedCount > 0 ? "warn" : "bad",
      reportId: latestDaily?.id,
    })
  }

  if (weekly && weekly.nogoCount > 0) {
    priorities.push({
      title: "查看本周 NoGo 是否持续堆积",
      description: `最新周报记录了 ${weekly.backtestCount} 次回测，其中 NoGo ${weekly.nogoCount} 次。它能帮助你判断当前卡点是偶发，还是已经形成连续趋势。`,
      tone: "warn",
      reportId: latestWeekly?.id,
    })
  }

  if (!latestDaily || !latestWeekly || stageSnapshots.length < STAGE_NAMES.length) {
    priorities.push({
      title: "补齐缺失报告",
      description: "如果某些时间窗没有日报、周报或阶段评审，先补生成；没有最新报告时，页面再漂亮也无法替你判断当前状态。",
      tone: "info",
    })
  }

  if (priorities.length === 0) {
    priorities.push({
      title: "先读最新阶段评审",
      description: "当前没有明显的红色阻断项时，阶段评审依然是最快理解系统是否可推进的入口。",
      tone: "info",
      reportId: primaryStage?.report.id,
    })
  }

  return priorities.slice(0, 3)
}

export function buildReportsDashboard(reports: ReportRecord[], auditEvents: AuditRecord[]): ReportsDashboard {
  const orderedReports = sortReports(reports)
  const latestDaily = latestReport(orderedReports, (report) => report.report_type === "daily_summary")
  const latestWeekly = latestReport(orderedReports, (report) => report.report_type === "weekly_summary")
  const stageSnapshots = STAGE_NAMES.map((stage) =>
    buildStageSnapshot(latestReport(orderedReports, (report) => report.report_type === `stage_review:${stage}`), stage),
  ).filter((snapshot): snapshot is StageSnapshot => snapshot !== null)

  const latestAuditTime =
    [...auditEvents].sort((left, right) => toTimestamp(right.created_at) - toTimestamp(left.created_at))[0]?.created_at ?? null

  const daily = summarizeDailyReport(latestDaily)
  const weekly = summarizeWeeklyReport(latestWeekly)
  const stageNoGoCount = stageSnapshots.filter((snapshot) => snapshot.decision.toLowerCase() === "nogo").length

  const quickReports = [
    latestDaily,
    latestWeekly,
    stageSnapshots.find((snapshot) => snapshot.stage === "M6")?.report ?? stageSnapshots[0]?.report ?? null,
  ].filter((report, index, items): report is ReportRecord => report !== null && items.findIndex((item) => item?.id === report.id) === index)

  return {
    headline: buildHeadline(stageSnapshots, latestWeekly, latestDaily),
    metrics: [
      {
        label: "阶段门槛",
        value: stageSnapshots.length === 0 ? "暂无" : `${stageNoGoCount}/${stageSnapshots.length} 未放行`,
        hint:
          stageSnapshots.length === 0
            ? "还没有最新阶段评审"
            : `最新 M4/M5/M6 中 NoGo ${stageNoGoCount} 份`,
        tone: stageNoGoCount > 0 ? "bad" : "good",
      },
      {
        label: "周报回测",
        value: weekly ? `${weekly.backtestCount} 次` : "暂无",
        hint: weekly ? `Go ${weekly.goCount} / 观察 ${weekly.watchCount} / NoGo ${weekly.nogoCount}` : "还没有最新周报",
        tone: weekly && weekly.nogoCount > 0 ? "warn" : "info",
      },
      {
        label: "日报候选",
        value: daily ? `${daily.candidateTotal} 个` : "暂无",
        hint: daily ? `准入 ${daily.admittedCount} / 拒绝 ${daily.rejectedCount} / 审计 ${daily.auditCount}` : "还没有最新日报",
        tone: daily && daily.rejectedCount > 0 && daily.admittedCount === 0 ? "warn" : "info",
      },
      {
        label: "最近审计",
        value: latestAuditTime ? "已更新" : "暂无",
        hint: latestAuditTime ?? "最近还没有新的审计轨迹",
        tone: latestAuditTime ? "good" : "info",
      },
    ],
    priorities: buildPriorities(stageSnapshots, latestWeekly, latestDaily),
    primaryStage: stageSnapshots.find((snapshot) => snapshot.stage === "M6") ?? stageSnapshots[0] ?? null,
    quickReports,
    stageSnapshots,
    latestDaily,
    latestWeekly,
    latestAuditTime,
  }
}
