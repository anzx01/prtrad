"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface TagDefinition {
  tag_key: string;
  tag_name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

interface RuleVersion {
  version_code: string;
  is_active: boolean;
  activated_at: string | null;
  created_at: string;
  rule_count: number;
}

interface TagDefinitionListResponse {
  definitions: TagDefinition[];
  total: number;
}

interface RuleVersionListResponse {
  versions: RuleVersion[];
  total: number;
}

export default function TaggingPage() {
  const [definitions, setDefinitions] = useState<TagDefinition[]>([]);
  const [versions, setVersions] = useState<RuleVersion[]>([]);
  const [loadingDefs, setLoadingDefs] = useState(true);
  const [loadingVersions, setLoadingVersions] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [includeInactive, setIncludeInactive] = useState(false);

  useEffect(() => {
    async function fetchDefinitions() {
      setLoadingDefs(true);
      try {
        const params = new URLSearchParams({ include_inactive: String(includeInactive) });
        const res = await fetch(`${API_BASE}/tagging/definitions?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json: TagDefinitionListResponse = await res.json();
        setDefinitions(json.definitions);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load tag definitions");
      } finally {
        setLoadingDefs(false);
      }
    }
    fetchDefinitions();
  }, [includeInactive]);

  useEffect(() => {
    async function fetchVersions() {
      setLoadingVersions(true);
      try {
        const res = await fetch(`${API_BASE}/tagging/versions?limit=20`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json: RuleVersionListResponse = await res.json();
        setVersions(json.versions);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load rule versions");
      } finally {
        setLoadingVersions(false);
      }
    }
    fetchVersions();
  }, []);

  return (
    <main className="mx-auto max-w-6xl px-6 py-10 lg:px-10">
      <div className="mb-8 space-y-1">
        <h1 className="text-3xl font-semibold text-white">Tagging Management</h1>
        <p className="text-slate-400 text-sm">
          Tag definitions and rule versions that drive market classification.
        </p>
      </div>

      {error && (
        <div className="mb-6 rounded-xl border border-red-500/30 bg-red-500/10 p-6 text-red-300">
          Error: {error}
        </div>
      )}

      {/* Tag Definitions */}
      <section className="mb-10">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-medium text-white">Tag Definitions</h2>
          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={includeInactive}
              onChange={(e) => setIncludeInactive(e.target.checked)}
              className="rounded border-white/10 bg-white/5 text-sky-500 focus:ring-sky-500/50"
            />
            Include inactive
          </label>
        </div>

        {loadingDefs && (
          <div className="py-10 text-center text-slate-400">Loading definitions…</div>
        )}

        {!loadingDefs && (
          <div className="rounded-2xl border border-white/10 bg-white/5 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 bg-white/5 text-left text-slate-400">
                  <th className="px-4 py-3 font-medium">Tag Key</th>
                  <th className="px-4 py-3 font-medium">Name</th>
                  <th className="px-4 py-3 font-medium hidden md:table-cell">Description</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {definitions.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-10 text-center text-slate-500">
                      No tag definitions found.
                    </td>
                  </tr>
                )}
                {definitions.map((def) => (
                  <tr
                    key={def.tag_key}
                    className="border-b border-white/5 hover:bg-white/5 transition-colors"
                  >
                    <td className="px-4 py-3 font-mono text-xs text-sky-300">
                      {def.tag_key}
                    </td>
                    <td className="px-4 py-3 text-slate-100">{def.tag_name}</td>
                    <td className="px-4 py-3 hidden md:table-cell text-slate-400 text-xs">
                      {def.description ?? "—"}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs ${
                          def.is_active
                            ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                            : "bg-slate-500/20 text-slate-400 border-slate-500/30"
                        }`}
                      >
                        {def.is_active ? "active" : "inactive"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Rule Versions */}
      <section>
        <h2 className="mb-4 text-lg font-medium text-white">Rule Versions</h2>

        {loadingVersions && (
          <div className="py-10 text-center text-slate-400">Loading versions…</div>
        )}

        {!loadingVersions && (
          <div className="rounded-2xl border border-white/10 bg-white/5 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 bg-white/5 text-left text-slate-400">
                  <th className="px-4 py-3 font-medium">Version Code</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium hidden md:table-cell">Rule Count</th>
                  <th className="px-4 py-3 font-medium hidden lg:table-cell">Activated At</th>
                  <th className="px-4 py-3 font-medium hidden lg:table-cell">Created At</th>
                </tr>
              </thead>
              <tbody>
                {versions.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-10 text-center text-slate-500">
                      No rule versions found.
                    </td>
                  </tr>
                )}
                {versions.map((ver) => (
                  <tr
                    key={ver.version_code}
                    className="border-b border-white/5 hover:bg-white/5 transition-colors"
                  >
                    <td className="px-4 py-3 font-mono text-xs text-sky-300">
                      {ver.version_code}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs ${
                          ver.is_active
                            ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                            : "bg-slate-500/20 text-slate-400 border-slate-500/30"
                        }`}
                      >
                        {ver.is_active ? "active" : "inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell text-slate-300">
                      {ver.rule_count}
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell text-slate-400 text-xs">
                      {ver.activated_at
                        ? new Date(ver.activated_at).toLocaleString()
                        : "—"}
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell text-slate-400 text-xs">
                      {new Date(ver.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
