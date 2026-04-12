"use client"

import { useEffect, useState } from "react"

import { ConsoleMetric } from "../components/console-ui"
import { PageIntro } from "../components/page-intro"
import { ActionPanels } from "./action-panels"
import { fetchDashboardSnapshot, runDashboardAction } from "./automation"
import {
  HeadlineSection,
  ResourceErrorsCallout,
  StorySection,
  WorkflowSection,
} from "./dashboard-sections"
import { deriveDashboardSummary } from "./insights"
import type { ActionId, DashboardSnapshot, DashboardTone } from "./types"

interface ActionFeedItem {
  id: string
  tone: DashboardTone
  message: string
}

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

export function SmartConsolePage() {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot>(emptySnapshot())
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [runningActionId, setRunningActionId] = useState<ActionId | null>(null)
  const [lastUpdatedAt, setLastUpdatedAt] = useState<string | null>(null)
  const [actionFeed, setActionFeed] = useState<ActionFeedItem[]>([])

  const summary = deriveDashboardSummary(snapshot)

  const appendFeed = (tone: DashboardTone, message: string) => {
    setActionFeed((current) => [
      { id: `${Date.now()}-${current.length}`, tone, message },
      ...current,
    ].slice(0, 14))
  }

  const loadSnapshot = async (background = false) => {
    if (background) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }

    const next = await fetchDashboardSnapshot()
    setSnapshot(next)
    setLastUpdatedAt(new Date().toISOString())
    setLoading(false)
    setRefreshing(false)
  }

  useEffect(() => {
    void loadSnapshot(false)
  }, [])

  const handleAction = async (actionId: ActionId) => {
    setRunningActionId(actionId)
    appendFeed("info", `已接管动作：${actionId}`)

    try {
      await runDashboardAction(actionId, appendFeed)
      appendFeed("good", "自动化动作执行完毕，正在刷新最新看板。")
      await loadSnapshot(true)
    } catch (error) {
      appendFeed("bad", error instanceof Error ? error.message : "自动化动作执行失败")
    } finally {
      setRunningActionId(null)
    }
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-5 md:px-6">
      <PageIntro
        eyebrow="Smart Console"
        title="让系统先告诉你现在卡在哪里"
        description="这里不再要求你先把整条主链路背熟，再自己去拼页面、猜 0 值、猜流程。首页会自动归纳现状、指出阻塞点，并把能自动做的动作直接串起来。"
        stats={[
          {
            label: "最近刷新",
            value: lastUpdatedAt ? new Date(lastUpdatedAt).toLocaleString("zh-CN") : "-",
          },
          { label: "自动判断", value: "已开启" },
        ]}
        guides={[
          {
            title: "结论优先",
            description: "先看系统判断，再决定要不要钻进细页，不需要先记住 M4/M5/M6 的全部细节。",
          },
          {
            title: "能自动就自动",
            description: "重算风险、重算校准、跑回测、跑 shadow、生成报告都可以直接在这里一键推进。",
          },
          {
            title: "人工环节会被点名",
            description: "像审核队列这种必须人工接住的地方，系统会直接告诉你它才是当前主要学习成本。",
          },
        ]}
      />

      <HeadlineSection
        summary={summary}
        refreshing={refreshing}
        runningActionId={runningActionId}
        onRefresh={() => void loadSnapshot(true)}
        onAction={(actionId) => void handleAction(actionId)}
      />

      <ResourceErrorsCallout
        snapshot={snapshot}
        refreshing={refreshing}
        runningActionId={runningActionId}
        onRefresh={() => void loadSnapshot(true)}
      />

      <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {summary.metrics.map((metric) => (
          <ConsoleMetric
            key={metric.label}
            label={metric.label}
            value={metric.value}
            hint={metric.hint}
            tone={metric.tone}
          />
        ))}
      </section>

      {loading ? <div className="py-20 text-center text-sm text-[#8b949e]">正在汇总首页判断...</div> : null}

      {!loading ? (
        <>
          <StorySection
            summary={summary}
            refreshing={refreshing}
            runningActionId={runningActionId}
            onAction={(actionId) => void handleAction(actionId)}
          />
          <WorkflowSection
            summary={summary}
            refreshing={refreshing}
            runningActionId={runningActionId}
            onAction={(actionId) => void handleAction(actionId)}
          />
          <ActionPanels
            actionFeed={actionFeed}
            refreshing={refreshing}
            runningActionId={runningActionId}
            onAction={(actionId) => void handleAction(actionId)}
          />
        </>
      ) : null}
    </main>
  )
}
