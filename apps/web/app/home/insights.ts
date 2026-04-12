import type { DashboardSnapshot, DashboardSummary } from "./types"
import { buildHeadline, buildMetrics, buildStageCards } from "./summary-core"
import { buildNarratives, buildNextActions, buildWorkflows } from "./summary-readouts"

export function deriveDashboardSummary(snapshot: DashboardSnapshot): DashboardSummary {
  return {
    headline: buildHeadline(snapshot),
    metrics: buildMetrics(snapshot),
    narratives: buildNarratives(snapshot),
    nextActions: buildNextActions(snapshot),
    workflows: buildWorkflows(snapshot),
    stages: buildStageCards(snapshot),
  }
}
