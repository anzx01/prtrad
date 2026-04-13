"use client"

import { useEffect, useMemo, useState } from "react"

import { apiGet } from "@/lib/api"

import { PageIntro, SoftPanel } from "../components/page-intro"

interface TagQualityMetric {
  metric_date: string
  rule_version: string
  total_classifications: number
  success_rate: number
  avg_confidence: number
  conflict_count: number
  anomalies_summary: Record<string, number>
}

interface TagQualityResponse {
  metrics: TagQualityMetric[]
}

export default function TagQualityPage() {
  const [metrics, setMetrics] = useState<TagQualityMetric[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiGet<TagQualityResponse>("/tag-quality/metrics")
      .then((data) => {
        setMetrics(data.metrics ?? [])
        setLoading(false)
      })
      .catch((fetchError) => {
        setError(fetchError instanceof Error ? fetchError.message : "加载标签质量指标失败")
        setLoading(false)
      })
  }, [])

  const totalAnomalies = useMemo(
    () => metrics.reduce((sum, metric) => sum + Object.values(metric.anomalies_summary || {}).reduce((a, b) => a + b, 0), 0),
    [metrics],
  )

  const latestMetric = metrics[0]

  return (
    <main className="mx-auto max-w-7xl px-4 py-5 md:px-6">
      <PageIntro
        eyebrow="Tag Quality"
        title="标签质量"
        description="这页不是看单条任务，而是看分类系统整体是否稳定。优先看成功率、平均置信度、冲突数和异常汇总，再决定是否需要人工回查分类规则。"
        stats={[
          { label: "最近规则版本", value: latestMetric?.rule_version ?? "-" },
          { label: "累计异常", value: String(totalAnomalies) },
        ]}
        guides={[
          {
            title: "先看什么",
            description: "先看最新成功率和置信度，再看最近几天是否出现持续冲突或异常抬升。",
          },
          {
            title: "什么时候算异常",
            description: "如果成功率明显下降、冲突持续升高或异常集中出现，就值得回查 tagging 规则或名单口径。",
          },
          {
            title: "下一步去哪",
            description: "如果异常落到人工审核任务上，继续去 review；如果怀疑规则本身变化，去 tagging 看版本。",
          },
        ]}
      />

      {loading ? <div className="py-20 text-center text-slate-400">正在加载标签质量指标...</div> : null}
      {error ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-5 text-sm text-rose-100">
          加载失败：{error}
        </div>
      ) : null}

      {!loading && !error ? (
        <>
          {metrics.length === 0 ? (
            <SoftPanel title="当前无数据" description="如果你预期这里有数据，优先确认 tag-quality 指标任务是否已运行。">
              <p className="text-sm text-slate-400">当前还没有标签质量指标。</p>
            </SoftPanel>
          ) : (
            <>
              <section className="mb-6 grid gap-4 md:grid-cols-4">
                <SoftPanel title="最新成功率">
                  <p className="text-3xl font-semibold text-white">{((latestMetric?.success_rate ?? 0) * 100).toFixed(1)}%</p>
                </SoftPanel>
                <SoftPanel title="平均置信度">
                  <p className="text-3xl font-semibold text-white">{((latestMetric?.avg_confidence ?? 0) * 100).toFixed(1)}%</p>
                </SoftPanel>
                <SoftPanel title="最新分类总量">
                  <p className="text-3xl font-semibold text-white">{latestMetric?.total_classifications ?? 0}</p>
                </SoftPanel>
                <SoftPanel title="异常总数">
                  <p className="text-3xl font-semibold text-white">{totalAnomalies}</p>
                </SoftPanel>
              </section>

              <SoftPanel title="最近 7 天趋势" description="重点看成功率是否持续走低、冲突和异常是否集中抬升。">
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[860px] text-sm">
                    <thead>
                      <tr className="border-b border-white/10 text-left text-slate-400">
                        <th className="px-4 py-3 font-medium">日期</th>
                        <th className="px-4 py-3 font-medium">规则版本</th>
                        <th className="px-4 py-3 font-medium text-right">分类总量</th>
                        <th className="px-4 py-3 font-medium text-right">成功率</th>
                        <th className="px-4 py-3 font-medium text-right">置信度</th>
                        <th className="px-4 py-3 font-medium text-right">冲突数</th>
                        <th className="px-4 py-3 font-medium">异常摘要</th>
                      </tr>
                    </thead>
                    <tbody>
                      {metrics.map((metric, index) => {
                        const anomalyCount = Object.values(metric.anomalies_summary || {}).reduce((a, b) => a + b, 0)
                        return (
                          <tr key={`${metric.metric_date}-${index}`} className="border-b border-white/5 transition hover:bg-white/[0.03]">
                            <td className="px-4 py-3 text-slate-300">{new Date(metric.metric_date).toLocaleDateString("zh-CN")}</td>
                            <td className="px-4 py-3 font-mono text-xs text-sky-300">{metric.rule_version}</td>
                            <td className="px-4 py-3 text-right text-slate-300">{metric.total_classifications}</td>
                            <td className="px-4 py-3 text-right">
                              <span className={`${metric.success_rate >= 0.9 ? "text-emerald-300" : metric.success_rate >= 0.8 ? "text-amber-300" : "text-rose-300"}`}>
                                {(metric.success_rate * 100).toFixed(1)}%
                              </span>
                            </td>
                            <td className="px-4 py-3 text-right text-slate-300">{(metric.avg_confidence * 100).toFixed(1)}%</td>
                            <td className="px-4 py-3 text-right text-slate-300">{metric.conflict_count}</td>
                            <td className="px-4 py-3 text-slate-400">
                              {anomalyCount > 0
                                ? Object.entries(metric.anomalies_summary).map(([key, value]) => `${key}: ${value}`).join("，")
                                : "-"}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </SoftPanel>
            </>
          )}
        </>
      ) : null}
    </main>
  )
}
