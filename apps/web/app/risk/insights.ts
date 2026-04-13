import { formatRiskStateLabel, formatThresholdMetricLabel } from "./constants"
import type { ExposureItem, KillSwitchItem, RiskStateData, ThresholdItem } from "./types"

type InsightTone = "info" | "good" | "warn" | "bad"

export interface RiskHeadline {
  title: string
  description: string
  tone: "safe" | "warning" | "danger"
}

export interface RiskPriority {
  id: string
  title: string
  description: string
  tone: InsightTone
  badge: string
}

export interface RiskSpotlight {
  title: string
  description: string
  tone: InsightTone
  items: string[]
  emptyState: string
}

export interface RiskInsights {
  headline: RiskHeadline
  priorities: RiskPriority[]
  spotlight: RiskSpotlight
}

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "-"
  }
  return new Date(value).toLocaleString("zh-CN", { hour12: false })
}

function latestSnapshotAt(exposures: ExposureItem[]) {
  if (exposures.length === 0) {
    return null
  }

  return exposures.reduce((latest, exposure) => {
    if (!latest) {
      return exposure.snapshot_at
    }
    return new Date(exposure.snapshot_at).getTime() > new Date(latest).getTime()
      ? exposure.snapshot_at
      : latest
  }, exposures[0]?.snapshot_at ?? null)
}

function buildHeadline(
  currentState: string,
  pendingRequests: KillSwitchItem[],
  breachedClusters: ExposureItem[],
): RiskHeadline {
  const currentStateLabel = formatRiskStateLabel(currentState)

  if (currentState === "RiskOff" || currentState === "Frozen") {
    return {
      title: `系统当前处于${currentStateLabel}，应先处理人工接管`,
      description: `这不是“顺手看看暴露”就能结束的状态。优先确认 ${pendingRequests.length} 条人工动作和 ${breachedClusters.length} 个越限簇是否已被解释，再讨论是否恢复自动链路。`,
      tone: "danger",
    }
  }

  if (pendingRequests.length > 0) {
    return {
      title: "先处理待审批 kill-switch，再判断风险是否可控",
      description: `当前有 ${pendingRequests.length} 条人工风险动作挂起。它们不处理完，后面的暴露、阈值和状态历史都只是背景信息，不是最终结论。`,
      tone: "warning",
    }
  }

  if (breachedClusters.length > 0) {
    return {
      title: "当前最需要解释的是越限簇，而不是页面本身",
      description: `系统状态虽然还是 ${currentStateLabel}，但已经有 ${breachedClusters.length} 个簇越限。先核对暴露与限额，再决定是否需要提交新的人工动作。`,
      tone: "warning",
    }
  }

  return {
    title: "当前风险链路相对稳定，可继续做例行观察",
    description: `当前状态为 ${currentStateLabel}，没有待审批 kill-switch，也没有暴露越限。此时更适合复核阈值覆盖与历史切换，而不是紧急人工接管。`,
    tone: "safe",
  }
}

function buildPriorities(
  riskState: RiskStateData | null,
  exposures: ExposureItem[],
  thresholds: ThresholdItem[],
  pendingRequests: KillSwitchItem[],
  breachedClusters: ExposureItem[],
): RiskPriority[] {
  const cards: RiskPriority[] = []
  const latestEvent = riskState?.history[0]
  const activeThresholds = thresholds.filter((threshold) => threshold.is_active)

  if (pendingRequests.length > 0) {
    cards.push({
      id: "kill-switch",
      title: "先处理人工风险动作",
      description: `待审批请求里最早的一条来自 ${pendingRequests[0].requested_by}，目标范围是 ${pendingRequests[0].target_scope}。在这些动作结论明确前，不建议继续把注意力分散到阈值调优。`,
      tone: pendingRequests.length > 1 ? "bad" : "warn",
      badge: `${pendingRequests.length} 条待审批`,
    })
  }

  if (breachedClusters.length > 0) {
    const highest = [...breachedClusters].sort((left, right) => right.utilization_rate - left.utilization_rate)[0]
    cards.push({
      id: "breached",
      title: "优先解释越限簇与限额关系",
      description: `当前最紧张的簇是 ${highest.cluster_code}，利用率 ${(highest.utilization_rate * 100).toFixed(1)}%，净暴露 ${highest.net_exposure.toFixed(4)}，上限 ${highest.limit_value.toFixed(2)}。`,
      tone: breachedClusters.length > 2 ? "bad" : "warn",
      badge: `${breachedClusters.length} 个簇越限`,
    })
  } else if (exposures.length > 0) {
    const nearest = [...exposures].sort((left, right) => right.utilization_rate - left.utilization_rate)[0]
    cards.push({
      id: "near-limit",
      title: "没有越限，但仍要盯住最接近门槛的簇",
      description: `当前最接近上限的是 ${nearest.cluster_code}，利用率 ${(nearest.utilization_rate * 100).toFixed(1)}%。如果它继续上升，下一步就该先看暴露而不是阈值表。`,
      tone: nearest.utilization_rate >= 0.7 ? "warn" : "info",
      badge: "离门槛最近",
    })
  }

  if (activeThresholds.length > 0) {
    const sample = activeThresholds
      .slice(0, 2)
      .map((threshold) => `${threshold.cluster_code} / ${formatThresholdMetricLabel(threshold.metric_name)}`)
      .join("、")
    cards.push({
      id: "thresholds",
      title: "当前已有阈值覆盖项生效",
      description: `系统并不完全依赖默认阈值。当前有 ${activeThresholds.length} 条覆盖项，示例包括 ${sample}。调整前应先确认问题来自真实风险，而不是人为放宽或收紧过。`,
      tone: activeThresholds.length > 2 ? "warn" : "info",
      badge: `${activeThresholds.length} 条覆盖`,
    })
  } else {
    cards.push({
      id: "thresholds-default",
      title: "当前回落在默认阈值上运行",
      description: "这意味着暴露异常更可能是链路真实状态，而不是某个临时阈值覆盖造成的显示偏差。",
      tone: "good",
      badge: "默认阈值",
    })
  }

  if (latestEvent) {
    cards.push({
      id: "history",
      title: "回看最近一次状态切换，确认是自动还是人工",
      description: `${formatDateTime(latestEvent.created_at)} 从 ${formatRiskStateLabel(latestEvent.from_state)} 切到 ${formatRiskStateLabel(latestEvent.to_state)}，${latestEvent.actor_id ? `操作人 ${latestEvent.actor_id}` : "由系统自动触发"}。`,
      tone: latestEvent.actor_id ? "info" : "warn",
      badge: latestEvent.actor_id ? "人工切换" : "自动切换",
    })
  }

  return cards.slice(0, 3)
}

function buildSpotlight(exposures: ExposureItem[], breachedClusters: ExposureItem[]): RiskSpotlight {
  const snapshotAt = formatDateTime(latestSnapshotAt(exposures))

  if (breachedClusters.length > 0) {
    const items = [...breachedClusters]
      .sort((left, right) => right.utilization_rate - left.utilization_rate)
      .slice(0, 4)
      .map(
        (exposure) =>
          `${exposure.cluster_code}：利用率 ${(exposure.utilization_rate * 100).toFixed(1)}%，净暴露 ${exposure.net_exposure.toFixed(4)} / 上限 ${exposure.limit_value.toFixed(2)}`,
      )

    return {
      title: "当前最该解释的越限簇",
      description: `这些簇已经越过门槛，最新快照时间 ${snapshotAt}。先把它们解释清楚，再决定是否需要提 kill-switch。`,
      tone: "bad",
      items,
      emptyState: "暂无越限簇。",
    }
  }

  if (exposures.length > 0) {
    const items = [...exposures]
      .sort((left, right) => right.utilization_rate - left.utilization_rate)
      .slice(0, 4)
      .map(
        (exposure) =>
          `${exposure.cluster_code}：利用率 ${(exposure.utilization_rate * 100).toFixed(1)}%，持仓 ${exposure.position_count}，快照 ${formatDateTime(exposure.snapshot_at)}`,
      )

    return {
      title: "当前最接近门槛的簇",
      description: `虽然还没有越限，但这些簇最值得继续盯。最新暴露快照时间 ${snapshotAt}。`,
      tone: "info",
      items,
      emptyState: "暂无暴露快照。",
    }
  }

  return {
    title: "当前还没有暴露快照",
    description: "先执行一次“重算暴露”，这页才能判断当前哪些簇真正进入风险区间。",
    tone: "warn",
    items: [],
    emptyState: "执行重算后，这里会列出最需要解释的簇。",
  }
}

export function buildRiskInsights({
  riskState,
  exposures,
  thresholds,
  killSwitchRequests,
}: {
  riskState: RiskStateData | null
  exposures: ExposureItem[]
  thresholds: ThresholdItem[]
  killSwitchRequests: KillSwitchItem[]
}): RiskInsights {
  const currentState = riskState?.state ?? "Normal"
  const pendingRequests = killSwitchRequests.filter((request) => request.status === "pending")
  const breachedClusters = exposures.filter((exposure) => exposure.is_breached)

  return {
    headline: buildHeadline(currentState, pendingRequests, breachedClusters),
    priorities: buildPriorities(riskState, exposures, thresholds, pendingRequests, breachedClusters),
    spotlight: buildSpotlight(exposures, breachedClusters),
  }
}
