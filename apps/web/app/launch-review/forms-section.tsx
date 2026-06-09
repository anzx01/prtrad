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
  suggestedShadowRunName,
  suggestedReviewTitle,
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
  suggestedShadowRunName: string
  suggestedReviewTitle: string
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
            <ConsoleField label="运行名称" hint={`可留空，系统会自动命名为 ${suggestedShadowRunName}`}>
              <ConsoleInput
                value={shadowForm.run_name}
                onChange={(event) => onShadowFormChange({ run_name: event.target.value })}
                placeholder={suggestedShadowRunName}
              />
            </ConsoleField>
            <ConsoleField label="执行人" hint="可选；留空时会记为系统执行。">
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
          description="这里尽量只保留必须确认的字段。评审标题可留空自动生成；如不指定 shadow，也会默认挂到最近一次。"
        >
          <form className="space-y-4" onSubmit={onCreateReview}>
            <ConsoleField label="评审标题" hint={`可留空，系统会自动命名为 ${suggestedReviewTitle}`}>
              <ConsoleInput
                value={reviewForm.title}
                onChange={(event) => onReviewFormChange({ title: event.target.value })}
                placeholder={suggestedReviewTitle}
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
              <ConsoleField label="申请人" hint="建议填写；如留空，会优先复用上面的执行人。">
                <ConsoleInput
                  value={reviewForm.requested_by}
                  onChange={(event) => onReviewFormChange({ requested_by: event.target.value })}
                  placeholder="可留空时复用上面的执行人"
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
