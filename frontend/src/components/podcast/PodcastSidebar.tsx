import type { UseAudioOverviewResult } from "../../hooks/useAudioOverview";

type Props = {
  audioOverview: UseAudioOverviewResult;
};

export default function PodcastSidebar({ audioOverview }: Props) {
  const formatUpdatedAt = (updatedAt: string) => {
    const parsed = new Date(updatedAt);
    if (Number.isNaN(parsed.getTime())) {
      return updatedAt;
    }

    return new Intl.DateTimeFormat("zh-CN", {
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
          <h3>合成预览</h3>
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
          <h3>最近播客</h3>
          <button
            type="button"
            className="ghost vsPodcastMiniBtn"
            onClick={() => void audioOverview.onRefreshList()}
            disabled={audioOverview.audioOverviewListBusy}
          >
            {audioOverview.audioOverviewListBusy ? "刷新中..." : "刷新列表"}
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
                  {item.language.toUpperCase()}｜台词 {item.script_lines.length} 条｜更新于{" "}
                  <time dateTime={item.updated_at}>{formatUpdatedAt(item.updated_at)}</time>
                </p>
              </div>
              <button
                type="button"
                className="ghost"
                onClick={() => void audioOverview.onLoadPodcast(item.id)}
              >
                载入
              </button>
            </div>
          ))}
          {!audioOverview.audioOverviewPodcasts.length ? (
            <p className="vsInlineEmptyState muted">暂时还没有播客记录。</p>
          ) : null}
        </div>
      </div>
    </aside>
  );
}
