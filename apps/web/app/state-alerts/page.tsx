"use client"

import { useEffect, useState } from "react"

import { apiGet, apiPost } from "@/lib/api"
import {
  ConsoleBadge,
  ConsoleButton,
  ConsoleCallout,
  ConsoleEmpty,
  ConsoleInset,
  ConsoleMetric,
  ConsolePanel,
} from "../components/console-ui"
import { PageIntro } from "../components/page-intro"
import { formatKillSwitchTypeLabel, formatRiskStateLabel } from "../risk/constants"

interface RiskStateEvent {
  id?: string
  to_state: string
  trigger_type: string
  trigger_metric: string
  trigger_value: number
  threshold_value?: number
  actor_id: string | null
  notes: string | null
  created_at: string
}

interface ExposureItem {
  cluster_code: string
  utilization_rate: number
  limit_value: number
  is_breached: boolean
  position_count: number
  net_exposure: number
}

interface KillSwitchItem {
  id: string
  request_type: string
  target_scope: string
  status: string
  requested_by: string
  created_at: string
}

interface MonitoringMetrics {
  review_queue: {
    pending: number
  }
  dq: {
    recent_failures: number
  }
  tag_quality: {
    open_anomalies: number
  }
}

function formatDate(value: string) {
  return new Date(value).toLocaleString("zh-CN")
}

export default function StateAlertsPage() {
  const [state, setState] = useState<string>("Normal")
  const [history, setHistory] = useState<RiskStateEvent[]>([])
  const [exposures, setExposures] = useState<ExposureItem[]>([])
  const [requests, setRequests] = useState<KillSwitchItem[]>([])
  const [metrics, setMetrics] = useState<MonitoringMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchAll = async () => {
    try {
      const [stateData, exposureData, requestData, metricData] = await Promise.all([
        apiGet<{ state: string }>("/risk/state"),
        apiGet<{ exposures: ExposureItem[] }>("/risk/exposures"),
        apiGet<{ requests: KillSwitchItem[] }>("/risk/kill-switch?status=pending"),
        apiGet<{ metrics: MonitoringMetrics }>("/monitoring/metrics"),
      ])

      const historyData = await apiGet<{ events: RiskStateEvent[] }>("/risk/state/history?limit=20")
      setState(stateData.state)
      setHistory(historyData.events)
      setExposures(exposureData.exposures)
      setRequests(requestData.requests)
      setMetrics(metricData.metrics)
      setError(null)
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "加载状态与告警失败，请稍后重试")
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    void fetchAll()
  }, [])

  const handleRefresh = async () => {
    setRefreshing(true)
    setError(null)
    try {
      await apiPost("/risk/exposures/compute")
      await fetchAll()
    } catch (refreshError) {
      setRefreshing(false)
      setError(refreshError instanceof Error ? refreshError.message : "刷新告警失败，请稍后重试")
    }
  }

  if (loading) {
    return <main className="mx-auto max-w-6xl px-4 py-5 text-[#8b949e] md:px-6">正在加载状态与告警...</main>
  }

  const breached = exposures.filter((item) => item.is_breached)
  const stateLabel = formatRiskStateLabel(state)
  const headline =
    state === "RiskOff" || state === "Frozen"
      ? `系统当前处于${stateLabel}，这不是“看一眼就走”的状态，优先检查人工处置和 kill-switch。`
      : requests.length > 0
        ? `当前有 ${requests.length} 个待处理 kill-switch，请先明确人工动作，再决定是否恢复自动链路。`
        : breached.length > 0
          ? `当前有 ${breached.length} 个簇越限，优先回到风险页核对暴露与阈值。`
          : "当前没有越限簇，也没有待处理 kill-switch；若指标为 0，通常只是这个时间窗没有新事件。"

  return (
    <main className="mx-auto max-w-6xl px-4 py-5 md:px-6">
      <PageIntro
        eyebrow="State & Alerts"
        title="状态与告警"
        description="这页是风控主链路的快速告警入口。先看当前全局状态和 breached clusters，再看 pending kill-switch、DQ 失败和状态迁移时间线。"
        stats={[
          { label: "当前状态", value: stateLabel },
          { label: "越限簇", value: String(breached.length) },
        ]}
        guides={[
          {
            title: "先看什么",
            description: "先看当前状态和越限数量，再看 pending kill-switch 和最近状态变化。",
          },
          {
            title: "什么时候算异常",
            description: "状态持续停在 RiskOff / Frozen、越限数量抬升、或 kill-switch 长时间挂起时，都值得优先处理。",
          },
          {
            title: "下一步去哪",
            description: "需要深入看暴露和阈值时去 risk；需要判断能不能上线时继续去 launch-review。",
          },
        ]}
      />

      <ConsoleCallout
        title="这页是告警入口，不是噪声墙。"
        description={headline}
        tone={state === "RiskOff" || state === "Frozen" ? "bad" : requests.length > 0 || breached.length > 0 ? "warn" : "info"}
        actions={
          <ConsoleButton type="button" onClick={() => void handleRefresh()} disabled={refreshing} tone="primary">
            {refreshing ? "重算中..." : "重算暴露"}
          </ConsoleButton>
        }
      />

      {error ? (
        <div className="mt-6 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <ConsoleMetric label="当前状态" value={stateLabel} tone={state === "Normal" ? "good" : state === "Caution" ? "warn" : "bad"} />
        <ConsoleMetric label="越限簇" value={String(breached.length)} hint="0 只表示当前没有越限，并不代表没有暴露数据。" />
        <ConsoleMetric label="待处理 Kill-Switch" value={String(requests.length)} hint="0 表示当前没人等待人工审批。" />
        <ConsoleMetric label="24h DQ 失败" value={String(metrics?.dq.recent_failures ?? 0)} tone={(metrics?.dq.recent_failures ?? 0) > 0 ? "bad" : "good"} />
      </section>

      <section className="mt-6 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <ConsolePanel
          title="暴露告警"
          description="这里帮助你快速判断哪些簇已经越限，以及越限程度是否值得立刻介入。"
          actions={<ConsoleBadge label={`${exposures.length} 个簇`} tone="neutral" />}
        >
          <div className="space-y-3">
            {exposures.length === 0 ? (
              <ConsoleEmpty
                title="当前还没有暴露快照"
                description="先执行一次重算，再回来判断哪些簇进入了告警状态。"
              />
            ) : (
              exposures.map((item) => (
                <ConsoleInset key={item.cluster_code}>
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-[#e6edf3]">{item.cluster_code}</p>
                      <p className="mt-1 text-sm text-[#8b949e]">
                        持仓 {item.position_count} · 净暴露 {item.net_exposure.toFixed(2)} / 限额 {item.limit_value.toFixed(2)}
                      </p>
                    </div>
                    <ConsoleBadge
                      label={`${(item.utilization_rate * 100).toFixed(1)}%`}
                      tone={item.is_breached ? "bad" : "good"}
                    />
                  </div>
                </ConsoleInset>
              ))
            )}
          </div>
        </ConsolePanel>

        <ConsolePanel
          title="活动告警"
          description="把最容易影响主链路的待处理事项集中显示出来。"
        >
          <div className="space-y-3">
            <ConsoleInset>
              <p className="console-kicker">待审队列</p>
              <p className="mt-2 text-2xl font-semibold text-[#e6edf3]">{metrics?.review_queue.pending ?? 0}</p>
            </ConsoleInset>
            <ConsoleInset>
              <p className="console-kicker">未解决标签异常</p>
              <p className="mt-2 text-2xl font-semibold text-[#e6edf3]">{metrics?.tag_quality.open_anomalies ?? 0}</p>
            </ConsoleInset>
            <ConsoleInset>
              <p className="console-kicker">待处理 Kill-Switch 请求</p>
              <div className="mt-3 space-y-2">
                {requests.length === 0 ? (
                  <p className="text-sm text-[#8b949e]">当前没有待处理 kill-switch 请求。</p>
                ) : (
                  requests.map((request) => (
                    <ConsoleInset key={request.id}>
                      <p className="font-medium text-[#e6edf3]">
                        {formatKillSwitchTypeLabel(request.request_type)} · {request.target_scope}
                      </p>
                      <p className="mt-1 text-sm text-[#8b949e]">
                        申请人 {request.requested_by} / {formatDate(request.created_at)}
                      </p>
                    </ConsoleInset>
                  ))
                )}
              </div>
            </ConsoleInset>
          </div>
        </ConsolePanel>
      </section>

      <ConsolePanel
        className="mt-8"
        title="状态迁移时间线"
        description="按时间顺序解释系统为什么进入当前状态，用于追溯触发指标和阈值。"
        actions={<ConsoleBadge label={`${history.length} 条`} tone="neutral" />}
      >
        <div className="space-y-3">
          {history.length === 0 ? (
            <ConsoleEmpty
              title="当前还没有状态迁移记录"
              description="一旦风险状态发生切换，这里会沉淀对应的时间线事件。"
            />
          ) : (
            history.map((event) => (
              <ConsoleInset key={event.id ?? `${event.created_at}-${event.to_state}`}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-medium text-[#e6edf3]">{formatRiskStateLabel(event.to_state)}</p>
                    <p className="mt-1 text-sm text-[#8b949e]">
                      {event.trigger_type} · {event.trigger_metric} · {formatDate(event.created_at)}
                    </p>
                  </div>
                  <div className="text-right text-sm text-[#c9d1d9]">
                    <p>触发值 {event.trigger_value.toFixed(3)}</p>
                    {"threshold_value" in event && event.threshold_value !== undefined ? (
                      <p className="text-[#8b949e]">阈值 {event.threshold_value.toFixed(3)}</p>
                    ) : null}
                  </div>
                </div>
                {event.notes ? <p className="mt-3 text-sm text-[#c9d1d9]">{event.notes}</p> : null}
              </ConsoleInset>
            ))
          )}
        </div>
      </ConsolePanel>
    </main>
  )
}
