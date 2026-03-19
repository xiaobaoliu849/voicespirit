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
  return (
    <section className="vsTtsWorkspace" style={{ padding: 0, height: "100%" }}>
      <form className="vsTtsLayout" onSubmit={audioOverview.onGenerateScript} style={{ margin: 0 }}>
        {/* ── Left Pane: Main Workspace ── */}
        <div className="vsTtsPrimary" style={{ flex: "1 1 65%" }}>
          <header className="vsTtsPrimaryHeader">
            <h2 className="vsTtsPrimaryTitle">{t("播客创作台 (Audio Overview)", "Podcast Overview")}</h2>
            <div className="vsTtsPrimaryStats">
              <span>
                {audioOverview.audioOverviewPodcastId
                  ? t(`当前项目: #${audioOverview.audioOverviewPodcastId}`, `Current project: #${audioOverview.audioOverviewPodcastId}`)
                  : t("新项目", "New project")}
              </span>
            </div>
          </header>

          <div className="vsTtsEditorWrap custom-scrollbar" style={{ padding: "24px", overflowY: "auto" }}>
            <PodcastHeader audioOverview={audioOverview} />

            <div style={{ marginTop: "20px" }}>
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
                <div className="vsPodcastSideCard" style={{ marginBottom: "20px" }}>
                  <div className="vsPodcastSideHeader">
                    <h3>{t("Agent 运行状态", "Agent Run Status")}</h3>
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
                  <p className="muted" style={{ margin: 0 }}>
                    {t(
                      `Run #${audioOverview.audioAgentRunId} · 状态 ${audioOverview.audioAgentStatus || "queued"} · 当前步骤 ${audioOverview.audioAgentCurrentStep || "prepare"} · 来源 ${audioOverview.audioAgentSources.length} 条`,
                      `Run #${audioOverview.audioAgentRunId} · Status ${audioOverview.audioAgentStatus || "queued"} · Step ${audioOverview.audioAgentCurrentStep || "prepare"} · ${audioOverview.audioAgentSources.length} sources`
                    )}
                  </p>
                </div>
              ) : null}
            </div>

            <div className="vsPodcastMain" style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
              <PodcastTopicStep audioOverview={audioOverview} />
              <PodcastScriptEditor audioOverview={audioOverview} />
              <PodcastSynthBar audioOverview={audioOverview} />
            </div>
          </div>
        </div>

        {/* ── Right Pane: Sidebar & Project History ── */}
        <div className="vsTtsSecondary" style={{ flex: "1 1 35%", width: "auto" }}>
          <PodcastSidebar audioOverview={audioOverview} />
        </div>
      </form>
    </section>
  );
}
