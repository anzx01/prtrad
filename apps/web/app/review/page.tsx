"use client"

import { useEffect, useState } from "react"
import { apiGet } from "@/lib/api"
import type { ReviewQueueResponse, ReviewQueueStatus, ReviewTaskSummary } from "@/lib/review"

const REVIEW_PAGE_SIZE = 20
const STATUS_OPTIONS: ReviewQueueStatus[] = [
  "pending",
  "in_progress",
  "approved",
  "rejected",
  "cancelled",
]

function formatStatusLabel(status: ReviewQueueStatus): string {
  return status.replace("_", " ").toUpperCase()
}

function formatCreatedAt(createdAt: string): string {
  return new Date(createdAt).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  })
}

export default function ReviewPage() {
  const [tasks, setTasks] = useState<ReviewTaskSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<ReviewQueueStatus>("pending")
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    let isCancelled = false

    setLoading(true)
    setError(null)

    apiGet<ReviewQueueResponse>(
      `/review/queue?queue_status=${statusFilter}&page=${page}&page_size=${REVIEW_PAGE_SIZE}`,
    )
      .then((data) => {
        if (isCancelled) {
          return
        }

        setTasks(data.tasks || [])
        setTotal(data.total || 0)
        setLoading(false)
      })
      .catch((err: { message?: string }) => {
        if (isCancelled) {
          return
        }

        console.error("Failed to fetch review tasks:", err)
        setError(err.message || "Failed to fetch review tasks")
        setTasks([])
        setTotal(0)
        setLoading(false)
      })

    return () => {
      isCancelled = true
    }
  }, [page, statusFilter])

  const totalPages = Math.max(1, Math.ceil(total / REVIEW_PAGE_SIZE))
  const rangeStart = total === 0 ? 0 : (page - 1) * REVIEW_PAGE_SIZE + 1
  const rangeEnd = total === 0 ? 0 : rangeStart + tasks.length - 1

  function handleStatusFilterChange(status: ReviewQueueStatus) {
    setStatusFilter(status)
    setPage(1)
  }

  if (loading) {
    return <div className="p-8 text-gray-500">加载中...</div>
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          <p className="font-semibold">错误</p>
          <p className="mt-1 text-sm">{error}</p>
          <p className="mt-2 text-xs text-red-600">请确保 API 服务器运行在 http://localhost:8000</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8">
      <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-3xl font-bold">Review Queue</h1>
          <p className="mt-2 text-sm text-gray-500">
            {total === 0
              ? "当前筛选下暂无审核任务"
              : `当前筛选共 ${total} 条，正在显示 ${rangeStart}-${rangeEnd} 条`}
          </p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm text-gray-600 shadow-sm">
          第 {page} / {totalPages} 页
        </div>
      </div>

      <div className="mb-6 flex flex-wrap gap-2">
        {STATUS_OPTIONS.map((status) => (
          <button
            key={status}
            onClick={() => handleStatusFilterChange(status)}
            className={`rounded px-4 py-2 ${
              statusFilter === status
                ? "bg-blue-600 text-white"
                : "bg-gray-200 text-gray-700 hover:bg-gray-300"
            }`}
          >
            {formatStatusLabel(status)}
          </button>
        ))}
      </div>

      <div className="rounded-lg bg-white shadow">
        {tasks.length === 0 ? (
          <p className="p-6 text-gray-500">当前筛选下暂无审核任务。</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full table-auto">
              <thead className="sticky top-0 bg-gray-50">
                <tr>
                  <th className="w-1/3 px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Market</th>
                  <th className="w-1/6 px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Priority</th>
                  <th className="w-1/6 px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Status</th>
                  <th className="w-1/6 px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Created</th>
                  <th className="w-1/6 px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {tasks.map((task) => {
                  return (
                    <tr key={task.id} className="border-b hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm text-gray-900">
                        <div className="font-medium">{task.market?.question ?? task.market_ref_id}</div>
                        <div className="mt-1 text-xs text-gray-400">{task.review_reason_code}</div>
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <span
                          className={`inline-block rounded px-2 py-1 text-xs font-medium ${
                            task.priority === "urgent"
                              ? "bg-red-100 text-red-800"
                              : task.priority === "high"
                                ? "bg-orange-100 text-orange-800"
                                : "bg-gray-100 text-gray-700"
                          }`}
                        >
                          {task.priority}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-700">{formatStatusLabel(task.queue_status)}</td>
                      <td className="px-6 py-4 text-sm text-gray-700">{formatCreatedAt(task.created_at)}</td>
                      <td className="px-6 py-4 text-sm">
                        <a
                          href={`/review/${task.id}`}
                          className="inline-block rounded bg-blue-600 px-3 py-1 font-medium text-white transition-colors hover:bg-blue-700"
                        >
                          View
                        </a>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="mt-6 flex items-center justify-between">
        <button
          onClick={() => setPage((currentPage) => Math.max(1, currentPage - 1))}
          disabled={page <= 1}
          className="rounded border border-gray-300 px-4 py-2 text-sm text-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          上一页
        </button>
        <span className="text-sm text-gray-500">共 {totalPages} 页</span>
        <button
          onClick={() => setPage((currentPage) => Math.min(totalPages, currentPage + 1))}
          disabled={page >= totalPages}
          className="rounded border border-gray-300 px-4 py-2 text-sm text-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          下一页
        </button>
      </div>
    </div>
  )
}
