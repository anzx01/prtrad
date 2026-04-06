import Link from "next/link";

const navCards = [
  {
    title: "Market Universe",
    body: "Browse, filter and inspect all ingested Polymarket markets with status, category, and DQ signals.",
    href: "/markets",
    cta: "View Markets",
  },
  {
    title: "Data Quality",
    body: "Monitor data quality check results across markets — pass/warn/fail distribution and recent check history.",
    href: "/dq",
    cta: "View DQ Dashboard",
  },
  {
    title: "Tagging",
    body: "Inspect tag definitions and rule versions that drive market classification and admission decisions.",
    href: "/tagging",
    cta: "View Tagging",
  },
  {
    title: "Review Queue",
    body: "Manage review tasks for markets requiring manual approval or rejection decisions.",
    href: "/review",
    cta: "View Review Queue",
  },
  {
    title: "List Management",
    body: "Configure whitelist, graylist, and blacklist entries for market filtering and classification.",
    href: "/lists",
    cta: "Manage Lists",
  },
  {
    title: "Monitoring",
    body: "Track system health, task execution metrics, and alert status across all services.",
    href: "/monitoring",
    cta: "View Monitoring",
  },
  {
    title: "Tag Quality",
    body: "Monitor classification quality metrics, anomaly detection, and distribution trends.",
    href: "/tag-quality",
    cta: "View Quality Metrics",
  },
  {
    title: "Reports",
    body: "Generate and view M2 milestone reports with approval rates, rejection codes, and SLA metrics.",
    href: "/reports",
    cta: "View Reports",
  },
  {
    title: "Calibration",
    body: "View probability calibration units by price bucket, category, and time window. Manage active trading units.",
    href: "/calibration",
    cta: "View Calibration",
  },
  {
    title: "NetEV Admission",
    body: "Review net expected value admission decisions with cost breakdown: fee, slippage, and dispute discount.",
    href: "/netev",
    cta: "View NetEV",
  },
  {
    title: "Portfolio Risk",
    body: "Monitor risk cluster exposures, global risk state (Normal/Caution/RiskOff/Frozen), and kill-switch approvals.",
    href: "/risk",
    cta: "View Risk",
  },
];

export default function HomePage() {
  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-12 px-6 py-12 lg:px-10">
      <header className="space-y-4">
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
          Polymarket Tail Risk Control Console
        </h1>
        <p className="max-w-3xl text-base leading-7 text-slate-300 sm:text-lg">
          Market ingestion, data quality, tagging, calibration, risk controls,
          and auditability — all in one place.
        </p>
      </header>

      <section className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
        {navCards.map((card) => (
          <article
            key={card.title}
            className="flex flex-col justify-between rounded-3xl border border-white/10 bg-white/5 p-6 shadow-[0_20px_80px_rgba(0,0,0,0.25)] backdrop-blur"
          >
            <div>
              <h2 className="text-xl font-medium text-white">{card.title}</h2>
              <p className="mt-3 text-sm leading-6 text-slate-300">{card.body}</p>
            </div>
            <Link
              href={card.href}
              className="mt-6 inline-flex w-fit rounded-full border border-sky-400/40 bg-sky-500/10 px-4 py-1.5 text-sm text-sky-200 hover:bg-sky-500/20 transition-colors"
            >
              {card.cta} →
            </Link>
          </article>
        ))}
      </section>

      <section className="rounded-3xl border border-white/10 bg-slate-950/40 p-6">
        <div className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
          <div className="space-y-3">
            <h2 className="text-2xl font-medium text-white">Local endpoints</h2>
            <p className="text-sm text-slate-300">
              The API server must be running for the business pages to load live data.
            </p>
          </div>
          <div className="rounded-2xl border border-sky-300/20 bg-sky-500/10 p-5 text-sm text-sky-100 space-y-1">
            <p className="font-medium text-white">Addresses</p>
            <p>Web: http://localhost:3000</p>
            <p>API: http://localhost:8000</p>
            <p>Docs: http://localhost:8000/docs</p>
          </div>
        </div>
      </section>
    </main>
  );
}
