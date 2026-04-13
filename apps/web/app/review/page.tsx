"use client"

import Link from "next/link"
import { useEffect, useMemo, useState } from "react"

import { apiGet, apiPost } from "@/lib/api"
import type {
  ReviewBulkAction,
  ReviewBulkActionResponse,
  ReviewQueueResponse,
  ReviewQueueStatus,
  ReviewTaskSummary,
} from "@/lib/review"

import {
  ConsoleBadge,
  ConsoleButton,
  ConsoleEmpty,
  ConsoleField,
  ConsoleInput,
  ConsoleMetric,
  ConsolePanel,
} from "../components/console-ui"
import { PageIntro } from "../components/page-intro"

const REVIEW_PAGE_SIZE = 20
const BULK_SELECT_PAGE_SIZE = 100
const STATUS_OPTIONS: ReviewQueueStatus[] = ["pending", "in_progress", "approved", "rejected", "cancelled"]
const ACTIONABLE_STATUSES: ReviewQueueStatus[] = ["pending", "in_progress"]

const STATUS_LABELS: Record<ReviewQueueStatus, string> = {
  pending: "待处理",
  in_progress: "处理中",
  approved: "已通过",
  rejected: "已拒绝",
  cancelled: "已取消",
}

function formatCreatedAt(createdAt: string) {
  return new Date(createdAt).toLocaleString("zh-CN", { hour12: false })
}

function statusTone(status: ReviewQueueStatus) {
  return status === "approved"
    ? "good"
    : status === "pending" || status === "in_progress"
      ? "warn"
      : status === "rejected"
        ? "bad"
        : "neutral"
}

function priorityTone(priority: string) {
  return priority === "urgent" ? "bad" : priority === "high" ? "warn" : priority === "normal" ? "info" : "neutral"
}

function isActionableStatus(status: ReviewQueueStatus) {
  return ACTIONABLE_STATUSES.includes(status)
}

function buildQueueUrl(statusFilter: ReviewQueueStatus, page: number, pageSize: number) {
  return `/review/queue?queue_status=${statusFilter}&page=${page}&page_size=${pageSize}`
}

function bulkActionLabel(action: ReviewBulkAction, count: number) {
  if (action === "start_review") {
    return `已开始审核 ${count} 条任务。`
  }
  if (action === "approve") {
    return `已通过 ${count} 条任务。`
  }
  return `已拒绝 ${count} 条任务。`
}

export default function ReviewPage() {
  const [tasks, setTasks] = useState<ReviewTaskSummary[]>([])
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<ReviewQueueStatus>("pending")
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [refreshKey, setRefreshKey] = useState(0)
  const [reviewerId, setReviewerId] = useState("reviewer_1")
  const [rejectReason, setRejectReason] = useState("")
  const [reviewNotes, setReviewNotes] = useState("")
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    apiGet<ReviewQueueResponse>(buildQueueUrl(statusFilter, page, REVIEW_PAGE_SIZE))
      .then((data) => {
        if (cancelled) {
          return
        }
        setTasks(data.tasks || [])
        setTotal(data.total || 0)
        setLoading(false)
      })
      .catch((fetchError) => {
        if (cancelled) {
          return
        }
        setError(fetchError instanceof Error ? fetchError.message : "加载审核队列失败")
        setTasks([])
        setTotal(0)
        setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [page, refreshKey, statusFilter])

  const totalPages = Math.max(1, Math.ceil(total / REVIEW_PAGE_SIZE))
  const rangeStart = total === 0 ? 0 : (page - 1) * REVIEW_PAGE_SIZE + 1
  const rangeEnd = total === 0 ? 0 : rangeStart + tasks.length - 1
  const allowsQueueActions = isActionableStatus(statusFilter)
  const selectedCount = selectedIds.length
  const selectedVisibleCount = tasks.filter((task) => selectedIds.includes(task.id)).length

  const summary = useMemo(() => {
    const urgentCount = tasks.filter((task) => task.priority === "urgent").length
    const highCount = tasks.filter((task) => task.priority === "high").length
    const actionableCount = tasks.filter((task) => isActionableStatus(task.queue_status)).length
    return { urgentCount, highCount, actionableCount }
  }, [tasks])

  const allVisibleSelected = tasks.length > 0 && selectedVisibleCount === tasks.length
  const allFilteredSelected = total > 0 && selectedCount === total
  const canBulkStart = allowsQueueActions && statusFilter === "pending" && selectedCount > 0
  const canBulkDecide = allowsQueueActions && selectedCount > 0

  async function selectAllFilteredTasks() {
    if (!allowsQueueActions || total === 0) {
      return
    }

    setActionLoading("select_all_filtered")
    setError(null)
    setActionMessage(null)

    try {
      const pageCount = Math.ceil(total / BULK_SELECT_PAGE_SIZE)
      const requests = Array.from({ length: pageCount }, (_, index) =>
        apiGet<ReviewQueueResponse>(buildQueueUrl(statusFilter, index + 1, BULK_SELECT_PAGE_SIZE)),
      )
      const pages = await Promise.all(requests)
      const ids = pages.flatMap((response) => response.tasks.map((task) => task.id))
      setSelectedIds(Array.from(new Set(ids)))
      setActionMessage(`已全选当前筛选下的 ${ids.length} 条任务。`)
    } catch (selectError) {
      setError(selectError instanceof Error ? selectError.message : "全选当前筛选失败")
    } finally {
      setActionLoading(null)
    }
  }

  async function runReviewAction(taskIds: string[], action: ReviewBulkAction) {
    if (taskIds.length === 0) {
      setError("请先选择至少一条审核任务。")
      return
    }
    if (!reviewerId.trim()) {
      setError("请先填写审核人。")
      return
    }
    if (action === "reject" && !rejectReason.trim()) {
      setError("批量拒绝前请先填写拒绝原因。")
      return
    }

    setActionLoading(`${action}:${taskIds.length}`)
    setError(null)
    setActionMessage(null)

    try {
      const response = await apiPost<ReviewBulkActionResponse>("/review/bulk-action", {
        task_ids: taskIds,
        action,
        actor_id: reviewerId.trim(),
        rejection_reason: action === "reject" ? rejectReason.trim() : null,
        notes: reviewNotes.trim() || null,
      })
      setActionMessage(bulkActionLabel(action, response.updated_count))
      setSelectedIds((current) => current.filter((id) => !taskIds.includes(id)))
      setRefreshKey((current) => current + 1)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "审核操作失败")
    } finally {
      setActionLoading(null)
    }
  }

  function toggleTask(taskId: string) {
    setSelectedIds((current) =>
      current.includes(taskId) ? current.filter((id) => id !== taskId) : [...current, taskId],
    )
  }

  function toggleAllVisible() {
    if (allVisibleSelected) {
      const visibleIds = new Set(tasks.map((task) => task.id))
      setSelectedIds((current) => current.filter((id) => !visibleIds.has(id)))
      return
    }
    setSelectedIds((current) => Array.from(new Set([...current, ...tasks.map((task) => task.id)])))
  }

  function resetSelection() {
    setSelectedIds([])
    setActionMessage(null)
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-5 md:px-6">
      <PageIntro
        eyebrow="Review Queue"
        title="人工审核队列"
        description="这页支持单条审核，也支持先全选再一键处理。全选默认先作用于当前页，你也可以直接全选当前筛选下的全部任务。"
        stats={[
          { label: "当前筛选总数", value: String(total) },
          { label: "当前已选", value: String(selectedCount) },
        ]}
        guides={[
          {
            title: "单条审核",
            description: "可以在列表里直接开始、通过、拒绝，也可以进入详情页看完整证据后再决定。",
          },
          {
            title: "全选审核",
            description: "先点“全选当前页”或“全选当前筛选”，再点一键通过或一键拒绝。",
          },
          {
            title: "拒绝注意",
            description: "一键拒绝前必须先填写拒绝原因，避免后续无法追溯为什么退回。",
          },
        ]}
      />

      <section className="mb-6 grid gap-4 md:grid-cols-4">
        <ConsoleMetric
          label="当前筛选结果"
          value={String(total)}
          hint={total === 0 ? "当前筛选下没有任务。" : `当前显示 ${rangeStart}-${rangeEnd} / ${total} 条。`}
        />
        <ConsoleMetric
          label="当前已选"
          value={String(selectedCount)}
          hint={allFilteredSelected ? "已覆盖当前筛选的全部任务。" : "可先全选，再一键处理。"}
          tone={selectedCount > 0 ? "info" : "neutral"}
        />
        <ConsoleMetric
          label="本页高优任务"
          value={String(summary.urgentCount + summary.highCount)}
          hint="优先处理 urgent / high。"
          tone={summary.urgentCount + summary.highCount > 0 ? "warn" : "good"}
        />
        <ConsoleMetric
          label="本页可操作"
          value={String(summary.actionableCount)}
          hint={allowsQueueActions ? "当前筛选支持直接审核。" : "当前筛选主要用于查看结果。"}
          tone={summary.actionableCount > 0 ? "info" : "neutral"}
        />
      </section>

      <ConsolePanel title="状态筛选" description="先按状态切分，再决定是单条处理，还是全选后统一审核。">
        <div className="flex flex-wrap gap-2">
          {STATUS_OPTIONS.map((status) => (
            <ConsoleButton
              key={status}
              type="button"
              onClick={() => {
                setStatusFilter(status)
                setPage(1)
                resetSelection()
              }}
              tone={statusFilter === status ? "primary" : "default"}
              size="sm"
            >
              {STATUS_LABELS[status]}
            </ConsoleButton>
          ))}
        </div>
      </ConsolePanel>

      <ConsolePanel
        className="mt-6"
        title="批量审核"
        description={
          allowsQueueActions
            ? "这里就是全选后的一键审核区。批量通过或拒绝时，系统会自动先接手 pending 任务，再完成审核。"
            : "当前筛选是已处理结果，不能再批量审核，只能查看历史结果。"
        }
      >
        <div className="grid gap-4 xl:grid-cols-[220px_220px_minmax(0,1fr)]">
          <ConsoleField label="审核人">
            <ConsoleInput
              value={reviewerId}
              onChange={(event) => setReviewerId(event.target.value)}
              placeholder="例如 reviewer_1"
            />
          </ConsoleField>
          <ConsoleField label="拒绝原因">
            <ConsoleInput
              value={rejectReason}
              onChange={(event) => setRejectReason(event.target.value)}
              placeholder="例如 INVALID_CATEGORY"
              disabled={!allowsQueueActions}
            />
          </ConsoleField>
          <ConsoleField label="备注">
            <ConsoleInput
              value={reviewNotes}
              onChange={(event) => setReviewNotes(event.target.value)}
              placeholder="可选：记录本次批量处理依据"
              disabled={!allowsQueueActions}
            />
          </ConsoleField>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <ConsoleBadge label={`已选 ${selectedCount} 条`} tone={selectedCount > 0 ? "info" : "neutral"} />
          <ConsoleButton
            type="button"
            size="sm"
            onClick={toggleAllVisible}
            disabled={!allowsQueueActions || tasks.length === 0 || actionLoading !== null}
          >
            {allVisibleSelected ? "取消全选当前页" : "全选当前页"}
          </ConsoleButton>
          <ConsoleButton
            type="button"
            size="sm"
            onClick={() => void selectAllFilteredTasks()}
            disabled={!allowsQueueActions || total === 0 || actionLoading !== null}
          >
            {allFilteredSelected ? `已全选当前筛选 ${total} 条` : `全选当前筛选 ${total} 条`}
          </ConsoleButton>
          <ConsoleButton
            type="button"
            size="sm"
            onClick={resetSelection}
            disabled={selectedCount === 0 || actionLoading !== null}
          >
            清空选择
          </ConsoleButton>
          <ConsoleButton
            type="button"
            size="sm"
            onClick={() => void runReviewAction(selectedIds, "start_review")}
            disabled={!canBulkStart || actionLoading !== null}
          >
            一键开始审核已选
          </ConsoleButton>
          <ConsoleButton
            type="button"
            size="sm"
            tone="success"
            onClick={() => void runReviewAction(selectedIds, "approve")}
            disabled={!canBulkDecide || actionLoading !== null}
          >
            一键通过已选
          </ConsoleButton>
          <ConsoleButton
            type="button"
            size="sm"
            tone="danger"
            onClick={() => void runReviewAction(selectedIds, "reject")}
            disabled={!canBulkDecide || !rejectReason.trim() || actionLoading !== null}
          >
            一键拒绝已选
          </ConsoleButton>
        </div>
      </ConsolePanel>

      <section className="mt-6">
        {loading ? <div className="py-20 text-center text-[#8b949e]">正在加载审核任务...</div> : null}
        {error ? (
          <div className="mb-4 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-5 text-sm text-rose-100">
            操作失败：{error}
          </div>
        ) : null}
        {actionMessage ? (
          <div className="mb-4 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-5 text-sm text-emerald-100">
            {actionMessage}
          </div>
        ) : null}

        {!loading ? (
          <ConsolePanel title="任务列表" description="表头也支持全选当前页；右侧支持直接单条审核。">
            {tasks.length === 0 ? (
              <ConsoleEmpty
                title="当前筛选下没有审核任务"
                description="如果你本来预期这里应该有数据，先确认最近的 tagging 自动分类是否真的在跑。"
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="console-table min-w-[1220px]">
                  <thead>
                    <tr>
                      {allowsQueueActions ? (
                        <th className="w-24">
                          <button
                            type="button"
                            onClick={toggleAllVisible}
                            className="text-xs text-[#8b949e] transition hover:text-[#e6edf3]"
                          >
                            {allVisibleSelected ? "取消全选" : "全选"}
                          </button>
                        </th>
                      ) : null}
                      <th>市场</th>
                      <th>触发原因</th>
                      <th>优先级</th>
                      <th>状态</th>
                      <th>创建时间</th>
                      <th>快捷审核</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tasks.map((task) => {
                      const rowLoading = actionLoading !== null
                      return (
                        <tr key={task.id}>
                          {allowsQueueActions ? (
                            <td>
                              <div className="flex items-center gap-2">
                                <input
                                  type="checkbox"
                                  checked={selectedIds.includes(task.id)}
                                  onChange={() => toggleTask(task.id)}
                                  className="h-4 w-4 rounded border border-[#30363d] bg-[#0d1117]"
                                />
                                <span className="text-xs text-[#8b949e]">选择</span>
                              </div>
                            </td>
                          ) : null}
                          <td>
                            <p className="max-w-xl text-sm leading-6 text-[#e6edf3]">
                              {task.market?.question ?? task.market_ref_id}
                            </p>
                            <p className="mt-1 text-xs text-[#8b949e]">
                              {task.market?.market_id ?? task.market_ref_id}
                            </p>
                          </td>
                          <td className="text-sm text-[#c9d1d9]">{task.review_reason_code ?? "-"}</td>
                          <td>
                            <ConsoleBadge label={task.priority} tone={priorityTone(task.priority)} />
                          </td>
                          <td>
                            <ConsoleBadge label={STATUS_LABELS[task.queue_status]} tone={statusTone(task.queue_status)} />
                          </td>
                          <td className="text-[#c9d1d9]">{formatCreatedAt(task.created_at)}</td>
                          <td>
                            <div className="flex flex-wrap gap-2">
                              {task.queue_status === "pending" ? (
                                <ConsoleButton
                                  type="button"
                                  size="sm"
                                  onClick={() => void runReviewAction([task.id], "start_review")}
                                  disabled={rowLoading}
                                >
                                  开始审核
                                </ConsoleButton>
                              ) : null}
                              {isActionableStatus(task.queue_status) ? (
                                <>
                                  <ConsoleButton
                                    type="button"
                                    size="sm"
                                    tone="success"
                                    onClick={() => void runReviewAction([task.id], "approve")}
                                    disabled={rowLoading}
                                  >
                                    通过
                                  </ConsoleButton>
                                  <ConsoleButton
                                    type="button"
                                    size="sm"
                                    tone="danger"
                                    onClick={() => void runReviewAction([task.id], "reject")}
                                    disabled={rowLoading || !rejectReason.trim()}
                                  >
                                    拒绝
                                  </ConsoleButton>
                                </>
                              ) : null}
                              <Link
                                href={`/review/${task.id}`}
                                className="inline-flex rounded-lg border border-[#58a6ff]/40 bg-[#1f6feb]/15 px-3 py-2 text-sm text-[#e6edf3] transition hover:border-[#58a6ff]/60 hover:bg-[#1f6feb]/22"
                              >
                                查看详情
                              </Link>
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}

            <div className="mt-4 flex items-center justify-between">
              <ConsoleButton
                type="button"
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                disabled={page <= 1}
              >
                上一页
              </ConsoleButton>
              <span className="text-sm text-[#8b949e]">
                第 {page} / {totalPages} 页
              </span>
              <ConsoleButton
                type="button"
                onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                disabled={page >= totalPages}
              >
                下一页
              </ConsoleButton>
            </div>
          </ConsolePanel>
        ) : null}
      </section>
    </main>
  )
}
