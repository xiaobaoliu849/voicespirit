import React from "react";
import type { AudioOverviewPodcast } from "../../api";
import { useI18n } from "../../i18n";

type Props = {
  item: AudioOverviewPodcast;
  isActive?: boolean;
  onClick: () => void;
  onDelete: (e: React.MouseEvent) => void;
};

/* Deterministic gradient palette based on podcast ID */
const COVER_GRADIENTS = [
  ["#f43f5e", "#fb7185", "#fda4af"], // rose
  ["#8b5cf6", "#a78bfa", "#c4b5fd"], // violet
  ["#3b82f6", "#60a5fa", "#93c5fd"], // blue
  ["#10b981", "#34d399", "#6ee7b7"], // emerald
  ["#f59e0b", "#fbbf24", "#fcd34d"], // amber
  ["#0ea5e9", "#38bdf8", "#7dd3fc"], // sky
];

function formatRelativeTime(dateStr: string | null | undefined, t: (zh: string, en: string) => string): string {
  if (!dateStr) return t("未知时间", "Unknown");
  const date = new Date(dateStr);
  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return t("刚刚", "Just now");
  if (diffMin < 60) return t(`${diffMin} 分钟前`, `${diffMin}m ago`);
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return t(`${diffHr} 小时前`, `${diffHr}h ago`);
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 30) return t(`${diffDay} 天前`, `${diffDay}d ago`);
  const diffMon = Math.floor(diffDay / 30);
  if (diffMon < 12) return t(`${diffMon} 个月前`, `${diffMon}mo ago`);
  return t(`${Math.floor(diffMon / 12)} 年前`, `${Math.floor(diffMon / 12)}y ago`);
}

/* SVG circle pattern for the card cover */
function CirclePattern({ color }: { color: string }) {
  return (
    <svg className="vsTranscribeCardWave" viewBox="0 0 100 100" preserveAspectRatio="none">
      <circle cx="20" cy="80" r="40" fill={color} opacity="0.3" />
      <circle cx="80" cy="20" r="60" fill={color} opacity="0.2" />
    </svg>
  );
}

export const PodcastCard: React.FC<Props> = ({
  item,
  isActive,
  onClick,
  onDelete,
}) => {
  const { t } = useI18n();
  const topic = item.topic || t("未命名播客", "Unnamed Podcast");
  const palette = COVER_GRADIENTS[item.id % COVER_GRADIENTS.length];

  const isCompleted = Boolean(item.audio_path);
  const hasScript = item.script_lines && item.script_lines.length > 0;
  
  const statusClass = isCompleted ? "completed" : hasScript ? "running" : "submitted";

  return (
    <div
      className={`vsTranscribeCard ${statusClass} ${isActive ? "active" : ""}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
    >
      {/* Cover */}
      <div className="vsTranscribeCardCover">
        <div
          className="vsTranscribeCardCoverBg"
          style={{
            background: `linear-gradient(135deg, ${palette[0]}, ${palette[1]} 60%, ${palette[2]})`,
          }}
        />
        <CirclePattern color="rgba(255,255,255,0.6)" />
        <button
          className="vsTranscribeCardPlayBtn"
          onClick={(e) => {
            e.stopPropagation();
            onClick();
          }}
          aria-label={t("查看详情", "View details")}
        >
          {isCompleted ? "▶" : "✎"}
        </button>
        <span className="vsTranscribeCardFormatBadge">#{item.id}</span>
      </div>

      {/* Meta */}
      <div className="vsTranscribeCardMeta">
        <div className="vsTranscribeCardMetaTop">
          <span className="vsTranscribeCardTime">
            {formatRelativeTime(item.updated_at, t)}
          </span>
        </div>
        <h4 className="vsTranscribeCardTitle" title={topic}>
          {topic}
        </h4>
        <p className="vsTranscribeCardPreview">
          {isCompleted
            ? t("合成完成", "Synthesis Completed")
            : hasScript
            ? t("脚本已就绪", "Script Ready")
            : t("草稿状态", "Draft")}
        </p>
      </div>

      {/* Footer */}
      <div className="vsTranscribeCardFooter">
        <span className="vsTranscribeCardMemoryBadge" style={{ background: "transparent" }} />
        <button
          className="vsTranscribeCardDeleteBtn"
          onClick={onDelete}
          title={t("删除播客", "Delete podcast")}
        >
          {t("删除", "Delete")}
        </button>
      </div>
    </div>
  );
};
