import { useEffect, useMemo, useState } from "react";

import type { VoiceAgentRunLink, VoiceAgentTimelineEventHistory } from "../api";
import type { UseVoiceChatResult } from "../hooks/useVoiceChat";
import { useI18n } from "../i18n";
import { buildVoiceTimelineMetrics } from "../utils/voiceTimelineMetrics";

type Props = {
  voiceChat: UseVoiceChatResult;
  onResumeAgentRun?: (link: VoiceAgentRunLink) => void | Promise<void>;
};

type TimelineFilter = "all" | "turn" | "interruption" | "tool" | "agent_run" | "metric";

function timelineText(event: VoiceAgentTimelineEventHistory): string {
  if (event.event_type === "interruption_decision") {
    return [event.payload.classification, event.payload.decision, event.payload.rule]
      .filter(Boolean)
      .map(String)
      .join(" · ");
  }
  if (event.event_type === "assistant_audio_started") {
    const value = event.payload.first_audio_ms ?? event.payload.elapsed_ms;
    return typeof value === "number" ? `first audio: ${value}ms` : "";
  }
  if (event.event_type === "interruption_client_stopped") {
    const value = event.payload.stop_latency_ms;
    return typeof value === "number" ? `playback stopped: ${value}ms` : "";
  }
  return event.text || event.query || "";
}

function matchesTimelineFilter(event: VoiceAgentTimelineEventHistory, filter: TimelineFilter): boolean {
  if (filter === "all") return true;
  if (filter === "turn") return event.source === "turn";
  if (filter === "interruption") return event.event_type.startsWith("interruption_");
  if (filter === "tool") return event.source === "tool_event" || event.event_type.startsWith("tool_");
  if (filter === "agent_run") return event.source === "agent_run" || event.event_type === "agent_run_linked";
  return event.source === "metric" || event.event_type === "assistant_audio_started";
}

function metricText(value: number | null | undefined): string {
  return typeof value === "number" ? `${Math.round(value)}ms` : "—";
}

export default function VoiceAgentHistoryPanel({ voiceChat, onResumeAgentRun }: Props) {
  const { t } = useI18n();
  const [timelineFilter, setTimelineFilter] = useState<TimelineFilter>("all");
  const [turnFilter, setTurnFilter] = useState("all");
  const selected = voiceChat.voiceAgentHistoryDetail;
  const timeline = selected?.timeline ?? [];
  const localMetrics = buildVoiceTimelineMetrics(timeline);
  const summary = voiceChat.voiceAgentMetricsSummary;

  useEffect(() => {
    void voiceChat.onLoadVoiceAgentHistory();
  }, []);

  const turnIds = useMemo(
    () => Array.from(new Set(timeline.map((event) => event.turn_id).filter(Boolean))),
    [timeline]
  );
  const filteredTimeline = useMemo(
    () => timeline.filter((event) => (
      matchesTimelineFilter(event, timelineFilter)
      && (turnFilter === "all" || event.turn_id === turnFilter)
    )),
    [timeline, timelineFilter, turnFilter]
  );

  return (
    <section className="vsCardSection" style={{ display: "grid", gap: 14 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <div>
          <h3 className="vsCardSubTitle">{t("语音 Agent 历史与运行", "Voice agent history and runs")}</h3>
          <p className="vsFieldHint">
            {t("跨会话指标、规范时间线与可恢复的持久 Agent Run。", "Cross-session metrics, canonical timelines, and resumable durable agent runs.")}
          </p>
        </div>
        <button
          type="button"
          className="vsBtnSecondary"
          disabled={voiceChat.voiceAgentHistoryBusy}
          onClick={() => void voiceChat.onLoadVoiceAgentHistory()}
        >
          {voiceChat.voiceAgentHistoryBusy ? t("加载中", "Loading") : t("刷新", "Refresh")}
        </button>
      </div>

      {voiceChat.voiceAgentHistoryError ? (
        <div className="vsVoiceMemoryNotice">{voiceChat.voiceAgentHistoryError}</div>
      ) : null}

      {summary ? (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <span className="vsVoiceMemoryChip">{t("会话", "Sessions")}: {summary.session_count}</span>
          <span className="vsVoiceMemoryChip">{t("轮次", "Turns")}: {summary.turn_count}</span>
          <span className="vsVoiceMemoryChip">P50 {t("首音频", "first audio")}: {metricText(summary.first_audio_ms.p50)}</span>
          <span className="vsVoiceMemoryChip">P95 {t("决策", "decision")}: {metricText(summary.interruption_decision_ms.p95)}</span>
          <span className="vsVoiceMemoryChip">P95 {t("停止", "stop")}: {metricText(summary.interruption_stop_ms.p95)}</span>
          <span className="vsVoiceMemoryChip">P50 {t("轮次完成", "turn completion")}: {metricText(summary.turn_completion_ms.p50)}</span>
          <span className="vsVoiceMemoryChip">
            {t("误中断代理", "False-interruption proxy")}: {summary.false_interruption_rate === null
              ? "—"
              : `${Math.round(summary.false_interruption_rate * 100)}%`}
          </span>
        </div>
      ) : null}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 280px), 1fr))", gap: 14 }}>
        <div style={{ display: "grid", gap: 8, alignContent: "start" }}>
          {voiceChat.voiceAgentHistorySessions.length > 0 ? voiceChat.voiceAgentHistorySessions.map((session) => (
            <button
              key={session.id}
              type="button"
              className="vsBtnSecondary"
              style={{ justifyContent: "flex-start", textAlign: "left" }}
              onClick={() => void voiceChat.onOpenVoiceAgentSession(session.id)}
            >
              <span style={{ display: "grid", gap: 2 }}>
                <strong>{session.provider} · {session.status}</strong>
                <span className="vsFieldHint">{session.model || t("未记录模型", "No model")} · {session.started_at}</span>
              </span>
            </button>
          )) : (
            <p className="vsFieldHint">{t("暂无持久化会话。", "No persisted sessions yet.")}</p>
          )}
        </div>

        <div style={{ minWidth: 0 }}>
          {selected ? (
            <div style={{ display: "grid", gap: 12 }}>
              <div className="vsRealtimeContent" style={{ border: "1px solid var(--line)", borderRadius: 10, padding: 12, background: "var(--panel)" }}>
                <strong>{selected.provider} · {selected.id}</strong>
                <div className="vsFieldHint">
                  {selected.turns.length} turns · {selected.tool_events.length} tools · {timeline.length} events
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
                  <span className="vsVoiceMemoryChip">{t("平均首音频", "Avg first audio")}: {metricText(localMetrics.firstAudioMs)}</span>
                  <span className="vsVoiceMemoryChip">{t("平均决策", "Avg decision")}: {metricText(localMetrics.interruptionDecisionMs)}</span>
                </div>
              </div>

              {(selected.agent_run_links?.length ?? 0) > 0 ? (
                <div className="vsField">
                  <label className="vsFieldLabel">{t("关联 Agent Runs", "Linked agent runs")}</label>
                  <div style={{ display: "grid", gap: 8 }}>
                    {(selected.agent_run_links ?? []).map((link) => (
                      <div key={link.id} className="vsRealtimeContent" style={{ border: "1px solid var(--line)", borderRadius: 10, padding: 12, background: "var(--panel)" }}>
                        <strong>{link.run.title || link.agent_run_id}</strong>
                        <div className="vsFieldHint">
                          {link.agent_run_id} · {link.run.status} · {link.run.current_step || "—"} · turn {link.voice_turn_id}
                        </div>
                        {onResumeAgentRun && link.run.source_kind === "audio_agent" ? (
                          <button type="button" className="vsBtnSecondary" onClick={() => void onResumeAgentRun(link)}>
                            {t("在播客工作台继续", "Resume in podcast workspace")}
                          </button>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <select className="vsSelect" value={timelineFilter} onChange={(event) => setTimelineFilter(event.target.value as TimelineFilter)} aria-label={t("时间线类型筛选", "Timeline type filter")}>
                  <option value="all">{t("全部事件", "All events")}</option>
                  <option value="turn">{t("轮次", "Turns")}</option>
                  <option value="interruption">{t("中断", "Interruptions")}</option>
                  <option value="tool">{t("工具", "Tools")}</option>
                  <option value="agent_run">Agent Runs</option>
                  <option value="metric">{t("指标", "Metrics")}</option>
                </select>
                <select className="vsSelect" value={turnFilter} onChange={(event) => setTurnFilter(event.target.value)} aria-label={t("时间线轮次筛选", "Timeline turn filter")}>
                  <option value="all">{t("全部轮次", "All turns")}</option>
                  {turnIds.map((turnId) => <option key={turnId} value={turnId}>{turnId}</option>)}
                </select>
                <span className="vsFieldHint">{filteredTimeline.length}/{timeline.length}</span>
              </div>

              <div style={{ display: "grid", gap: 8 }}>
                {filteredTimeline.map((event) => (
                  <div key={event.id} className="vsRealtimeContent" style={{ border: "1px solid var(--line)", borderRadius: 10, padding: 12, background: "var(--panel)" }}>
                    <strong>{event.event_type}{event.tool_name ? ` · ${event.tool_name}` : ""}</strong>
                    <div className="vsFieldHint">
                      {event.timestamp}{event.turn_id ? ` · ${event.turn_id}` : ""}{event.provider ? ` · ${event.provider}` : ""}
                    </div>
                    {timelineText(event) ? <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{timelineText(event)}</div> : null}
                  </div>
                ))}
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <button type="button" className="vsBtnSecondary" onClick={voiceChat.onExportVoiceAgentSession}>
                  {t("导出 JSON", "Export JSON")}
                </button>
              </div>
            </div>
          ) : (
            <p className="vsFieldHint">{t("选择一个历史会话查看规范时间线。", "Select a session to inspect its canonical timeline.")}</p>
          )}
        </div>
      </div>
    </section>
  );
}
