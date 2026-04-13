"use client"

import { FormEvent, useEffect, useState } from "react"

import { apiGet, apiPost } from "@/lib/api"
import {
  ConsoleBadge,
  ConsoleButton,
  ConsoleCallout,
  ConsoleEmpty,
  ConsoleField,
  ConsoleInput,
  ConsoleInset,
  ConsoleMetric,
  ConsolePanel,
} from "../components/console-ui"
import { PageIntro } from "../components/page-intro"

interface BacktestRun {
  id: string
  run_name: string
  recommendation: "go" | "watch" | "nogo"
  status: string
  window_start: string
  window_end: string
  strategy_version: string | null
  executed_by: string | null
  summary: {
    totals?: {
      candidate_count?: number
      admitted_count?: number
      rejected_count?: number
      resolved_ratio?: number
      avg_admit_net_ev?: number
    }
    cluster_breakdown?: Record<string, number>
    stress_tests?: Record<string, { positive_count: number; avg_net_ev: number }>
  }
  completed_at: string
}

function formatDate(value: string) {
  return new Date(value).toLocaleString("zh-CN")
}

function formatRecommendationLabel(value: BacktestRun["recommendation"]) {
  return value === "go" ? "Go，可继续" : value === "watch" ? "观察" : "NoGo，暂不放行"
}

function recommendationTone(value: BacktestRun["recommendation"]) {
  return value === "go" ? "good" : value === "watch" ? "warn" : "bad"
}

function getRecommendationHint(value: BacktestRun["recommendation"]) {
  if (value === "go") {
    return "这次回测没有给出明显阻断信号，但上线前仍要结合风险和阶段评审一起看。"
  }
  if (value === "watch") {
    return "这次回测建议先观察，优先去看压力测试和风险暴露是否解释得通。"
  }
  return "这次回测已经给出阻断信号，先回到风险、报告和上线评审链路补证据。"
}

export default function BacktestsPage() {
  const [runs, setRuns] = useState<BacktestRun[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState({
    run_name: "",
    window_days: "30",
    executed_by: "",
    strategy_version: "baseline-v1",
  })

  const fetchRuns = async () => {
    try {
      const data = await apiGet<{ runs: BacktestRun[] }>("/backtests")
      setRuns(data.runs)
      setError(null)
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "加载回测记录失败，请稍后重试")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void fetchRuns()
  }, [])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await apiPost("/backtests/run", {
        run_name: form.run_name,
        window_days: Number.parseInt(form.window_days, 10),
        executed_by: form.executed_by || null,
        strategy_version: form.strategy_version || null,
      })
      setForm((current) => ({ ...current, run_name: "", executed_by: "" }))
      await fetchRuns()
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "创建回测任务失败，请稍后重试")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-5 md:px-6">
      <PageIntro
        eyebrow="Backtests"
        title="回测实验室"
        description="这页回答的是“如果按当前准入和风控逻辑回放一遍，结果会怎样”。先看 recommendation，再看候选数、准入数、聚类分布和 stress test。"
        stats={[
          { label: "最近回测数", value: String(runs.length) },
          { label: "最近建议", value: runs[0] ? formatRecommendationLabel(runs[0].recommendation) : "-" },
        ]}
        guides={[
          {
            title: "先看什么",
            description: "先看回测 recommendation，再看 admitted / rejected、resolved ratio 和 avg admit NetEV。",
          },
          {
            title: "什么时候算异常",
            description: "如果你明明已经运行过回测，但这里没有记录，优先检查 backtest run 是否真正落库。",
          },
          {
            title: "下一步去哪",
            description: "如果回测给出 watch / nogo，继续去 risk、reports 或 launch-review 看阻断证据。",
          },
        ]}
      />

      {error ? (
        <div className="mb-6 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      <ConsoleCallout
        title="回测不是终点，而是上线证据的一部分。"
        description="真正重要的不是跑了多少次，而是最近一次回测给出的建议能不能和风险状态、阶段评审一起讲通。"
        tone="info"
      />

      <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <ConsoleMetric label="回测归档" value={String(runs.length)} />
        <ConsoleMetric
          label="最近建议"
          value={runs[0] ? formatRecommendationLabel(runs[0].recommendation) : "-"}
          tone={runs[0] ? recommendationTone(runs[0].recommendation) : "neutral"}
        />
        <ConsoleMetric
          label="最近候选数"
          value={String(runs[0]?.summary.totals?.candidate_count ?? 0)}
          hint="最新一次回测里进入评估的候选数量。"
        />
        <ConsoleMetric
          label="最近准入数"
          value={String(runs[0]?.summary.totals?.admitted_count ?? 0)}
          hint="最新一次回测里最终通过的候选数量。"
        />
      </section>

      <ConsolePanel
        className="mt-6 bg-[#0d1117]"
        title="执行回测"
        description="把窗口、策略版本和执行人固定下来，方便后续和阶段评审做证据关联。"
      >
        <form className="grid gap-4 md:grid-cols-2" onSubmit={handleSubmit}>
          <ConsoleField label="回测名称">
            <ConsoleInput
              value={form.run_name}
              onChange={(event) => setForm((current) => ({ ...current, run_name: event.target.value }))}
              placeholder="backtest-20260410"
            />
          </ConsoleField>
          <ConsoleField label="回看天数">
            <ConsoleInput
              type="number"
              min={1}
              max={365}
              value={form.window_days}
              onChange={(event) => setForm((current) => ({ ...current, window_days: event.target.value }))}
            />
          </ConsoleField>
          <ConsoleField label="执行人">
            <ConsoleInput
              value={form.executed_by}
              onChange={(event) => setForm((current) => ({ ...current, executed_by: event.target.value }))}
              placeholder="researcher_a"
            />
          </ConsoleField>
          <ConsoleField label="策略版本">
            <ConsoleInput
              value={form.strategy_version}
              onChange={(event) => setForm((current) => ({ ...current, strategy_version: event.target.value }))}
            />
          </ConsoleField>
          <div className="md:col-span-2">
            <ConsoleButton type="submit" disabled={submitting} tone="primary">
              {submitting ? "运行中..." : "运行回测"}
            </ConsoleButton>
          </div>
        </form>
      </ConsolePanel>

      <ConsolePanel
        className="mt-8"
        title="最近回测"
        description="优先看结论、关键指标和两块解释材料：聚类分布与压力测试。"
        actions={<ConsoleBadge label={`${runs.length} 次`} tone="neutral" />}
      >
        {loading ? <p className="text-sm text-[#8b949e]">正在加载回测记录...</p> : null}
        {!loading && runs.length === 0 ? (
          <ConsoleEmpty
            title="当前还没有回测记录"
            description="运行一条回测后，这里会开始积累真正可用于 Go/NoGo 决策的证据。"
          />
        ) : null}

        <div className="space-y-4">
          {runs.map((run) => (
            <ConsoleInset key={run.id}>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h3 className="text-xl font-medium text-[#e6edf3]">{run.run_name}</h3>
                  <p className="mt-2 text-sm text-[#8b949e]">
                    {formatDate(run.window_start)} 到 {formatDate(run.window_end)}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <ConsoleBadge label={run.status} tone="neutral" />
                  <ConsoleBadge label={run.recommendation === "go" ? "Go" : run.recommendation === "watch" ? "观察" : "NoGo"} tone={recommendationTone(run.recommendation)} />
                </div>
              </div>

              <div className="mt-4 rounded-xl border border-[#30363d] bg-[#161b22] p-4 text-sm text-[#c9d1d9]">
                <p className="font-medium text-[#e6edf3]">当前结论：{formatRecommendationLabel(run.recommendation)}</p>
                <p className="mt-2 leading-6 text-[#8b949e]">{getRecommendationHint(run.recommendation)}</p>
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-5">
                <ConsoleMetric label="候选数" value={String(run.summary.totals?.candidate_count ?? 0)} />
                <ConsoleMetric label="准入数" value={String(run.summary.totals?.admitted_count ?? 0)} />
                <ConsoleMetric label="拒绝数" value={String(run.summary.totals?.rejected_count ?? 0)} />
                <ConsoleMetric label="已结算占比" value={`${(((run.summary.totals?.resolved_ratio ?? 0) as number) * 100).toFixed(1)}%`} />
                <ConsoleMetric label="准入平均 NetEV" value={(run.summary.totals?.avg_admit_net_ev ?? 0).toFixed(4)} />
              </div>

              <div className="mt-5 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
                <div>
                  <p className="console-kicker">聚类分布</p>
                  <div className="mt-3 space-y-2">
                    {Object.entries(run.summary.cluster_breakdown ?? {}).length === 0 ? (
                      <ConsoleEmpty
                        title="没有聚类分布数据"
                        description="当前回测没有输出聚类分布，阅读时先看上面的结论和核心指标。"
                      />
                    ) : (
                      Object.entries(run.summary.cluster_breakdown ?? {}).map(([cluster, count]) => (
                        <ConsoleInset key={cluster} className="flex items-center justify-between">
                          <span className="text-sm text-[#c9d1d9]">{cluster}</span>
                          <span className="text-sm font-medium text-[#e6edf3]">{count}</span>
                        </ConsoleInset>
                      ))
                    )}
                  </div>
                </div>
                <div>
                  <p className="console-kicker">压力测试</p>
                  <div className="mt-3 space-y-2">
                    {Object.entries(run.summary.stress_tests ?? {}).length === 0 ? (
                      <ConsoleEmpty
                        title="没有压力测试结果"
                        description="当前回测没有输出压力测试明细，可把这次结果理解为基础重放。"
                      />
                    ) : (
                      Object.entries(run.summary.stress_tests ?? {}).map(([scenario, result]) => (
                        <ConsoleInset key={scenario}>
                          <div className="flex items-center justify-between gap-3">
                            <span className="text-sm text-[#c9d1d9]">{scenario}</span>
                            <span className="text-sm font-medium text-[#e6edf3]">{result.positive_count} 个正收益样本</span>
                          </div>
                          <p className="mt-2 text-sm text-[#8b949e]">平均 NetEV {result.avg_net_ev.toFixed(4)}</p>
                        </ConsoleInset>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </ConsoleInset>
          ))}
        </div>
      </ConsolePanel>
    </main>
  )
}
