import { ConsoleButton, ConsolePanel } from "../components/console-ui"
import { toneToClass } from "./dashboard-sections"
import type { ActionId, DashboardTone } from "./types"

export function ActionPanels({
  actionFeed,
  refreshing,
  runningActionId,
  onAction,
}: {
  actionFeed: Array<{ id: string; tone: DashboardTone; message: string }>
  refreshing: boolean
  runningActionId: ActionId | null
  onAction: (actionId: ActionId) => void
}) {
  return (
    <section className="mt-6 grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
      <ConsolePanel title="一键推进中心" description="把最常用的自动化动作集中在一起，减少你在各个页面间来回跳。">
        <div className="flex flex-wrap gap-2">
          {([
            ["refreshEvidencePack", "一键刷新证据包"],
            ["recomputeRisk", "重算风险暴露"],
            ["recomputeCalibration", "重算长窗口校准"],
            ["runBacktest", "运行回测"],
            ["runShadow", "运行影子"],
            ["generateDaily", "生成日报"],
            ["generateWeekly", "生成周报"],
            ["generateStageBundle", "生成 M4-M6"],
          ] as Array<[ActionId, string]>).map(([actionId, label]) => (
            <ConsoleButton
              key={actionId}
              type="button"
              tone={actionId === "refreshEvidencePack" ? "primary" : "default"}
              disabled={refreshing || runningActionId !== null}
              onClick={() => onAction(actionId)}
            >
              {runningActionId === actionId ? "执行中..." : label}
            </ConsoleButton>
          ))}
        </div>
        <div className="mt-4 text-sm leading-6 text-[#8b949e]">
          人工审核这类必须人来判断的动作不会被偷偷自动化，但系统会明确把它标出来，不再要求你自己先学会整套流程。
        </div>
      </ConsolePanel>

      <ConsolePanel title="自动化动作日志" description="让每一步都可见，避免“点了没反应”这类不确定感。">
        {actionFeed.length === 0 ? (
          <div className="rounded-xl border border-[#30363d] bg-[#0d1117] p-4 text-sm text-[#8b949e]">
            还没有执行自动化动作。点击左侧任意按钮后，这里会滚动显示系统已经做了什么。
          </div>
        ) : (
          <div className="space-y-2">
            {actionFeed.map((item) => (
              <div key={item.id} className={`rounded-lg border px-4 py-3 text-sm ${toneToClass(item.tone)}`}>
                {item.message}
              </div>
            ))}
          </div>
        )}
      </ConsolePanel>
    </section>
  )
}
