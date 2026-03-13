import type { UseAudioOverviewResult } from "../../hooks/useAudioOverview";
import { useI18n } from "../../i18n";

type Props = {
  audioOverview: UseAudioOverviewResult;
};

export default function PodcastHeader({ audioOverview }: Props) {
  const { t } = useI18n();
  return (
    <div className="vsPodcastHeader">
      <div className="vsPodcastHeaderCopy">
        <h2>{t("播客工作台", "Podcast Studio")}</h2>
        <p>{t("从一个主题开始，逐步生成脚本并合成双人播客。", "Start from one topic, generate a script, then synthesize a two-host podcast.")}</p>
      </div>
      <div className="vsPodcastHeaderActions">
        <span className="vsPodcastStatusChip">{audioOverview.currentAudioOverviewLabel}</span>
        <span
          className={`vsPodcastStatusChip ${audioOverview.audioOverviewMemoryConfigured ? "is-memory" : "is-muted"}`}
        >
          {audioOverview.audioOverviewMemoryConfigured
            ? t("长期记忆已接入", "Long-term memory connected")
            : t("长期记忆未接入", "Long-term memory not connected")}
        </span>
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
          {t("新建草稿", "New draft")}
        </button>
        <div className="vsPodcastMenuWrap">
          <button
            type="button"
            className="ghost vsPodcastMenuTrigger"
            aria-label={t("更多操作", "More actions")}
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
                {t("删除当前", "Delete current")}
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
