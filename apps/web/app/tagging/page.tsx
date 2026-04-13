"use client"

import { useEffect, useState } from "react"

import { apiGet } from "@/lib/api"

import { PageIntro, SoftPanel } from "../components/page-intro"

interface TagDefinition {
  tag_code: string
  tag_name: string
  description: string | null
  is_active: boolean
}

interface RuleVersion {
  version_code: string
  is_active: boolean
  activated_at: string | null
  created_at: string
  rule_count: number
}

interface TagDefinitionListResponse {
  definitions: TagDefinition[]
}

interface RuleVersionListResponse {
  versions: RuleVersion[]
}

function StatusPill({ active }: { active: boolean }) {
  return (
    <span
      className={`rounded-full border px-2.5 py-1 text-xs ${
        active
          ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-100"
          : "border-white/10 bg-white/5 text-slate-300"
      }`}
    >
      {active ? "启用中" : "已停用"}
    </span>
  )
}

export default function TaggingPage() {
  const [definitions, setDefinitions] = useState<TagDefinition[]>([])
  const [versions, setVersions] = useState<RuleVersion[]>([])
  const [loadingDefs, setLoadingDefs] = useState(true)
  const [loadingVersions, setLoadingVersions] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [includeInactive, setIncludeInactive] = useState(false)

  useEffect(() => {
    setLoadingDefs(true)
    apiGet<TagDefinitionListResponse>(`/tagging/definitions?include_inactive=${includeInactive}`)
      .then((data) => setDefinitions(data.definitions ?? []))
      .catch((fetchError) => setError(fetchError instanceof Error ? fetchError.message : "加载标签定义失败"))
      .finally(() => setLoadingDefs(false))
  }, [includeInactive])

  useEffect(() => {
    setLoadingVersions(true)
    apiGet<RuleVersionListResponse>("/tagging/versions?limit=20")
      .then((data) => setVersions(data.versions ?? []))
      .catch((fetchError) => setError(fetchError instanceof Error ? fetchError.message : "加载规则版本失败"))
      .finally(() => setLoadingVersions(false))
  }, [])

  const activeDefinitionCount = definitions.filter((item) => item.is_active).length
  const activeVersion = versions.find((item) => item.is_active)

  return (
    <main className="mx-auto max-w-7xl px-4 py-5 md:px-6">
      <PageIntro
        eyebrow="Tagging"
        title="标签分类"
        description="这页主要解释分类体系本身，而不是分类结果。先看有哪些标签定义、当前哪一版规则在生效，再去理解 review queue 或 tag-quality 为什么会出现那些结果。"
        stats={[
          { label: "标签定义数", value: String(definitions.length) },
          { label: "生效版本", value: activeVersion?.version_code ?? "-" },
        ]}
        guides={[
          {
            title: "先看什么",
            description: "先看当前启用的 rule version，再看核心标签定义是否齐全、描述是否清楚。",
          },
          {
            title: "什么时候算异常",
            description: "如果 review 或 tag-quality 明显异常，先回来看是不是规则版本切换或标签定义被停用了。",
          },
          {
            title: "下一步去哪",
            description: "想看分类结果质量时去 tag-quality；想看需要人工介入的任务时去 review。",
          },
        ]}
      />

      {error ? (
        <div className="mb-6 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-5 text-sm text-rose-100">
          加载失败：{error}
        </div>
      ) : null}

      <section className="mb-6 grid gap-4 md:grid-cols-3">
        <SoftPanel title="全部标签" description="当前页面按是否包含停用标签决定统计口径。">
          <p className="text-3xl font-semibold text-white">{definitions.length}</p>
        </SoftPanel>
        <SoftPanel title="启用标签" description="通常这部分才会参与当前分类主链路。">
          <p className="text-3xl font-semibold text-white">{activeDefinitionCount}</p>
        </SoftPanel>
        <SoftPanel title="当前口径" description="停用标签默认不显示，避免把历史遗留项和现行定义混在一起。">
          <p className="text-sm leading-6 text-slate-300">{includeInactive ? "当前包含已停用标签" : "当前仅显示启用标签"}</p>
        </SoftPanel>
      </section>

      <SoftPanel title="标签定义" description="标签定义是分类体系的词典；定义不清会直接影响审核与准入。">
        <div className="mb-4 flex items-center justify-between">
          <p className="text-sm text-slate-400">可切换是否查看已停用定义。</p>
          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={includeInactive}
              onChange={(event) => setIncludeInactive(event.target.checked)}
              className="rounded border-white/10 bg-white/5 text-sky-500"
            />
            显示已停用标签
          </label>
        </div>

        {loadingDefs ? <p className="py-10 text-center text-slate-400">正在加载标签定义...</p> : null}
        {!loadingDefs ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-slate-400">
                  <th className="px-4 py-3 font-medium">标签编码</th>
                  <th className="px-4 py-3 font-medium">名称</th>
                  <th className="px-4 py-3 font-medium">说明</th>
                  <th className="px-4 py-3 font-medium">状态</th>
                </tr>
              </thead>
              <tbody>
                {definitions.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-10 text-center text-slate-500">
                      当前没有标签定义。若你预期这里应有数据，先检查 API 与种子数据是否已初始化。
                    </td>
                  </tr>
                ) : null}
                {definitions.map((definition) => (
                  <tr key={definition.tag_code} className="border-b border-white/5 transition hover:bg-white/[0.03]">
                    <td className="px-4 py-3 font-mono text-xs text-sky-300">{definition.tag_code}</td>
                    <td className="px-4 py-3 text-slate-100">{definition.tag_name}</td>
                    <td className="px-4 py-3 text-slate-400">{definition.description ?? "-"}</td>
                    <td className="px-4 py-3"><StatusPill active={definition.is_active} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </SoftPanel>

      <div className="mt-6">
        <SoftPanel title="规则版本" description="如果分类口径变了，通常先从这里看当前哪一版正在生效。">
          {loadingVersions ? <p className="py-10 text-center text-slate-400">正在加载规则版本...</p> : null}
          {!loadingVersions ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-left text-slate-400">
                    <th className="px-4 py-3 font-medium">版本号</th>
                    <th className="px-4 py-3 font-medium">状态</th>
                    <th className="px-4 py-3 font-medium">规则数</th>
                    <th className="px-4 py-3 font-medium">启用时间</th>
                    <th className="px-4 py-3 font-medium">创建时间</th>
                  </tr>
                </thead>
                <tbody>
                  {versions.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-10 text-center text-slate-500">
                        当前没有规则版本记录。
                      </td>
                    </tr>
                  ) : null}
                  {versions.map((version) => (
                    <tr key={version.version_code} className="border-b border-white/5 transition hover:bg-white/[0.03]">
                      <td className="px-4 py-3 font-mono text-xs text-sky-300">{version.version_code}</td>
                      <td className="px-4 py-3"><StatusPill active={version.is_active} /></td>
                      <td className="px-4 py-3 text-slate-300">{version.rule_count}</td>
                      <td className="px-4 py-3 text-slate-400">
                        {version.activated_at ? new Date(version.activated_at).toLocaleString("zh-CN", { hour12: false }) : "-"}
                      </td>
                      <td className="px-4 py-3 text-slate-400">
                        {new Date(version.created_at).toLocaleString("zh-CN", { hour12: false })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </SoftPanel>
      </div>
    </main>
  )
}
