"use client";

import { useEffect, useState, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Market {
  id: string;
  market_id: string;
  question: string;
  description: string | null;
  market_status: string | null;
  category_raw: string | null;
  close_time: string | null;
  created_at: string;
  updated_at: string;
}

interface MarketListResponse {
  markets: Market[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

const STATUS_COLORS: Record<string, string> = {
  active_accepting_orders: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  active_not_accepting_orders: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  closed: "bg-slate-500/20 text-slate-300 border-slate-500/30",
  resolved: "bg-blue-500/20 text-blue-300 border-blue-500/30",
};

function statusBadge(status: string | null) {
  if (!status) return null;
  const cls = STATUS_COLORS[status] ?? "bg-slate-500/20 text-slate-300 border-slate-500/30";
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs ${cls}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

export default function MarketsPage() {
  const [data, setData] = useState<MarketListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const fetchMarkets = useCallback(async () => {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({ page: String(page), page_size: "20" });
    if (search) params.set("search", search);
    if (statusFilter) params.set("status", statusFilter);

    try {
      const res = await fetch(`${API_BASE}/markets?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load markets");
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter]);

  useEffect(() => {
    fetchMarkets();
  }, [fetchMarkets]);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput);
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-10 lg:px-10">
      <div className="mb-8 space-y-1">
        <h1 className="text-3xl font-semibold text-white">Market Universe</h1>
        <p className="text-slate-400 text-sm">
          All ingested markets — filter by status or search by question text.
        </p>
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-wrap gap-3">
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search markets…"
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:border-sky-500/50 focus:outline-none"
          />
          <button
            type="submit"
            className="rounded-lg border border-sky-400/30 bg-sky-500/10 px-3 py-1.5 text-sm text-sky-200 hover:bg-sky-500/20 transition-colors"
          >
            Search
          </button>
          {(search || statusFilter) && (
            <button
              type="button"
              onClick={() => { setSearch(""); setSearchInput(""); setStatusFilter(""); setPage(1); }}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-slate-300 hover:bg-white/10 transition-colors"
            >
              Clear
            </button>
          )}
        </form>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="rounded-lg border border-white/10 bg-[#0c1724] px-3 py-1.5 text-sm text-slate-300 focus:border-sky-500/50 focus:outline-none"
        >
          <option value="">All statuses</option>
          <option value="active_accepting_orders">Active (accepting orders)</option>
          <option value="active_not_accepting_orders">Active (not accepting)</option>
          <option value="closed">Closed</option>
          <option value="resolved">Resolved</option>
        </select>
      </div>

      {/* Results info */}
      {data && (
        <p className="mb-4 text-sm text-slate-400">
          {data.total} market{data.total !== 1 ? "s" : ""} found — page {data.page}
        </p>
      )}

      {/* States */}
      {loading && (
        <div className="py-20 text-center text-slate-400">Loading markets…</div>
      )}
      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6 text-red-300">
          Error: {error}
        </div>
      )}

      {/* Table */}
      {!loading && !error && data && (
        <>
          <div className="rounded-2xl border border-white/10 bg-white/5 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 bg-white/5 text-left text-slate-400">
                  <th className="px-4 py-3 font-medium">Question</th>
                  <th className="px-4 py-3 font-medium hidden md:table-cell">Category</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium hidden lg:table-cell">Closes</th>
                </tr>
              </thead>
              <tbody>
                {data.markets.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-10 text-center text-slate-500">
                      No markets match the current filters.
                    </td>
                  </tr>
                )}
                {data.markets.map((market) => (
                  <tr
                    key={market.id}
                    className="border-b border-white/5 hover:bg-white/5 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <span
                        className="line-clamp-2 text-slate-100 leading-snug"
                        title={market.question}
                      >
                        {market.question}
                      </span>
                      <span className="mt-0.5 block text-xs text-slate-500">
                        {market.market_id}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell text-slate-400">
                      {market.category_raw ?? "—"}
                    </td>
                    <td className="px-4 py-3">
                      {statusBadge(market.market_status)}
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell text-slate-400">
                      {market.close_time
                        ? new Date(market.close_time).toLocaleDateString()
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="mt-4 flex items-center justify-between">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-slate-300 disabled:opacity-40 hover:bg-white/10 transition-colors"
            >
              ← Prev
            </button>
            <span className="text-sm text-slate-400">Page {page}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={!data.has_more}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-slate-300 disabled:opacity-40 hover:bg-white/10 transition-colors"
            >
              Next →
            </button>
          </div>
        </>
      )}
    </main>
  );
}
