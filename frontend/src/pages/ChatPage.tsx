import {
  getChatQuickActions,
  type QuickAction
} from "../appConfig";
import ErrorNotice from "../components/ErrorNotice";
import type { UseChatResult } from "../hooks/useChat";
import type { UseVoiceChatResult } from "../hooks/useVoiceChat";
import { useI18n } from "../i18n";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  chat: UseChatResult;
  voiceChat: UseVoiceChatResult;
  errorRuntimeContext: ErrorRuntimeContext;
};

/* ── Inline SVG icons ── */
const PaperclipIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>
);
const MicIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" x2="12" y1="19" y2="22"></line></svg>
);
const StopIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="14" height="14" x="5" y="5" rx="2"></rect></svg>
);
const SendIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3.714 3.048a.498.498 0 0 0-.683.627l2.843 7.627a2 2 0 0 1 0 1.396l-2.842 7.627a.498.498 0 0 0 .682.627l18.168-8.215a.5.5 0 0 0 0-.904z"></path><line x1="6" x2="11" y1="12" y2="12"></line></svg>
);
const SpinnerIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="vsSpin"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>
);

function isVoiceRealtimeModel(provider: string, model: string): boolean {
  const normalizedProvider = (provider || "").trim().toLowerCase();
  const normalizedModel = (model || "").trim().toLowerCase();
  if (!normalizedModel) {
    return false;
  }
  if (normalizedProvider === "dashscope") {
    return normalizedModel.includes("realtime");
  }
  if (normalizedProvider === "google") {
    return (
      normalizedModel.includes("native-audio") ||
      normalizedModel.includes("live") ||
      normalizedModel.includes("realtime")
    );
  }
  return normalizedModel.includes("realtime");
}

/* ── Composer sub-component (shared between empty & chat modes) ── */
function Composer({
  chat,
  voiceChat,
  textChatBlockedReason,
}: {
  chat: UseChatResult;
  voiceChat: UseVoiceChatResult;
  textChatBlockedReason: string;
}) {
  const { t } = useI18n();
  const textChatBlocked = Boolean(textChatBlockedReason);
  return (
    <div className="vsComposer">
      <textarea
        rows={1}
        value={chat.chatInput}
        onChange={(e) => chat.onInputChange(e.target.value)}
        placeholder={t("输入问题或指令，Shift+Enter 换行", "Type a question or instruction. Shift+Enter for a new line")}
        onKeyDown={chat.onComposerKeyDown}
        disabled={textChatBlocked}
      />
      {textChatBlocked ? <div className="vsComposerInlineHint">{textChatBlockedReason}</div> : null}
      <div className="vsComposerToolbar">
        <div className="vsComposerToolbarLeft">
          <button type="button" className="vsToolbarBtn" aria-label={t("附件", "Attachment")}>
            <PaperclipIcon />
          </button>
          <button
            type="button"
            className={`vsToolbarBtn ${voiceChat.voiceChatRecording ? "recording" : ""}`}
            aria-label={t("语音聊天", "Voice chat")}
            onClick={() => void voiceChat.onToggleRecording()}
            disabled={!voiceChat.voiceChatSupported || voiceChat.voiceChatBusy}
          >
            {voiceChat.voiceChatRecording ? <StopIcon /> : <MicIcon />}
          </button>
        </div>
        <div className="vsComposerToolbarRight">
          <button
            type="submit"
            className="vsSendBtn"
            disabled={chat.chatBusy || textChatBlocked}
            aria-label={t("发送", "Send")}
            title={textChatBlocked ? textChatBlockedReason : t("发送", "Send")}
          >
            {chat.chatBusy ? <SpinnerIcon /> : <SendIcon />}
          </button>
        </div>
      </div>
    </div>
  );
}

function VoiceChatRuntimeNotice({
  voiceChat,
  errorRuntimeContext,
}: {
  voiceChat: UseVoiceChatResult;
  errorRuntimeContext: ErrorRuntimeContext;
}) {
  const { t } = useI18n();
  const runtimeState = voiceChat.voiceChatConnected || voiceChat.voiceChatRecording
    ? t("会话中", "In session")
    : voiceChat.voiceChatBusy
      ? t("连接中", "Connecting")
      : t("待机", "Idle");

  return (
    <div className="vsVoiceRuntimeNotice">
      <div className="vsVoiceRuntimeRow">
        <strong className="vsVoiceRuntimeTitle">{t("实时语音", "Realtime voice")}</strong>
        <span className="vsFieldHint">{runtimeState}</span>
      </div>
      <p className="vsVoiceRuntimeMeta">
        {t(
          `麦克风按钮当前使用 ${voiceChat.voiceChatProvider} / ${voiceChat.voiceChatModel || "默认实时模型"}`,
          `Microphone is using ${voiceChat.voiceChatProvider} / ${voiceChat.voiceChatModel || "default realtime model"}`
        )}
      </p>
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
  );
}

export default function ChatPage({ chat, voiceChat, errorRuntimeContext }: Props) {
  const { t } = useI18n();
  const quickActions: QuickAction[] = getChatQuickActions(t);
  const combinedMessages = [...chat.chatMessages, ...voiceChat.sessionSummary];
  const isEmpty = !combinedMessages.length;
  const textChatBlockedReason = isVoiceRealtimeModel(chat.chatProvider, chat.chatModel)
    ? t(
      "当前是实时语音模型。请点击麦克风开始对话，或切换到普通文本模型后再发送文字。",
      "The current model is a realtime voice model. Use the microphone to start, or switch to a standard text model before sending."
    )
    : "";
  const hasSavedMemory = combinedMessages.some((msg) => msg.memorySaved);
  const latestMemoryActivity = [...combinedMessages]
    .reverse()
    .find((msg) => msg.memorySaved || msg.memoriesUsed);
  // Use a variable to track if we should show the welcome/empty state
  // We hide it if there's an active voice session even if message list is empty
  const showWelcome = isEmpty && !voiceChat.voiceChatRecording && !voiceChat.voiceChatConnected;
  const isVoiceActive = voiceChat.voiceChatRecording || voiceChat.voiceChatConnected;

  return (
    <section className="vsChatWorkspace">
      {/* ── Topbar ── */}
      <header className="vsTopbar">
        <div className="vsTopbarLeft">
          <label className="vsTopbarField">
            <span>{t("供应商", "Provider")}</span>
            <select
              value={chat.chatProvider}
              onChange={(e) => chat.onProviderChange(e.target.value)}
            >
              {chat.chatProviderOptions.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>

          <div className="vsTopbarDivider" />

          {/* 记忆状态标识 */}
          {hasSavedMemory || latestMemoryActivity?.memoriesUsed ? (
            <div className="vsChatMemoryChip">
              {hasSavedMemory ? <span>{t("已存入记忆", "Saved to memory")}</span> : null}
              {latestMemoryActivity?.memoriesUsed ? (
                <span>
                  {hasSavedMemory ? " · " : ""}
                  {t(
                    `已回忆 ${latestMemoryActivity.memoriesUsed} 条记忆`,
                    `Recalled ${latestMemoryActivity.memoriesUsed} memories`
                  )}
                </span>
              ) : null}
            </div>
          ) : null}

          <div className="vsTopbarDivider" />

          <label className="vsTopbarField vsTopbarModelField">
            <span>{t("模型", "Model")}</span>
            <input
              list="chat-model-options"
              value={chat.chatModel}
              onChange={(e) => chat.onModelChange(e.target.value)}
              placeholder={chat.chatModelOptions[0] || t("输入模型名称", "Enter a model name")}
            />
            {chat.chatModelOptions.length ? (
              <datalist id="chat-model-options">
                {chat.chatModelOptions.map((item) => (
                  <option key={item} value={item} />
                ))}
              </datalist>
            ) : null}
          </label>

          {/* ── NEW: Topbar Voice Selection ── */}
          <div className="vsTopbarDivider" />
          <label className="vsTopbarVoiceField">
            <span>{t("音色", "Voice")}</span>
            <select
              value={voiceChat.voiceChatVoice}
              onChange={(e) => voiceChat.onVoiceChange(e.target.value)}
              disabled={voiceChat.voiceChatRecording || voiceChat.voiceChatConnected}
            >
              {voiceChat.voiceChatVoiceOptions.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      <div className="vsChatRuntimeBar">
        <VoiceChatRuntimeNotice
          voiceChat={voiceChat}
          errorRuntimeContext={errorRuntimeContext}
        />
      </div>

      {/* ── Body ── */}
      <div className={`vsChatBody ${showWelcome ? "empty" : ""}`}>
        {showWelcome ? (
          /* ═══ EMPTY STATE: centered like Claude/Gemini ═══ */
          <div className="vsChatCentered">
            <div className="vsWelcome">
              <h1>VoiceSpirit</h1>
            </div>

            <form onSubmit={chat.onSubmit} className="vsComposerWrapCentered">
              <Composer
                chat={chat}
                voiceChat={voiceChat}
                textChatBlockedReason={textChatBlockedReason}
              />
            </form>

            <div className="vsQuickActions">
              {quickActions.map((action) => (
                <button
                  key={action.title}
                  type="button"
                  className="vsQuickActionPill"
                  onClick={() => chat.onQuickAction(action.prompt)}
                >
                  <span className="vsQuickActionIcon" aria-hidden="true">
                    {action.icon}
                  </span>
                  <span>{action.title}</span>
                </button>
              ))}
            </div>

            <p className="vsChatDisclaimer">{t("AI 生成内容可能存在误差。", "AI content may contain mistakes.")}</p>
            <ErrorNotice
              message={chat.chatError}
              scope="chat"
              context={{
                ...errorRuntimeContext,
                provider: chat.chatProvider,
                model: chat.chatModel
              }}
            />
          </div>
        ) : (
          /* ═══ MESSAGE LIST ═══ */
          <div className="vsMessageList">
            {combinedMessages.map((msg, idx) => (
              <div
                key={`${idx}-${msg.role}`}
                className={msg.role === "user" ? "bubble user" : "bubble assistant"}
              >
                {msg.memorySaved || msg.memoriesUsed || msg.memorySourceSummary ? (
                  <div className="vsBubbleMeta">
                    {msg.memorySaved ? (
                      <span className="vsBubbleMemoryTag saved">{t("✓ 已记忆", "✓ Saved")}</span>
                    ) : null}
                    {msg.memoriesUsed ? (
                      <span className="vsBubbleMemoryTag used">
                        {t(`🧠 回忆了 ${msg.memoriesUsed} 条`, `🧠 Recalled ${msg.memoriesUsed}`)}
                      </span>
                    ) : null}
                    {msg.memorySourceSummary ? (
                      <span className="vsBubbleMemoryTag used">{msg.memorySourceSummary}</span>
                    ) : null}
                  </div>
                ) : null}
                <p>
                  {msg.content ||
                    (chat.chatBusy &&
                      idx === chat.chatMessages.length - 1 &&
                      msg.role === "assistant"
                      ? "..."
                      : "")}
                </p>
              </div>
            ))}

            {/* ── NEW: Live Streaming Bubbles ── */}
            {isVoiceActive && voiceChat.voiceChatTranscript && (
              <div className="bubble user live">
                <div className="vsBubbleMeta">
                  <span className="vsStreamingIndicator">{t("(实时输入)", "(live input)")}</span>
                </div>
                <p>{voiceChat.voiceChatTranscript}</p>
              </div>
            )}
            {isVoiceActive && voiceChat.voiceChatReply && (
              <div className="bubble assistant live">
                <div className="vsBubbleMeta">
                  <span className="vsStreamingIndicator">{t("(正在回复)", "(replying)")}</span>
                </div>
                <p>{voiceChat.voiceChatReply}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Bottom composer (visible when not in welcome mode or when voice active) ── */}
      {(!showWelcome || isVoiceActive) && (
        <form onSubmit={chat.onSubmit} className="vsComposerWrap">
          <Composer
            chat={chat}
            voiceChat={voiceChat}
            textChatBlockedReason={textChatBlockedReason}
          />

          <p className="vsChatDisclaimer">{t("AI 生成内容可能存在误差，请按需核对关键信息。", "AI-generated content may contain mistakes. Verify important details when needed.")}</p>
          <ErrorNotice
            message={chat.chatError}
            scope="chat"
            context={{
              ...errorRuntimeContext,
              provider: chat.chatProvider,
              model: chat.chatModel
            }}
          />
        </form>
      )}
    </section>
  );
}
