"use client"

import { useEffect, useState } from "react"
import { apiGet } from "@/lib/api"

export default function MonitoringPage() {
  const [metrics, setMetrics] = useState<any>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)

    apiGet("/monitoring/metrics")
      .then((data: any) => {
        // API returns { metrics: { status, metrics: { ... } } }
        setMetrics(data.metrics?.metrics || data.metrics || {})
        setLoading(false)
      })
      .catch((err: any) => {
        console.error("Failed to fetch metrics:", err)
        setError(err.message || "Failed to fetch metrics")
        setLoading(false)
      })
  }, [])

  if (loading) {
    return <div className="p-8 text-gray-500">加载中...</div>
  }

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

  const reviewQueue = metrics.review_queue || {}
  const tagQuality = metrics.tag_quality || {}
  const dq = metrics.dq || {}

  const isHealthy = (tagQuality.open_anomalies || 0) === 0 && (dq.recent_failures || 0) === 0

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">Monitoring Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">System Status</h3>
          <p className={`text-3xl font-bold ${isHealthy ? "text-green-600" : "text-amber-600"}`}>
            {isHealthy ? "Healthy" : "Warning"}
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Pending Reviews</h3>
          <p className="text-3xl font-bold text-blue-600">
            {reviewQueue.pending || 0}
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Tag Success Rate</h3>
          <p className="text-3xl font-bold text-indigo-600">
            {((tagQuality.latest_success_rate || 0) * 100).toFixed(1)}%
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Open Anomalies</h3>
          <p className={`text-3xl font-bold ${(tagQuality.open_anomalies || 0) > 0 ? "text-red-600" : "text-gray-900"}`}>
            {tagQuality.open_anomalies || 0}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4 border-b pb-2">Review Queue Today</h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Approved Today</span>
              <span className="font-bold text-green-600">{reviewQueue.approved_today || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Rejected Today</span>
              <span className="font-bold text-red-600">{reviewQueue.rejected_today || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Current In Progress</span>
              <span className="font-bold text-blue-600">{reviewQueue.in_progress || 0}</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4 border-b pb-2">Data Quality (24h)</h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Recent Failures</span>
              <span className={`font-bold ${(dq.recent_failures || 0) > 0 ? "text-red-600" : "text-green-600"}`}>
                {dq.recent_failures || 0}
              </span>
            </div>
            <div className="mt-4 p-4 bg-gray-50 rounded text-sm text-gray-500 italic">
              Data quality issues are tracked in real-time via audit logs.
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
