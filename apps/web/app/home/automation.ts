import { apiGet, apiPost } from "@/lib/api"

import type {
  ActionId,
  BacktestRun,
  CalibrationUnit,
  DashboardSnapshot,
  DQSummaryResponse,
  ExposureItem,
  KillSwitchRequest,
  LaunchReview,
  MonitoringMetrics,
  ReportRecord,
  ReviewQueueResponse,
  RiskStateData,
  ShadowRun,
} from "./types"

type LogHandler = (tone: "info" | "good" | "warn" | "bad", message: string) => void

const AUTOPILOT_ACTOR = "console_autopilot"
const STAGES = ["M4", "M5", "M6"] as const

function emptySnapshot(): DashboardSnapshot {
  return {
    monitoring: null,
    dq: null,
    reviewQueue: null,
    riskState: null,
    exposures: [],
    killSwitches: [],
    calibration: [],
    backtests: [],
    shadowRuns: [],
    launchReviews: [],
    reports: [],
    errors: {},
  }
}

function formatErrorMessage(error: unknown) {
  if (error instanceof Error) {
    return error.message
  }
  return typeof error === "string" ? error : "请求失败"
}

function isLockedError(error: unknown) {
  return formatErrorMessage(error).toLowerCase().includes("database is locked")
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

function buildStamp() {
  const date = new Date()
  const pad = (value: number) => String(value).padStart(2, "0")
  return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`
}

async function runStep(
  label: string,
  execute: () => Promise<unknown>,
  onLog: LogHandler,
  attempt = 1,
) {
  onLog("info", `正在执行：${label}`)

  try {
    await execute()
    onLog("good", `已完成：${label}`)
  } catch (error) {
    if (attempt < 2 && isLockedError(error)) {
      onLog("warn", `${label} 遇到数据库锁，0.8 秒后自动重试`)
      await sleep(800)
      await runStep(label, execute, onLog, attempt + 1)
      return
    }
    throw error
  }
}

export async function fetchDashboardSnapshot(): Promise<DashboardSnapshot> {
  const snapshot = emptySnapshot()
  const [
    monitoringResult,
    dqResult,
    reviewQueueResult,
    riskStateResult,
    exposuresResult,
    killSwitchesResult,
    calibrationResult,
    backtestsResult,
    shadowRunsResult,
    launchReviewsResult,
    reportsResult,
  ] = await Promise.allSettled([
    apiGet<{ metrics: MonitoringMetrics }>("/monitoring/metrics"),
    apiGet<DQSummaryResponse>("/dq/summary?limit=5"),
    apiGet<ReviewQueueResponse>("/review/queue?queue_status=pending&page=1&page_size=5"),
    apiGet<RiskStateData>("/risk/state"),
    apiGet<{ exposures: ExposureItem[] }>("/risk/exposures"),
    apiGet<{ requests: KillSwitchRequest[] }>("/risk/kill-switch?status=pending"),
    apiGet<CalibrationUnit[]>("/calibration/units?include_inactive=true"),
    apiGet<{ runs: BacktestRun[] }>("/backtests"),
    apiGet<{ runs: ShadowRun[] }>("/shadow"),
    apiGet<{ reviews: LaunchReview[] }>("/launch-review"),
    apiGet<{ reports: ReportRecord[] }>("/reports"),
  ])

  if (monitoringResult.status === "fulfilled") {
    snapshot.monitoring = monitoringResult.value.metrics ?? null
  } else {
    snapshot.errors.monitoring = formatErrorMessage(monitoringResult.reason)
  }

  if (dqResult.status === "fulfilled") {
    snapshot.dq = dqResult.value
  } else {
    snapshot.errors.dq = formatErrorMessage(dqResult.reason)
  }

  if (reviewQueueResult.status === "fulfilled") {
    snapshot.reviewQueue = reviewQueueResult.value
  } else {
    snapshot.errors.reviewQueue = formatErrorMessage(reviewQueueResult.reason)
  }

  if (riskStateResult.status === "fulfilled") {
    snapshot.riskState = riskStateResult.value
  } else {
    snapshot.errors.riskState = formatErrorMessage(riskStateResult.reason)
  }

  if (exposuresResult.status === "fulfilled") {
    snapshot.exposures = exposuresResult.value.exposures ?? []
  } else {
    snapshot.errors.exposures = formatErrorMessage(exposuresResult.reason)
  }

  if (killSwitchesResult.status === "fulfilled") {
    snapshot.killSwitches = killSwitchesResult.value.requests ?? []
  } else {
    snapshot.errors.killSwitches = formatErrorMessage(killSwitchesResult.reason)
  }

  if (calibrationResult.status === "fulfilled") {
    snapshot.calibration = calibrationResult.value
  } else {
    snapshot.errors.calibration = formatErrorMessage(calibrationResult.reason)
  }

  if (backtestsResult.status === "fulfilled") {
    snapshot.backtests = backtestsResult.value.runs ?? []
  } else {
    snapshot.errors.backtests = formatErrorMessage(backtestsResult.reason)
  }

  if (shadowRunsResult.status === "fulfilled") {
    snapshot.shadowRuns = shadowRunsResult.value.runs ?? []
  } else {
    snapshot.errors.shadowRuns = formatErrorMessage(shadowRunsResult.reason)
  }

  if (launchReviewsResult.status === "fulfilled") {
    snapshot.launchReviews = launchReviewsResult.value.reviews ?? []
  } else {
    snapshot.errors.launchReviews = formatErrorMessage(launchReviewsResult.reason)
  }

  if (reportsResult.status === "fulfilled") {
    snapshot.reports = reportsResult.value.reports ?? []
  } else {
    snapshot.errors.reports = formatErrorMessage(reportsResult.reason)
  }

  return snapshot
}

export async function runDashboardAction(actionId: ActionId, onLog: LogHandler) {
  const stamp = buildStamp()

  const stageStep = (stage: (typeof STAGES)[number]) => ({
    label: `生成 ${stage} 阶段评审`,
    execute: () =>
      apiPost("/reports/generate", {
        report_type: "stage_review",
        generated_by: AUTOPILOT_ACTOR,
        stage_name: stage,
      }),
  })

  const plans: Record<ActionId, Array<{ label: string; execute: () => Promise<unknown> }>> = {
    refreshEvidencePack: [
      { label: "重算风险暴露", execute: () => apiPost("/risk/exposures/compute") },
      {
        label: "重算长窗口校准",
        execute: () => apiPost("/calibration/recompute-all?window_type=long"),
      },
      {
        label: "运行回测",
        execute: () =>
          apiPost("/backtests/run", {
            run_name: `autopilot-backtest-${stamp}`,
            window_days: 30,
            executed_by: AUTOPILOT_ACTOR,
            strategy_version: "baseline-v1",
          }),
      },
      {
        label: "运行影子检查",
        execute: () =>
          apiPost("/shadow/execute", {
            run_name: `autopilot-shadow-${stamp}`,
            executed_by: AUTOPILOT_ACTOR,
          }),
      },
      {
        label: "生成日报",
        execute: () =>
          apiPost("/reports/generate", {
            report_type: "daily_summary",
            generated_by: AUTOPILOT_ACTOR,
          }),
      },
      {
        label: "生成周报",
        execute: () =>
          apiPost("/reports/generate", {
            report_type: "weekly_summary",
            generated_by: AUTOPILOT_ACTOR,
          }),
      },
      stageStep("M4"),
      stageStep("M5"),
      stageStep("M6"),
    ],
    recomputeRisk: [{ label: "重算风险暴露", execute: () => apiPost("/risk/exposures/compute") }],
    recomputeCalibration: [
      {
        label: "重算长窗口校准",
        execute: () => apiPost("/calibration/recompute-all?window_type=long"),
      },
    ],
    runBacktest: [
      {
        label: "运行回测",
        execute: () =>
          apiPost("/backtests/run", {
            run_name: `autopilot-backtest-${stamp}`,
            window_days: 30,
            executed_by: AUTOPILOT_ACTOR,
            strategy_version: "baseline-v1",
          }),
      },
    ],
    runShadow: [
      {
        label: "运行影子检查",
        execute: () =>
          apiPost("/shadow/execute", {
            run_name: `autopilot-shadow-${stamp}`,
            executed_by: AUTOPILOT_ACTOR,
          }),
      },
    ],
    generateDaily: [
      {
        label: "生成日报",
        execute: () =>
          apiPost("/reports/generate", {
            report_type: "daily_summary",
            generated_by: AUTOPILOT_ACTOR,
          }),
      },
    ],
    generateWeekly: [
      {
        label: "生成周报",
        execute: () =>
          apiPost("/reports/generate", {
            report_type: "weekly_summary",
            generated_by: AUTOPILOT_ACTOR,
          }),
      },
    ],
    generateStageBundle: [stageStep("M4"), stageStep("M5"), stageStep("M6")],
    generateStageM4: [stageStep("M4")],
    generateStageM5: [stageStep("M5")],
    generateStageM6: [stageStep("M6")],
  }

  for (const step of plans[actionId]) {
    await runStep(step.label, step.execute, onLog)
    await sleep(160)
  }
}
