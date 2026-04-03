"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface DQSummary {
  total_checks: number;
  status_distribution: Record<string, number>;
  pass_rate: number;
}

interface DQResult {
  id: string;
  market_ref_id: string;
  checked_at: string;
  status: string;
  score: number | null;
  failure_count: number;
  rule_version: string;
}

interface DQSummaryResponse {
  summary: DQSummary;
  recent_results: DQResult[];
}

const STATUS_STYLES: Record<string, string> = {
  pass: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  warn: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  fail: "bg-red-500/20 text-red-300 border-red-500/30",
};

function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_STYLES[status] ?? "bg-slate-500/20 text-slate-300 border-slate-500/30";
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs ${cls}`}>
      {status}
    </span>
  );
}

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-1 text-3xl font-semibold text-white">{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

export default function DQPage() {
  const [data, setData] = useState<DQSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchDQ() {
      try {
        const res = await fetch(`${API_BASE}/dq/summary?limit=20`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        setData(json);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load DQ data");
      } finally {
        setLoading(false);
      }
    }
    fetchDQ();
  }, []);

  const summary = data?.summary;
  const dist = summary?.status_distribution ?? {};

  return (
    <main className="mx-auto max-w-6xl px-6 py-10 lg:px-10">
      <div className="mb-8 space-y-1">
        <h1 className="text-3xl font-semibold text-white">Data Quality Dashboard</h1>
        <p className="text-slate-400 text-sm">
          Aggregate DQ check results and recent check history.
        </p>
      </div>

      {loading && (
        <div className="py-20 text-center text-slate-400">Loading DQ data…</div>
      )}
      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6 text-red-300">
          Error: {error}
        </div>
      )}

      {!loading && !error && summary && (
        <>
          {/* Stats */}
          <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Total Checks" value={summary.total_checks} />
            <StatCard
              label="Pass Rate"
              value={`${(summary.pass_rate * 100).toFixed(1)}%`}
            />
            <StatCard
              label="Pass"
              value={dist.pass ?? 0}
              sub="status = pass"
            />
            <StatCard
              label="Warn / Fail"
              value={`${dist.warn ?? 0} / ${dist.fail ?? 0}`}
              sub="warn / fail"
            />
          </div>

          {/* Status distribution bar */}
          {summary.total_checks > 0 && (
            <div className="mb-8 rounded-2xl border border-white/10 bg-white/5 p-5">
              <p className="mb-3 text-sm font-medium text-slate-300">Status distribution</p>
              <div className="flex h-4 w-full overflow-hidden rounded-full">
                {(["pass", "warn", "fail"] as const).map((s) => {
                  const pct = ((dist[s] ?? 0) / summary.total_checks) * 100;
                  if (pct === 0) return null;
                  const colors = {
                    pass: "bg-emerald-500",
                    warn: "bg-yellow-500",
                    fail: "bg-red-500",
                  };
                  return (
                    <div
                      key={s}
                      className={`${colors[s]} transition-all`}
                      style={{ width: `${pct}%` }}
                      title={`${s}: ${dist[s]} (${pct.toFixed(1)}%)`}
                    />
                  );
                })}
              </div>
              <div className="mt-2 flex gap-4 text-xs text-slate-400">
                {(["pass", "warn", "fail"] as const).map((s) => (
                  <span key={s}>
                    <span
                      className={`mr-1 inline-block h-2 w-2 rounded-full ${
                        s === "pass" ? "bg-emerald-500" : s === "warn" ? "bg-yellow-500" : "bg-red-500"
                      }`}
                    />
                    {s}: {dist[s] ?? 0}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Recent results */}
          <h2 className="mb-4 text-lg font-medium text-white">Recent Checks</h2>
          <div className="rounded-2xl border border-white/10 bg-white/5 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 bg-white/5 text-left text-slate-400">
                  <th className="px-4 py-3 font-medium">Market ID</th>
                  <th className="px-4 py-3 font-medium">Checked At</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium hidden md:table-cell">Score</th>
                  <th className="px-4 py-3 font-medium hidden lg:table-cell">Failures</th>
                  <th className="px-4 py-3 font-medium hidden lg:table-cell">Rule Version</th>
                </tr>
              </thead>
              <tbody>
                {data!.recent_results.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-10 text-center text-slate-500">
                      No DQ results found.
                    </td>
                  </tr>
                )}
                {data!.recent_results.map((result) => (
                  <tr
                    key={result.id}
                    className="border-b border-white/5 hover:bg-white/5 transition-colors"
                  >
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">
                      {result.market_ref_id.slice(0, 8)}…
                    </td>
                    <td className="px-4 py-3 text-slate-300">
                      {new Date(result.checked_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={result.status} />
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell text-slate-300">
                      {result.score !== null ? result.score.toFixed(3) : "—"}
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell text-slate-300">
                      {result.failure_count}
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell text-slate-500 text-xs">
                      {result.rule_version}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </main>
  );
}
