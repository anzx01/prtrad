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
    <header className="mb-8 space-y-5">
      <div className="grid gap-5 xl:grid-cols-[1.25fr_0.75fr]">
        <section className="relative overflow-hidden rounded-[34px] border border-[color:var(--oa-border)] bg-[linear-gradient(145deg,rgba(255,253,249,0.96),rgba(246,235,222,0.86))] px-6 py-7 shadow-[0_28px_70px_rgba(49,31,20,0.08)] md:px-8 md:py-9">
          <div className="absolute -right-10 top-0 h-36 w-36 rounded-full bg-[radial-gradient(circle,rgba(181,72,47,0.18),transparent_68%)] soft-float" />
          <div className="absolute bottom-0 right-10 h-24 w-24 rounded-full bg-[radial-gradient(circle,rgba(33,95,141,0.12),transparent_70%)]" />

          <div className="relative z-10 max-w-4xl">
            <p className="text-[11px] uppercase tracking-[0.24em] text-[color:var(--oa-muted)]">{eyebrow}</p>
            <h1 className="mt-3 text-[2.3rem] font-semibold leading-[1.04] tracking-tight text-[color:var(--oa-text)] [font-family:var(--oa-font-display)] md:text-[3.6rem]">
              {title}
            </h1>
            <p className="mt-4 max-w-3xl text-[15px] leading-8 text-[color:var(--oa-muted)] md:text-[17px]">
              {description}
            </p>

            <div className="mt-6 flex flex-wrap gap-3">
              <span className="rounded-full border border-[color:rgba(181,72,47,0.16)] bg-[color:rgba(181,72,47,0.08)] px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.18em] text-[color:var(--oa-accent-strong)]">
                自动判断优先
              </span>
              <span className="rounded-full border border-[color:rgba(33,95,141,0.14)] bg-[color:rgba(33,95,141,0.08)] px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.18em] text-[color:var(--oa-blue)]">
                单页完成闭环
              </span>
              <span className="rounded-full border border-[color:rgba(47,125,81,0.14)] bg-[color:rgba(47,125,81,0.08)] px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.18em] text-[color:var(--oa-green)]">
                小白友好
              </span>
            </div>
          </div>
        </section>

        {stats.length > 0 ? (
          <section className="grid gap-3">
            {stats.map((stat) => (
              <article
                key={stat.label}
                className="rounded-[26px] border border-[color:var(--oa-border)] bg-[linear-gradient(180deg,rgba(255,255,255,0.94),rgba(247,239,229,0.82))] px-5 py-5 shadow-[0_18px_44px_rgba(49,31,20,0.06)]"
              >
                <p className="text-[11px] uppercase tracking-[0.2em] text-[color:var(--oa-muted)]">{stat.label}</p>
                <p className="mt-3 text-[2.15rem] font-semibold tracking-tight text-[color:var(--oa-text)] [font-family:var(--oa-font-display)]">
                  {stat.value}
                </p>
              </article>
            ))}
          </section>
        ) : null}
      </div>

      {guides.length > 0 ? (
        <section className="grid gap-3 md:grid-cols-3">
          {guides.map((guide, index) => (
            <article
              key={guide.title}
              className="rounded-[24px] border border-[color:var(--oa-border)] bg-[rgba(255,251,246,0.82)] p-5 shadow-[0_14px_34px_rgba(49,31,20,0.05)]"
            >
              <div className="flex items-center gap-3">
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-[color:rgba(181,72,47,0.16)] bg-[color:rgba(181,72,47,0.08)] text-sm font-semibold text-[color:var(--oa-accent-strong)]">
                  0{index + 1}
                </span>
                <p className="text-base font-semibold tracking-tight text-[color:var(--oa-text)] [font-family:var(--oa-font-display)]">
                  {guide.title}
                </p>
              </div>
              <p className="mt-3 text-sm leading-7 text-[color:var(--oa-muted)]">{guide.description}</p>
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
    <section className="rounded-[28px] border border-[color:var(--oa-border)] bg-[linear-gradient(180deg,rgba(255,253,248,0.95),rgba(247,239,229,0.84))] shadow-[0_22px_52px_rgba(49,31,20,0.07)]">
      <div className="border-b border-[color:var(--oa-border)] px-5 py-5">
        <h2 className="text-lg font-semibold text-[color:var(--oa-text)] [font-family:var(--oa-font-display)]">
          {title}
        </h2>
        {description ? <p className="mt-2 text-sm leading-7 text-[color:var(--oa-muted)]">{description}</p> : null}
      </div>
      <div className="px-5 py-5">{children}</div>
    </section>
  )
}
