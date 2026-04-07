"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface DQReasonCount {
  reason_code: string;
  count: number;
}

interface DQSummary {
  total_checks: number;
  status_distribution: Record<string, number>;
  pass_rate: number;
  latest_checked_at: string | null;
  latest_snapshot_time: string | null;
  snapshot_age_seconds: number | null;
  freshness_status: string;
  top_blocking_reasons: DQReasonCount[];
}

interface DQResult {
  id: string;
  market_ref_id: string;
  market_id: string | null;
  checked_at: string;
  status: string;
  score: number | null;
  failure_count: number;
  rule_version: string;
  blocking_reason_codes: string[];
  warning_reason_codes: string[];
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

function formatAge(seconds: number | null): string {
  if (seconds === null) return "Unknown";
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
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
  const freshnessStatus = summary?.freshness_status ?? "unknown";
  const freshnessClassName =
    freshnessStatus === "fresh"
      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
      : freshnessStatus === "stale"
        ? "border-amber-500/30 bg-amber-500/10 text-amber-100"
        : "border-slate-500/30 bg-slate-500/10 text-slate-200";

  return (
    <main className="mx-auto max-w-6xl px-6 py-10 lg:px-10">
      <div className="mb-8 space-y-1">
        <h1 className="text-3xl font-semibold text-white">Data Quality Dashboard</h1>
        <p className="text-sm text-slate-400">
          Latest DQ batch health, freshness signals, and top blocking reasons.
        </p>
      </div>

      {loading && <div className="py-20 text-center text-slate-400">Loading DQ data...</div>}
      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6 text-red-300">
          Error: {error}
        </div>
      )}

      {!loading && !error && summary && (
        <>
          <div className={`mb-6 rounded-2xl border p-5 ${freshnessClassName}`}>
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm font-medium">Latest DQ batch</p>
                <p className="mt-1 text-xs opacity-90">
                  Checked at {summary.latest_checked_at ? new Date(summary.latest_checked_at).toLocaleString() : "-"}
                </p>
              </div>
              <div className="text-sm">
                Latest snapshot age: <span className="font-semibold">{formatAge(summary.snapshot_age_seconds)}</span>
              </div>
            </div>
          </div>

          <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Batch Size" value={summary.total_checks} />
            <StatCard label="Pass Rate" value={`${(summary.pass_rate * 100).toFixed(1)}%`} />
            <StatCard label="Pass" value={dist.pass ?? 0} sub="status = pass" />
            <StatCard label="Warn / Fail" value={`${dist.warn ?? 0} / ${dist.fail ?? 0}`} sub="warn / fail" />
          </div>

          {summary.total_checks > 0 && (
            <div className="mb-8 rounded-2xl border border-white/10 bg-white/5 p-5">
              <p className="mb-3 text-sm font-medium text-slate-300">Latest batch distribution</p>
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

          <div className="mb-8 rounded-2xl border border-white/10 bg-white/5 p-5">
            <p className="mb-3 text-sm font-medium text-slate-300">Top blocking reasons</p>
            {summary.top_blocking_reasons.length === 0 ? (
              <p className="text-sm text-slate-500">No blocking reasons in the latest batch.</p>
            ) : (
              <div className="flex flex-wrap gap-3">
                {summary.top_blocking_reasons.map((item) => (
                  <div key={item.reason_code} className="rounded-full border border-white/10 bg-black/20 px-3 py-1.5 text-sm text-slate-200">
                    {item.reason_code} <span className="ml-2 text-xs text-slate-400">{item.count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <h2 className="mb-4 text-lg font-medium text-white">Latest Batch Results</h2>
          <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 bg-white/5 text-left text-slate-400">
                  <th className="px-4 py-3 font-medium">Market</th>
                  <th className="px-4 py-3 font-medium">Checked At</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium hidden md:table-cell">Score</th>
                  <th className="px-4 py-3 font-medium hidden lg:table-cell">Failures</th>
                  <th className="px-4 py-3 font-medium hidden lg:table-cell">Reasons</th>
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
                  <tr key={result.id} className="border-b border-white/5 transition-colors hover:bg-white/5">
                    <td className="px-4 py-3 font-mono text-xs text-slate-300">
                      {result.market_id ?? result.market_ref_id.slice(0, 8)}
                    </td>
                    <td className="px-4 py-3 text-slate-300">
                      {new Date(result.checked_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={result.status} />
                    </td>
                    <td className="hidden px-4 py-3 text-slate-300 md:table-cell">
                      {result.score !== null ? result.score.toFixed(3) : "-"}
                    </td>
                    <td className="hidden px-4 py-3 text-slate-300 lg:table-cell">{result.failure_count}</td>
                    <td className="hidden px-4 py-3 text-xs text-slate-400 lg:table-cell">
                      {[...result.blocking_reason_codes, ...result.warning_reason_codes].slice(0, 3).join(", ") || "-"}
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
