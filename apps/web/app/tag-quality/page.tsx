"use client"

import { useEffect, useState } from "react"

interface TagQualityMetric {
  metric_date: string
  rule_version: string
  total_classifications: number
  success_rate: number
  avg_confidence: number
  conflict_count: number
  category_distribution: Record<string, number>
  anomalies_summary: Record<string, number>
}

export default function TagQualityPage() {
  const [metrics, setMetrics] = useState<TagQualityMetric[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/tag-quality/metrics`)
      .then((res) => res.json())
      .then((data) => {
        setMetrics(data.metrics || [])
        setLoading(false)
      })
      .catch((err) => {
        console.error("Failed to fetch metrics:", err)
        setError(err.message || "Failed to fetch metrics")
        setLoading(false)
      })
  }, [])

  if (loading) return <div className="p-8 text-gray-500">加载中...</div>

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          <p className="font-semibold">错误</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      </div>
    )
  }

  const totalAnomalies = metrics.reduce((sum, m) => {
    return sum + Object.values(m.anomalies_summary || {}).reduce((a, b) => a + b, 0)
  }, 0)

  const latestMetric = metrics[0]

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">Tag Quality Metrics</h1>

      {metrics.length === 0 ? (
        <p className="text-gray-500">暂无质量指标数据。</p>
      ) : (
        <>
          {/* 摘要卡片 */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-medium text-gray-500 mb-2">最新成功率</h3>
              <p className="text-3xl font-bold text-green-600">
                {((latestMetric.success_rate || 0) * 100).toFixed(1)}%
              </p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-medium text-gray-500 mb-2">平均置信度</h3>
              <p className="text-3xl font-bold text-indigo-600">
                {((latestMetric.avg_confidence || 0) * 100).toFixed(1)}%
              </p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-medium text-gray-500 mb-2">最新分类总量</h3>
              <p className="text-3xl font-bold text-blue-600">
                {latestMetric.total_classifications}
              </p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-medium text-gray-500 mb-2">异常总数</h3>
              <p className={`text-3xl font-bold ${totalAnomalies > 0 ? "text-red-600" : "text-gray-900"}`}>
                {totalAnomalies}
              </p>
            </div>
          </div>

          {/* 指标明细表 */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4 border-b pb-2">最近 7 天指标</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">日期</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">规则版本</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">分类总量</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">成功率</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">置信度</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">冲突数</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">异常</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {metrics.map((m, idx) => {
                    const anomalyCount = Object.values(m.anomalies_summary || {}).reduce((a, b) => a + b, 0)
                    return (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm text-gray-900">
                          {new Date(m.metric_date).toLocaleDateString("zh-CN")}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">{m.rule_version}</td>
                        <td className="px-4 py-3 text-sm text-right">{m.total_classifications}</td>
                        <td className="px-4 py-3 text-sm text-right">
                          <span className={`font-medium ${m.success_rate >= 0.9 ? "text-green-600" : m.success_rate >= 0.8 ? "text-amber-600" : "text-red-600"}`}>
                            {(m.success_rate * 100).toFixed(1)}%
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-right text-gray-700">
                          {(m.avg_confidence * 100).toFixed(1)}%
                        </td>
                        <td className="px-4 py-3 text-sm text-right text-gray-700">{m.conflict_count}</td>
                        <td className="px-4 py-3 text-sm">
                          {anomalyCount > 0 ? (
                            <span className="px-2 py-1 rounded bg-red-100 text-red-700 text-xs">
                              {Object.entries(m.anomalies_summary).map(([k, v]) => `${k}: ${v}`).join(", ")}
                            </span>
                          ) : (
                            <span className="text-gray-400">—</span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
