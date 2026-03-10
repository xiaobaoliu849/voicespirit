import {
  CHAT_QUICK_ACTIONS,
  type QuickAction
} from "../appConfig";
import ErrorNotice from "../components/ErrorNotice";
import type { UseChatResult } from "../hooks/useChat";
import type { UseVoiceChatResult } from "../hooks/useVoiceChat";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  chat: UseChatResult;
  voiceChat: UseVoiceChatResult;
  errorRuntimeContext: ErrorRuntimeContext;
};

const quickActions: QuickAction[] = CHAT_QUICK_ACTIONS;

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

/* ── Composer sub-component (shared between empty & chat modes) ── */
function Composer({ chat, voiceChat }: { chat: UseChatResult; voiceChat: UseVoiceChatResult }) {
  return (
    <div className="vsComposer">
      <textarea
        rows={1}
        value={chat.chatInput}
        onChange={(e) => chat.onInputChange(e.target.value)}
        placeholder="输入问题或指令，Shift+Enter 换行"
        onKeyDown={chat.onComposerKeyDown}
      />
      <div className="vsComposerToolbar">
        <div className="vsComposerToolbarLeft">
          <button type="button" className="vsToolbarBtn" aria-label="附件">
            <PaperclipIcon />
          </button>
          <button
            type="button"
            className={`vsToolbarBtn ${voiceChat.voiceChatRecording ? "recording" : ""}`}
            aria-label="语音聊天"
            onClick={() => void voiceChat.onToggleRecording()}
            disabled={!voiceChat.voiceChatSupported || voiceChat.voiceChatBusy}
          >
            {voiceChat.voiceChatRecording ? <StopIcon /> : <MicIcon />}
          </button>
        </div>
        <div className="vsComposerToolbarRight">
          <button type="submit" className="vsSendBtn" disabled={chat.chatBusy} aria-label="发送">
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
  const runtimeState = voiceChat.voiceChatConnected || voiceChat.voiceChatRecording
    ? "会话中"
    : voiceChat.voiceChatBusy
      ? "连接中"
      : "待机";

  return (
    <div
      style={{
        marginBottom: 16,
        padding: 14,
        borderRadius: 18,
        border: "1px solid var(--border-color)",
        background: "var(--surface-color)",
        boxShadow: "var(--card-shadow)",
        display: "grid",
        gap: 8,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <strong style={{ fontSize: 14 }}>实时语音入口</strong>
        <span className="vsFieldHint">{runtimeState}</span>
      </div>
      <div className="vsFieldHint" style={{ textAlign: "left" }}>
        麦克风按钮已同步：使用 {voiceChat.voiceChatProvider} / {voiceChat.voiceChatModel || "默认模型"}。
        可通过上方供应商与模型快速切换。
      </div>
      <div className="vsEmptyDesc" style={{ minHeight: 0, textAlign: "left" }}>
        {voiceChat.voiceChatStatus}
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
  );
}

export default function ChatPage({ chat, voiceChat, errorRuntimeContext }: Props) {
  const combinedMessages = [...chat.chatMessages, ...voiceChat.sessionSummary];
  const isEmpty = !combinedMessages.length;
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
            <span>供应商</span>
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
          {chat.chatMessages.some((m) => m.memorySaved) && (
            <div
              style={{
                fontSize: 12,
                padding: "2px 8px",
                backgroundColor: "var(--primary-color)",
                color: "white",
                borderRadius: 4,
                opacity: 0.9,
                display: "flex",
                alignItems: "center",
                gap: 4
              }}
            >
              <span>已存入记忆</span>
            </div>
          )}

          <div className="vsTopbarDivider" />

          <label className="vsTopbarField vsTopbarModelField">
            <span>模型</span>
            <input
              list="chat-model-options"
              value={chat.chatModel}
              onChange={(e) => chat.onModelChange(e.target.value)}
              placeholder={chat.chatModelOptions[0] || "输入模型名称"}
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
            <span>音色</span>
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

      {/* ── Body ── */}
      <div className={`vsChatBody ${showWelcome ? "empty" : ""}`}>
        {showWelcome ? (
          /* ═══ EMPTY STATE: centered like Claude/Gemini ═══ */
          <div className="vsChatCentered">
            <div className="vsWelcome">
              <h2>你好，有什么可以帮你的？</h2>
            </div>

            <form onSubmit={chat.onSubmit} className="vsComposerWrapCentered">
              <Composer chat={chat} voiceChat={voiceChat} />
            </form>

            <VoiceChatRuntimeNotice
              voiceChat={voiceChat}
              errorRuntimeContext={errorRuntimeContext}
            />

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

            <p className="vsChatDisclaimer">AI 生成内容可能存在误差，请按需核对关键信息。</p>
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
                <strong>
                  {msg.role === "user" ? "你" : "助手"}
                  {msg.memorySaved && (
                    <span style={{ fontSize: "10px", marginLeft: "8px", color: "rgba(255,255,255,0.7)" }}>✓ 已记忆</span>
                  )}
                  {msg.memoriesUsed ? (
                    <span style={{ fontSize: "10px", marginLeft: "8px", color: "var(--primary-color)" }}>🧠 回忆了 {msg.memoriesUsed} 条</span>
                  ) : null}
                </strong>
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
                <strong>你 <span className="vsStreamingIndicator">(实时)</span></strong>
                <p>{voiceChat.voiceChatTranscript}</p>
              </div>
            )}
            {isVoiceActive && voiceChat.voiceChatReply && (
              <div className="bubble assistant live">
                <strong>助手 <span className="vsStreamingIndicator">(正在回复)</span></strong>
                <p>{voiceChat.voiceChatReply}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Bottom composer (visible when not in welcome mode or when voice active) ── */}
      {(!showWelcome || isVoiceActive) && (
        <form onSubmit={chat.onSubmit} className="vsComposerWrap">
          <Composer chat={chat} voiceChat={voiceChat} />

          {/* Runtime notice only if there's an error or we need status while chatting */}
          {(voiceChat.voiceChatError || !isVoiceActive) && (
            <VoiceChatRuntimeNotice
              voiceChat={voiceChat}
              errorRuntimeContext={errorRuntimeContext}
            />
          )}

          <p className="vsChatDisclaimer">AI 生成内容可能存在误差，请按需核对关键信息。</p>
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
