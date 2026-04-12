"use client"

import { ConsoleBadge, ConsoleInset, ConsolePanel } from "../components/console-ui"
import { formatRiskStateLabel } from "../risk/constants"

export interface LinkedEvidence {
  id: string
  run_name?: string
  report_type?: string
  created_at?: string
  window_end?: string
  generated_at?: string
  recommendation?: string
  risk_state?: string
  decision?: string
  report_period_end?: string
}

export interface LaunchEvidenceSummary {
  latest_backtest?: LinkedEvidence | null
  latest_shadow_run?: LinkedEvidence | null
  latest_stage_review?: LinkedEvidence | null
}

function formatRecommendation(value?: string | null) {
  switch (value?.toLowerCase()) {
    case "go":
      return "Go，可继续"
    case "watch":
      return "观察"
    case "block":
    case "nogo":
      return "阻断"
    default:
      return "-"
  }
}

function formatDecision(value?: string | null) {
  switch (value?.toLowerCase()) {
    case "go":
      return "Go，可进入上线决策"
    case "nogo":
      return "NoGo，暂不上线"
    case "pending":
      return "待决策"
    default:
      return value ?? "-"
  }
}

function formatReportType(value?: string | null) {
  switch (value) {
    case "daily_summary":
      return "日报"
    case "weekly_summary":
      return "周报"
    case "stage_review":
      return "阶段评审"
    default:
      return value ?? "尚未关联阶段评审"
  }
}

function formatDate(value?: string | null) {
  if (!value) {
    return "-"
  }
  return new Date(value).toLocaleString()
}

function EvidenceCard({
  title,
  subtitle,
  lines,
}: {
  title: string
  subtitle: string
  lines: string[]
}) {
  return (
    <ConsoleInset className="text-sm text-[#c9d1d9]">
      <p className="text-xs uppercase tracking-[0.18em] text-[#8b949e]">{subtitle}</p>
      <p className="mt-2 font-medium text-[#e6edf3]">{title}</p>
      <div className="mt-3 space-y-1">
        {lines.map((line) => (
          <p key={line}>{line}</p>
        ))}
      </div>
    </ConsoleInset>
  )
}

export function LaunchEvidenceSection({ evidence }: { evidence: LaunchEvidenceSummary | null }) {
  const backtest = evidence?.latest_backtest ?? null
  const shadow = evidence?.latest_shadow_run ?? null
  const stageReview = evidence?.latest_stage_review ?? null

  return (
    <ConsolePanel
      className="mt-4"
      title="上线证据概览"
      description="把能不能 Go 拆成三份证据看：回测、影子运行、阶段评审。哪一块缺失，就回到对应页面补齐。"
      actions={
        evidence ? <ConsoleBadge label="已绑定证据" tone="info" /> : <ConsoleBadge label="证据待补齐" tone="warn" />
      }
    >
      <div className="grid gap-3 lg:grid-cols-3">
        <EvidenceCard
          title={backtest?.run_name ?? "尚未关联回测"}
          subtitle="最近一次回测证据"
          lines={
            backtest
              ? [
                  `建议：${formatRecommendation(backtest?.recommendation)}`,
                  `生成时间：${formatDate(backtest?.created_at)}`,
                  `回看区间结束：${formatDate(backtest?.window_end)}`,
                ]
              : ["当前评审还没绑定回测记录；先去“回测实验室”执行并落库。"]
          }
        />
        <EvidenceCard
          title={shadow?.run_name ?? "尚未关联影子运行"}
          subtitle="最近一次影子运行证据"
          lines={
            shadow
              ? [
                  `建议：${formatRecommendation(shadow?.recommendation)}`,
                  `运行时风险状态：${shadow?.risk_state ? formatRiskStateLabel(shadow.risk_state) : "-"}`,
                  `生成时间：${formatDate(shadow?.created_at)}`,
                ]
              : ["当前评审还没绑定影子运行；先跑一次 shadow run 再回来判断。"]
          }
        />
        <EvidenceCard
          title={formatReportType(stageReview?.report_type)}
          subtitle="最近一次阶段评审证据"
          lines={
            stageReview
              ? [
                  `结论：${formatDecision(stageReview?.decision)}`,
                  `生成时间：${formatDate(stageReview?.generated_at)}`,
                  `报告周期结束：${formatDate(stageReview?.report_period_end)}`,
                ]
              : ["当前还没有阶段评审证据；先去“日报、周报与阶段评审”生成对应报告。"]
          }
        />
      </div>
    </ConsolePanel>
  )
}
