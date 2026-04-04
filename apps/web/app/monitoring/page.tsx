"use client"

import { useEffect, useState } from "react"

export default function MonitoringPage() {
  const [metrics, setMetrics] = useState<any>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/monitoring/metrics`)
      .then((res) => res.json())
      .then((data) => {
        setMetrics(data.metrics || {})
        setLoading(false)
      })
      .catch((err) => {
        console.error("Failed to fetch metrics:", err)
        setLoading(false)
      })
  }, [])

  if (loading) {
    return <div className="p-8">Loading...</div>
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">Monitoring Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">System Status</h3>
          <p className="text-3xl font-bold text-green-600">Healthy</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Active Tasks</h3>
          <p className="text-3xl font-bold">0</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Success Rate</h3>
          <p className="text-3xl font-bold text-green-600">100%</p>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Recent Activity</h2>
        <p className="text-gray-500">No recent activity to display.</p>
      </div>
    </div>
  )
}
