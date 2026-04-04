"use client"

import { useEffect, useState } from "react"

export default function ReportsPage() {
  const [reports, setReports] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/reports`)
      .then((res) => res.json())
      .then((data) => {
        setReports(data.reports || [])
        setLoading(false)
      })
      .catch((err) => {
        console.error("Failed to fetch reports:", err)
        setLoading(false)
      })
  }, [])

  if (loading) {
    return <div className="p-8">Loading...</div>
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">M2 Reports</h1>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Available Reports</h2>
        {reports.length === 0 ? (
          <p className="text-gray-500">No reports generated yet.</p>
        ) : (
          <p className="text-gray-500">Reports will be displayed here.</p>
        )}
      </div>
    </div>
  )
}
