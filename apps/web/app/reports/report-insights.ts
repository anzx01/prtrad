import { asBoolean, asNumber, asRecord, asStringList, formatLabel, type ReportRecord } from "./report-primitives"

type InsightTone = "neutral" | "good" | "warn" | "bad"

interface ReportInsight {
  title: string
  detail: string
  tone: InsightTone
  hints: string[]
}

function pickToneForDecision(decision: string): InsightTone {
  return decision.toLowerCase() === "go" ? "good" : "bad"
}

function joinList(values: string[]) {
  return values.filter((item) => item.trim().length > 0).join("、")
}

function describeDailySummary(report: ReportRecord): ReportInsight {
  const data = asRecord(report.report_data)
  const summary = asRecord(data.summary)
  const candidateTotal = asNumber(summary.candidate_total) ?? 0
  const admittedCount = asNumber(summary.admitted_count) ?? 0
  const rejectedCount = asNumber(summary.rejected_count) ?? 0
  const auditCount = asNumber(summary.audit_event_count) ?? 0
  const auditable = asBoolean(summary.auditable) ?? false
  const dqFailures = asNumber(asRecord(data.dq_alert_snapshot).recent_failures) ?? 0
  const missingSections = asStringList(data.missing_sections).map(formatLabel)

  if (candidateTotal === 0) {
    return {
      title: "这份日报所在时间窗内，没有新的准入候选进入评估。",
      detail: `当前更像是一张“链路健康确认单”：审计事件 ${auditCount} 条，最近 DQ 失败 ${dqFailures} 次。`,
      tone: auditable ? "neutral" : "warn",
      hints: [
        "候选、准入、拒绝全为 0，通常表示当天没有新的 NetEV 评估输入，不一定是页面故障。",
        auditable ? "本日报已有审计日志支撑，可用于追溯。" : "当前缺少审计日志，报告可追溯性不足。",
        ...missingSections.map((item) => `缺少 ${item}，阅读时要注意信息并不完整。`),
      ],
    }
  }

  return {
    title: `这份日报显示当日共评估 ${candidateTotal} 个候选，其中准入 ${admittedCount} 个，拒绝 ${rejectedCount} 个。`,
    detail: `审计事件 ${auditCount} 条，最近 DQ 失败 ${dqFailures} 次${auditable ? "，当前可审计" : "，但当前审计证据不足"}。`,
    tone: admittedCount > 0 ? "good" : rejectedCount > 0 ? "warn" : "neutral",
    hints: [
      rejectedCount > 0 ? "若拒绝数较高，重点看下方拒绝原因分布。" : "当前没有明显拒绝堆积。",
      dqFailures > 0 ? "若 DQ 失败次数上升，优先排查 snapshot / ingest 链路。" : "当前看不到明显的数据质量失败信号。",
    ],
  }
}

function describeWeeklySummary(report: ReportRecord): ReportInsight {
  const data = asRecord(report.report_data)
  const summary = asRecord(data.summary)

  if (Object.keys(summary).length === 0 && "total_markets" in data) {
    const totalMarkets = asNumber(data.total_markets) ?? 0
    const highRisk = asNumber(data.high_risk_markets) ?? 0
    const reviewed = asNumber(data.reviewed_count) ?? 0
    const approved = asNumber(data.approved_count) ?? 0
    const rejected = asNumber(data.rejected_count) ?? 0
    return {
      title: `这份旧版周报覆盖 ${totalMarkets} 个市场，其中高风险 ${highRisk} 个。`,
      detail: `本周人工审核 ${reviewed} 个，已通过 ${approved} 个，拒绝 ${rejected} 个。`,
      tone: highRisk > 0 ? "warn" : "neutral",
      hints: ["这是历史结构的周报，字段含义偏总览统计，不含新版回测/风险时间线。"],
    }
  }

  const backtestCount = asNumber(summary.backtest_run_count) ?? 0
  const riskEventCount = asNumber(summary.risk_event_count) ?? 0
  const recommendationBreakdown = asRecord(summary.recommendation_breakdown)
  const goCount = asNumber(recommendationBreakdown.go) ?? 0
  const watchCount = asNumber(recommendationBreakdown.watch) ?? 0
  const nogoCount = asNumber(recommendationBreakdown.nogo) ?? 0

  if (backtestCount === 0 && riskEventCount === 0) {
    return {
      title: "这份周报所在时间窗内，没有新的回测结果，也没有新的风险状态变化。",
      detail: "这通常表示本周没有执行新的回测/风控动作，不代表报表系统本身异常。",
      tone: "neutral",
      hints: [
        "如果你本来预期这里有数据，优先确认 backtest run 和 risk-state event 是否真的在该时间窗内产生。",
        "只有在执行过回测或发生风险状态切换后，周报才会更有信息量。",
      ],
    }
  }

  return {
    title: `这份周报显示本周完成 ${backtestCount} 次回测，发生 ${riskEventCount} 次风险状态变化。`,
    detail: `回测建议分布为 Go ${goCount}、观察 ${watchCount}、NoGo ${nogoCount}。`,
    tone: nogoCount > 0 ? "warn" : goCount > 0 ? "good" : "neutral",
    hints: [
      nogoCount > 0 ? "若 NoGo 较多，优先下钻查看最近回测结论和风险时间线。" : "当前没有明显的 NoGo 堆积。",
    ],
  }
}

function describeStageReview(report: ReportRecord): ReportInsight {
  const data = asRecord(report.report_data)
  const stageName = String(data.stage_name ?? "M6")
  const decision = String(data.decision ?? "NoGo")
  const reasons = asStringList(data.nogo_reasons).map(formatLabel)
  const latestBacktest = asRecord(data.latest_backtest)
  const latestShadowRun = asRecord(data.latest_shadow_run)
  const latestBacktestRecommendation = String(latestBacktest.recommendation ?? "").toLowerCase()
  const latestBacktestName = String(latestBacktest.run_name ?? "").trim()
  const latestShadowRecommendation = String(latestShadowRun.recommendation ?? "").toLowerCase()

  if (decision.toLowerCase() === "go") {
    return {
      title: `当前 ${stageName} 阶段评审结论为 Go，可以继续进入 Go/NoGo 决策。`,
      detail: "backtest、shadow run、审计等核心证据已满足当前门槛。",
      tone: "good",
      hints: ["继续决策前，仍建议人工复核下方 linked evidence 是否对应最新批次。"],
    }
  }

  const backtestDetail =
    latestBacktestRecommendation === "nogo"
      ? `最新回测 ${latestBacktestName || "未命名回测"} 给出了 NoGo。`
      : reasons.length > 0
        ? `主要阻断原因：${joinList(reasons)}。`
        : "存在未满足的门槛，但报告中没有写明具体阻断原因。"

  const shadowDetail =
    latestShadowRecommendation === "go"
      ? "影子运行虽然是 Go，但目前还不足以解除门槛。"
      : latestShadowRecommendation.length > 0
        ? `影子运行当前为 ${formatLabel(latestShadowRecommendation)}。`
        : ""

  return {
    title: `当前 ${stageName} 阶段评审结论为 NoGo，暂时不建议推进上线。`,
    detail: `${backtestDetail}${shadowDetail ? ` ${shadowDetail}` : ""}`,
    tone: pickToneForDecision(decision),
    hints: [
      "如果这里看到 NoGo，不是页面报错，而是门槛检查真的没有通过。",
      "优先补齐 backtest、shadow run、审计或 stage review 证据，再重新生成评审。",
    ],
  }
}

function describeTaggingQuality(report: ReportRecord): ReportInsight {
  const data = asRecord(report.report_data)
  const totalTagged = asNumber(data.total_tagged) ?? 0
  const accuracyRate = asNumber(data.accuracy_rate) ?? 0
  const manualReviews = asNumber(data.manual_reviews) ?? 0
  const conflictsDetected = asNumber(data.conflicts_detected) ?? 0

  return {
    title: `这份标签质量报告汇总了 ${totalTagged} 条打标结果，整体准确率约 ${(accuracyRate * 100).toFixed(1)}%。`,
    detail: `其中人工复核 ${manualReviews} 条，发现冲突 ${conflictsDetected} 条。`,
    tone: accuracyRate >= 0.95 ? "good" : accuracyRate >= 0.9 ? "warn" : "bad",
    hints: ["这类报告属于历史总览，不是 M5 主链路里的日报/周报/阶段评审。"],
  }
}

function describeRiskAssessment(report: ReportRecord): ReportInsight {
  const data = asRecord(report.report_data)
  const criticalAlerts = asNumber(data.critical_alerts) ?? 0
  const warningAlerts = asNumber(data.warning_alerts) ?? 0
  const infoAlerts = asNumber(data.info_alerts) ?? 0

  return {
    title: `这份风险评估报告记录了 ${criticalAlerts} 条严重告警、${warningAlerts} 条预警和 ${infoAlerts} 条提示。`,
    detail: criticalAlerts > 0 ? "优先关注下方重点风险列表中的市场和触发原因。" : "当前没有严重告警，主要用于做总体观察。",
    tone: criticalAlerts > 0 ? "bad" : warningAlerts > 0 ? "warn" : "good",
    hints: ["这类报告同样属于历史结构，阅读时更适合看总体风险热区，而不是上线门槛。"],
  }
}

function describeGeneric(report: ReportRecord): ReportInsight {
  const topFields = Object.entries(asRecord(report.report_data))
    .filter(([, value]) => typeof value === "number" || typeof value === "string" || typeof value === "boolean")
    .slice(0, 3)
    .map(([key, value]) => `${formatLabel(key)}：${String(value)}`)

  return {
    title: "这份报告暂时没有专用中文解读模版。",
    detail: topFields.length > 0 ? `可先关注这些关键字段：${topFields.join("；")}。` : "可展开下方原始 JSON 查看详细内容。",
    tone: "neutral",
    hints: ["如果这类报告后续还会长期使用，可以再补专门的展示模版。"],
  }
}

export function describeReport(report: ReportRecord): ReportInsight {
  if (report.report_type === "daily_summary") {
    return describeDailySummary(report)
  }
  if (report.report_type === "weekly_summary") {
    return describeWeeklySummary(report)
  }
  if (report.report_type.startsWith("stage_review:")) {
    return describeStageReview(report)
  }
  if (report.report_type === "tagging_quality") {
    return describeTaggingQuality(report)
  }
  if (report.report_type === "risk_assessment") {
    return describeRiskAssessment(report)
  }
  return describeGeneric(report)
}
