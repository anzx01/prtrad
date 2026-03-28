const cards = [
  {
    title: "Web Console",
    body: "Next.js workspace is online and ready for Market Universe, review, calibration, and risk views."
  },
  {
    title: "API Service",
    body: "FastAPI will expose health, market, tagging, calibration, and audit endpoints from the same root project."
  },
  {
    title: "Worker Runtime",
    body: "Celery workers will own ingestion, DQ, calibration refresh, and reporting tasks."
  }
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#0f2744,transparent_45%),linear-gradient(180deg,#06101b,#0c1724)] text-slate-100">
      <section className="mx-auto flex min-h-screen max-w-6xl flex-col gap-12 px-6 py-12 lg:px-10">
        <header className="space-y-6">
          <p className="inline-flex rounded-full border border-sky-400/30 bg-sky-400/10 px-3 py-1 text-sm text-sky-200">
            Wave 1 scaffold
          </p>
          <div className="max-w-3xl space-y-4">
            <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
              Polymarket Tail Risk Control Console
            </h1>
            <p className="text-base leading-7 text-slate-300 sm:text-lg">
              This workspace is set up for research-first delivery: market
              ingestion, data quality, tagging, calibration, risk controls, and
              auditability.
            </p>
          </div>
        </header>

        <section className="grid gap-5 md:grid-cols-3">
          {cards.map((card) => (
            <article
              key={card.title}
              className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-[0_20px_80px_rgba(0,0,0,0.25)] backdrop-blur"
            >
              <h2 className="text-xl font-medium text-white">{card.title}</h2>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                {card.body}
              </p>
            </article>
          ))}
        </section>

        <section className="grid gap-6 rounded-3xl border border-white/10 bg-slate-950/40 p-6 lg:grid-cols-[1.3fr_0.7fr]">
          <div className="space-y-4">
            <h2 className="text-2xl font-medium text-white">
              Development starting point
            </h2>
            <ol className="space-y-3 text-sm leading-6 text-slate-300">
              <li>1. Run the bootstrap script to install Python and Node dependencies.</li>
              <li>2. Start the web, API, and worker processes from the root workspace.</li>
              <li>3. Continue with `PKG-DATA-01` and `PKG-PLAT-02` after scaffold verification.</li>
            </ol>
          </div>

          <div className="rounded-2xl border border-sky-300/20 bg-sky-500/10 p-5 text-sm text-sky-100">
            <p className="font-medium text-white">Local endpoints</p>
            <p className="mt-3">Web: http://localhost:3000</p>
            <p>API: http://localhost:8000</p>
            <p>API health: http://localhost:8000/health</p>
          </div>
        </section>
      </section>
    </main>
  );
}

