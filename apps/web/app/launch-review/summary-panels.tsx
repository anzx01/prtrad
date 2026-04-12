import { ConsoleBadge, ConsoleButton, ConsoleCallout, ConsoleInset, ConsolePanel } from "../components/console-ui"

import type { LaunchInsights, LaunchJumpTarget } from "./insights"

function toneLabel(tone: "info" | "good" | "warn" | "bad") {
  if (tone === "bad") {
    return "优先处理"
  }
  if (tone === "warn") {
    return "建议先看"
  }
  if (tone === "good") {
    return "可以推进"
  }
  return "建议动作"
}

export function LaunchSummaryPanels({
  insights,
  onJump,
}: {
  insights: LaunchInsights
  onJump: (target: LaunchJumpTarget) => void
}) {
  return (
    <section className="space-y-6">
      <ConsoleCallout
        eyebrow="当前判断"
        title={insights.headline.title}
        description={insights.headline.description}
        tone={insights.headline.tone}
        actions={
          <>
            {insights.headline.actions.map((action) => (
              <ConsoleButton
                key={`${action.target}-${action.label}`}
                type="button"
                size="sm"
                tone="primary"
                onClick={() => onJump(action.target)}
              >
                {action.label}
              </ConsoleButton>
            ))}
          </>
        }
      />

      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <ConsolePanel
          title="系统建议先看这里"
          description="这里不是字段说明，而是把当前更值得先做的动作按顺序排出来。"
        >
          <div className="space-y-3">
            {insights.priorities.map((priority) => (
              <ConsoleInset key={priority.id} className="space-y-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-[#e6edf3]">{priority.title}</p>
                    <p className="mt-2 text-sm leading-6 text-[#8b949e]">{priority.description}</p>
                  </div>
                  <ConsoleBadge label={toneLabel(priority.tone)} tone={priority.tone} />
                </div>
                {priority.badges && priority.badges.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {priority.badges.map((badge) => (
                      <ConsoleBadge key={badge} label={badge} tone={priority.tone === "bad" ? "warn" : priority.tone} />
                    ))}
                  </div>
                ) : null}
                <ConsoleButton type="button" size="sm" onClick={() => onJump(priority.target)}>
                  {priority.cta}
                </ConsoleButton>
              </ConsoleInset>
            ))}
          </div>
        </ConsolePanel>

        <ConsolePanel
          title={insights.blockerSummary.title}
          description={insights.blockerSummary.description}
        >
          {insights.blockerSummary.blockers.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {insights.blockerSummary.blockers.map((blocker) => (
                <ConsoleBadge key={blocker} label={blocker} tone={insights.blockerSummary.tone} />
              ))}
            </div>
          ) : (
            <ConsoleInset>
              <p className="text-sm leading-6 text-[#c9d1d9]">
                当前没有直接阻断 Go 的明显缺口。此时更重要的是把责任人、评审结论和说明记录完整。
              </p>
            </ConsoleInset>
          )}
        </ConsolePanel>
      </section>
    </section>
  )
}
