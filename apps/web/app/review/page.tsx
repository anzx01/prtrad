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
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Market</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {tasks.map((task) => (
                  <tr key={task.id}>
                    <td className="px-6 py-4 text-sm">{task.market_ref_id}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={`px-2 py-1 rounded ${
                        task.priority === "urgent" ? "bg-red-100 text-red-800" :
                        task.priority === "high" ? "bg-orange-100 text-orange-800" :
                        "bg-gray-100 text-gray-800"
                      }`}>
                        {task.priority}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{task.queue_status}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{new Date(task.created_at).toLocaleDateString()}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <a href={`/review/${task.id}`} className="text-blue-600 hover:text-blue-800">View</a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
