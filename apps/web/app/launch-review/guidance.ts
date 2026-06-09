import { formatChecklistLabel } from "./constants"
import type { LaunchReview, ShadowRun } from "./types"

export interface LaunchReviewGuidance {
  tone: "good" | "warn" | "bad" | "info"
  conclusion: string
  reason: string
  nextActionLabel: string
}

function failedChecklistItems(review: LaunchReview) {
  return review.checklist.filter((item) => !item.passed)
}

export function buildSuggestedShadowRunName(date = new Date()) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  const hour = String(date.getHours()).padStart(2, "0")
  const minute = String(date.getMinutes()).padStart(2, "0")
  return `shadow-${year}${month}${day}-${hour}${minute}`
}

export function buildSuggestedLaunchReviewTitle(
  stageName: string,
  latestShadow: ShadowRun | null,
) {
  const normalizedStage = stageName.trim() || "M6"
  if (!latestShadow) {
    return `${normalizedStage} 上线评审`
  }
  return `${normalizedStage} 上线评审 / ${latestShadow.run_name}`
}

export function buildLaunchReviewGuidance(review: LaunchReview): LaunchReviewGuidance {
  const failedItems = failedChecklistItems(review)

  if (review.status === "go") {
    return {
      tone: "good",
      conclusion: "这条评审已经明确允许推进",
      reason: "Go 已记录完成；除非出现新的 shadow、回测或阶段评审证据，否则不需要重复创建新评审。",
      nextActionLabel: "查看结果",
    }
  }

  if (review.status === "nogo") {
    return {
      tone: "bad",
      conclusion: "这条评审已经明确暂不上线",
      reason: "NoGo 已经是正式结论。下一步应先补能推翻它的新证据，而不是继续反复点 Go。",
      nextActionLabel: "补新证据",
    }
  }

  if (failedItems.length > 0) {
    const preview = failedItems
      .slice(0, 3)
      .map((item) => formatChecklistLabel(item))
      .join("、")
    return {
      tone: "bad",
      conclusion: "当前还不能提交 Go",
      reason: `这条评审仍有 ${failedItems.length} 项门槛未过，主要卡在 ${preview}。先补证据，不要把“Go 点不动”误判成页面问题。`,
      nextActionLabel: "补齐证据",
    }
  }

  return {
    tone: "good",
    conclusion: "当前证据已齐，可以记录最终决定",
    reason: "checklist 已通过。现在更重要的是把责任人、Go/NoGo 结论和说明写清楚，而不是继续堆更多 pending 评审。",
    nextActionLabel: "记录决定",
  }
}
