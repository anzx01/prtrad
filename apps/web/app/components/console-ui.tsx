import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react"

function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ")
}

type Tone = "neutral" | "info" | "good" | "warn" | "bad"

const BADGE_TONE_CLASS: Record<Tone, string> = {
  neutral: "border-[#30363d] bg-[#21262d] text-[#8b949e]",
  info: "border-[#58a6ff]/40 bg-[#1f6feb]/15 text-[#c9d1d9]",
  good: "border-[#3fb950]/35 bg-[#238636]/15 text-[#c9f0d1]",
  warn: "border-[#d29922]/35 bg-[#9e6a03]/15 text-[#f2cc60]",
  bad: "border-[#f85149]/35 bg-[#da3633]/15 text-[#ffd8d3]",
}

const BUTTON_TONE_CLASS = {
  default:
    "border-[#30363d] bg-[#161b22] text-[#c9d1d9] hover:border-[#58a6ff]/35 hover:bg-[#21262d]",
  primary:
    "border-[#58a6ff]/40 bg-[#1f6feb]/15 text-[#e6edf3] hover:border-[#58a6ff]/60 hover:bg-[#1f6feb]/22",
  success:
    "border-[#3fb950]/35 bg-[#238636]/15 text-[#d7f7dd] hover:border-[#3fb950]/55 hover:bg-[#238636]/22",
  danger:
    "border-[#f85149]/35 bg-[#da3633]/15 text-[#ffe2df] hover:border-[#f85149]/55 hover:bg-[#da3633]/22",
} as const

export function ConsolePanel({
  title,
  description,
  actions,
  children,
  className,
  bodyClassName,
}: {
  title?: string
  description?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
  bodyClassName?: string
}) {
  const hasHeader = title || description || actions

  return (
    <section className={cx("rounded-xl border border-[#30363d] bg-[#161b22]", className)}>
      {hasHeader ? (
        <div className="flex flex-col gap-4 border-b border-[#30363d] px-5 py-4 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            {title ? <h2 className="text-base font-semibold text-[#e6edf3]">{title}</h2> : null}
            {description ? (
              <p className="mt-1 max-w-3xl text-sm leading-6 text-[#8b949e]">{description}</p>
            ) : null}
          </div>
          {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
        </div>
      ) : null}
      <div className={cx("min-w-0 px-5 py-4", bodyClassName)}>{children}</div>
    </section>
  )
}

export function ConsoleInset({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cx("rounded-lg border border-[#30363d] bg-[#0d1117] p-4", className)}>
      {children}
    </div>
  )
}

export function ConsoleMetric({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string
  value: string
  hint?: string
  tone?: Tone
}) {
  return (
    <ConsoleInset
      className={cx(
        "space-y-2",
        tone === "good" && "border-[#3fb950]/25",
        tone === "warn" && "border-[#d29922]/25",
        tone === "bad" && "border-[#f85149]/25",
        tone === "info" && "border-[#58a6ff]/25",
      )}
    >
      <p className="text-[11px] uppercase tracking-[0.2em] text-[#8b949e]">{label}</p>
      <p className="text-3xl font-semibold tracking-tight text-[#e6edf3]">{value}</p>
      {hint ? <p className="text-xs leading-5 text-[#8b949e]">{hint}</p> : null}
    </ConsoleInset>
  )
}

export function ConsoleBadge({
  label,
  tone = "neutral",
  className,
}: {
  label: string
  tone?: Tone
  className?: string
}) {
  return (
    <span
      className={cx(
        "inline-flex max-w-full items-center rounded-md border px-2.5 py-1 text-[11px] uppercase tracking-[0.14em] break-all",
        BADGE_TONE_CLASS[tone],
        className,
      )}
    >
      {label}
    </span>
  )
}

export function ConsoleCallout({
  eyebrow,
  title,
  description,
  tone = "neutral",
  actions,
}: {
  eyebrow?: string
  title: string
  description: string
  tone?: Tone
  actions?: ReactNode
}) {
  const toneClass =
    tone === "good"
      ? "border-[#3fb950]/30 bg-[#238636]/12"
      : tone === "warn"
        ? "border-[#d29922]/30 bg-[#9e6a03]/12"
        : tone === "bad"
          ? "border-[#f85149]/30 bg-[#da3633]/12"
          : tone === "info"
            ? "border-[#58a6ff]/30 bg-[#1f6feb]/12"
            : "border-[#30363d] bg-[#161b22]"

  return (
    <section className={cx("rounded-xl border px-5 py-4", toneClass)}>
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          {eyebrow ? (
            <p className="text-[11px] uppercase tracking-[0.2em] text-[#8b949e]">{eyebrow}</p>
          ) : null}
          <h3 className="mt-1 text-lg font-semibold text-[#e6edf3]">{title}</h3>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-[#c9d1d9]">{description}</p>
        </div>
        {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
      </div>
    </section>
  )
}

export function ConsoleButton({
  className,
  tone = "default",
  size = "md",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  tone?: keyof typeof BUTTON_TONE_CLASS
  size?: "sm" | "md"
}) {
  return (
    <button
      {...props}
      className={cx(
        "inline-flex items-center justify-center rounded-lg border font-medium transition disabled:cursor-not-allowed disabled:opacity-55",
        size === "sm" ? "px-3 py-2 text-sm" : "px-4 py-2.5 text-sm",
        BUTTON_TONE_CLASS[tone],
        className,
      )}
    />
  )
}

export function ConsoleField({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: ReactNode
}) {
  return (
    <label className="block space-y-2">
      <span className="text-[11px] uppercase tracking-[0.18em] text-[#8b949e]">{label}</span>
      {children}
      {hint ? <span className="block text-xs leading-5 text-[#8b949e]">{hint}</span> : null}
    </label>
  )
}

export function ConsoleInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={cx(
        "w-full rounded-lg border border-[#30363d] bg-[#0d1117] px-3.5 py-3 text-sm text-[#e6edf3] outline-none transition placeholder:text-[#6e7681] focus:border-[#58a6ff]/45",
        props.className,
      )}
    />
  )
}

export function ConsoleSelect(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={cx(
        "w-full rounded-lg border border-[#30363d] bg-[#0d1117] px-3.5 py-3 text-sm text-[#e6edf3] outline-none transition focus:border-[#58a6ff]/45",
        props.className,
      )}
    />
  )
}

export function ConsoleTextarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={cx(
        "w-full rounded-lg border border-[#30363d] bg-[#0d1117] px-3.5 py-3 text-sm text-[#e6edf3] outline-none transition placeholder:text-[#6e7681] focus:border-[#58a6ff]/45",
        props.className,
      )}
    />
  )
}

export function ConsoleEmpty({
  title,
  description,
}: {
  title: string
  description: string
}) {
  return (
    <ConsoleInset className="py-10 text-center">
      <p className="text-sm font-medium text-[#e6edf3]">{title}</p>
      <p className="mx-auto mt-2 max-w-2xl text-sm leading-6 text-[#8b949e]">{description}</p>
    </ConsoleInset>
  )
}
