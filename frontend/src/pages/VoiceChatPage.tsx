import ErrorNotice from "../components/ErrorNotice";
import type { UseVoiceChatResult } from "../hooks/useVoiceChat";
import { useI18n } from "../i18n";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  voiceChat: UseVoiceChatResult;
  errorRuntimeContext: ErrorRuntimeContext;
};

export default function VoiceChatPage({ voiceChat, errorRuntimeContext }: Props) {
  const { t } = useI18n();
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
            </div>

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
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 12 }}>
              <button type="button" className="vsBtnSecondary" onClick={voiceChat.onResetSession}>
                {t("清空本轮", "Clear session")}
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
