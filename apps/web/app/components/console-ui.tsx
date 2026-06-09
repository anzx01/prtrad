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
  neutral:
    "border-[color:rgba(63,47,34,0.12)] bg-[color:rgba(255,252,247,0.72)] text-[color:var(--oa-muted)]",
  info:
    "border-[color:rgba(33,95,141,0.18)] bg-[color:rgba(33,95,141,0.09)] text-[color:var(--oa-blue)]",
  good:
    "border-[color:rgba(47,125,81,0.2)] bg-[color:rgba(47,125,81,0.1)] text-[color:var(--oa-green)]",
  warn:
    "border-[color:rgba(155,106,36,0.2)] bg-[color:rgba(155,106,36,0.1)] text-[color:var(--oa-gold)]",
  bad:
    "border-[color:rgba(177,63,51,0.2)] bg-[color:rgba(177,63,51,0.1)] text-[color:var(--oa-red)]",
}

const BUTTON_TONE_CLASS = {
  default:
    "border-[color:var(--oa-border-strong)] bg-[color:rgba(255,251,246,0.8)] text-[color:var(--oa-text)] shadow-[0_10px_24px_rgba(56,39,24,0.08)] hover:-translate-y-0.5 hover:border-[color:rgba(63,47,34,0.26)] hover:bg-[color:rgba(255,255,255,0.95)]",
  primary:
    "border-[color:rgba(181,72,47,0.28)] bg-[linear-gradient(135deg,rgba(181,72,47,0.18),rgba(255,255,255,0.96))] text-[color:var(--oa-text)] shadow-[0_14px_30px_rgba(123,56,33,0.12)] hover:-translate-y-0.5 hover:border-[color:rgba(181,72,47,0.44)] hover:bg-[linear-gradient(135deg,rgba(181,72,47,0.24),rgba(255,255,255,1))]",
  success:
    "border-[color:rgba(47,125,81,0.24)] bg-[linear-gradient(135deg,rgba(47,125,81,0.16),rgba(255,255,255,0.96))] text-[color:var(--oa-text)] shadow-[0_14px_30px_rgba(47,125,81,0.1)] hover:-translate-y-0.5 hover:border-[color:rgba(47,125,81,0.36)] hover:bg-[linear-gradient(135deg,rgba(47,125,81,0.22),rgba(255,255,255,1))]",
  danger:
    "border-[color:rgba(177,63,51,0.24)] bg-[linear-gradient(135deg,rgba(177,63,51,0.16),rgba(255,255,255,0.96))] text-[color:var(--oa-text)] shadow-[0_14px_30px_rgba(177,63,51,0.1)] hover:-translate-y-0.5 hover:border-[color:rgba(177,63,51,0.36)] hover:bg-[linear-gradient(135deg,rgba(177,63,51,0.22),rgba(255,255,255,1))]",
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
    <section
      className={cx(
        "overflow-hidden rounded-[28px] border border-[color:var(--oa-border)] bg-[linear-gradient(180deg,rgba(255,253,248,0.96),rgba(255,248,239,0.9))] shadow-[0_24px_60px_rgba(52,34,20,0.08)]",
        className,
      )}
    >
      {hasHeader ? (
        <div className="flex flex-col gap-4 border-b border-[color:var(--oa-border)] px-5 py-5 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            {title ? (
              <h2 className="text-lg font-semibold tracking-tight text-[color:var(--oa-text)] [font-family:var(--oa-font-display)]">
                {title}
              </h2>
            ) : null}
            {description ? (
              <p className="mt-1 max-w-3xl text-sm leading-6 text-[color:var(--oa-muted)]">{description}</p>
            ) : null}
          </div>
          {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
        </div>
      ) : null}
      <div className={cx("min-w-0 px-5 py-5", bodyClassName)}>{children}</div>
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
    <div
      className={cx(
        "rounded-[22px] border border-[color:rgba(63,47,34,0.12)] bg-[linear-gradient(180deg,rgba(255,255,255,0.9),rgba(247,239,229,0.72))] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.5)]",
        className,
      )}
    >
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
        "relative overflow-hidden",
        tone === "good" && "border-[color:rgba(47,125,81,0.18)]",
        tone === "warn" && "border-[color:rgba(155,106,36,0.18)]",
        tone === "bad" && "border-[color:rgba(177,63,51,0.18)]",
        tone === "info" && "border-[color:rgba(33,95,141,0.18)]",
      )}
    >
      <div
        className={cx(
          "absolute inset-x-0 top-0 h-1",
          tone === "good" && "bg-[linear-gradient(90deg,rgba(47,125,81,0.75),rgba(47,125,81,0.12))]",
          tone === "warn" && "bg-[linear-gradient(90deg,rgba(155,106,36,0.75),rgba(155,106,36,0.12))]",
          tone === "bad" && "bg-[linear-gradient(90deg,rgba(177,63,51,0.75),rgba(177,63,51,0.12))]",
          tone === "info" && "bg-[linear-gradient(90deg,rgba(33,95,141,0.75),rgba(33,95,141,0.12))]",
          tone === "neutral" && "bg-[linear-gradient(90deg,rgba(91,68,48,0.4),rgba(91,68,48,0.06))]",
        )}
      />
      <p className="text-[11px] uppercase tracking-[0.22em] text-[color:var(--oa-muted)]">{label}</p>
      <p className="mt-3 text-4xl font-semibold tracking-tight text-[color:var(--oa-text)] [font-family:var(--oa-font-display)] md:text-[2.6rem]">
        {value}
      </p>
      {hint ? <p className="mt-3 text-xs leading-5 text-[color:var(--oa-muted)]">{hint}</p> : null}
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
        "inline-flex max-w-full items-center rounded-full border px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.16em] break-all",
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
      ? "border-[color:rgba(47,125,81,0.2)] bg-[linear-gradient(135deg,rgba(47,125,81,0.14),rgba(255,251,245,0.94))]"
      : tone === "warn"
        ? "border-[color:rgba(155,106,36,0.2)] bg-[linear-gradient(135deg,rgba(155,106,36,0.14),rgba(255,251,245,0.94))]"
        : tone === "bad"
          ? "border-[color:rgba(177,63,51,0.2)] bg-[linear-gradient(135deg,rgba(177,63,51,0.14),rgba(255,251,245,0.94))]"
          : tone === "info"
            ? "border-[color:rgba(33,95,141,0.2)] bg-[linear-gradient(135deg,rgba(33,95,141,0.14),rgba(255,251,245,0.94))]"
            : "border-[color:var(--oa-border)] bg-[linear-gradient(135deg,rgba(255,255,255,0.94),rgba(247,239,229,0.88))]"

  return (
    <section className={cx("rounded-[28px] border px-5 py-5 shadow-[0_20px_44px_rgba(52,34,20,0.06)]", toneClass)}>
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          {eyebrow ? (
            <p className="text-[11px] uppercase tracking-[0.22em] text-[color:var(--oa-muted)]">{eyebrow}</p>
          ) : null}
          <h3 className="mt-1 text-[1.55rem] font-semibold leading-tight text-[color:var(--oa-text)] [font-family:var(--oa-font-display)] md:text-[1.8rem]">
            {title}
          </h3>
          <p className="mt-3 max-w-4xl text-sm leading-7 text-[color:var(--oa-muted)] md:text-[15px]">
            {description}
          </p>
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
        "inline-flex items-center justify-center rounded-full border font-medium transition duration-200 disabled:cursor-not-allowed disabled:opacity-55",
        size === "sm" ? "px-3.5 py-2 text-sm" : "px-5 py-3 text-sm",
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
      <span className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--oa-muted)]">{label}</span>
      {children}
      {hint ? <span className="block text-xs leading-5 text-[color:var(--oa-muted)]">{hint}</span> : null}
    </label>
  )
}

export function ConsoleInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={cx(
        "w-full rounded-full border border-[color:var(--oa-border)] bg-[rgba(255,253,249,0.88)] px-4 py-3 text-sm text-[color:var(--oa-text)] outline-none transition placeholder:text-[color:rgba(29,24,20,0.42)] focus:border-[color:rgba(181,72,47,0.34)] focus:bg-white",
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
        "w-full rounded-full border border-[color:var(--oa-border)] bg-[rgba(255,253,249,0.88)] px-4 py-3 text-sm text-[color:var(--oa-text)] outline-none transition focus:border-[color:rgba(181,72,47,0.34)] focus:bg-white",
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
        "w-full rounded-[22px] border border-[color:var(--oa-border)] bg-[rgba(255,253,249,0.88)] px-4 py-3 text-sm text-[color:var(--oa-text)] outline-none transition placeholder:text-[color:rgba(29,24,20,0.42)] focus:border-[color:rgba(181,72,47,0.34)] focus:bg-white",
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
    <ConsoleInset className="py-12 text-center">
      <p className="text-base font-semibold text-[color:var(--oa-text)] [font-family:var(--oa-font-display)]">
        {title}
      </p>
      <p className="mx-auto mt-2 max-w-2xl text-sm leading-7 text-[color:var(--oa-muted)]">{description}</p>
    </ConsoleInset>
  )
}
