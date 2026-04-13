import { formatChecklistLabel, formatChecklistLabels, formatRecommendationLabel } from "./constants"
import type { LaunchReview, ShadowRun } from "./types"

type InsightTone = "info" | "good" | "warn" | "bad"

export type LaunchJumpTarget = "shadow-form" | "review-form" | "shadow-runs" | "reviews"

export interface LaunchHeadlineAction {
  label: string
  target: LaunchJumpTarget
}

export interface LaunchHeadline {
  title: string
  description: string
  tone: InsightTone
  actions: LaunchHeadlineAction[]
}

export interface LaunchPriority {
  id: string
  title: string
  description: string
  tone: InsightTone
  cta: string
  target: LaunchJumpTarget
  badges?: string[]
}

export interface LaunchBlockerSummary {
  title: string
  description: string
  tone: InsightTone
  blockers: string[]
}

export interface LaunchInsights {
  headline: LaunchHeadline
  priorities: LaunchPriority[]
  blockerSummary: LaunchBlockerSummary
}

function pendingReview(reviews: LaunchReview[]) {
  return reviews.find((review) => review.status === "pending") ?? null
}

function failedChecklistItems(review: LaunchReview | null) {
  return review?.checklist.filter((item) => !item.passed) ?? []
}

function latestBreachedClusters(run: ShadowRun | null) {
  return run?.summary.exposure_summary?.breached_clusters ?? []
}

function buildHeadline(shadowRuns: ShadowRun[], reviews: LaunchReview[]): LaunchHeadline {
  const latestShadow = shadowRuns[0] ?? null
  const latestReview = reviews[0] ?? null
  const activePendingReview = pendingReview(reviews)
  const failedItems = failedChecklistItems(activePendingReview)

  if (!latestShadow) {
    return {
      title: "还不能讨论 Go/NoGo，先跑一次 shadow",
      description: "没有影子运行证据时，创建评审只会得到一条信息不足的记录。先让系统跑完影子检查，再谈是否进入正式评审。",
      tone: "bad",
      actions: [{ label: "去执行影子运行", target: "shadow-form" }],
    }
  }

  if (activePendingReview && failedItems.length > 0) {
    const labels = formatChecklistLabels(failedItems).slice(0, 3).join("、")
    return {
      title: "当前不能提交 Go，证据门槛还没过",
      description: `最近待决策评审《${activePendingReview.title}》仍有 ${failedItems.length} 项未通过，主要卡在 ${labels}。这时该做的是补证据，不是反复点 Go。`,
      tone: "bad",
      actions: [
        { label: "去看待决策评审", target: "reviews" },
        { label: "回看最新 shadow", target: "shadow-runs" },
      ],
    }
  }

  if (activePendingReview) {
    return {
      title: "当前证据已齐，可以进入最终决策",
      description: `待决策评审《${activePendingReview.title}》的 checklist 已通过。接下来要做的不是再补数据，而是明确记录这次 Go / NoGo 的责任人与说明。`,
      tone: "good",
      actions: [{ label: "去记录决策", target: "reviews" }],
    }
  }

  if (latestReview?.status === "go") {
    return {
      title: "最近一次上线评审已经给出 Go",
      description: `最近评审《${latestReview.title}》已放行。后续如果要推翻这个结论，应先给出新的 shadow、backtest 或阶段评审证据。`,
      tone: "good",
      actions: [{ label: "回看评审记录", target: "reviews" }],
    }
  }

  if (latestReview?.status === "nogo") {
    return {
      title: "最近一次上线评审明确给出了 NoGo",
      description: `最近评审《${latestReview.title}》没有放行。下一步不是新建更多 pending 记录，而是先补齐能推翻 NoGo 的新证据。`,
      tone: "bad",
      actions: [
        { label: "回看 NoGo 原因", target: "reviews" },
        { label: "查看影子运行", target: "shadow-runs" },
      ],
    }
  }

  if (latestShadow.recommendation === "block") {
    return {
      title: "最新 shadow 已给出阻断，不建议直接进入 Go",
      description: "影子运行本身已经说明当前链路存在阻断项。应先解释阻断来源，再把这个结论固化为一条正式评审记录。",
      tone: "bad",
      actions: [
        { label: "查看 shadow 细节", target: "shadow-runs" },
        { label: "创建评审记录", target: "review-form" },
      ],
    }
  }

  if (latestShadow.recommendation === "watch") {
    return {
      title: "最新 shadow 仍是观察态，推进前先解释清楚风险",
      description: "这类状态不是不能建评审，而是建了之后很可能会卡在待决策。最好先把观察项解释清楚，再决定是否进入 Go/NoGo。",
      tone: "warn",
      actions: [
        { label: "回看 shadow 观察项", target: "shadow-runs" },
        { label: "创建评审记录", target: "review-form" },
      ],
    }
  }

  return {
    title: "影子运行已完成，可固化为正式上线评审",
    description: `最新 shadow 建议为 ${formatRecommendationLabel(latestShadow.recommendation)}。下一步是把阶段、申请人和关联 shadow 固化成一条可追溯的 Go/NoGo 记录。`,
    tone: "info",
    actions: [{ label: "创建评审记录", target: "review-form" }],
  }
}

function buildPriorities(shadowRuns: ShadowRun[], reviews: LaunchReview[]): LaunchPriority[] {
  const latestShadow = shadowRuns[0] ?? null
  const activePendingReview = pendingReview(reviews)
  const failedItems = failedChecklistItems(activePendingReview)
  const cards: LaunchPriority[] = []

  if (!latestShadow) {
    cards.push({
      id: "run-shadow",
      title: "先执行影子运行，补第一层证据",
      description: "shadow 会把风险状态、越限簇、DQ 告警和 kill-switch 队列整理成一条明确建议，后面的上线评审都应该建立在它之上。",
      tone: "bad",
      cta: "执行影子运行",
      target: "shadow-form",
    })
    return cards
  }

  const breachedClusters = latestBreachedClusters(latestShadow)
  if (breachedClusters.length > 0) {
    cards.push({
      id: "shadow-breaches",
      title: "先解释最新 shadow 里的越限簇",
      description: `最新 shadow 里还有 ${breachedClusters.length} 个越限簇。它们不解释清楚，即使建了 review，也大概率会停在 pending 或直接 NoGo。`,
      tone: "bad",
      cta: "查看影子运行",
      target: "shadow-runs",
      badges: breachedClusters.slice(0, 3),
    })
  }

  if (!reviews.length) {
    cards.push({
      id: "create-review",
      title: "把当前证据固化为一条正式评审记录",
      description: "如果这里只有 shadow 没有 review，系统还没真正形成 Go/NoGo 决策链。把阶段、申请人和 shadow 绑定起来，才能开始追踪结论。",
      tone: "info",
      cta: "创建评审",
      target: "review-form",
    })
  }

  if (activePendingReview && failedItems.length > 0) {
    cards.push({
      id: "fill-checklist",
      title: "优先补齐 pending review 的 checklist 缺口",
      description: `当前待决策评审《${activePendingReview.title}》仍有 ${failedItems.length} 项失败。不要把“Go 按钮点不动”误判成页面问题。`,
      tone: "bad",
      cta: "查看待决策评审",
      target: "reviews",
      badges: failedItems.slice(0, 3).map((item) => formatChecklistLabel(item)),
    })
  } else if (activePendingReview) {
    cards.push({
      id: "make-decision",
      title: "当前待决策评审已具备决策条件",
      description: `《${activePendingReview.title}》的 checklist 已通过。现在最重要的是记录 Go / NoGo 与评审说明，而不是再新建更多 review。`,
      tone: "good",
      cta: "记录决策",
      target: "reviews",
    })
  }

  if (reviews[0]?.status === "nogo") {
    cards.push({
      id: "recover-from-nogo",
      title: "若要推翻 NoGo，先补新证据而不是重复创建评审",
      description: "NoGo 不是按钮状态，而是上一轮证据链给出的正式结论。需要新的 shadow、backtest 或阶段评审来改变它。",
      tone: "warn",
      cta: "回看评审记录",
      target: "reviews",
    })
  }

  if (cards.length === 0) {
    cards.push({
      id: "review-ready",
      title: "当前可继续沉淀正式评审记录",
      description: "最新 shadow 没有明确阻断项，且当前没有待决策积压。最合适的动作是创建或复核正式上线评审。",
      tone: "good",
      cta: "创建评审",
      target: "review-form",
    })
  }

  return cards.slice(0, 3)
}

function buildBlockerSummary(shadowRuns: ShadowRun[], reviews: LaunchReview[]) {
  const latestShadow = shadowRuns[0] ?? null
  const activePendingReview = pendingReview(reviews)
  const failedItems = failedChecklistItems(activePendingReview)

  if (!latestShadow) {
    return {
      title: "当前 Go 阻塞项",
      description: "不是门槛没过，而是第一层证据还没产生。",
      tone: "bad" as const,
      blockers: ["还没有 shadow 运行记录"],
    }
  }

  if (activePendingReview && failedItems.length > 0) {
    return {
      title: "当前 Go 阻塞项",
      description: "这些是最近待决策评审里仍然未通过的门槛。",
      tone: "bad" as const,
      blockers: failedItems.map((item) => formatChecklistLabel(item)),
    }
  }

  if (!reviews.length) {
    return {
      title: "当前主要缺口",
      description: "影子运行已经有了，但正式 Go/NoGo 记录还没建立。",
      tone: "warn" as const,
      blockers: ["还没有正式 launch review 记录"],
    }
  }

  if (reviews[0]?.status === "nogo") {
    return {
      title: "当前主要缺口",
      description: "上一轮结论已经明确是 NoGo，除非有新证据，否则不应继续向上线推进。",
      tone: "bad" as const,
      blockers: ["最近一次评审结论是 NoGo"],
    }
  }

  if (latestShadow.recommendation === "watch") {
    return {
      title: "当前主要关注项",
      description: "虽然没有明确阻断，但最新 shadow 仍处在观察态。",
      tone: "warn" as const,
      blockers: ["最新 shadow 建议仍为观察"],
    }
  }

  return {
    title: "当前没有明显 Go 阻塞项",
    description: "至少从最新 shadow 与 review 状态看，系统没有直接拦住上线的证据缺口。",
    tone: "good" as const,
    blockers: [],
  }
}

export function buildLaunchInsights(shadowRuns: ShadowRun[], reviews: LaunchReview[]): LaunchInsights {
  return {
    headline: buildHeadline(shadowRuns, reviews),
    priorities: buildPriorities(shadowRuns, reviews),
    blockerSummary: buildBlockerSummary(shadowRuns, reviews),
  }
}
