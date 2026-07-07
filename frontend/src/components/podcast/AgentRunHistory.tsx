import type { AudioAgentRun } from "../../api";
import { useI18n } from "../../i18n";

type Props = {
  runs: AudioAgentRun[];
  busy: boolean;
  onRefresh: () => void;
  onOpenRun: (run: AudioAgentRun) => void;
};

const STATUS_ZH: Record<string, string> = {
  queued: "排队中",
  running: "执行中",
  awaiting_review: "待审核",
  draft_ready: "草稿就绪",
  synthesizing: "合成中",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

const STATUS_EN: Record<string, string> = {
  queued: "Queued",
  running: "Running",
  awaiting_review: "Awaiting review",
  draft_ready: "Draft ready",
  synthesizing: "Synthesizing",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

function formatTime(isoString: string): string {
  if (!isoString) return "";
  try {
    const d = new Date(isoString);
    return d.toLocaleString();
  } catch {
    return isoString;
  }
}

export default function AgentRunHistory({ runs, busy, onRefresh, onOpenRun }: Props) {
  const { t, language } = useI18n();
  const statusLabels = language === "zh-CN" ? STATUS_ZH : STATUS_EN;

  if (busy && runs.length === 0) {
    return (
      <div className="vsTranscribeEmpty">
        <div className="vsTranscribeEmptyIcon">
          <div className="spinner vsLoadingSpinner" />
        </div>
        <p className="vsTranscribeEmptyDesc">
          {t("加载 Agent 运行记录中…", "Loading agent runs...")}
        </p>
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div className="vsTranscribeEmpty">
        <div className="vsTranscribeEmptyIcon">🤖</div>
        <h3 className="vsTranscribeEmptyTitle">
          {t("暂无 Agent 运行记录", "No agent runs yet")}
        </h3>
        <p className="vsTranscribeEmptyDesc">
          {t("生成播客脚本后，Agent 运行记录会显示在这里。", "Agent run history will appear here after you generate a podcast script.")}
        </p>
      </div>
    );
  }

  return (
    <div className="vsAgentHistoryList">
      <div className="vsAgentHistoryToolbar">
        <button
          className="vsBtnGhost vsBtnSmall"
          onClick={() => void onRefresh()}
          disabled={busy}
        >
          ↻ {busy ? t("刷新中...", "Refreshing...") : t("刷新", "Refresh")}
        </button>
      </div>
      {runs.map((run) => {
        const statusLabel = statusLabels[run.status] || run.status;
        return (
          <button
            key={run.id}
            className="vsAgentHistoryItem"
            onClick={() => onOpenRun(run)}
          >
            <div className="vsAgentHistoryItemHeader">
              <span className="vsAgentHistoryTopic">{run.topic}</span>
              <span className={`vsAgentStatusBadge vsAgentStatus-${run.status}`}>
                {statusLabel}
              </span>
            </div>
            <div className="vsAgentHistoryMeta">
              <span>#{run.id}</span>
              <span>{run.provider}{run.model ? ` / ${run.model}` : ""}</span>
              <span>{run.language.toUpperCase()}</span>
              <span>{formatTime(run.created_at)}</span>
            </div>
            {run.error_message ? (
              <p className="vsAgentHistoryError">{run.error_message}</p>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
