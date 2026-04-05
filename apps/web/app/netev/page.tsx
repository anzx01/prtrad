"use client"

import { useEffect, useState } from "react"
import { apiGet } from "@/lib/api"

export default function NetEVPage() {
  const [candidates, setCandidates] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState("")

  useEffect(() => {
    setLoading(true)
    setError(null)

    const endpoint = filter ? `/netev/candidates?decision=${filter}` : "/netev/candidates"

    apiGet(endpoint)
      .then((data: any) => {
        setCandidates(data || [])
        setLoading(false)
      })
      .catch((err: any) => {
        console.error("Failed to fetch NetEV candidates:", err)
        setError(err.message || "Failed to fetch NetEV candidates")
        setLoading(false)
      })
  }, [filter])

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

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">M3 NetEV 准入评估</h1>
        <div className="flex space-x-2">
          <button
            className={`px-4 py-2 rounded transition-colors ${!filter ? "bg-indigo-600 text-white" : "bg-gray-200 text-gray-700"}`}
            onClick={() => setFilter("")}
          >
            全部
          </button>
          <button
            className={`px-4 py-2 rounded transition-colors ${filter === "admit" ? "bg-green-600 text-white" : "bg-gray-200 text-gray-700"}`}
            onClick={() => setFilter("admit")}
          >
            Admit
          </button>
          <button
            className={`px-4 py-2 rounded transition-colors ${filter === "reject" ? "bg-red-600 text-white" : "bg-gray-200 text-gray-700"}`}
            onClick={() => setFilter("reject")}
          >
            Reject
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6">
        {candidates.length > 0 ? candidates.map((c) => (
          <div key={c.id} className={`bg-white border-l-4 rounded-lg shadow-sm p-6 flex flex-col md:flex-row justify-between items-center ${
            c.admission_decision === "admit" ? "border-green-500" : "border-red-500"
          }`}>
            <div className="flex-1">
              <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Market REF ID</div>
              <div className="text-sm font-mono text-gray-900 truncate max-w-xs">{c.market_ref_id}</div>
              <div className="text-xs text-gray-500 mt-1">Evaluated at: {new Date(c.evaluated_at).toLocaleString()}</div>
            </div>

            <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-4 w-full md:w-auto my-4 md:my-0">
              <div className="text-center">
                <div className="text-xs text-gray-400">Gross Edge</div>
                <div className="text-sm font-semibold text-gray-900">{(c.gross_edge * 100).toFixed(2)}%</div>
              </div>
              <div className="text-center">
                <div className="text-xs text-gray-400">Trading Costs</div>
                <div className="text-sm font-semibold text-red-500">-{( (c.fee_cost + c.slippage_cost) * 100).toFixed(2)}%</div>
              </div>
              <div className="text-center">
                <div className="text-xs text-gray-400">Dispute Risk</div>
                <div className="text-sm font-semibold text-red-500">-{(c.dispute_discount * 100).toFixed(2)}%</div>
              </div>
              <div className="text-center bg-gray-50 rounded p-1">
                <div className="text-xs text-gray-400">Net EV</div>
                <div className={`text-sm font-bold ${c.net_ev > 0 ? "text-green-600" : "text-red-600"}`}>
                  {(c.net_ev * 100).toFixed(2)}%
                </div>
              </div>
            </div>

            <div className="w-full md:w-32 text-right">
              <span className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest ${
                c.admission_decision === "admit" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
              }`}>
                {c.admission_decision}
              </span>
              {c.rejection_reason_code && (
                <div className="text-[10px] text-red-400 mt-2 italic">{c.rejection_reason_code}</div>
              )}
            </div>
          </div>
        )) : (
          <div className="bg-white border rounded-lg p-12 text-center text-gray-400 italic">
            暂无评估记录，系统运行平稳中。
          </div>
        )}
      </div>
    </div>
  )
}
