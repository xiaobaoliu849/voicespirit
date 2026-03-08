import type { UseAudioOverviewResult } from "../../hooks/useAudioOverview";

type Props = {
  audioOverview: UseAudioOverviewResult;
};

export default function PodcastHeader({ audioOverview }: Props) {
  return (
    <div className="vsPodcastHeader">
      <div className="vsPodcastHeaderCopy">
        <h2>播客工作台</h2>
        <p>从一个主题开始，逐步生成脚本并合成双人播客。</p>
      </div>
      <div className="vsPodcastHeaderActions">
        <span className="vsPodcastStatusChip">{audioOverview.currentAudioOverviewLabel}</span>
        <button
          type="button"
          className="ghost vsPodcastMiniBtn"
          onClick={audioOverview.onNewDraft}
          disabled={
            audioOverview.audioOverviewBusy ||
            audioOverview.audioOverviewSaving ||
            audioOverview.audioOverviewSynthBusy
          }
        >
          新建草稿
        </button>
        <div className="vsPodcastMenuWrap">
          <button
            type="button"
            className="ghost vsPodcastMenuTrigger"
            aria-label="更多操作"
            aria-expanded={audioOverview.audioOverviewMenuOpen}
            onClick={audioOverview.onToggleMenu}
          >
            ⋯
          </button>
          {audioOverview.audioOverviewMenuOpen ? (
            <div className="vsPodcastMenu">
              <button
                type="button"
                className="vsPodcastMenuItem danger"
                onClick={() => void audioOverview.onDeleteCurrent()}
                disabled={audioOverview.audioOverviewPodcastId === null}
              >
                删除当前
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
