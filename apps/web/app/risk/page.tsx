"use client"

import { useEffect, useState } from "react"
import { apiGet, apiPost } from "@/lib/api"

interface StateEvent {
  from_state: string
  to_state: string
  trigger_type: string
  trigger_metric: string
  trigger_value: number
  actor_id: string | null
  notes: string | null
  created_at: string
}

interface RiskStateData {
  state: string
  history: StateEvent[]
}

interface ExposureItem {
  cluster_code: string
  gross_exposure: number
  net_exposure: number
  position_count: number
  limit_value: number
  utilization_rate: number
  is_breached: boolean
  snapshot_at: string
}

interface KillSwitchItem {
  id: string
  request_type: string
  target_scope: string
  requested_by: string
  reason: string
  status: string
  reviewed_by: string | null
  reviewed_at: string | null
  review_notes: string | null
  created_at: string
}

const STATE_COLORS: Record<string, string> = {
  Normal: "text-green-400",
  Caution: "text-yellow-400",
  RiskOff: "text-orange-400",
  Frozen: "text-red-500",
}

const STATE_BG: Record<string, string> = {
  Normal: "bg-green-500/10 border-green-500/30",
  Caution: "bg-yellow-500/10 border-yellow-500/30",
  RiskOff: "bg-orange-500/10 border-orange-500/30",
  Frozen: "bg-red-500/10 border-red-500/30",
}

const KS_STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-500/10 text-yellow-300",
  approved: "bg-green-500/10 text-green-300",
  rejected: "bg-red-500/10 text-red-300",
}

export default function RiskPage() {
  const [riskState, setRiskState] = useState<RiskStateData | null>(null)
  const [exposures, setExposures] = useState<ExposureItem[]>([])
  const [ksRequests, setKsRequests] = useState<KillSwitchItem[]>([])
  const [loading, setLoading] = useState(true)
  const [computing, setComputing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Kill-switch form state
  const [ksForm, setKsForm] = useState({
    request_type: "risk_off",
    target_scope: "global",
    requested_by: "",
    reason: "",
  })
  const [submitting, setSubmitting] = useState(false)

  const fetchAll = async () => {
    try {
      const [stateData, expData, ksData] = await Promise.all([
        apiGet<RiskStateData>("/risk/state"),
        apiGet<{ exposures: ExposureItem[] }>("/risk/exposures"),
        apiGet<{ requests: KillSwitchItem[] }>("/risk/kill-switch"),
      ])
      setRiskState(stateData)
      setExposures(expData.exposures)
      setKsRequests(ksData.requests)
      setError(null)
    } catch (e: any) {
      setError(e.message || "Failed to load risk data")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
  }, [])

  const handleCompute = async () => {
    setComputing(true)
    try {
      await apiPost("/risk/exposures/compute")
      await fetchAll()
    } catch (e: any) {
      setError(e.message)
    } finally {
      setComputing(false)
    }
  }

  const handleKsSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!ksForm.requested_by || !ksForm.reason) return
    setSubmitting(true)
    try {
      await apiPost("/risk/kill-switch", ksForm)
      setKsForm({ request_type: "risk_off", target_scope: "global", requested_by: "", reason: "" })
      await fetchAll()
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleReview = async (id: string, action: "approve" | "reject") => {
    const reviewer = prompt("Reviewer ID:")
    if (!reviewer) return
    try {
      await apiPost(`/risk/kill-switch/${id}/${action}`, { reviewer, notes: "" })
      await fetchAll()
    } catch (e: any) {
      setError(e.message)
    }
  }

  if (loading) return <div className="p-8 text-slate-400">加载中...</div>

  const currentState = riskState?.state ?? "Normal"
  const stateColor = STATE_COLORS[currentState] ?? "text-slate-300"
  const stateBg = STATE_BG[currentState] ?? "bg-slate-800 border-slate-700"
  const pendingKs = ksRequests.filter((r) => r.status === "pending")

  return (
    <div className="mx-auto max-w-6xl px-6 py-8 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-semibold">Portfolio Risk</h1>
        <button
          onClick={handleCompute}
          disabled={computing}
          className="rounded-full border border-sky-400/40 bg-sky-500/10 px-4 py-1.5 text-sm text-sky-200 hover:bg-sky-500/20 transition-colors disabled:opacity-50"
        >
          {computing ? "计算中..." : "刷新暴露快照"}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-red-300 text-sm">{error}</div>
      )}

      {/* 风险状态 */}
      <div className={`rounded-2xl border p-6 ${stateBg}`}>
        <p className="text-sm text-slate-400 mb-1">当前全局风险状态</p>
        <p className={`text-5xl font-bold ${stateColor}`}>{currentState}</p>
        {riskState?.history[0] && (
          <p className="mt-2 text-xs text-slate-500">
            最后变更：{new Date(riskState.history[0].created_at).toLocaleString("zh-CN")}
            {riskState.history[0].actor_id ? ` · 操作人: ${riskState.history[0].actor_id}` : " · 自动触发"}
          </p>
        )}
      </div>

      {/* 风险暴露 */}
      <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
        <h2 className="text-xl font-medium mb-4">风险簇暴露</h2>
        {exposures.length === 0 ? (
          <p className="text-slate-400 text-sm">暂无暴露快照。点击"刷新暴露快照"生成。</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="text-left text-xs text-slate-400 uppercase border-b border-white/10">
                  <th className="pb-2 pr-4">风险簇</th>
                  <th className="pb-2 pr-4 text-right">净暴露</th>
                  <th className="pb-2 pr-4 text-right">持仓数</th>
                  <th className="pb-2 pr-4 text-right">限额</th>
                  <th className="pb-2 pr-4 text-right">占用率</th>
                  <th className="pb-2 text-center">状态</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {exposures.map((exp) => {
                  const pct = (exp.utilization_rate * 100).toFixed(1)
                  const breached = exp.is_breached
                  return (
                    <tr key={exp.cluster_code} className={breached ? "bg-red-500/5" : ""}>
                      <td className="py-3 pr-4 text-sm font-mono text-slate-200">{exp.cluster_code}</td>
                      <td className="py-3 pr-4 text-sm text-right text-slate-300">{exp.net_exposure.toFixed(4)}</td>
                      <td className="py-3 pr-4 text-sm text-right text-slate-300">{exp.position_count}</td>
                      <td className="py-3 pr-4 text-sm text-right text-slate-400">{exp.limit_value.toFixed(2)}</td>
                      <td className="py-3 pr-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-20 h-1.5 rounded-full bg-slate-700">
                            <div
                              className={`h-1.5 rounded-full ${breached ? "bg-red-500" : exp.utilization_rate > 0.6 ? "bg-yellow-500" : "bg-green-500"}`}
                              style={{ width: `${Math.min(exp.utilization_rate * 100, 100)}%` }}
                            />
                          </div>
                          <span className={`text-sm font-medium ${breached ? "text-red-400" : "text-slate-300"}`}>
                            {pct}%
                          </span>
                        </div>
                      </td>
                      <td className="py-3 text-center">
                        {breached ? (
                          <span className="px-2 py-0.5 rounded text-xs bg-red-500/20 text-red-300">超限</span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-xs bg-green-500/10 text-green-400">正常</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 状态迁移历史 */}
      {riskState && riskState.history.length > 0 && (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
          <h2 className="text-xl font-medium mb-4">状态迁移历史</h2>
          <div className="space-y-3">
            {riskState.history.map((ev, i) => (
              <div key={i} className="flex items-start gap-3 text-sm">
                <div className="mt-1 w-2 h-2 rounded-full bg-slate-500 shrink-0" />
                <div>
                  <span className={STATE_COLORS[ev.from_state] ?? "text-slate-300"}>{ev.from_state}</span>
                  <span className="text-slate-500 mx-1">→</span>
                  <span className={STATE_COLORS[ev.to_state] ?? "text-slate-300"}>{ev.to_state}</span>
                  <span className="ml-2 text-slate-500">
                    [{ev.trigger_type}] {ev.trigger_metric}={ev.trigger_value.toFixed(3)}
                  </span>
                  {ev.actor_id && <span className="ml-2 text-slate-500">by {ev.actor_id}</span>}
                  <div className="text-xs text-slate-600 mt-0.5">
                    {new Date(ev.created_at).toLocaleString("zh-CN")}
                    {ev.notes && ` · ${ev.notes}`}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Kill-Switch */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Pending 审批 */}
        <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
          <h2 className="text-xl font-medium mb-4">
            待审批请求
            {pendingKs.length > 0 && (
              <span className="ml-2 px-2 py-0.5 rounded text-xs bg-yellow-500/20 text-yellow-300">{pendingKs.length}</span>
            )}
          </h2>
          {pendingKs.length === 0 ? (
            <p className="text-slate-400 text-sm">暂无待审批请求。</p>
          ) : (
            <div className="space-y-3">
              {pendingKs.map((req) => (
                <div key={req.id} className="rounded-xl border border-yellow-500/20 bg-yellow-500/5 p-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="text-sm font-medium text-slate-200 uppercase">{req.request_type}</p>
                      <p className="text-xs text-slate-400 mt-0.5">
                        scope: {req.target_scope} · by {req.requested_by}
                      </p>
                      <p className="text-xs text-slate-300 mt-1">{req.reason}</p>
                    </div>
                  </div>
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={() => handleReview(req.id, "approve")}
                      className="rounded-full px-3 py-1 text-xs bg-green-500/10 text-green-300 hover:bg-green-500/20 transition-colors"
                    >
                      批准
                    </button>
                    <button
                      onClick={() => handleReview(req.id, "reject")}
                      className="rounded-full px-3 py-1 text-xs bg-red-500/10 text-red-300 hover:bg-red-500/20 transition-colors"
                    >
                      驳回
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 提交新请求 */}
        <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
          <h2 className="text-xl font-medium mb-4">提交 Kill-Switch 请求</h2>
          <form onSubmit={handleKsSubmit} className="space-y-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">操作类型</label>
              <select
                value={ksForm.request_type}
                onChange={(e) => setKsForm({ ...ksForm, request_type: e.target.value })}
                className="w-full rounded-lg bg-slate-800 border border-white/10 px-3 py-2 text-sm text-slate-200"
              >
                <option value="risk_off">风险关闭 (RiskOff)</option>
                <option value="freeze">冻结 (Freeze)</option>
                <option value="unfreeze">解冻恢复 (Unfreeze)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">目标范围</label>
              <input
                value={ksForm.target_scope}
                onChange={(e) => setKsForm({ ...ksForm, target_scope: e.target.value })}
                placeholder="global 或 cluster_code"
                className="w-full rounded-lg bg-slate-800 border border-white/10 px-3 py-2 text-sm text-slate-200 placeholder-slate-500"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">申请人 ID</label>
              <input
                value={ksForm.requested_by}
                onChange={(e) => setKsForm({ ...ksForm, requested_by: e.target.value })}
                placeholder="your_user_id"
                className="w-full rounded-lg bg-slate-800 border border-white/10 px-3 py-2 text-sm text-slate-200 placeholder-slate-500"
                required
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">原因</label>
              <textarea
                value={ksForm.reason}
                onChange={(e) => setKsForm({ ...ksForm, reason: e.target.value })}
                placeholder="详细说明原因..."
                rows={3}
                className="w-full rounded-lg bg-slate-800 border border-white/10 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 resize-none"
                required
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-full border border-orange-400/40 bg-orange-500/10 px-4 py-2 text-sm text-orange-200 hover:bg-orange-500/20 transition-colors disabled:opacity-50"
            >
              {submitting ? "提交中..." : "提交请求"}
            </button>
          </form>
        </div>
      </div>

      {/* 历史请求列表 */}
      {ksRequests.filter((r) => r.status !== "pending").length > 0 && (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
          <h2 className="text-xl font-medium mb-4">历史审批记录</h2>
          <div className="space-y-2">
            {ksRequests.filter((r) => r.status !== "pending").map((req) => (
              <div key={req.id} className="flex items-center justify-between text-sm py-2 border-b border-white/5 last:border-0">
                <div>
                  <span className="font-mono uppercase text-slate-300 text-xs">{req.request_type}</span>
                  <span className="text-slate-500 mx-2">·</span>
                  <span className="text-slate-400">{req.target_scope}</span>
                  <span className="text-slate-500 mx-2">by</span>
                  <span className="text-slate-300">{req.requested_by}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-xs ${KS_STATUS_COLORS[req.status] ?? "bg-slate-700 text-slate-300"}`}>
                    {req.status}
                  </span>
                  <span className="text-xs text-slate-500">
                    {new Date(req.created_at).toLocaleDateString("zh-CN")}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
