import { useState, useEffect } from "react";
import type { UseAudioOverviewResult } from "../hooks/useAudioOverview";
import PodcastHeader from "../components/podcast/PodcastHeader";
import PodcastScriptEditor from "../components/podcast/PodcastScriptEditor";
import PodcastSidebar from "../components/podcast/PodcastSidebar";
import PodcastSynthBar from "../components/podcast/PodcastSynthBar";
import PodcastTopicStep from "../components/podcast/PodcastTopicStep";
import ErrorNotice from "../components/ErrorNotice";
import { useI18n } from "../i18n";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  audioOverview: UseAudioOverviewResult;
  errorRuntimeContext: ErrorRuntimeContext;
};

export default function AudioOverviewPage({
  audioOverview,
  errorRuntimeContext
}: Props) {
  const { t } = useI18n();
  
  // Track manual stepper tab selections.
  const [stageOverride, setStageOverride] = useState<1 | 2 | null>(null);
  
  const hasScript = audioOverview.audioOverviewScriptLines.length > 0;

  // Derive active stage synchronously to avoid microtask/rendering lag in tests
  const activeStage = stageOverride !== null ? stageOverride : (hasScript ? 2 : 1);

  // Reset manual override whenever the script state changes (e.g. creating a new draft)
  useEffect(() => {
    setStageOverride(null);
  }, [hasScript]);

  return (
    <section className="vsMainScrollArea" style={{ background: "var(--bg-secondary)", padding: "24px" }}>
      <form className="vsPodcastLayout" onSubmit={audioOverview.onGenerateScript} style={{ maxWidth: "1400px", margin: "0 auto", width: "100%" }}>
        {/* ── Center Pane: Main Workspace ── */}
        <div className="vsPodcastMain">
          {/* Header & Stepper Card */}
          <div className="vsPodcastStepCard" style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--line)", background: "color-mix(in oklab, var(--bg-card) 60%, transparent)" }}>
              <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h2 style={{ margin: 0, fontSize: "18px", fontWeight: "700", color: "var(--text)" }}>
                  {t("播客创作台 (Audio Overview)", "Podcast Overview")}
                </h2>
                <div style={{ fontSize: "12px", color: "var(--muted)", background: "var(--surface)", padding: "4px 10px", borderRadius: "12px", border: "1px solid var(--line)" }}>
                  {audioOverview.audioOverviewPodcastId
                    ? t(`当前项目: #${audioOverview.audioOverviewPodcastId}`, `Current project: #${audioOverview.audioOverviewPodcastId}`)
                    : t("新项目", "New project")}
                </div>
              </header>
            </div>

            <div style={{ padding: "0 24px" }}>
              <PodcastHeader audioOverview={audioOverview} />
            </div>

            {/* Stepper Progress Bar */}
            <div 
              className="vsPodcastStepper" 
              style={{ 
                display: "flex", 
                gap: "16px", 
                padding: "20px 24px"
              }}
            >
              <div 
                className={`vsStepIndicator ${activeStage === 1 ? "active" : ""}`}
                onClick={() => setStageOverride(1)}
                style={{
                  flex: 1,
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  cursor: "pointer",
                  padding: "12px 16px",
                  borderRadius: "12px",
                  background: activeStage === 1 ? "var(--brand-soft)" : "color-mix(in oklab, var(--surface) 50%, transparent)",
                  border: activeStage === 1 ? "1px solid var(--brand)" : "1px solid var(--line)",
                  transition: "all 0.25s ease"
                }}
              >
                <span style={{ 
                  width: "28px", 
                  height: "28px", 
                  borderRadius: "50%", 
                  background: activeStage === 1 ? "var(--brand)" : "var(--line-strong)", 
                  color: activeStage === 1 ? "#fff" : "var(--muted)",
                  display: "flex", 
                  alignItems: "center", 
                  justifyContent: "center",
                  fontSize: "13px",
                  fontWeight: "bold",
                  flexShrink: 0
                }}>1</span>
                <div>
                  <div style={{ fontSize: "14px", fontWeight: "700", color: activeStage === 1 ? "var(--brand-dark)" : "var(--text)" }}>
                    {t("主题与资料", "Topic & Sources")}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--muted)", marginTop: "2px" }}>
                    {t("配置约束并创作脚本", "Configure and draft script")}
                  </div>
                </div>
              </div>

              <div 
                className={`vsStepIndicator ${activeStage === 2 ? "active" : ""} ${!hasScript ? "disabled" : ""}`}
                onClick={() => hasScript && setStageOverride(2)}
                style={{
                  flex: 1,
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  cursor: hasScript ? "pointer" : "not-allowed",
                  opacity: hasScript ? 1 : 0.5,
                  padding: "12px 16px",
                  borderRadius: "12px",
                  background: activeStage === 2 ? "var(--brand-soft)" : "color-mix(in oklab, var(--surface) 50%, transparent)",
                  border: activeStage === 2 ? "1px solid var(--brand)" : "1px solid var(--line)",
                  transition: "all 0.25s ease"
                }}
              >
                <span style={{ 
                  width: "28px", 
                  height: "28px", 
                  borderRadius: "50%", 
                  background: activeStage === 2 ? "var(--brand)" : "var(--line-strong)", 
                  color: activeStage === 2 ? "#fff" : "var(--muted)",
                  display: "flex", 
                  alignItems: "center", 
                  justifyContent: "center",
                  fontSize: "13px",
                  fontWeight: "bold",
                  flexShrink: 0
                }}>2</span>
                <div>
                  <div style={{ fontSize: "14px", fontWeight: "700", color: activeStage === 2 ? "var(--brand-dark)" : "var(--text)" }}>
                    {t("剧本与配音", "Script & Voice")}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--muted)", marginTop: "2px" }}>
                    {t("编辑台词并合成音频", "Tweak lines & synthesize")}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Error notifications and Status panels */}
            <div>
              <ErrorNotice
                message={audioOverview.audioOverviewError}
                scope="audio_overview"
                context={{
                  ...errorRuntimeContext,
                  provider: audioOverview.audioOverviewProvider,
                  model: audioOverview.audioOverviewModel,
                  language: audioOverview.audioOverviewLanguage,
                  podcast_id: audioOverview.audioOverviewPodcastId,
                  merge_strategy: audioOverview.audioOverviewMergeStrategy
                }}
              />
              {audioOverview.audioOverviewInfo ? (
                <p className="vsSettingsNotice ok" style={{ marginBottom: "20px" }}>{audioOverview.audioOverviewInfo}</p>
              ) : null}
              {audioOverview.audioAgentRunId !== null ? (
                <div className="vsPodcastSideCard" style={{ marginBottom: "16px", background: "var(--bg-card)" }}>
                  <div className="vsPodcastSideHeader">
                    <h3 style={{ fontSize: "14px" }}>{t("Agent 运行状态", "Agent Run Status")}</h3>
                    {audioOverview.audioAgentCanRetry ? (
                      <button
                        type="button"
                        className="ghost vsPodcastMiniBtn"
                        onClick={() => void audioOverview.onRetryAgentRun()}
                        disabled={audioOverview.audioOverviewBusy || audioOverview.audioOverviewSynthBusy}
                      >
                        {t("重试", "Retry")}
                      </button>
                    ) : null}
                  </div>
                  <p className="muted" style={{ margin: 0, fontSize: "13px" }}>
                    {t(
                      `Run #${audioOverview.audioAgentRunId} · 状态 ${audioOverview.audioAgentStatus || "queued"} · 当前步骤 ${audioOverview.audioAgentCurrentStep || "prepare"} · 来源 ${audioOverview.audioAgentSources.length} 条`,
                      `Run #${audioOverview.audioAgentRunId} · Status ${audioOverview.audioAgentStatus || "queued"} · Step ${audioOverview.audioAgentCurrentStep || "prepare"} · ${audioOverview.audioAgentSources.length} sources`
                    )}
                  </p>
                </div>
              ) : null}
            </div>

            {/* Main Stage Panel Switcher */}
            <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
              <div style={{ display: activeStage === 1 ? "block" : "none" }}>
                <PodcastTopicStep audioOverview={audioOverview} />
              </div>
              <div style={{ display: activeStage === 2 ? "block" : "none" }}>
                <PodcastScriptEditor audioOverview={audioOverview} />
                <PodcastSynthBar audioOverview={audioOverview} />
              </div>
            </div>
        </div>

        {/* ── Right Pane: Sidebar & Project History ── */}
        <div className="vsPodcastSide">
          <PodcastSidebar audioOverview={audioOverview} />
        </div>
      </form>
    </section>
  );
}
