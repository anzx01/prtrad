import type {
  DashboardActionSuggestion,
  DashboardNarrative,
  DashboardSnapshot,
  WorkflowCard,
} from "./types"
import { formatReviewReasonDisplay } from "@/lib/review"
import {
  formatCount,
  formatDateTime,
  formatRecommendation,
  formatRiskState,
  latestStageReport,
  reportDecision,
} from "./summary-shared"

function pushNarrative(list: DashboardNarrative[], narrative: DashboardNarrative) {
  if (!list.some((item) => item.id === narrative.id)) {
    list.push(narrative)
  }
}

export function buildNarratives(snapshot: DashboardSnapshot): DashboardNarrative[] {
  const narratives: DashboardNarrative[] = []
  const dqSummary = snapshot.dq?.summary
  const pendingReviews = snapshot.reviewQueue?.total ?? snapshot.monitoring?.review_queue?.pending ?? 0
  const latestBacktest = snapshot.backtests[0]
  const latestShadow = snapshot.shadowRuns[0]
  const latestM6 = latestStageReport(snapshot.reports, "M6")
  const activeCalibration = snapshot.calibration.filter((unit) => unit.is_active).length
  const topReviewReason = snapshot.reviewQueue?.tasks[0]?.review_reason_code

  if (dqSummary) {
    pushNarrative(narratives, {
      id: "dq-health",
      title: "数据接入不是当前主阻塞",
      body: `最新 DQ 快照在 ${dqSummary.snapshot_age_seconds ?? "-"} 秒前，${formatCount(dqSummary.total_checks)} 个市场里没有 fail。即使 warn 偏多，也更像“需要持续观察”，不是“链路断了”。`,
      tone: dqSummary.freshness_status === "fresh" ? "good" : "warn",
      href: "/dq",
    })
  }

  if (pendingReviews > 0) {
    pushNarrative(narratives, {
      id: "review-backlog",
      title: "人工审核积压是当前最明显的学习成本",
      body: `Review Queue 里还有 ${formatCount(pendingReviews)} 条 pending。样例原因是 ${formatReviewReasonDisplay(topReviewReason)}，说明很多问题不是系统没跑，而是结果还在等人工接住。`,
      tone: pendingReviews > 500 ? "bad" : "warn",
      href: "/review",
    })
  }

  if (latestShadow && latestBacktest) {
    pushNarrative(narratives, {
      id: "evidence-conflict",
      title: "上线证据目前相互打架",
      body: `最新 shadow 给的是 ${formatRecommendation(latestShadow.recommendation)}，但最近 backtest 仍是 ${formatRecommendation(latestBacktest.recommendation)}。在这种冲突没解释清楚前，Go/NoGo 理应不放行。`,
      tone: latestBacktest.recommendation === "nogo" ? "bad" : "warn",
      href: "/launch-review",
    })
  }

  if (latestM6) {
    pushNarrative(narratives, {
      id: "stage-review",
      title: "阶段评审要和新证据一起刷新",
      body: `当前 M6 评审生成于 ${formatDateTime(latestM6.generated_at)}，结论是 ${reportDecision(latestM6).toUpperCase() || "-"}。如果 backtest 或 shadow 已更新，阶段评审也应同步重生，不然用户只能手动对比。`,
      tone: reportDecision(latestM6) === "go" ? "good" : "warn",
      href: "/reports",
    })
  }

  pushNarrative(narratives, {
    id: "calibration",
    title: "校准不是全无，而是可用样本还偏薄",
    body: `${formatCount(snapshot.calibration.length)} 个校准单元里有 ${formatCount(activeCalibration)} 个活跃。看到很多 0 或 inactive 时，更常见的含义是样本不足，而不是页面乱了。`,
    tone: activeCalibration > 0 ? "info" : "warn",
    href: "/calibration",
  })

  return narratives.slice(0, 5)
}

export function buildNextActions(snapshot: DashboardSnapshot) {
  const actions: DashboardActionSuggestion[] = []
  const pendingReviews = snapshot.reviewQueue?.total ?? snapshot.monitoring?.review_queue?.pending ?? 0
  const latestBacktest = snapshot.backtests[0]
  const latestM6 = latestStageReport(snapshot.reports, "M6")
  const activeCalibration = snapshot.calibration.filter((unit) => unit.is_active).length

  if (pendingReviews > 0) {
    actions.push({
      id: "review-queue",
      title: "先消化待审队列",
      body: `当前有 ${formatCount(pendingReviews)} 条 pending。系统暂时不能自动替你做人审，但可以明确告诉你这是现在最大的人工瓶颈。`,
      tone: pendingReviews > 500 ? "bad" : "warn",
      cta: "打开 Review Queue",
      href: "/review",
    })
  }

  if (!latestBacktest || latestBacktest.recommendation !== "go") {
    actions.push({
      id: "run-backtest",
      title: "重新跑一轮回测，先确认 NoGo 还成不成立",
      body: latestBacktest
        ? `最近回测仍是 ${formatRecommendation(latestBacktest.recommendation)}，而且 admitted 为 ${(latestBacktest.summary.totals?.admitted_count ?? 0).toString()}。建议在当前数据基础上重新跑一轮。`
        : "当前还没有可用 backtest 证据，建议直接补一轮默认窗口回测。",
      tone: "bad",
      cta: "运行回测",
      actionId: "runBacktest",
    })
  }

  if (!latestM6 || reportDecision(latestM6) !== "go") {
    actions.push({
      id: "stage-bundle",
      title: "把 M4 / M5 / M6 阶段评审一次补齐",
      body: "阶段评审不该散落在各个细页里手动对照。这里可以一口气重生三份阶段评审，让主链路判断更完整。",
      tone: "warn",
      cta: "生成阶段评审包",
      actionId: "generateStageBundle",
    })
  }

  if (activeCalibration === 0) {
    actions.push({
      id: "recompute-calibration",
      title: "先重算长窗口校准",
      body: "当活跃校准单元为 0 时，最先该做的是重算，而不是继续猜页面显示是不是坏了。",
      tone: "warn",
      cta: "重算校准",
      actionId: "recomputeCalibration",
    })
  }

  actions.push({
    id: "autopilot-refresh",
    title: "直接一键刷新完整证据包",
    body: "系统会顺序重算风险暴露、重算校准、跑 backtest、跑 shadow、生成日报/周报与 M4-M6 阶段评审，尽量把手工拼流程这件事降到最低。",
    tone: "info",
    cta: "一键刷新证据包",
    actionId: "refreshEvidencePack",
  })

  return actions.slice(0, 4)
}

export function buildWorkflows(snapshot: DashboardSnapshot): WorkflowCard[] {
  const dqSummary = snapshot.dq?.summary
  const pendingReviews = snapshot.reviewQueue?.total ?? snapshot.monitoring?.review_queue?.pending ?? 0
  const breachedCount = snapshot.exposures.filter((item) => item.is_breached).length
  const activeCalibration = snapshot.calibration.filter((unit) => unit.is_active).length
  const latestShadow = snapshot.shadowRuns[0]
  const latestLaunch = snapshot.launchReviews[0]
  const failedLaunchChecks = latestLaunch?.checklist.filter((item) => !item.passed).length ?? 0

  return [
    {
      id: "dq",
      label: "数据接入与 DQ",
      status: dqSummary?.freshness_status === "fresh" ? "新鲜" : "待处理",
      detail: dqSummary
        ? `最新批次 ${formatCount(dqSummary.total_checks)} 市场，warn ${(dqSummary.status_distribution.warn ?? 0).toString()}，fail ${(dqSummary.status_distribution.fail ?? 0).toString()}。`
        : "还没有拿到 DQ 摘要。",
      tone: dqSummary?.freshness_status === "fresh" ? "good" : "warn",
      href: "/dq",
    },
    {
      id: "review",
      label: "分类与人工审核",
      status: pendingReviews > 0 ? "积压中" : "已清空",
      detail:
        pendingReviews > 0
          ? `待审 ${formatCount(pendingReviews)} 条，最适合先去处理队列，而不是继续盯着 0 值发愁。`
          : "当前没有待审任务。",
      tone: pendingReviews > 500 ? "bad" : pendingReviews > 0 ? "warn" : "good",
      href: "/review",
    },
    {
      id: "calibration",
      label: "校准与准入",
      status: activeCalibration > 0 ? "可用" : "待重算",
      detail: `${formatCount(activeCalibration)} / ${formatCount(snapshot.calibration.length)} 个校准单元活跃。`,
      tone: activeCalibration > 0 ? "good" : "warn",
      href: "/calibration",
    },
    {
      id: "risk",
      label: "风险与影子运行",
      status: latestShadow ? formatRecommendation(latestShadow.recommendation) : "缺证据",
      detail: latestShadow
        ? `风险状态 ${formatRiskState(latestShadow.risk_state)}，当前 breached exposure ${formatCount(breachedCount)} 个。`
        : "当前还没有可用 shadow run。",
      tone:
        latestShadow?.recommendation === "go" && breachedCount === 0 ? "good" : latestShadow ? "warn" : "warn",
      href: "/risk",
    },
    {
      id: "launch",
      label: "上线门槛与 Go/NoGo",
      status: latestLaunch ? latestLaunch.status.toUpperCase() : "未建立",
      detail: latestLaunch
        ? `最近评审还有 ${formatCount(failedLaunchChecks)} 项 checklist 未通过，标题为 ${latestLaunch.title}。`
        : "当前还没有 launch review，系统无法替你汇总最终结论。",
      tone: failedLaunchChecks > 0 ? "bad" : latestLaunch ? "good" : "warn",
      href: "/launch-review",
    },
    {
      id: "reports",
      label: "日报、周报与阶段评审",
      status: snapshot.reports.length > 0 ? "已归档" : "空白",
      detail:
        snapshot.reports.length > 0
          ? `最近已有 ${formatCount(snapshot.reports.length)} 份报告，可直接作为解释层阅读。`
          : "当前还没有结构化报告。",
      tone: snapshot.reports.length > 0 ? "info" : "warn",
      href: "/reports",
    },
  ]
}
