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
    <section className="vsToolWorkspace">
      <form onSubmit={audioOverview.onGenerateScript}>
        <div className="vsPodcastPage">
          <PodcastHeader audioOverview={audioOverview} />

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
            <p className="ok">{audioOverview.audioOverviewInfo}</p>
          ) : null}

          <div className="vsPodcastLayout">
            <div className="vsPodcastMain">
              <PodcastTopicStep audioOverview={audioOverview} />
              <PodcastScriptEditor audioOverview={audioOverview} />
              <PodcastSynthBar audioOverview={audioOverview} />
            </div>
            <PodcastSidebar audioOverview={audioOverview} />
          </div>
        </div>
      </form>
    </section>
  );
}
