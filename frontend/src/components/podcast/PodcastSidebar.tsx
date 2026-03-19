import type { UseAudioOverviewResult } from "../../hooks/useAudioOverview";
import { useI18n } from "../../i18n";

type Props = {
  audioOverview: UseAudioOverviewResult;
};

export default function PodcastSidebar({ audioOverview }: Props) {
  const { t, language } = useI18n();
  const formatEventLabel = (eventType: string) => {
    const labels: Record<string, string> = {
      run_created: t("任务已创建", "Run created"),
      step_started: t("步骤开始", "Step started"),
      step_completed: t("步骤完成", "Step completed"),
      retrieval_summary: t("检索完成", "Retrieval completed"),
      draft_created: t("草稿已生成", "Draft created"),
      podcast_saved: t("草稿已保存", "Draft saved"),
      synthesis_started: t("开始合成", "Synthesis started"),
      synthesis_completed: t("合成完成", "Synthesis completed"),
      run_failed: t("任务失败", "Run failed"),
      execution_deferred: t("等待执行", "Execution deferred")
    };
    return labels[eventType] || eventType;
  };
  const formatStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      queued: t("排队中", "Queued"),
      running: t("执行中", "Running"),
      draft_ready: t("草稿已就绪", "Draft ready"),
      synthesizing: t("合成中", "Synthesizing"),
      completed: t("已完成", "Completed"),
      failed: t("失败", "Failed"),
      completed_step: t("已完成", "Completed")
    };
    return labels[status] || status;
  };
  const formatStepLabel = (stepName: string) => {
    const labels: Record<string, string> = {
      prepare: t("准备", "Prepare"),
      retrieve: t("检索", "Retrieve"),
      assemble_evidence: t("整理资料", "Assemble Evidence"),
      generate_script: t("生成脚本", "Generate Script"),
      persist_draft: t("保存草稿", "Persist Draft"),
      synthesize_audio: t("合成音频", "Synthesize Audio")
    };
    return labels[stepName] || stepName;
  };
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

      <div className="vsPodcastSideCard">
        <div className="vsPodcastSideHeader">
          <h3>{t("Agent 执行", "Agent Execution")}</h3>
        </div>
        {audioOverview.audioAgentRunId !== null ? (
          <div className="voiceList">
            <div className="voiceItem">
              <div>
                <strong>
                  #{audioOverview.audioAgentRunId} {audioOverview.audioAgentStatus || "queued"}
                </strong>
                <p>
                  {t("当前步骤：", "Current step: ")}
                  {formatStepLabel(audioOverview.audioAgentCurrentStep || "prepare")}
                  {audioOverview.audioAgentResultProvider
                    ? ` · ${audioOverview.audioAgentResultProvider}`
                    : ""}
                  {audioOverview.audioAgentResultModel
                    ? ` / ${audioOverview.audioAgentResultModel}`
                    : ""}
                </p>
              </div>
            </div>
            {audioOverview.audioAgentSteps.map((step) => (
              <div key={`agent-step-${step.id}`} className="voiceItem">
                <div>
                  <strong>{formatStepLabel(step.step_name)}</strong>
                  <p>{formatStatusLabel(step.status)}</p>
                </div>
              </div>
            ))}
            {audioOverview.audioAgentErrorMessage ? (
              <div className="voiceItem">
                <div>
                  <strong>{t("失败信息", "Failure message")}</strong>
                  <p>{audioOverview.audioAgentErrorMessage}</p>
                </div>
              </div>
            ) : null}
          </div>
        ) : (
          <p className="vsInlineEmptyState muted">
            {t("生成脚本后会在这里显示检索、写稿和落库步骤。", "Retrieval, drafting, and persistence steps will appear here after generation.")}
          </p>
        )}
      </div>

      <div className="vsPodcastSideCard">
        <div className="vsPodcastSideHeader">
          <h3>{t("资料来源", "Sources")}</h3>
        </div>
        {audioOverview.audioAgentSources.length ? (
          <div className="voiceList">
            {audioOverview.audioAgentSources.map((source) => (
              <div key={`agent-source-${source.id}`} className="voiceItem">
                <details>
                  <summary>
                    <strong>{source.title || source.source_type}</strong>
                    <p>{source.snippet || source.uri || t("无摘要", "No snippet")}</p>
                  </summary>
                  <p>{source.content || source.uri || t("暂无更多内容。", "No additional content.")}</p>
                </details>
              </div>
            ))}
          </div>
        ) : (
          <p className="vsInlineEmptyState muted">
            {t("暂无来源信息。", "No source information yet.")}
          </p>
        )}
      </div>

      <div className="vsPodcastSideCard">
        <div className="vsPodcastSideHeader">
          <h3>{t("最近事件", "Recent Events")}</h3>
        </div>
        {audioOverview.audioAgentEvents.length ? (
          <div className="voiceList">
            {audioOverview.audioAgentEvents.slice(-8).reverse().map((event) => (
              <div key={`agent-event-${event.id}`} className="voiceItem">
                <div>
                  <strong>{formatEventLabel(event.event_type)}</strong>
                  <p>
                    {typeof event.payload.step_name === "string"
                      ? `${formatStepLabel(event.payload.step_name)} · `
                      : ""}
                    <time dateTime={event.created_at}>{formatUpdatedAt(event.created_at)}</time>
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="vsInlineEmptyState muted">
            {t("暂无事件记录。", "No event records yet.")}
          </p>
        )}
      </div>
    </aside>
  );
}
