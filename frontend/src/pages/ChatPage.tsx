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
  const isVoiceActive = voiceChat.voiceChatRecording || voiceChat.voiceChatConnected;
  const hasInput = chat.chatInput.trim().length > 0;
  const isRealtime = isVoiceRealtimeModel(chat.chatProvider, chat.chatModel);

  return (
    <div className="vsComposer">
      {!isVoiceActive ? (
        <>
          <textarea
            rows={1}
            value={chat.chatInput}
            onChange={(e) => chat.onInputChange(e.target.value)}
            placeholder={t("随便说点什么...一个想法、半句话...", "Say anything... a thought, half a sentence...")}
            onKeyDown={chat.onComposerKeyDown}
            disabled={textChatBlocked}
          />
          {textChatBlocked ? <div className="vsComposerInlineHint">{textChatBlockedReason}</div> : null}
        </>
      ) : (
        <div className="vsLiveSessionBanner">
          <div className="vsPulseDot vsPulseDotRed" />
          <span className="vsLiveSessionLabel">
            {voiceChat.voiceChatRecording ? t("正在聆听您的声音...", "Listening to your voice...") : t("实时通话连接中...", "Connecting live session...")}
          </span>
        </div>
      )}

      <div className="vsComposerToolbar">
        <div className="vsComposerToolbarLeft">
          <button type="button" className="vsToolbarBtn" aria-label={t("附件", "Attachment")}>
            <PaperclipIcon />
          </button>
          
          {/* Alma-style inline dropdowns */}
          <select
            className="vsComposerPillSelect"
            value={chat.chatModel}
            onChange={(e) => chat.onModelChange(e.target.value)}
            title={t("切换模型", "Switch model")}
          >
            {chat.chatModelOptions.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
            {!chat.chatModelOptions.includes(chat.chatModel) && chat.chatModel && (
              <option value={chat.chatModel}>{chat.chatModel}</option>
            )}
          </select>

          {isRealtime && (
            <select
              className="vsComposerPillSelect"
              value={voiceChat.voiceChatVoice}
              onChange={(e) => voiceChat.onVoiceChange(e.target.value)}
              disabled={isVoiceActive}
              title={t("切换音色", "Switch voice")}
            >
              {voiceChat.voiceChatVoiceOptions.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          )}
        </div>

        <div className="vsComposerToolbarRight">
          {hasInput && !isVoiceActive ? (
            <button
              type="submit"
              className="vsSendBtn"
              disabled={chat.chatBusy || textChatBlocked}
              aria-label={t("发送", "Send")}
              title={textChatBlocked ? textChatBlockedReason : t("发送", "Send")}
            >
              {chat.chatBusy ? <SpinnerIcon /> : <SendIcon />}
            </button>
          ) : (
            <button
              type="button"
              className={`vsComposerVoiceBtn ${isVoiceActive ? "recording" : ""}`}
              aria-label={t("语音聊天", "Voice chat")}
              onClick={() => void voiceChat.onToggleRecording()}
              disabled={!voiceChat.voiceChatSupported || voiceChat.voiceChatBusy}
              title={isVoiceActive ? t("结束通话", "End session") : t("开始语音聊天", "Start voice chat")}
            >
              {isVoiceActive ? <StopIcon /> : <MicIcon />}
            </button>
          )}
        </div>
      </div>
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
  
  // Use a variable to track if we should show the welcome/empty state
  // We hide it if there's an active voice session even if message list is empty
  const showWelcome = isEmpty && !voiceChat.voiceChatRecording && !voiceChat.voiceChatConnected;
  const isVoiceActive = voiceChat.voiceChatRecording || voiceChat.voiceChatConnected;

  return (
    <section className="vsChatWorkspace">
      {/* ── Body ── */}
      <div className={`vsChatBody ${showWelcome ? "empty" : ""}`}>
        {showWelcome ? (
          /* ═══ EMPTY STATE: centered like Claude/Gemini ═══ */
          <div className="vsChatCentered">
            <div className="vsWelcomeHero">
              <div className="vsWelcomeHeroIcon">
                ✨
              </div>
              <div>
                <h1 className="vsWelcomeHeroTitle">{t("今天聊点什么？", "What shall we chat about today?")}</h1>
                <p className="vsWelcomeHeroSubtitle">{t("随便说点什么...剩下交给 VoiceSpirit。", "Say anything... leave the rest to VoiceSpirit.")}</p>
              </div>
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
            {voiceChat.voiceChatError && (
              <div className="vsVoiceChatErrorSection">
                <h4 className="vsVoiceChatErrorTitle">{t("实时语音", "Realtime Voice")}</h4>
                <ErrorNotice
                  message={voiceChat.voiceChatError}
                  scope="voice_chat"
                  context={{
                    ...errorRuntimeContext,
                    provider: voiceChat.voiceChatProvider,
                    model: voiceChat.voiceChatModel
                  }}
                />
              </div>
            )}
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

            {/* ── Live Streaming Bubbles ── */}
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
        <div className="vsComposerWrap">
          <form onSubmit={chat.onSubmit}>
            <Composer
              chat={chat}
              voiceChat={voiceChat}
              textChatBlockedReason={textChatBlockedReason}
            />
          </form>

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
          {voiceChat.voiceChatError && (
            <div className="vsVoiceChatErrorSection">
              <h4 className="vsVoiceChatErrorTitle">{t("实时语音", "Realtime Voice")}</h4>
              <ErrorNotice
                message={voiceChat.voiceChatError}
                scope="voice_chat"
                context={{
                  ...errorRuntimeContext,
                  provider: voiceChat.voiceChatProvider,
                  model: voiceChat.voiceChatModel
                }}
              />
            </div>
          )}
        </div>
      )}
    </section>
  );
}
