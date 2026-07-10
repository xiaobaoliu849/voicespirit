import ErrorNotice from "../components/ErrorNotice";
import type { VoiceAgentTimelineEventHistory } from "../api";
import type { UseVoiceChatResult } from "../hooks/useVoiceChat";
import { useI18n } from "../i18n";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  voiceChat: UseVoiceChatResult;
  errorRuntimeContext: ErrorRuntimeContext;
};

function timelineText(event: VoiceAgentTimelineEventHistory): string {
  return event.text || event.query || "";
}

export default function VoiceChatPage({ voiceChat, errorRuntimeContext }: Props) {
  const { t } = useI18n();
  const selectedHistory = voiceChat.voiceAgentHistoryDetail;
  const selectedHistoryTimeline = selectedHistory?.timeline ?? [];
  const timelineEventLabels: Record<string, string> = {
    session_open: t("会话开始", "Session opened"),
    session_closed: t("会话结束", "Session closed"),
    user_transcript: t("用户语音转写", "User transcript"),
    assistant_response: t("助手回应", "Assistant response"),
    memory_commit: t("记忆写入", "Memory commit"),
    turn_completed: t("轮次完成", "Turn completed"),
    tool_call_started: t("工具开始", "Tool started"),
    agent_progress: t("Agent 进度", "Agent progress"),
    tool_call_completed: t("工具完成", "Tool completed"),
    tool_call_failed: t("工具失败", "Tool failed"),
    tool_call_cancelled: t("工具取消", "Tool cancelled"),
    response_gated: t("回应闸门", "Response gated"),
    tool_context_injected: t("工具上下文注入", "Tool context injected"),
    agent_result: t("Agent 结果", "Agent result"),
  };
  return (
    <section className="vsTtsWorkspace">
      <div className="vsTtsLayout">
        <div className="vsTtsPrimary">
          <header className="vsTtsPrimaryHeader">
            <div>
              <h2 className="vsTtsPrimaryTitle">{t("语音聊天工作台", "Voice chat workspace")}</h2>
              <p className="vsFieldHint">
                {t(
                  `通过后端代理直接连接 ${voiceChat.voiceChatProvider} 实时语音服务，支持持续收音和即时回传。`,
                  `Connect to ${voiceChat.voiceChatProvider} realtime voice through the backend proxy, with continuous capture and instant return audio.`
                )}
              </p>
            </div>
            <div className="vsTtsPrimaryStats">
              <span>{voiceChat.voiceChatConnected ? t("实时会话中", "Live session") : t("待机", "Idle")}</span>
            {voiceChat.voiceChatMemoriesRetrieved > 0 ? (
              <span className="vsVoiceMemoryChip">
                {t(`已回忆 ${voiceChat.voiceChatMemoriesRetrieved} 条记忆`, `Recalled ${voiceChat.voiceChatMemoriesRetrieved} memories`)}
              </span>
            ) : null}
            {voiceChat.voiceChatMemoryScope ? (
              <span className="vsVoiceMemoryChip">
                Scope: {voiceChat.voiceChatMemoryScope}
              </span>
            ) : null}
            {voiceChat.voiceChatMemoryGroupId ? (
              <span className="vsVoiceMemoryChip">
                Group: {voiceChat.voiceChatMemoryGroupId}
              </span>
            ) : null}
          </div>
          </header>

          <div className="vsCardSection" style={{ display: "grid", gap: 16 }}>
            <div className="vsField">
              <label className="vsFieldLabel">{t("当前模型供应商", "Current provider")}</label>
              <select
                className="vsSelect"
                value={voiceChat.voiceChatProvider}
                onChange={(e) => voiceChat.onProviderChange(e.target.value)}
                disabled={voiceChat.voiceChatBusy}
              >
                {voiceChat.voiceChatProviderOptions.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>

            <div className="vsField">
              <label className="vsFieldLabel">{t("当前模型", "Current model")}</label>
              <input
                className="vsInput"
                list="voice-chat-model-options"
                value={voiceChat.voiceChatModel}
                onChange={(e) => voiceChat.onModelChange(e.target.value)}
                disabled={voiceChat.voiceChatBusy}
              />
              <datalist id="voice-chat-model-options">
                {voiceChat.voiceChatModelOptions.map((item) => (
                  <option key={item} value={item} />
                ))}
              </datalist>
            </div>

            <div className="vsField">
              <label className="vsFieldLabel">
                {t(`${voiceChat.voiceChatProvider} 实时音色`, `${voiceChat.voiceChatProvider} realtime voice`)}
              </label>
              <select
                className="vsSelect"
                value={voiceChat.voiceChatVoice}
                onChange={(e) => voiceChat.onVoiceChange(e.target.value)}
                disabled={voiceChat.voiceChatBusy || voiceChat.voiceChatConnected}
              >
                {voiceChat.voiceChatVoiceOptions.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
              <p className="vsFieldHint">
                {t(`当前音色：${voiceChat.voiceChatVoiceLabel}`, `Current voice: ${voiceChat.voiceChatVoiceLabel}`)}
              </p>
            </div>

            {voiceChat.voiceChatLiveTranslate ? (
              <div className="vsLiveTranslateSettings">
                <div className="vsField">
                  <label className="vsFieldLabel">{t("翻译目标语言", "Translation target language")}</label>
                  <select
                    className="vsSelect"
                    value={voiceChat.voiceChatTargetLanguageCode}
                    onChange={(e) => voiceChat.onTargetLanguageCodeChange(e.target.value)}
                    disabled={voiceChat.voiceChatBusy || voiceChat.voiceChatConnected}
                  >
                    {voiceChat.voiceChatTargetLanguageOptions.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </div>
                <label className="vsComposerToggle" title={t("输入已经是目标语言时也朗读出来", "Echo speech that is already in the target language")}>
                  <input
                    type="checkbox"
                    checked={voiceChat.voiceChatEchoTargetLanguage}
                    onChange={(e) => voiceChat.onEchoTargetLanguageChange(e.target.checked)}
                    disabled={voiceChat.voiceChatBusy || voiceChat.voiceChatConnected}
                  />
                  <span>{t("同语回放", "Echo target language")}</span>
                </label>
              </div>
            ) : null}

            <div
              style={{
                display: "grid",
                placeItems: "center",
                gap: 12,
                minHeight: 220,
                borderRadius: 24,
                border: "1px solid var(--border-color)",
                background: "var(--surface-color)",
              }}
            >
              <button
                type="button"
                className={voiceChat.voiceChatRecording ? "vsBtnPrimary" : "vsBtnSecondary"}
                onClick={() => void voiceChat.onToggleRecording()}
                disabled={!voiceChat.voiceChatSupported || voiceChat.voiceChatBusy}
                style={{
                  width: 160,
                  height: 160,
                  borderRadius: "50%",
                  fontSize: 20,
                }}
              >
                {voiceChat.voiceChatRecording ? t("结束会话", "End session") : t("开始实时聊天", "Start realtime chat")}
              </button>
              <div className="vsEmptyDesc">{voiceChat.voiceChatStatus}</div>
            </div>

            <ErrorNotice
              message={voiceChat.voiceChatError}
              scope="voice-chat"
              context={{
                ...errorRuntimeContext,
                provider: voiceChat.voiceChatProvider,
                model: voiceChat.voiceChatModel,
                voice: voiceChat.voiceChatVoice,
              }}
            />
          </div>
        </div>

        <div className="vsTtsSecondary">
          <div className="vsCardSection">
            <h3 className="vsCardSubTitle">{t("实时会话说明", "Realtime session notes")}</h3>
            <p className="vsFieldHint">
              {t(
                "支持 Google Native Realtime 和 DashScope Qwen Omni 实时分流。连接后会持续监听麦克风，用户讲话会实时转成文字，模型语音和文字会同步回传。",
                "Supports Google Native Realtime and DashScope Qwen Omni. Once connected, the microphone is monitored continuously and both transcript and model voice are streamed back in real time."
              )}
            </p>
          </div>

          <div className="vsCardSection border-top">
            <h3 className="vsCardSubTitle">{t("本轮语音内容", "Current session content")}</h3>
            <div className="vsField">
              <label className="vsFieldLabel">{t("识别结果", "Transcript")}</label>
              <div className="vsRealtimeContent" style={{ border: "1px solid var(--line)", borderRadius: 10, padding: 12, background: "white" }}>
                {voiceChat.voiceChatTranscript || t("转录将显示在这里...", "The transcript will appear here...")}
              </div>
            </div>
            <div className="vsField" style={{ marginTop: 12 }}>
              <label className="vsFieldLabel">{t("助手回复", "Assistant reply")}</label>
              <div className="vsRealtimeContent" style={{ border: "1px solid var(--line)", borderRadius: 10, padding: 12, background: "white" }}>
                {voiceChat.voiceChatReply || t("回复将显示在这里...", "The reply will appear here...")}
              </div>
            </div>
            {voiceChat.voiceChatMemoriesRetrieved > 0 ? (
              <div className="vsVoiceMemoryNotice">
                {t(`本轮已回忆 ${voiceChat.voiceChatMemoriesRetrieved} 条长期记忆。`, `This session recalled ${voiceChat.voiceChatMemoriesRetrieved} long-term memories.`)}
              </div>
            ) : null}
            {voiceChat.voiceChatMemorySourceStatus ? (
              <div className="vsVoiceMemoryNotice">
                {voiceChat.voiceChatMemorySourceStatus}
              </div>
            ) : null}
            {voiceChat.voiceChatMemoryWriteStatus ? (
              <div className="vsVoiceMemoryNotice">
                {voiceChat.voiceChatMemoryWriteStatus}
              </div>
            ) : null}
            {voiceChat.voiceChatAgentToolStatus ? (
              <div className="vsVoiceMemoryNotice">
                {voiceChat.voiceChatAgentToolStatus}
              </div>
            ) : null}
            {voiceChat.voiceChatAgentRunMeta ? (
              <div className="vsFieldHint">
                {voiceChat.voiceChatAgentRunMeta}
              </div>
            ) : null}
            {voiceChat.voiceChatAgentSources.length > 0 ? (
              <div className="vsField" style={{ marginTop: 12 }}>
                <label className="vsFieldLabel">{t("工具来源", "Tool sources")}</label>
                <div style={{ display: "grid", gap: 8 }}>
                  {voiceChat.voiceChatAgentSources.map((source, index) => (
                    <div
                      key={`${source.uri || source.title}-${index}`}
                      className="vsRealtimeContent"
                      style={{ border: "1px solid var(--line)", borderRadius: 10, padding: 12, background: "white" }}
                    >
                      <div style={{ fontWeight: 700 }}>{source.title || t("未命名来源", "Untitled source")}</div>
                      {source.uri ? (
                        <a href={source.uri} target="_blank" rel="noreferrer" className="vsFieldHint">
                          {source.uri}
                        </a>
                      ) : null}
                      <div className="vsFieldHint">{source.snippet}</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 12 }}>
              <button type="button" className="vsBtnSecondary" onClick={voiceChat.onResetSession}>
                {t("清空本轮", "Clear session")}
              </button>
            </div>
          </div>

          <div className="vsCardSection border-top">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
              <h3 className="vsCardSubTitle">{t("历史语音 Agent 会话", "Voice agent session history")}</h3>
              <button
                type="button"
                className="vsBtnSecondary"
                onClick={() => void voiceChat.onLoadVoiceAgentHistory()}
                disabled={voiceChat.voiceAgentHistoryBusy}
              >
                {voiceChat.voiceAgentHistoryBusy ? t("加载中", "Loading") : t("刷新历史", "Refresh")}
              </button>
            </div>
            {voiceChat.voiceAgentHistoryError ? (
              <div className="vsVoiceMemoryNotice">{voiceChat.voiceAgentHistoryError}</div>
            ) : null}
            {voiceChat.voiceAgentHistorySessions.length > 0 ? (
              <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
                {voiceChat.voiceAgentHistorySessions.map((session) => (
                  <button
                    key={session.id}
                    type="button"
                    className="vsBtnSecondary"
                    onClick={() => void voiceChat.onOpenVoiceAgentSession(session.id)}
                    disabled={voiceChat.voiceAgentHistoryBusy}
                    style={{ justifyContent: "flex-start", textAlign: "left" }}
                  >
                    <span style={{ display: "grid", gap: 2 }}>
                      <strong>{session.provider} · {session.status}</strong>
                      <span className="vsFieldHint">
                        {session.model || t("未记录模型", "Model not recorded")} · {session.started_at}
                      </span>
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="vsFieldHint" style={{ marginTop: 12 }}>
                {t("刷新后会显示后端已持久化的语音 Agent 会话。", "Refresh to show voice agent sessions persisted by the backend.")}
              </p>
            )}

            {selectedHistory ? (
              <div style={{ display: "grid", gap: 12, marginTop: 16 }}>
                <div className="vsRealtimeContent" style={{ border: "1px solid var(--line)", borderRadius: 10, padding: 12, background: "white" }}>
                  <div style={{ fontWeight: 700 }}>
                    {t("已打开历史会话", "Opened history session")}: {selectedHistory.id}
                  </div>
                  <div className="vsFieldHint">
                    {selectedHistory.provider} · {selectedHistory.model || t("未记录模型", "Model not recorded")} · {selectedHistory.voice || t("未记录音色", "Voice not recorded")}
                  </div>
                  <div className="vsFieldHint">
                    {t(
                      `轮次 ${selectedHistory.turns.length}，工具事件 ${selectedHistory.tool_events.length}，时间线 ${selectedHistoryTimeline.length}`,
                      `${selectedHistory.turns.length} turns, ${selectedHistory.tool_events.length} tool events, ${selectedHistoryTimeline.length} timeline events`
                    )}
                  </div>
                </div>

                {selectedHistoryTimeline.length > 0 ? (
                  <div className="vsField">
                    <label className="vsFieldLabel" style={{ fontSize: 16, color: "var(--primary-color)" }}>
                      {t("会话时间线回放 (Timeline Replay)", "Session Timeline Replay")}
                    </label>
                    <div style={{ display: "grid", gap: 12, marginTop: 8 }}>
                      {selectedHistoryTimeline.map((event) => {
                        const label = timelineEventLabels[event.event_type] || event.event_type;
                        const mainText = timelineText(event);
                        const isAssistant = event.event_type === "assistant_response";
                        const isUser = event.event_type === "user_transcript";
                        const isTool = event.source === "tool_event";

                        let bgColor = "white";
                        let borderColor = "var(--line)";
                        if (isUser) {
                          bgColor = "var(--surface-color)";
                        } else if (isAssistant) {
                          bgColor = "var(--primary-color-light, #f0f7ff)";
                          borderColor = "var(--primary-color)";
                        } else if (isTool) {
                          bgColor = "#fffcf0";
                        }

                        return (
                          <div
                            key={event.id}
                            className="vsRealtimeContent"
                            style={{ border: `1px solid ${borderColor}`, borderRadius: 10, padding: 12, background: bgColor }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                              <div style={{ fontWeight: 700 }}>
                                {label}
                                {event.tool_name ? ` · ${event.tool_name}` : ""}
                              </div>
                              {event.elapsed_ms !== undefined ? (
                                <span className="vsVoiceMemoryChip" style={{ margin: 0, opacity: 0.8 }}>
                                  {event.elapsed_ms}ms
                                </span>
                              ) : null}
                            </div>
                            <div className="vsFieldHint" style={{ marginTop: 4, marginBottom: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
                              <span>{event.timestamp}</span>
                              {event.turn_id ? <span>· turn: {event.turn_id}</span> : null}
                              {event.stage ? <span>· stage: {event.stage}</span> : null}
                              {event.provider ? <span>· {event.provider}</span> : null}
                              {event.transport ? <span>· {event.transport}</span> : null}
                            </div>
                            {mainText ? (
                              <div style={{ marginTop: 4, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                                {mainText}
                              </div>
                            ) : null}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : null}

                <details style={{ marginTop: 16 }}>
                  <summary className="vsFieldHint" style={{ cursor: "pointer", userSelect: "none" }}>
                    {t("查看原始轮次与事件", "View raw turns and events")}
                  </summary>
                  <div style={{ display: "grid", gap: 16, marginTop: 12 }}>
                    {selectedHistory.turns.length > 0 ? (
                      <div className="vsField">
                        <label className="vsFieldLabel">{t("历史轮次", "History turns")}</label>
                        <div style={{ display: "grid", gap: 8 }}>
                          {selectedHistory.turns.map((turn) => (
                            <div
                              key={turn.id}
                              className="vsRealtimeContent"
                              style={{ border: "1px solid var(--line)", borderRadius: 10, padding: 12, background: "white" }}
                            >
                              <div style={{ fontWeight: 700 }}>{turn.turn_id || t("未记录 turn_id", "turn_id not recorded")}</div>
                              {turn.user_text ? <div>{t("用户", "User")}: {turn.user_text}</div> : null}
                              {turn.assistant_text ? <div>{t("助手", "Assistant")}: {turn.assistant_text}</div> : null}
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {selectedHistory.tool_events.length > 0 ? (
                      <div className="vsField">
                        <label className="vsFieldLabel">{t("历史工具事件", "History tool events")}</label>
                        <div style={{ display: "grid", gap: 8 }}>
                          {selectedHistory.tool_events.map((event) => (
                            <div
                              key={event.id}
                              className="vsRealtimeContent"
                              style={{ border: "1px solid var(--line)", borderRadius: 10, padding: 12, background: "white" }}
                            >
                              <div style={{ fontWeight: 700 }}>{event.event_type} · {event.tool_name || t("未记录工具", "Tool not recorded")}</div>
                              {event.query ? <div className="vsFieldHint">{event.query}</div> : null}
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                </details>

                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <button type="button" className="vsBtnSecondary" onClick={voiceChat.onExportVoiceAgentSession}>
                    {t("导出 JSON", "Export JSON")}
                  </button>
                </div>
                {voiceChat.voiceAgentHistoryExportText ? (
                  <textarea
                    className="vsTextarea"
                    value={voiceChat.voiceAgentHistoryExportText}
                    readOnly
                    rows={6}
                    aria-label={t("历史会话 JSON 导出", "History session JSON export")}
                  />
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}
