"use client"

import { useEffect, useState } from "react"

export default function TagQualityPage() {
  const [metrics, setMetrics] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/tag-quality/metrics`)
      .then((res) => res.json())
      .then((data) => {
        setMetrics(data.metrics || [])
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
      <h1 className="text-3xl font-bold mb-6">Tag Quality Metrics</h1>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Quality Overview</h2>
        {metrics.length === 0 ? (
          <p className="text-gray-500">No quality metrics available yet.</p>
        ) : (
          <p className="text-gray-500">Quality metrics will be displayed here.</p>
        )}
      </div>
    </div>
  )
}
