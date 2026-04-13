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
import type { KillSwitchFormState, KillSwitchItem, ReviewAction } from "./types"

function formatDate(value: string): string {
  return new Date(value).toLocaleString()
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-[#8b949e]">{label}</span>
      {children}
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
  pendingRequests: KillSwitchItem[]
  submitting: boolean
  onSubmit: FormEventHandler<HTMLFormElement>
  onFormChange: (patch: Partial<KillSwitchFormState>) => void
  onReview: (id: string, action: ReviewAction) => void
}

export function KillSwitchSection({
  killSwitchForm,
  pendingRequests,
  submitting,
  onSubmit,
  onFormChange,
  onReview,
}: KillSwitchSectionProps) {
  return (
    <section className="grid gap-6 lg:grid-cols-2">
      <ConsolePanel title="提交 Kill-Switch 请求" description="用于人工切换 RiskOff / 冻结等动作。">
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

          <Field label="目标范围">
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

          <Field label="原因">
            <ConsoleTextarea
              value={killSwitchForm.reason}
              onChange={(event) => onFormChange({ reason: event.target.value })}
              placeholder="说明为什么需要这个动作"
              rows={4}
              required
            />
          </Field>

          <ConsoleButton
            type="submit"
            disabled={submitting}
            tone="danger"
          >
            {submitting ? "提交中..." : "提交请求"}
          </ConsoleButton>
        </form>
      </ConsolePanel>

      <ConsolePanel title="待审批请求" description="这里决定人工动作是否真正生效。">
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
                  <ActionButton label="批准" tone="approve" onClick={() => onReview(request.id, "approve")} />
                  <ActionButton label="拒绝" tone="reject" onClick={() => onReview(request.id, "reject")} />
                </div>
              </div>
            ))}
          </div>
        )}
      </ConsolePanel>
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
