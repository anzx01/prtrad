import type { DashboardMetric, DashboardSnapshot, DashboardSummary, StageCard, StageName } from "./types"
import {
  formatCount,
  formatDateTime,
  formatRecommendation,
  formatRiskState,
  latestEvidenceTime,
  latestStageReport,
  reportDecision,
  reportReasons,
  stageActionId,
} from "./summary-shared"

const stageNames: StageName[] = ["M4", "M5", "M6"]

export function buildStageCards(snapshot: DashboardSnapshot): StageCard[] {
  const evidenceTime = latestEvidenceTime(snapshot)

  return stageNames.map((stage) => {
    const report = latestStageReport(snapshot.reports, stage)
    if (!report) {
      return {
        stage,
        title: `${stage} 阶段评审缺失`,
        detail: `当前还没有 ${stage} 的阶段评审，建议先生成一份，避免主链路停在“没人知道现在算不算通过”。`,
        tone: "warn",
        actionId: stageActionId(stage),
      }
    }

    const generatedAt = new Date(report.generated_at).getTime()
    const stale = evidenceTime !== null && Number.isFinite(generatedAt) && generatedAt < evidenceTime
    const decision = reportDecision(report)
    const reasons = reportReasons(report)

    if (stale) {
      return {
        stage,
        title: `${stage} 阶段评审需要刷新`,
        detail: `${formatDateTime(report.generated_at)} 的评审已经落后于更新的 backtest / shadow 证据，建议重新生成。`,
        tone: "warn",
        actionId: stageActionId(stage),
      }
    }

    if (decision === "go") {
      return {
        stage,
        title: `${stage} 阶段评审已通过`,
        detail: `最近一份 ${stage} 评审给出的结论是 Go，可继续作为上线证据使用。`,
        tone: "good",
        actionId: stageActionId(stage),
      }
    }

    return {
      stage,
      title: `${stage} 阶段评审仍未通过`,
      detail:
        reasons.length > 0
          ? `最近结论仍是 NoGo，阻塞点包括：${reasons.slice(0, 3).join("、")}。`
          : "最近结论仍是 NoGo，需要重新核对 backtest、shadow 与审计证据。",
      tone: "bad",
      actionId: stageActionId(stage),
    }
  })
}

export function buildHeadline(snapshot: DashboardSnapshot): DashboardSummary["headline"] {
  const pendingReviews = snapshot.reviewQueue?.total ?? snapshot.monitoring?.review_queue?.pending ?? 0
  const latestBacktest = snapshot.backtests[0]
  const latestShadow = snapshot.shadowRuns[0]
  const latestM6 = latestStageReport(snapshot.reports, "M6")
  const pendingKillSwitches = snapshot.killSwitches.length
  const riskState = snapshot.riskState?.state ?? "Normal"

  if (pendingKillSwitches > 0 || riskState === "RiskOff" || riskState === "Frozen") {
    return {
      title: "系统仍处于风险接管状态",
      description: `当前风险状态为 ${formatRiskState(riskState)}，待处理 kill-switch ${formatCount(pendingKillSwitches)} 条。建议先解除人工接管，再讨论是否推进。`,
      tone: "bad",
    }
  }

  if (latestBacktest?.recommendation === "nogo" || reportDecision(latestM6) === "nogo") {
    return {
      title: "现在不适合直接推进上线",
      description: `最新 shadow 是 ${formatRecommendation(latestShadow?.recommendation)}，但 backtest / 阶段评审仍没有转成 Go，当前更像“证据冲突”，不是“页面没反应”。`,
      tone: "bad",
    }
  }

  if (pendingReviews > 0) {
    return {
      title: "系统能继续跑，但人工积压明显",
      description: `当前 pending review 还有 ${formatCount(pendingReviews)} 条，主链路最大的学习成本不在页面，而在需要人工消化的分类与审批积压。`,
      tone: "warn",
    }
  }

  return {
    title: "主链路整体可继续推进",
    description: "当前没有明显的风险接管或证据阻断，接下来可以按阶段评审和上线复核继续推进。",
    tone: "good",
  }
}

export function buildMetrics(snapshot: DashboardSnapshot): DashboardMetric[] {
  const dqSummary = snapshot.dq?.summary
  const activeCalibration = snapshot.calibration.filter((unit) => unit.is_active).length
  const failedLaunchChecks =
    snapshot.launchReviews[0]?.checklist.filter((item) => !item.passed).length ?? 0

  return [
    {
      label: "待审任务",
      value: formatCount(snapshot.reviewQueue?.total ?? snapshot.monitoring?.review_queue?.pending ?? 0),
      hint: "需要人工判断的分类/审批积压",
      tone: (snapshot.reviewQueue?.total ?? 0) > 0 ? "bad" : "good",
    },
    {
      label: "DQ 快照",
      value:
        dqSummary?.snapshot_age_seconds !== null && dqSummary?.snapshot_age_seconds !== undefined
          ? `${dqSummary.snapshot_age_seconds} 秒前`
          : "-",
      hint: dqSummary
        ? `${formatCount(dqSummary.total_checks)} 市场，最近 fail ${(dqSummary.status_distribution.fail ?? 0).toString()}`
        : "还没有 DQ 数据",
      tone: dqSummary?.freshness_status === "fresh" ? "good" : "warn",
    },
    {
      label: "活跃校准",
      value: `${formatCount(activeCalibration)} / ${formatCount(snapshot.calibration.length)}`,
      hint: "活跃单元 / 全部单元",
      tone: activeCalibration > 0 ? "good" : "warn",
    },
    {
      label: "最新回测",
      value: formatRecommendation(snapshot.backtests[0]?.recommendation),
      hint: snapshot.backtests[0] ? formatDateTime(snapshot.backtests[0].created_at) : "还没有回测记录",
      tone:
        snapshot.backtests[0]?.recommendation === "go"
          ? "good"
          : snapshot.backtests[0]?.recommendation === "watch"
            ? "warn"
            : snapshot.backtests[0]
              ? "bad"
              : "neutral",
    },
    {
      label: "最新影子",
      value: formatRecommendation(snapshot.shadowRuns[0]?.recommendation),
      hint: snapshot.shadowRuns[0]
        ? `风险状态 ${formatRiskState(snapshot.shadowRuns[0].risk_state)}`
        : "还没有影子记录",
      tone:
        snapshot.shadowRuns[0]?.recommendation === "go"
          ? "good"
          : snapshot.shadowRuns[0]?.recommendation === "watch"
            ? "warn"
            : snapshot.shadowRuns[0]
              ? "bad"
              : "neutral",
    },
    {
      label: "上线评审",
      value: snapshot.launchReviews[0] ? `${failedLaunchChecks} 项未过` : "-",
      hint: snapshot.launchReviews[0]
        ? `${snapshot.launchReviews[0].status.toUpperCase()} / ${snapshot.launchReviews[0].stage_name}`
        : "还没有 launch review",
      tone: failedLaunchChecks > 0 ? "bad" : "good",
    },
  ]
}
