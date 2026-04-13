import { ConsoleCallout, ConsoleInset } from "../components/console-ui"
import { describeReport } from "./report-insights"
import { type ReportRecord } from "./report-primitives"

export function ReportSummaryBanner({ report }: { report: ReportRecord }) {
  const insight = describeReport(report)

  return (
    <>
      <ConsoleCallout
        eyebrow="一句话结论"
        title={insight.title}
        description={insight.detail}
        tone={insight.tone === "neutral" ? "info" : insight.tone}
      />
      {insight.hints.length > 0 ? (
        <ConsoleInset className="mt-3">
          <p className="console-kicker">阅读提示</p>
          <div className="mt-3 space-y-2">
            {insight.hints.map((hint) => (
              <p key={hint} className="text-sm leading-6 text-[#c9d1d9]">
                {hint}
              </p>
            ))}
          </div>
        </ConsoleInset>
      ) : null}
    </>
  )
}
