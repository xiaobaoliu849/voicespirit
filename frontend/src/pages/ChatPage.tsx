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

export default function ChatPage({ chat, voiceChat, errorRuntimeContext }: Props) {
  const combinedMessages = [...chat.chatMessages, ...voiceChat.sessionSummary];

  return (
    <section className="vsChatWorkspace">
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
        </div>

        <div className="vsTopbarActions">
          <button
            type="button"
            className="vsTopbarBtn"
            onClick={() => void voiceChat.onToggleRecording()}
            disabled={!voiceChat.voiceChatSupported || voiceChat.voiceChatBusy}
          >
            {voiceChat.voiceChatRecording ? "结束语音" : "语音聊天"}
          </button>
          <button type="button" className="vsTopbarBtn">
            分享
          </button>
          <button type="button" className="vsTopbarIconBtn" aria-label="更多操作">
            ···
          </button>
        </div>
      </header>

      <div className="vsChatBody">
        {voiceChat.voiceChatRecording || voiceChat.voiceChatConnected ? (
          <div
            style={{
              marginBottom: 16,
              padding: 18,
              borderRadius: 20,
              border: "1px solid var(--border-color)",
              background: "var(--surface-color)",
              boxShadow: "var(--card-shadow)",
              display: "grid",
              gap: 14,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
              <div>
                <strong style={{ display: "block", fontSize: 16 }}>语音会话中</strong>
                <span className="vsFieldHint">
                  保持在当前聊天页内。用户转录和助手回复会继续写回这条对话。
                </span>
              </div>
              <button
                type="button"
                className="vsBtnSecondary"
                onClick={() => void voiceChat.onToggleRecording()}
              >
                结束会话
              </button>
            </div>

            <div style={{ display: "grid", gap: 12, gridTemplateColumns: "1fr 1fr" }}>
              <label className="vsTopbarField" style={{ minWidth: 0 }}>
                <span>实时模型</span>
                <input
                  list="voice-chat-model-options"
                  value={voiceChat.voiceChatModel}
                  onChange={(e) => voiceChat.onModelChange(e.target.value)}
                  disabled={voiceChat.voiceChatRecording}
                />
                {voiceChat.voiceChatModelOptions.length ? (
                  <datalist id="voice-chat-model-options">
                    {voiceChat.voiceChatModelOptions.map((item) => (
                      <option key={item} value={item} />
                    ))}
                  </datalist>
                ) : null}
              </label>

              <label className="vsTopbarField" style={{ minWidth: 0 }}>
                <span>实时音色</span>
                <select
                  value={voiceChat.voiceChatVoice}
                  onChange={(e) => voiceChat.onVoiceChange(e.target.value)}
                  disabled={voiceChat.voiceChatRecording}
                >
                  {voiceChat.voiceChatVoiceOptions.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 12,
              }}
            >
              <div className="vsCardSection" style={{ padding: 14 }}>
                <strong style={{ display: "block", marginBottom: 8 }}>你的实时转录</strong>
                <div className="vsEmptyDesc" style={{ minHeight: 72, textAlign: "left" }}>
                  {voiceChat.voiceChatTranscript || "开始说话后，这里会实时出现你的语音转录。"}
                </div>
              </div>
              <div className="vsCardSection" style={{ padding: 14 }}>
                <strong style={{ display: "block", marginBottom: 8 }}>助手实时回复</strong>
                <div className="vsEmptyDesc" style={{ minHeight: 72, textAlign: "left" }}>
                  {voiceChat.voiceChatReply || "模型语音和文本会同步回到这里。"}
                </div>
              </div>
            </div>

            <ErrorNotice
              message={voiceChat.voiceChatError}
              scope="voice-chat"
              context={{
                ...errorRuntimeContext,
                provider: "Google",
                model: voiceChat.voiceChatModel,
                voice: voiceChat.voiceChatVoice,
              }}
            />
          </div>
        ) : null}

        {!combinedMessages.length ? (
          <div className="vsChatEmptyState">
            <div className="vsEmptyLogo">AI</div>
            <h2>开始一段新对话</h2>
            <p>输入问题、任务或想法，也可以直接从这里发起实时语音对话。</p>
            <div className="vsQuickActions">
              {quickActions.map((action) => (
                <button
                  key={action.title}
                  type="button"
                  className="vsQuickActionBtn"
                  onClick={() => chat.onQuickAction(action.prompt)}
                >
                  <span className="vsQuickActionIcon" aria-hidden="true">
                    {action.icon}
                  </span>
                  <span>{action.title}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
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
          </div>
        )}
      </div>

      <form onSubmit={chat.onSubmit} className="vsComposerWrap">
        <div className="vsComposer">
          <button type="button" className="vsAttachBtn" aria-label="附件">
            +
          </button>
          <button
            type="button"
            className="vsAttachBtn"
            aria-label="语音聊天"
            onClick={() => void voiceChat.onToggleRecording()}
            disabled={!voiceChat.voiceChatSupported || voiceChat.voiceChatBusy}
          >
            {voiceChat.voiceChatRecording ? "■" : "🎤"}
          </button>
          <textarea
            rows={1}
            value={chat.chatInput}
            onChange={(e) => chat.onInputChange(e.target.value)}
            placeholder="输入问题或指令，Shift+Enter 换行"
            onKeyDown={chat.onComposerKeyDown}
          />
          <button type="submit" className="vsSendBtn" disabled={chat.chatBusy}>
            {chat.chatBusy ? "发送中" : "发送"}
          </button>
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
      </form>
    </section >
  );
}
