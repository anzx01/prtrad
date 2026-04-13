"use client"

import { useEffect, useMemo, useState } from "react"

import { apiGet } from "@/lib/api"

import {
  ConsoleCallout,
  ConsoleInset,
  ConsoleMetric,
  ConsolePanel,
} from "../components/console-ui"
import { PageIntro } from "../components/page-intro"

interface MonitoringMetrics {
  review_queue?: {
    pending?: number
    in_progress?: number
    approved_today?: number
    rejected_today?: number
  }
  tag_quality?: {
    latest_total?: number
    latest_success_rate?: number
    latest_avg_confidence?: number
    open_anomalies?: number
  }
  dq?: {
    recent_failures?: number
  }
}

interface MonitoringResponse {
  metrics?: MonitoringMetrics | { metrics?: MonitoringMetrics }
}

function hasNestedMetrics(
  payload: MonitoringResponse["metrics"],
): payload is { metrics?: MonitoringMetrics } {
  return Boolean(payload && typeof payload === "object" && "metrics" in payload)
}

function resolveMetrics(payload: MonitoringResponse["metrics"]): MonitoringMetrics {
  if (!payload) {
    return {}
  }
  if (hasNestedMetrics(payload)) {
    return payload.metrics ?? {}
  }
  return payload
}

export default function MonitoringPage() {
  const [metrics, setMetrics] = useState<MonitoringMetrics>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)

    apiGet<MonitoringResponse>("/monitoring/metrics")
      .then((data) => {
        setMetrics(resolveMetrics(data.metrics))
        setLoading(false)
      })
      .catch((fetchError) => {
        setError(fetchError instanceof Error ? fetchError.message : "加载监控指标失败")
        setLoading(false)
      })
  }, [])

  const reviewQueue = metrics.review_queue ?? {}
  const tagQuality = metrics.tag_quality ?? {}
  const dq = metrics.dq ?? {}

  const overview = useMemo(() => {
    const anomalies = tagQuality.open_anomalies ?? 0
    const recentFailures = dq.recent_failures ?? 0
    const pending = reviewQueue.pending ?? 0

    if (recentFailures > 0 || anomalies > 0) {
      return {
        tone: "warn" as const,
        title: "当前系统需要关注",
        description: "DQ 失败或标签异常并不一定会立刻阻断，但它们是最容易让下游页面掉数的前置信号。",
      }
    }
    if (pending > 0) {
      return {
        tone: "info" as const,
        title: "系统基本健康，但有待处理任务",
        description: "当前没有明显质量异常，不过审核队列里还有待人工处理的任务。",
      }
    }
    return {
      tone: "good" as const,
      title: "系统整体健康",
      description: "目前看不到明显的 DQ 失败、标签异常或审核堆积。",
    }
  }, [dq.recent_failures, reviewQueue.pending, tagQuality.open_anomalies])

  return (
    <main className="mx-auto max-w-7xl px-4 py-5 md:px-6">
      <PageIntro
        eyebrow="Monitoring"
        title="系统监控"
        description="这页不是纯技术监控面板，而是一个“现在有没有卡住主链路”的总入口。优先看待审任务、标签异常和最近 24 小时 DQ 失败。"
        guides={[
          {
            title: "先看什么",
            description: "先看总判断，再看审核队列、标签质量和 DQ 三个块。",
          },
          {
            title: "什么时候需要人工介入",
            description: "当 open anomalies、recent failures 或 pending reviews 明显升高时，就该顺着对应页面往下查。",
          },
          {
            title: "下一步去哪",
            description: "审核异常去 review，DQ 异常去 dq，标签异常去 tag-quality。",
          },
        ]}
      />

      {loading ? <div className="py-20 text-center text-[#8b949e]">正在加载监控指标...</div> : null}
      {error ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-5 text-sm text-rose-100">
          加载失败：{error}
        </div>
      ) : null}

      {!loading && !error ? (
        <>
          <ConsoleCallout
            title={overview.title}
            description={overview.description}
            tone={overview.tone}
          />

          <section className="mb-6 mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <ConsoleMetric label="待审任务" value={String(reviewQueue.pending ?? 0)} tone={(reviewQueue.pending ?? 0) > 0 ? "warn" : "good"} />
            <ConsoleMetric label="处理中任务" value={String(reviewQueue.in_progress ?? 0)} />
            <ConsoleMetric label="标签成功率" value={`${((tagQuality.latest_success_rate ?? 0) * 100).toFixed(1)}%`} tone={(tagQuality.latest_success_rate ?? 0) >= 0.95 ? "good" : "warn"} />
            <ConsoleMetric label="DQ 最近失败" value={String(dq.recent_failures ?? 0)} tone={(dq.recent_failures ?? 0) > 0 ? "bad" : "good"} />
          </section>

          <section className="grid gap-6 lg:grid-cols-3">
            <ConsolePanel title="审核队列" description="决定人工审核是否正在堆积。">
              <div className="space-y-3 text-sm text-[#c9d1d9]">
                <ConsoleInset className="flex items-center justify-between"><span>待处理</span><span>{reviewQueue.pending ?? 0}</span></ConsoleInset>
                <ConsoleInset className="flex items-center justify-between"><span>处理中</span><span>{reviewQueue.in_progress ?? 0}</span></ConsoleInset>
                <ConsoleInset className="flex items-center justify-between"><span>今日通过</span><span>{reviewQueue.approved_today ?? 0}</span></ConsoleInset>
                <ConsoleInset className="flex items-center justify-between"><span>今日拒绝</span><span>{reviewQueue.rejected_today ?? 0}</span></ConsoleInset>
              </div>
            </ConsolePanel>

            <ConsolePanel title="标签质量" description="标签质量异常很容易向下游传播。">
              <div className="space-y-3 text-sm text-[#c9d1d9]">
                <ConsoleInset className="flex items-center justify-between"><span>最近分类总量</span><span>{tagQuality.latest_total ?? 0}</span></ConsoleInset>
                <ConsoleInset className="flex items-center justify-between"><span>最近成功率</span><span>{((tagQuality.latest_success_rate ?? 0) * 100).toFixed(1)}%</span></ConsoleInset>
                <ConsoleInset className="flex items-center justify-between"><span>平均置信度</span><span>{(tagQuality.latest_avg_confidence ?? 0).toFixed(3)}</span></ConsoleInset>
                <ConsoleInset className="flex items-center justify-between"><span>未解决异常</span><span>{tagQuality.open_anomalies ?? 0}</span></ConsoleInset>
              </div>
            </ConsolePanel>

            <ConsolePanel title="DQ 与排障建议" description="把 DQ 失败看成上游供数健康度信号。">
              <div className="space-y-3 text-sm leading-6 text-[#c9d1d9]">
                <ConsoleInset>最近 24 小时 DQ 失败：{dq.recent_failures ?? 0}</ConsoleInset>
                <ConsoleInset>若这里升高，优先去 `dq` 页面看 freshness、blocking reasons 和 snapshot capture 诊断。</ConsoleInset>
                <ConsoleInset>若标签异常升高，则继续去 `tag-quality` 或 `review` 查人工任务是否同步堆积。</ConsoleInset>
              </div>
            </ConsolePanel>
          </section>
        </>
      ) : null}
    </main>
  )
}
