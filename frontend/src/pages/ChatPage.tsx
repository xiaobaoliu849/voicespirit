import {
  CHAT_QUICK_ACTIONS,
  PROVIDERS,
  type QuickAction
} from "../appConfig";
import ErrorNotice from "../components/ErrorNotice";
import type { UseChatResult } from "../hooks/useChat";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  chat: UseChatResult;
  errorRuntimeContext: ErrorRuntimeContext;
};

const quickActions: QuickAction[] = CHAT_QUICK_ACTIONS;

export default function ChatPage({ chat, errorRuntimeContext }: Props) {
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
              {PROVIDERS.map((item) => (
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
              value={chat.chatModel}
              onChange={(e) => chat.onModelChange(e.target.value)}
              placeholder="gemini-2.5-flash"
            />
          </label>
        </div>

        <div className="vsTopbarActions">
          <button type="button" className="vsTopbarBtn">
            分享
          </button>
          <button type="button" className="vsTopbarIconBtn" aria-label="更多操作">
            ···
          </button>
        </div>
      </header>

      <div className="vsChatBody">
        {!chat.chatMessages.length ? (
          <div className="vsChatEmptyState">
            <div className="vsEmptyLogo">AI</div>
            <h2>开始一段新对话</h2>
            <p>输入问题、任务或想法，我会直接给出可执行结果。</p>
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
            {chat.chatMessages.map((msg, idx) => (
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
