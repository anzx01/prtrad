import type { FormEventHandler, ReactNode } from "react"

import {
  ConsoleBadge,
  ConsoleButton,
  ConsoleEmpty,
  ConsoleInput,
  ConsolePanel,
  ConsoleSelect,
  ConsoleTextarea,
} from "../components/console-ui"
import {
  formatKillSwitchTypeLabel,
  formatReviewStatusLabel,
} from "./constants"
import type { KillSwitchFormState, KillSwitchItem, KillSwitchReviewDraft, ReviewAction } from "./types"

function formatDate(value: string): string {
  return new Date(value).toLocaleString()
}

function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-[#8b949e]">{label}</span>
      {children}
      {hint ? <span className="mt-2 block text-xs leading-5 text-[#8b949e]">{hint}</span> : null}
    </label>
  )
}

function ActionButton({
  label,
  tone,
  onClick,
}: {
  label: string
  tone: ReviewAction
  onClick: () => void
}) {
  return (
    <ConsoleButton onClick={onClick} type="button" tone={tone === "approve" ? "success" : "danger"} size="sm">
      {label}
    </ConsoleButton>
  )
}

interface KillSwitchSectionProps {
  killSwitchForm: KillSwitchFormState
  suggestedReason: string
  pendingRequests: KillSwitchItem[]
  submitting: boolean
  reviewDraft: KillSwitchReviewDraft | null
  reviewSubmitting: boolean
  onSubmit: FormEventHandler<HTMLFormElement>
  onFormChange: (patch: Partial<KillSwitchFormState>) => void
  onUseSuggestedReason: () => void
  onReviewStart: (request: KillSwitchItem, action: ReviewAction) => void
  onReviewDraftChange: (patch: Partial<Pick<KillSwitchReviewDraft, "reviewer" | "notes">>) => void
  onReviewSubmit: FormEventHandler<HTMLFormElement>
  onReviewCancel: () => void
}

export function KillSwitchSection({
  killSwitchForm,
  suggestedReason,
  pendingRequests,
  submitting,
  reviewDraft,
  reviewSubmitting,
  onSubmit,
  onFormChange,
  onUseSuggestedReason,
  onReviewStart,
  onReviewDraftChange,
  onReviewSubmit,
  onReviewCancel,
}: KillSwitchSectionProps) {
  return (
    <section className="grid gap-6 lg:grid-cols-2">
      <section id="kill-switch-form">
        <ConsolePanel title="提交人工风险动作" description="只有在系统已经提示需要人工接管时，才建议来这里提交请求。">
          <form onSubmit={onSubmit} className="space-y-4">
          <Field label="请求类型">
            <ConsoleSelect
              value={killSwitchForm.request_type}
              onChange={(event) => onFormChange({ request_type: event.target.value })}
            >
              <option value="risk_off">切到 RiskOff</option>
              <option value="freeze">冻结交易</option>
              <option value="unfreeze">解除冻结</option>
            </ConsoleSelect>
          </Field>

          <Field label="目标范围" hint="通常填 global；只有明确知道具体簇时，才填 cluster code。">
            <ConsoleInput
              value={killSwitchForm.target_scope}
              onChange={(event) => onFormChange({ target_scope: event.target.value })}
              placeholder="global 或具体 cluster code"
              required
            />
          </Field>

          <Field label="申请人">
            <ConsoleInput
              value={killSwitchForm.requested_by}
              onChange={(event) => onFormChange({ requested_by: event.target.value })}
              placeholder="ops_user"
              required
            />
          </Field>

          <Field label="原因" hint="不想自己组织措辞时，可直接使用系统建议原因。">
            <ConsoleTextarea
              value={killSwitchForm.reason}
              onChange={(event) => onFormChange({ reason: event.target.value })}
              placeholder="说明为什么需要这个动作"
              rows={4}
              required
            />
          </Field>

          <div className="flex flex-wrap gap-2">
            <ConsoleButton type="button" onClick={onUseSuggestedReason} size="sm">
              使用系统建议原因
            </ConsoleButton>
            <ConsoleButton
              type="submit"
              disabled={submitting}
              tone="danger"
            >
              {submitting ? "提交中..." : "提交请求"}
            </ConsoleButton>
          </div>
          <div className="rounded-xl border border-[#58a6ff]/25 bg-[#1f6feb]/10 p-4 text-sm text-[#c9d1d9]">
            <p className="font-medium text-[#e6edf3]">系统建议原因</p>
            <p className="mt-2 leading-6">{suggestedReason}</p>
          </div>
          </form>
        </ConsolePanel>
      </section>

      <section id="kill-switch-pending">
        <ConsolePanel title="待审批请求" description="不要再用弹窗逐个输 ID；在卡片里直接确认审批人和备注即可。">
        {pendingRequests.length === 0 ? (
          <ConsoleEmpty title="当前没有待审批 kill-switch 请求" description="如果这里为空，说明目前没有挂起的人工风险动作。" />
        ) : (
          <div className="space-y-3">
            {pendingRequests.map((request) => (
              <div key={request.id} className="rounded-xl border border-[#d29922]/30 bg-[#9e6a03]/12 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="text-sm font-medium text-[#e6edf3]">{formatKillSwitchTypeLabel(request.request_type)}</div>
                    <div className="mt-1 text-xs text-[#8b949e]">
                      {request.target_scope} / 申请人 {request.requested_by}
                    </div>
                    <p className="mt-2 text-sm text-[#c9d1d9]">{request.reason}</p>
                  </div>
                  <ConsoleBadge label="待审批" tone="warn" />
                </div>
                <div className="mt-4 flex gap-2">
                  <ActionButton label="批准" tone="approve" onClick={() => onReviewStart(request, "approve")} />
                  <ActionButton label="拒绝" tone="reject" onClick={() => onReviewStart(request, "reject")} />
                </div>
                {reviewDraft?.requestId === request.id ? (
                  <form onSubmit={onReviewSubmit} className="mt-4 rounded-xl border border-[#58a6ff]/25 bg-[#1f6feb]/10 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-[#e6edf3]">
                          准备{reviewDraft.action === "approve" ? "批准" : "拒绝"}这条请求
                        </p>
                        <p className="mt-1 text-xs text-[#8b949e]">
                          审批会直接影响当前全局风险状态，请确认后再提交。
                        </p>
                      </div>
                      <ConsoleBadge
                        label={reviewDraft.action === "approve" ? "准备批准" : "准备拒绝"}
                        tone={reviewDraft.action === "approve" ? "good" : "bad"}
                      />
                    </div>
                    <div className="mt-4 grid gap-4 md:grid-cols-2">
                      <Field label="审批人 ID">
                        <ConsoleInput
                          value={reviewDraft.reviewer}
                          onChange={(event) => onReviewDraftChange({ reviewer: event.target.value })}
                          placeholder="risk_lead"
                          required
                        />
                      </Field>
                      <Field label="备注" hint="可选；用于记录这次审批的判断依据。">
                        <ConsoleTextarea
                          value={reviewDraft.notes}
                          onChange={(event) => onReviewDraftChange({ notes: event.target.value })}
                          rows={3}
                          placeholder="例如：已确认越限原因，允许执行这条人工动作"
                        />
                      </Field>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <ConsoleButton
                        type="submit"
                        tone={reviewDraft.action === "approve" ? "success" : "danger"}
                        disabled={reviewSubmitting}
                      >
                        {reviewSubmitting
                          ? "提交中..."
                          : reviewDraft.action === "approve"
                            ? "确认批准"
                            : "确认拒绝"}
                      </ConsoleButton>
                      <ConsoleButton type="button" onClick={onReviewCancel} disabled={reviewSubmitting}>
                        取消
                      </ConsoleButton>
                    </div>
                  </form>
                ) : null}
              </div>
            ))}
          </div>
        )}
        </ConsolePanel>
      </section>
    </section>
  )
}

export function ReviewHistorySection({ requests }: { requests: KillSwitchItem[] }) {
  if (requests.length === 0) {
    return null
  }

  return (
    <ConsolePanel className="mt-8" title="审批历史" description="回看历史动作，确认谁申请、谁审批、为什么。">
      <div className="space-y-3">
        {requests.map((request) => (
          <div key={request.id} className="flex flex-col gap-2 rounded-xl border border-[#30363d] bg-[#0d1117] p-4 md:flex-row md:items-start md:justify-between">
            <div>
              <div className="text-sm font-medium text-[#e6edf3]">
                {formatKillSwitchTypeLabel(request.request_type)} / {request.target_scope}
              </div>
              <div className="mt-1 text-xs text-[#8b949e]">
                申请人 {request.requested_by}
                {request.reviewed_by ? ` / 审批人 ${request.reviewed_by}` : ""}
              </div>
              <div className="mt-2 text-sm text-[#c9d1d9]">{request.reason}</div>
              {request.review_notes && (
                <div className="mt-2 text-xs text-[#8b949e]">备注：{request.review_notes}</div>
              )}
            </div>
            <div className="text-right">
              <ConsoleBadge label={formatReviewStatusLabel(request.status)} tone={request.status === "approved" ? "good" : request.status === "rejected" ? "bad" : "neutral"} />
              <div className="mt-2 text-xs text-[#8b949e]">{formatDate(request.created_at)}</div>
            </div>
          </div>
        ))}
      </div>
    </ConsolePanel>
  )
}
