"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import type { ReviewTask } from "@/lib/review"

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export default function ReviewTaskDetailPage() {
  const params = useParams()
  const router = useRouter()
  const taskId = params.id as string

  const [task, setTask] = useState<ReviewTask | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState("")
  const [showRejectForm, setShowRejectForm] = useState(false)
  const [actorId] = useState("reviewer_1")

  useEffect(() => {
    fetch(`${API_BASE}/review/${taskId}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data) => {
        setTask(data.task)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [taskId])

  async function startReview() {
    setActionLoading(true)
    try {
      const res = await fetch(`${API_BASE}/review/${taskId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ queue_status: "in_progress", assigned_to: actorId }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setTask((prev) => prev ? { ...prev, ...data.task } : null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败")
    } finally {
      setActionLoading(false)
    }
  }

  async function approveTask() {
    setActionLoading(true)
    try {
      const res = await fetch(`${API_BASE}/review/${taskId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ actor_id: actorId, approval_notes: null }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setTask((prev) => prev ? { ...prev, ...data.task } : null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败")
    } finally {
      setActionLoading(false)
    }
  }

  async function rejectTask() {
    if (!rejectReason.trim()) {
      setError("请填写拒绝原因")
      return
    }
    setActionLoading(true)
    try {
      const res = await fetch(`${API_BASE}/review/${taskId}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          actor_id: actorId,
          rejection_reason: rejectReason,
          rejection_notes: null,
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setTask((prev) => prev ? { ...prev, ...data.task } : null)
      setShowRejectForm(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败")
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) return <div className="p-8 text-gray-700">Loading...</div>
  if (error && !task) return <div className="p-8 text-red-600">Error: {error}</div>
  if (!task) return <div className="p-8 text-gray-500">任务不存在</div>

  const isTerminal = ["approved", "rejected", "cancelled"].includes(task.queue_status)

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <button
        onClick={() => router.push("/review")}
        className="mb-6 text-blue-600 hover:text-blue-800 text-sm"
      >
        ← 返回队列
      </button>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">审核任务详情</h1>
          <div className="flex items-center gap-3 mt-2">
            <StatusBadge status={task.queue_status} />
            <span className="text-xs text-gray-500">优先级: {task.priority}</span>
          </div>
        </div>
        {/* 快捷操作按钮（顶部） */}
        {!isTerminal && task.queue_status === "pending" && (
          <button
            onClick={startReview}
            disabled={actionLoading}
            className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
          >
            {actionLoading ? "处理中..." : "开始审核"}
          </button>
        )}
        {!isTerminal && task.queue_status === "in_progress" && (
          <div className="flex gap-2">
            <button
              onClick={approveTask}
              disabled={actionLoading}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 font-medium"
            >
              批准
            </button>
            <button
              onClick={() => setShowRejectForm(!showRejectForm)}
              disabled={actionLoading}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 font-medium"
            >
              拒绝
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">关闭</button>
        </div>
      )}

      {/* 市场信息 */}
      <section className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">市场信息</h2>
        <div className="space-y-3">
          <div>
            <span className="text-xs text-gray-500 uppercase">问题</span>
            <p className="text-gray-900 font-medium mt-1">{task.market?.question ?? "—"}</p>
          </div>
          {task.market?.description && (
            <div>
              <span className="text-xs text-gray-500 uppercase">描述</span>
              <p className="text-gray-700 mt-1 text-sm">{task.market.description}</p>
            </div>
          )}
          <div className="flex gap-6">
            <div>
              <span className="text-xs text-gray-500 uppercase">市场状态</span>
              <p className="text-gray-700 mt-1 text-sm">{task.market?.market_status ?? "—"}</p>
            </div>
            <div>
              <span className="text-xs text-gray-500 uppercase">优先级</span>
              <p className="text-gray-700 mt-1 text-sm">{task.priority}</p>
            </div>
            <div>
              <span className="text-xs text-gray-500 uppercase">触发原因</span>
              <p className="text-gray-700 mt-1 text-sm">{task.review_reason_code ?? "—"}</p>
            </div>
          </div>
        </div>
      </section>

      {/* 分类结果 */}
      <section className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">分类结果</h2>
        {task.classification_result ? (
          <div className="grid grid-cols-2 gap-4">
            <InfoItem label="分类状态" value={task.classification_result.classification_status} />
            <InfoItem label="主类别" value={task.classification_result.primary_category_code ?? "—"} />
            <InfoItem
              label="置信度"
              value={
                task.classification_result.confidence != null
                  ? `${(task.classification_result.confidence * 100).toFixed(1)}%`
                  : "—"
              }
            />
            <InfoItem label="冲突数" value={String(task.classification_result.conflict_count ?? 0)} />
            <InfoItem
              label="需要审核"
              value={task.classification_result.requires_review ? "是" : "否"}
            />
          </div>
        ) : (
          <p className="text-gray-500 text-sm">无分类结果</p>
        )}
      </section>

      {/* 审核操作区 */}
      {!isTerminal && (
        <section className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">审核操作</h2>

          {task.queue_status === "pending" && (
            <div>
              <p className="text-sm text-gray-600 mb-4">点击"开始审核"将任务标记为处理中。</p>
              <button
                onClick={startReview}
                disabled={actionLoading}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {actionLoading ? "处理中..." : "开始审核"}
              </button>
            </div>
          )}

          {task.queue_status === "in_progress" && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                审核人：<span className="font-medium">{task.assigned_to ?? actorId}</span>
              </p>
              <div className="flex gap-3">
                <button
                  onClick={approveTask}
                  disabled={actionLoading || showRejectForm}
                  className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                >
                  {actionLoading && !showRejectForm ? "处理中..." : "批准"}
                </button>
                <button
                  onClick={() => setShowRejectForm(!showRejectForm)}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
                >
                  拒绝
                </button>
              </div>

              {showRejectForm && (
                <div className="mt-4 p-4 bg-red-50 rounded border border-red-200">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    拒绝原因 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="输入拒绝原因码，如 INVALID_CATEGORY"
                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm text-gray-900 focus:outline-none focus:border-red-400"
                  />
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={rejectTask}
                      disabled={actionLoading}
                      className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 text-sm"
                    >
                      {actionLoading ? "处理中..." : "确认拒绝"}
                    </button>
                    <button
                      onClick={() => { setShowRejectForm(false); setRejectReason("") }}
                      className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 text-sm"
                    >
                      取消
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {/* 终态展示 */}
      {isTerminal && (
        <section className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">审核结论</h2>
          <p className="text-gray-700 text-sm">
            状态：<StatusBadge status={task.queue_status} />
          </p>
          {task.resolved_at && (
            <p className="text-gray-500 text-xs mt-2">
              完成时间：{new Date(task.resolved_at).toLocaleString()}
            </p>
          )}
        </section>
      )}
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    in_progress: "bg-blue-100 text-blue-800",
    approved: "bg-green-100 text-green-800",
    rejected: "bg-red-100 text-red-800",
    cancelled: "bg-gray-100 text-gray-600",
  }
  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${styles[status] ?? "bg-gray-100 text-gray-700"}`}>
      {status.replace("_", " ").toUpperCase()}
    </span>
  )
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-xs text-gray-500 uppercase">{label}</span>
      <p className="text-gray-900 text-sm mt-1">{value}</p>
    </div>
  )
}
