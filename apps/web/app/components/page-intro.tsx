interface GuideItem {
  title: string
  description: string
}

interface PageStat {
  label: string
  value: string
}

interface PageIntroProps {
  eyebrow: string
  title: string
  description: string
  guides?: GuideItem[]
  stats?: PageStat[]
}

export function PageIntro({
  eyebrow,
  title,
  description,
  guides = [],
  stats = [],
}: PageIntroProps) {
  return (
    <header className="mb-6 border-b border-[#30363d] pb-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <p className="text-[11px] uppercase tracking-[0.2em] text-[#8b949e]">{eyebrow}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[#e6edf3] md:text-[30px]">
            {title}
          </h1>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-[#8b949e]">{description}</p>
        </div>
        {stats.length > 0 ? (
          <div className="grid gap-2 sm:grid-cols-2 lg:min-w-[320px] lg:grid-cols-1">
            {stats.map((stat) => (
              <div
                key={stat.label}
                className="rounded-lg border border-[#30363d] bg-[#161b22] px-4 py-3"
              >
                <p className="text-[11px] uppercase tracking-[0.18em] text-[#8b949e]">{stat.label}</p>
                <p className="mt-1 text-xl font-semibold text-[#e6edf3]">{stat.value}</p>
              </div>
            ))}
          </div>
        ) : null}
      </div>

      {guides.length > 0 ? (
        <section className="mt-5 grid gap-3 md:grid-cols-3">
          {guides.map((guide) => (
            <article
              key={guide.title}
              className="rounded-lg border border-[#30363d] bg-[#161b22] p-4"
            >
              <p className="text-sm font-medium text-[#e6edf3]">{guide.title}</p>
              <p className="mt-2 text-sm leading-6 text-[#8b949e]">{guide.description}</p>
            </article>
          ))}
        </section>
      ) : null}
    </header>
  )
}

export function SoftPanel({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children: React.ReactNode
}) {
  return (
    <section className="rounded-xl border border-[#30363d] bg-[#161b22]">
      <div className="border-b border-[#30363d] px-5 py-4">
        <h2 className="text-lg font-medium text-[#e6edf3]">{title}</h2>
        {description ? <p className="mt-2 text-sm leading-6 text-[#8b949e]">{description}</p> : null}
      </div>
      <div className="px-5 py-4">{children}</div>
    </section>
  )
}
