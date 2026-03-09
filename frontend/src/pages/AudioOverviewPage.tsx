import type { UseAudioOverviewResult } from "../hooks/useAudioOverview";
import PodcastHeader from "../components/podcast/PodcastHeader";
import PodcastScriptEditor from "../components/podcast/PodcastScriptEditor";
import PodcastSidebar from "../components/podcast/PodcastSidebar";
import PodcastSynthBar from "../components/podcast/PodcastSynthBar";
import PodcastTopicStep from "../components/podcast/PodcastTopicStep";
import ErrorNotice from "../components/ErrorNotice";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  audioOverview: UseAudioOverviewResult;
  errorRuntimeContext: ErrorRuntimeContext;
};

export default function AudioOverviewPage({
  audioOverview,
  errorRuntimeContext
}: Props) {
  return (
    <section className="vsTtsWorkspace" style={{ padding: 0, height: "100%" }}>
      <form className="vsTtsLayout" onSubmit={audioOverview.onGenerateScript} style={{ margin: 0 }}>
        {/* ── Left Pane: Main Workspace ── */}
        <div className="vsTtsPrimary" style={{ flex: "1 1 65%" }}>
          <header className="vsTtsPrimaryHeader">
            <h2 className="vsTtsPrimaryTitle">播客创作台 (Audio Overview)</h2>
            <div className="vsTtsPrimaryStats">
              <span>{audioOverview.audioOverviewPodcastId ? `当前项目: #${audioOverview.audioOverviewPodcastId}` : "新项目"}</span>
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
