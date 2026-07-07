import { useMemo } from "react";
import type { AudioAgentStep } from "../../api";
import { useI18n } from "../../i18n";

const STEP_ORDER = [
  "prepare",
  "retrieve",
  "assemble_evidence",
  "generate_script",
  "persist_draft",
  "synthesize_audio",
] as const;

type StepStatus = "completed" | "running" | "failed" | "pending";

type Props = {
  steps: AudioAgentStep[];
  currentStep: string;
  agentStatus: string;
  errorMessage: string;
  canRetry: boolean;
  onRetry: () => void;
  busy: boolean;
};

const STEP_LABELS_ZH: Record<string, string> = {
  prepare: "准备任务",
  retrieve: "检索资料",
  assemble_evidence: "整理证据",
  generate_script: "生成脚本",
  persist_draft: "保存草稿",
  synthesize_audio: "合成音频",
};

const STEP_LABELS_EN: Record<string, string> = {
  prepare: "Prepare",
  retrieve: "Retrieve sources",
  assemble_evidence: "Assemble evidence",
  generate_script: "Generate script",
  persist_draft: "Persist draft",
  synthesize_audio: "Synthesize audio",
};

function computeStepDuration(step: AudioAgentStep): string {
  if (!step.started_at) return "";
  const start = new Date(step.started_at).getTime();
  const end = step.finished_at ? new Date(step.finished_at).getTime() : Date.now();
  const seconds = Math.round((end - start) / 1000);
  if (seconds < 1) return "<1s";
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return `${minutes}m ${remaining}s`;
}

function resolveStepStatus(
  stepName: string,
  steps: AudioAgentStep[],
  currentStep: string,
  agentStatus: string
): StepStatus {
  const stepRecord = steps.find((s) => s.step_name === stepName);
  if (stepRecord) {
    if (stepRecord.status === "completed") return "completed";
    if (stepRecord.status === "failed") return "failed";
    if (stepRecord.status === "running") return "running";
  }
  if (agentStatus === "running" || agentStatus === "queued") {
    if (stepName === currentStep) return "running";
    const currentIdx = STEP_ORDER.indexOf(currentStep as typeof STEP_ORDER[number]);
    const stepIdx = STEP_ORDER.indexOf(stepName as typeof STEP_ORDER[number]);
    if (currentIdx >= 0 && stepIdx >= 0 && stepIdx < currentIdx) return "completed";
  }
  if (agentStatus === "draft_ready" || agentStatus === "completed") {
    return "completed";
  }
  return "pending";
}

function StepIcon({ status }: { status: StepStatus }) {
  if (status === "completed") {
    return (
      <span className="vsAgentStepIcon vsAgentStepDone">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </span>
    );
  }
  if (status === "running") {
    return <span className="vsAgentStepIcon vsAgentStepActive"><div className="spinner vsAgentStepSpinner" /></span>;
  }
  if (status === "failed") {
    return (
      <span className="vsAgentStepIcon vsAgentStepFailed">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </span>
    );
  }
  return <span className="vsAgentStepIcon vsAgentStepPending"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="8" /></svg></span>;
}

export default function AgentProgressPanel({
  steps,
  currentStep,
  agentStatus,
  errorMessage,
  canRetry,
  onRetry,
  busy,
}: Props) {
  const { t, language } = useI18n();
  const labels = language === "zh-CN" ? STEP_LABELS_ZH : STEP_LABELS_EN;

  const failedStep = useMemo(
    () => steps.find((s) => s.status === "failed"),
    [steps]
  );

  return (
    <div className="vsAgentProgress">
      <div className="vsAgentProgressHeader">
        <h4 className="vsAgentProgressTitle">
          {t("Agent 执行进度", "Agent Progress")}
        </h4>
        <span className={`vsAgentStatusBadge vsAgentStatus-${agentStatus}`}>
          {agentStatus}
        </span>
      </div>
      <ol className="vsAgentStepList">
        {STEP_ORDER.map((stepName) => {
          const status = resolveStepStatus(stepName, steps, currentStep, agentStatus);
          const stepRecord = steps.find((s) => s.step_name === stepName);
          const duration = stepRecord ? computeStepDuration(stepRecord) : "";
          return (
            <li key={stepName} className={`vsAgentStepItem vsAgentStep-${status}`}>
              <StepIcon status={status} />
              <div className="vsAgentStepInfo">
                <span className="vsAgentStepName">{labels[stepName] || stepName}</span>
                {duration ? <span className="vsAgentStepDuration">{duration}</span> : null}
                {status === "failed" && stepRecord?.error_message ? (
                  <span className="vsAgentStepError">{stepRecord.error_message}</span>
                ) : null}
              </div>
            </li>
          );
        })}
      </ol>
      {canRetry && (
        <div className="vsAgentRetryBar">
          <span className="vsAgentRetryMsg">
            {failedStep?.error_message || errorMessage || t("执行失败", "Execution failed")}
          </span>
          <button
            className="vsBtnSecondary vsBtnSmall"
            onClick={onRetry}
            disabled={busy}
          >
            {busy ? t("重试中...", "Retrying...") : t("重试", "Retry")}
          </button>
        </div>
      )}
    </div>
  );
}
