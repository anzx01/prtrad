"use client"

import { FormEvent, useEffect, useState } from "react"

import { apiGet, apiPost } from "@/lib/api"

interface ShadowRun {
  id: string
  run_name: string
  risk_state: string
  recommendation: "go" | "watch" | "block"
  executed_by: string | null
  summary: {
    exposure_summary?: {
      breached_clusters?: string[]
    }
  }
  checklist: Array<{ code: string; label: string; passed: boolean }>
  created_at: string
}

interface LaunchReview {
  id: string
  title: string
  stage_name: string
  shadow_run_id: string | null
  requested_by: string
  reviewed_by: string | null
  status: "pending" | "go" | "nogo"
  checklist: Array<{ code: string; label: string; passed: boolean }>
  evidence_summary: Record<string, unknown> | null
  review_notes: string | null
  decided_at: string | null
  created_at: string
}

function formatDate(value: string | null) {
  if (!value) {
    return "-"
  }
  return new Date(value).toLocaleString()
}

export default function LaunchReviewPage() {
  const [shadowRuns, setShadowRuns] = useState<ShadowRun[]>([])
  const [reviews, setReviews] = useState<LaunchReview[]>([])
  const [loading, setLoading] = useState(true)
  const [runningShadow, setRunningShadow] = useState(false)
  const [creatingReview, setCreatingReview] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [shadowForm, setShadowForm] = useState({ run_name: "", executed_by: "" })
  const [reviewForm, setReviewForm] = useState({ title: "", stage_name: "M6", requested_by: "", shadow_run_id: "" })

  const fetchAll = async () => {
    try {
      const [shadowData, reviewData] = await Promise.all([
        apiGet<{ runs: ShadowRun[] }>("/shadow"),
        apiGet<{ reviews: LaunchReview[] }>("/launch-review"),
      ])
      setShadowRuns(shadowData.runs)
      setReviews(reviewData.reviews)
      setError(null)
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Failed to load launch review data")
    } finally {
      setLoading(false)
      setRunningShadow(false)
      setCreatingReview(false)
    }
  }

  useEffect(() => {
    void fetchAll()
  }, [])

  const handleRunShadow = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setRunningShadow(true)
    setError(null)
    try {
      await apiPost("/shadow/execute", {
        run_name: shadowForm.run_name,
        executed_by: shadowForm.executed_by || null,
      })
      setShadowForm({ run_name: "", executed_by: "" })
      await fetchAll()
    } catch (runError) {
      setRunningShadow(false)
      setError(runError instanceof Error ? runError.message : "Failed to execute shadow run")
    }
  }

  const handleCreateReview = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setCreatingReview(true)
    setError(null)
    try {
      await apiPost("/launch-review", {
        title: reviewForm.title,
        stage_name: reviewForm.stage_name,
        requested_by: reviewForm.requested_by,
        shadow_run_id: reviewForm.shadow_run_id || null,
      })
      setReviewForm({ title: "", stage_name: "M6", requested_by: "", shadow_run_id: "" })
      await fetchAll()
    } catch (createError) {
      setCreatingReview(false)
      setError(createError instanceof Error ? createError.message : "Failed to create review")
    }
  }

  const handleDecision = async (reviewId: string, decision: "go" | "nogo") => {
    const reviewedBy = window.prompt("Reviewer ID")
    if (!reviewedBy) {
      return
    }
    const notes = window.prompt("Optional review notes") ?? ""
    setError(null)
    try {
      await apiPost(`/launch-review/${reviewId}/decide`, {
        decision,
        reviewed_by: reviewedBy,
        notes,
      })
      await fetchAll()
    } catch (decisionError) {
      setError(decisionError instanceof Error ? decisionError.message : "Failed to record decision")
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-8 lg:px-10">
      <section className="mb-8 rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur">
        <p className="text-sm uppercase tracking-[0.2em] text-sky-200">M6 Shadow Run & Launch Review</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Pre-launch gates and Go/NoGo review</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
          Run a shadow snapshot before launch, then create a review package with checklist evidence and a controlled Go/NoGo decision.
        </p>
      </section>

      {error ? (
        <div className="mb-6 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      <section className="mb-8 grid gap-6 lg:grid-cols-2">
        <article className="rounded-3xl border border-white/10 bg-slate-950/50 p-6">
          <h2 className="text-xl font-medium text-white">Execute shadow run</h2>
          <form className="mt-4 space-y-4" onSubmit={handleRunShadow}>
            <label className="block space-y-2">
              <span className="text-sm text-slate-300">Run name</span>
              <input
                value={shadowForm.run_name}
                onChange={(event) => setShadowForm((current) => ({ ...current, run_name: event.target.value }))}
                className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none"
                placeholder="shadow-20260410"
              />
            </label>
            <label className="block space-y-2">
              <span className="text-sm text-slate-300">Operator</span>
              <input
                value={shadowForm.executed_by}
                onChange={(event) => setShadowForm((current) => ({ ...current, executed_by: event.target.value }))}
                className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none"
                placeholder="ops_lead"
              />
            </label>
            <button
              type="submit"
              disabled={runningShadow}
              className="rounded-full border border-sky-400/40 bg-sky-500/10 px-5 py-2 text-sm text-sky-100 transition hover:bg-sky-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {runningShadow ? "Running..." : "Execute Shadow Run"}
            </button>
          </form>
        </article>

        <article className="rounded-3xl border border-white/10 bg-slate-950/50 p-6">
          <h2 className="text-xl font-medium text-white">Create launch review</h2>
          <form className="mt-4 space-y-4" onSubmit={handleCreateReview}>
            <label className="block space-y-2">
              <span className="text-sm text-slate-300">Title</span>
              <input
                value={reviewForm.title}
                onChange={(event) => setReviewForm((current) => ({ ...current, title: event.target.value }))}
                className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none"
                placeholder="M6 launch readiness review"
              />
            </label>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="block space-y-2">
                <span className="text-sm text-slate-300">Stage</span>
                <input
                  value={reviewForm.stage_name}
                  onChange={(event) => setReviewForm((current) => ({ ...current, stage_name: event.target.value }))}
                  className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none"
                />
              </label>
              <label className="block space-y-2">
                <span className="text-sm text-slate-300">Requested by</span>
                <input
                  value={reviewForm.requested_by}
                  onChange={(event) => setReviewForm((current) => ({ ...current, requested_by: event.target.value }))}
                  className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none"
                  required
                />
              </label>
            </div>
            <label className="block space-y-2">
              <span className="text-sm text-slate-300">Shadow run</span>
              <select
                value={reviewForm.shadow_run_id}
                onChange={(event) => setReviewForm((current) => ({ ...current, shadow_run_id: event.target.value }))}
                className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none"
              >
                <option value="">Use latest shadow run</option>
                {shadowRuns.map((run) => (
                  <option key={run.id} value={run.id}>
                    {run.run_name} · {run.recommendation}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="submit"
              disabled={creatingReview}
              className="rounded-full border border-sky-400/40 bg-sky-500/10 px-5 py-2 text-sm text-sky-100 transition hover:bg-sky-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {creatingReview ? "Creating..." : "Create Review"}
            </button>
          </form>
        </article>
      </section>

      <section className="mb-8 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-medium text-white">Recent shadow runs</h2>
          <span className="text-xs uppercase tracking-[0.2em] text-slate-400">{shadowRuns.length} runs</span>
        </div>
        {loading ? <p className="text-slate-300">Loading shadow runs...</p> : null}
        {!loading && shadowRuns.length === 0 ? (
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6 text-sm text-slate-400">
            No shadow runs yet.
          </div>
        ) : null}
        {shadowRuns.map((run) => (
          <article key={run.id} className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h3 className="text-lg font-medium text-white">{run.run_name}</h3>
                <p className="mt-1 text-sm text-slate-400">
                  {formatDate(run.created_at)} · risk state {run.risk_state}
                </p>
              </div>
              <span className={`rounded-full px-3 py-1 text-xs ${run.recommendation === "go" ? "bg-emerald-500/15 text-emerald-200" : run.recommendation === "watch" ? "bg-amber-500/15 text-amber-200" : "bg-rose-500/15 text-rose-200"}`}>
                {run.recommendation}
              </span>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {run.checklist.map((item) => (
                <div key={item.code} className="rounded-2xl border border-white/10 bg-slate-950/50 p-4 text-sm">
                  <p className="text-slate-200">{item.label}</p>
                  <p className={`mt-2 font-medium ${item.passed ? "text-emerald-300" : "text-rose-300"}`}>
                    {item.passed ? "Passed" : "Failed"}
                  </p>
                </div>
              ))}
            </div>
          </article>
        ))}
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-medium text-white">Launch reviews</h2>
          <span className="text-xs uppercase tracking-[0.2em] text-slate-400">{reviews.length} reviews</span>
        </div>
        {loading ? <p className="text-slate-300">Loading reviews...</p> : null}
        {!loading && reviews.length === 0 ? (
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6 text-sm text-slate-400">
            No launch reviews yet.
          </div>
        ) : null}
        {reviews.map((review) => (
          <article key={review.id} className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h3 className="text-lg font-medium text-white">{review.title}</h3>
                <p className="mt-1 text-sm text-slate-400">
                  {review.stage_name} · requested by {review.requested_by} · {formatDate(review.created_at)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className={`rounded-full px-3 py-1 text-xs ${review.status === "go" ? "bg-emerald-500/15 text-emerald-200" : review.status === "nogo" ? "bg-rose-500/15 text-rose-200" : "bg-amber-500/15 text-amber-200"}`}>
                  {review.status}
                </span>
                {review.status === "pending" ? (
                  <>
                    <button
                      type="button"
                      onClick={() => void handleDecision(review.id, "go")}
                      className="rounded-full border border-emerald-400/30 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-200"
                    >
                      Go
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDecision(review.id, "nogo")}
                      className="rounded-full border border-rose-400/30 bg-rose-500/10 px-3 py-1 text-xs text-rose-200"
                    >
                      NoGo
                    </button>
                  </>
                ) : null}
              </div>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {review.checklist.map((item) => (
                <div key={item.code} className="rounded-2xl border border-white/10 bg-slate-950/50 p-4 text-sm">
                  <p className="text-slate-200">{item.label}</p>
                  <p className={`mt-2 font-medium ${item.passed ? "text-emerald-300" : "text-rose-300"}`}>
                    {item.passed ? "Passed" : "Failed"}
                  </p>
                </div>
              ))}
            </div>

            <div className="mt-4 rounded-2xl border border-white/10 bg-slate-950/50 p-4 text-sm text-slate-300">
              <p>Reviewed by: {review.reviewed_by ?? "-"}</p>
              <p className="mt-1">Decision time: {formatDate(review.decided_at)}</p>
              <p className="mt-1">Notes: {review.review_notes ?? "-"}</p>
            </div>
          </article>
        ))}
      </section>
    </main>
  )
}
