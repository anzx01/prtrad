import type { FormEventHandler } from "react"

import {
  ConsoleButton,
  ConsoleField,
  ConsoleInput,
  ConsolePanel,
  ConsoleSelect,
} from "../components/console-ui"

import { STAGE_OPTIONS, formatRecommendationLabel } from "./constants"
import type { ShadowRun } from "./types"

export function LaunchActionForms({
  shadowForm,
  reviewForm,
  shadowRuns,
  runningShadow,
  creatingReview,
  onShadowFormChange,
  onReviewFormChange,
  onRunShadow,
  onCreateReview,
}: {
  shadowForm: { run_name: string; executed_by: string }
  reviewForm: {
    title: string
    stage_name: (typeof STAGE_OPTIONS)[number]
    requested_by: string
    shadow_run_id: string
  }
  shadowRuns: ShadowRun[]
  runningShadow: boolean
  creatingReview: boolean
  onShadowFormChange: (patch: Partial<{ run_name: string; executed_by: string }>) => void
  onReviewFormChange: (
    patch: Partial<{
      title: string
      stage_name: (typeof STAGE_OPTIONS)[number]
      requested_by: string
      shadow_run_id: string
    }>,
  ) => void
  onRunShadow: FormEventHandler<HTMLFormElement>
  onCreateReview: FormEventHandler<HTMLFormElement>
}) {
  return (
    <section className="mt-6 grid gap-6 lg:grid-cols-2">
      <section id="shadow-form">
        <ConsolePanel
          className="bg-[#0d1117]"
          title="执行影子运行"
          description="先用 shadow run 确认当前风险状态和核心检查项，再决定是否进入正式评审。"
        >
          <form className="space-y-4" onSubmit={onRunShadow}>
            <ConsoleField label="运行名称">
              <ConsoleInput
                value={shadowForm.run_name}
                onChange={(event) => onShadowFormChange({ run_name: event.target.value })}
                placeholder="shadow-20260413"
              />
            </ConsoleField>
            <ConsoleField label="执行人">
              <ConsoleInput
                value={shadowForm.executed_by}
                onChange={(event) => onShadowFormChange({ executed_by: event.target.value })}
                placeholder="ops_lead"
              />
            </ConsoleField>
            <ConsoleButton type="submit" disabled={runningShadow} tone="primary">
              {runningShadow ? "执行中..." : "执行影子运行"}
            </ConsoleButton>
          </form>
        </ConsolePanel>
      </section>

      <section id="review-form">
        <ConsolePanel
          className="bg-[#0d1117]"
          title="创建上线评审"
          description="把当前阶段、申请人和关联的 shadow run 固定下来，形成一条可追溯的 Go/NoGo 决策记录。"
        >
          <form className="space-y-4" onSubmit={onCreateReview}>
            <ConsoleField label="评审标题">
              <ConsoleInput
                value={reviewForm.title}
                onChange={(event) => onReviewFormChange({ title: event.target.value })}
                placeholder="M6 上线准备评审"
              />
            </ConsoleField>
            <div className="grid gap-4 md:grid-cols-2">
              <ConsoleField label="阶段">
                <ConsoleSelect
                  value={reviewForm.stage_name}
                  onChange={(event) =>
                    onReviewFormChange({ stage_name: event.target.value as (typeof STAGE_OPTIONS)[number] })
                  }
                >
                  {STAGE_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </ConsoleSelect>
              </ConsoleField>
              <ConsoleField label="申请人">
                <ConsoleInput
                  value={reviewForm.requested_by}
                  onChange={(event) => onReviewFormChange({ requested_by: event.target.value })}
                  required
                />
              </ConsoleField>
            </div>
            <ConsoleField label="关联影子运行" hint="如不指定，将默认使用最近一次影子运行。">
              <ConsoleSelect
                value={reviewForm.shadow_run_id}
                onChange={(event) => onReviewFormChange({ shadow_run_id: event.target.value })}
              >
                <option value="">使用最近一次影子运行</option>
                {shadowRuns.map((run) => (
                  <option key={run.id} value={run.id}>
                    {run.run_name} / {formatRecommendationLabel(run.recommendation)}
                  </option>
                ))}
              </ConsoleSelect>
            </ConsoleField>
            <ConsoleButton type="submit" disabled={creatingReview} tone="primary">
              {creatingReview ? "创建中..." : "创建评审"}
            </ConsoleButton>
          </form>
        </ConsolePanel>
      </section>
    </section>
  )
}
