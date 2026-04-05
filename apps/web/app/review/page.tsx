"use client"

import { useEffect, useState } from "react"

export default function ReviewPage() {
  const [tasks, setTasks] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState("pending")

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/review/queue?queue_status=${statusFilter}`)
      .then((res) => res.json())
      .then((data) => {
        setTasks(data.tasks || [])
        setLoading(false)
      })
      .catch((err) => {
        console.error("Failed to fetch review tasks:", err)
        setLoading(false)
      })
  }, [statusFilter])

  if (loading) {
    return <div className="p-8">Loading...</div>
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">Review Queue</h1>

      <div className="mb-6 flex gap-2">
        {["pending", "in_progress", "approved", "rejected"].map((status) => (
          <button
            key={status}
            onClick={() => setStatusFilter(status)}
            className={`px-4 py-2 rounded ${
              statusFilter === status
                ? "bg-blue-600 text-white"
                : "bg-gray-200 text-gray-700 hover:bg-gray-300"
            }`}
          >
            {status.replace("_", " ").toUpperCase()}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-lg shadow">
        {tasks.length === 0 ? (
          <p className="p-6 text-gray-500">No review tasks found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full table-auto">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase w-1/3">Market</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase w-1/6">Priority</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase w-1/6">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase w-1/6">Created</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase w-1/6">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {tasks.map((task, idx) => {
                  return (
                    <tr key={task.id} className="hover:bg-gray-50 border-b">
                      <td className="px-6 py-4 text-sm text-gray-900">
                        <div className="font-medium">{task.market?.question ?? task.market_ref_id}</div>
                        <div className="text-xs text-gray-400 mt-1">{task.review_reason_code}</div>
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <span className={`px-2 py-1 rounded text-xs font-medium inline-block ${
                          task.priority === "urgent" ? "bg-red-100 text-red-800" :
                          task.priority === "high" ? "bg-orange-100 text-orange-800" :
                          "bg-gray-100 text-gray-700"
                        }`}>
                          {task.priority}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-700">{task.queue_status}</td>
                      <td className="px-6 py-4 text-sm text-gray-700">{new Date(task.created_at).toLocaleDateString()}</td>
                      <td className="px-6 py-4 text-sm">
                        <a href={`/review/${task.id}`} className="inline-block px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 font-medium transition-colors">View</a>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
