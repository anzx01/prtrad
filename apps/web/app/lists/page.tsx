"use client"

import { useEffect, useState } from "react"

interface ListEntry {
  id: string
  list_type: string
  entry_type: string
  entry_value: string
  match_mode: string
  is_active: boolean
  created_at: string
}

const LIST_TYPE_STYLES: Record<string, string> = {
  blacklist: "bg-red-100 text-red-800",
  whitelist: "bg-green-100 text-green-800",
  greylist: "bg-yellow-100 text-yellow-800",
}

export default function ListsPage() {
  const [entries, setEntries] = useState<ListEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<string>("all")

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/lists/entries`)
      .then((res) => res.json())
      .then((data) => {
        setEntries(data.entries || [])
        setLoading(false)
      })
      .catch((err) => {
        console.error("Failed to fetch list entries:", err)
        setError(err.message || "Failed to fetch list entries")
        setLoading(false)
      })
  }, [])

  if (loading) return <div className="p-8 text-gray-500">加载中...</div>

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

  const counts = {
    all: entries.length,
    blacklist: entries.filter((e) => e.list_type === "blacklist").length,
    whitelist: entries.filter((e) => e.list_type === "whitelist").length,
    greylist: entries.filter((e) => e.list_type === "greylist").length,
  }

  const filtered = filter === "all" ? entries : entries.filter((e) => e.list_type === filter)

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">List Management</h1>

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {(["all", "blacklist", "whitelist", "greylist"] as const).map((type) => (
          <button
            key={type}
            onClick={() => setFilter(type)}
            className={`rounded-lg shadow p-4 text-left transition-all ${
              filter === type ? "ring-2 ring-blue-500" : ""
            } bg-white`}
          >
            <p className="text-sm text-gray-500 mb-1 capitalize">{type === "all" ? "全部" : type}</p>
            <p className="text-2xl font-bold text-gray-900">{counts[type]}</p>
          </button>
        ))}
      </div>

      {/* 列表 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4 border-b pb-2">
          名单条目
          {filter !== "all" && <span className="ml-2 text-sm font-normal text-gray-500">— {filter}</span>}
        </h2>

        {filtered.length === 0 ? (
          <p className="text-gray-500 py-4">暂无条目。</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">名单类型</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">条目类型</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">值</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">匹配模式</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">创建时间</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filtered.map((entry) => (
                  <tr key={entry.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${LIST_TYPE_STYLES[entry.list_type] ?? "bg-gray-100 text-gray-700"}`}>
                        {entry.list_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700">{entry.entry_type}</td>
                    <td className="px-4 py-3 text-sm font-mono text-gray-900">{entry.entry_value}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{entry.match_mode}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${entry.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                        {entry.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {new Date(entry.created_at).toLocaleDateString("zh-CN")}
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
