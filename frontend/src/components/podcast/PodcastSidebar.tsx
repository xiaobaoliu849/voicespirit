import type { UseAudioOverviewResult } from "../../hooks/useAudioOverview";
import { useI18n } from "../../i18n";

type Props = {
  audioOverview: UseAudioOverviewResult;
};

export default function PodcastSidebar({ audioOverview }: Props) {
  const { t, language } = useI18n();
  const formatUpdatedAt = (updatedAt: string) => {
    const parsed = new Date(updatedAt);
    if (Number.isNaN(parsed.getTime())) {
      return updatedAt;
    }

    return new Intl.DateTimeFormat(language === "en-US" ? "en-US" : "zh-CN", {
      month: "numeric",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    }).format(parsed);
  };

  return (
    <aside className="vsPodcastSide">
      <div className="vsPodcastSideCard">
        <div className="vsPodcastSideHeader">
          <h3>{t("合成预览", "Synthesis Preview")}</h3>
        </div>
        {audioOverview.audioOverviewAudioUrl ? (
          <div className="audioWrap vsPodcastAudioWrap">
            <audio controls src={audioOverview.audioOverviewAudioUrl} />
          </div>
        ) : (
          <div className="vsPodcastPreviewEmpty" aria-hidden="true">
            🎧
          </div>
        )}
      </div>

      <div className="vsPodcastSideCard">
        <div className="vsPodcastSideHeader">
          <h3>{t("最近播客", "Recent podcasts")}</h3>
          <button
            type="button"
            className="ghost vsPodcastMiniBtn"
            onClick={() => void audioOverview.onRefreshList()}
            disabled={audioOverview.audioOverviewListBusy}
          >
            {audioOverview.audioOverviewListBusy ? t("刷新中...", "Refreshing...") : t("刷新列表", "Refresh list")}
          </button>
        </div>
        <div className="voiceList">
          {audioOverview.audioOverviewPodcasts.map((item) => (
            <div key={`podcast-${item.id}`} className="voiceItem">
              <div>
                <strong>
                  #{item.id} {item.topic}
                </strong>
                <p>
                  {t(
                    `${item.language.toUpperCase()}｜台词 ${item.script_lines.length} 条｜更新于 `,
                    `${item.language.toUpperCase()} | ${item.script_lines.length} lines | Updated `
                  )}
                  <time dateTime={item.updated_at}>{formatUpdatedAt(item.updated_at)}</time>
                </p>
              </div>
              <button
                type="button"
                className="ghost"
                onClick={() => void audioOverview.onLoadPodcast(item.id)}
              >
                {t("载入", "Load")}
              </button>
            </div>
          ))}
          {!audioOverview.audioOverviewPodcasts.length ? (
            <p className="vsInlineEmptyState muted">{t("暂时还没有播客记录。", "No podcast history yet.")}</p>
          ) : null}
        </div>
      </div>
    </aside>
  );
}
