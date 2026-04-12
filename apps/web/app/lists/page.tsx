"use client"

import { useEffect, useMemo, useState } from "react"

import { apiGet } from "@/lib/api"

import { PageIntro, SoftPanel } from "../components/page-intro"

interface ListEntry {
  id: string
  list_type: string
  entry_type: string
  entry_value: string
  match_mode: string
  is_active: boolean
  created_at: string
}

interface ListEntriesResponse {
  entries: ListEntry[]
}

const LIST_LABELS: Record<string, string> = {
  all: "全部",
  blacklist: "黑名单",
  whitelist: "白名单",
  greylist: "灰名单",
}

const LIST_STYLES: Record<string, string> = {
  blacklist: "border-rose-400/30 bg-rose-500/10 text-rose-100",
  whitelist: "border-emerald-400/30 bg-emerald-500/10 text-emerald-100",
  greylist: "border-amber-400/30 bg-amber-500/10 text-amber-100",
}

export default function ListsPage() {
  const [entries, setEntries] = useState<ListEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<string>("all")

  useEffect(() => {
    apiGet<ListEntriesResponse>("/lists/entries")
      .then((data) => {
        setEntries(data.entries ?? [])
        setLoading(false)
      })
      .catch((fetchError) => {
        setError(fetchError instanceof Error ? fetchError.message : "加载名单条目失败")
        setLoading(false)
      })
  }, [])

  const counts = useMemo(
    () => ({
      all: entries.length,
      blacklist: entries.filter((entry) => entry.list_type === "blacklist").length,
      whitelist: entries.filter((entry) => entry.list_type === "whitelist").length,
      greylist: entries.filter((entry) => entry.list_type === "greylist").length,
    }),
    [entries],
  )

  const filtered = filter === "all" ? entries : entries.filter((entry) => entry.list_type === filter)

  return (
    <main className="mx-auto max-w-7xl px-4 py-5 md:px-6">
      <PageIntro
        eyebrow="Lists"
        title="名单管理"
        description="这页主要定义哪些市场需要被强制放行、强制拦截或进入灰区观察。它不会直接告诉你分类结果，但会显著影响 tagging、review 和准入判断。"
        stats={[
          { label: "总条目数", value: String(entries.length) },
          { label: "当前筛选", value: LIST_LABELS[filter] ?? filter },
        ]}
        guides={[
          {
            title: "先看什么",
            description: "先看黑名单和白名单数量，再看条目类型、匹配模式和值是否合理。",
          },
          {
            title: "什么时候算异常",
            description: "如果某批市场判断明显不符合预期，可以先回来看是不是名单规则把结果提前改写了。",
          },
          {
            title: "下一步去哪",
            description: "名单只负责口径约束；想看实际受影响的任务，要继续去 tagging、review 或 netev。",
          },
        ]}
      />

      {loading ? <div className="py-20 text-center text-slate-400">正在加载名单条目...</div> : null}
      {error ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-5 text-sm text-rose-100">
          加载失败：{error}
        </div>
      ) : null}

      {!loading && !error ? (
        <>
          <section className="mb-6 grid gap-4 md:grid-cols-4">
            {(["all", "blacklist", "whitelist", "greylist"] as const).map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => setFilter(type)}
                className={`rounded-[24px] border p-4 text-left transition ${
                  filter === type
                    ? "border-sky-300/40 bg-sky-500/12"
                    : "border-white/10 bg-white/[0.045] hover:bg-white/10"
                }`}
              >
                <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">{LIST_LABELS[type]}</p>
                <p className="mt-2 text-3xl font-semibold text-white">{counts[type]}</p>
              </button>
            ))}
          </section>

          <SoftPanel
            title="名单条目"
            description={filter === "all" ? "这里展示全部名单条目。" : `当前只看 ${LIST_LABELS[filter] ?? filter} 条目。`}
          >
            {filtered.length === 0 ? (
              <p className="py-4 text-sm text-slate-400">当前筛选下没有条目。</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[860px] text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-left text-slate-400">
                      <th className="px-4 py-3 font-medium">名单类型</th>
                      <th className="px-4 py-3 font-medium">条目类型</th>
                      <th className="px-4 py-3 font-medium">匹配值</th>
                      <th className="px-4 py-3 font-medium">匹配模式</th>
                      <th className="px-4 py-3 font-medium">状态</th>
                      <th className="px-4 py-3 font-medium">创建时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((entry) => (
                      <tr key={entry.id} className="border-b border-white/5 transition hover:bg-white/[0.03]">
                        <td className="px-4 py-3">
                          <span className={`rounded-full border px-2.5 py-1 text-xs ${LIST_STYLES[entry.list_type] ?? "border-white/10 bg-white/5 text-slate-300"}`}>
                            {LIST_LABELS[entry.list_type] ?? entry.list_type}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-300">{entry.entry_type}</td>
                        <td className="px-4 py-3 font-mono text-xs text-slate-100">{entry.entry_value}</td>
                        <td className="px-4 py-3 text-slate-400">{entry.match_mode}</td>
                        <td className="px-4 py-3">
                          <span className={`rounded-full border px-2.5 py-1 text-xs ${entry.is_active ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-100" : "border-white/10 bg-white/5 text-slate-300"}`}>
                            {entry.is_active ? "启用中" : "已停用"}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-400">
                          {new Date(entry.created_at).toLocaleString("zh-CN", { hour12: false })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SoftPanel>
        </>
      ) : null}
    </main>
  )
}
