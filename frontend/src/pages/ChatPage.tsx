import { useEffect, useRef, useState } from "react";
import {
  getChatQuickActions,
  type QuickAction
} from "../appConfig";
import { extractPdfText, type VoiceAgentRunLink } from "../api";
import ErrorNotice from "../components/ErrorNotice";
import VoiceAgentHistoryPanel from "../components/VoiceAgentHistoryPanel";
import type { UseChatResult } from "../hooks/useChat";
import type { UseVoiceChatResult } from "../hooks/useVoiceChat";
import { useI18n } from "../i18n";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  chat: UseChatResult;
  voiceChat: UseVoiceChatResult;
  errorRuntimeContext: ErrorRuntimeContext;
  onResumeAgentRun?: (link: VoiceAgentRunLink) => void | Promise<void>;
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
const PhoneIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.78 19.78 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.78 19.78 0 0 1 2.12 4.18 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.12.9.33 1.77.62 2.6a2 2 0 0 1-.45 2.11L8.09 9.62a16 16 0 0 0 6.29 6.29l1.19-1.19a2 2 0 0 1 2.11-.45c.83.29 1.7.5 2.6.62A2 2 0 0 1 22 16.92Z"></path></svg>
);
const SendIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3.714 3.048a.498.498 0 0 0-.683.627l2.843 7.627a2 2 0 0 1 0 1.396l-2.842 7.627a.498.498 0 0 0 .682.627l18.168-8.215a.5.5 0 0 0 0-.904z"></path><line x1="6" x2="11" y1="12" y2="12"></line></svg>
);
const SpinnerIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="vsSpin"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>
);
const CopyIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="14" height="14" x="8" y="8" rx="2"></rect><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"></path></svg>
);

const HistoryIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><path d="M3 3v5h5"></path><path d="M12 7v5l4 2"></path></svg>
);

function isVoiceRealtimeModel(provider: string, model: string): boolean {
  const normalizedProvider = (provider || "").trim().toLowerCase();
  const normalizedModel = (model || "").trim().toLowerCase();
  if (!normalizedModel) {
    return false;
  }
  if (normalizedProvider === "dashscope") {
    return normalizedModel.includes("realtime") || normalizedModel.includes("livetranslate");
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

async function copyTextToClipboard(value: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(value);
      return;
    } catch {
      // Fall through to the desktop WebView-compatible selection path.
    }
  }
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.inset = "-9999px auto auto -9999px";
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  if (!copied) {
    throw new Error("clipboard copy failed");
  }
}

type SpeechRecognitionResultLike = {
  readonly isFinal: boolean;
  readonly 0: { readonly transcript: string };
};

type SpeechRecognitionEventLike = Event & {
  readonly resultIndex: number;
  readonly results: ArrayLike<SpeechRecognitionResultLike>;
};

type SpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type SpeechRecognitionWindow = Window & {
  SpeechRecognition?: new () => SpeechRecognitionLike;
  webkitSpeechRecognition?: new () => SpeechRecognitionLike;
};

/* ── Composer sub-component (shared between empty & chat modes) ── */
function Composer({
  chat,
  voiceChat,
}: {
  chat: UseChatResult;
  voiceChat: UseVoiceChatResult;
}) {
  const { t } = useI18n();
  const isVoiceActive = voiceChat.voiceChatRecording || voiceChat.voiceChatConnected;
  const hasInput = chat.chatInput.trim().length > 0;
  const isRealtime = isVoiceRealtimeModel(chat.chatProvider, chat.chatModel);
  const isLiveTranslate = voiceChat.voiceChatLiveTranslate;
  const textChatBlockedReason = isRealtime
    ? t(
      "当前是实时语音/实时翻译模型。请点击实时通话按钮开始语音会话，或切换到普通文本模型后再发送文字。",
      "The current model is realtime voice/live translation only. Start a realtime call, or switch to a text model before sending."
    )
    : "";
  const [dictating, setDictating] = useState(false);
  const [dictationError, setDictationError] = useState("");
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  function appendDictationText(text: string) {
    const clean = text.trim();
    if (!clean) {
      return;
    }
    const current = chat.chatInput.trimEnd();
    chat.onInputChange(current ? `${current} ${clean}` : clean);
  }

  function toggleDictation() {
    if (dictating) {
      recognitionRef.current?.stop();
      setDictating(false);
      return;
    }
    const speechWindow = window as SpeechRecognitionWindow;
    const SpeechRecognitionCtor = speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) {
      setDictationError(t(
        "当前桌面壳不支持语音转文字。请在 Edge/Chrome 网页版使用麦克风转写，或直接点击实时通话按钮。",
        "Speech-to-text dictation is not supported in this shell. Use Edge/Chrome in the browser, or start a realtime call."
      ));
      return;
    }
    const recognition = new SpeechRecognitionCtor();
    recognition.lang = "zh-CN";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.onresult = (event) => {
      let finalText = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        if (result.isFinal) {
          finalText += result[0]?.transcript || "";
        }
      }
      appendDictationText(finalText);
    };
    recognition.onerror = (event) => {
      setDictationError(t(
        `语音转文字失败：${event.error || "未知错误"}`,
        `Speech-to-text failed: ${event.error || "Unknown error"}`
      ));
      setDictating(false);
    };
    recognition.onend = () => setDictating(false);
    recognitionRef.current = recognition;
    setDictationError("");
    setDictating(true);
    recognition.start();
  }

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [parsingFiles, setParsingFiles] = useState<string[]>([]);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (file.type === "application/pdf" || file.name.endsWith(".pdf")) {
        setParsingFiles((prev) => [...prev, file.name]);
        try {
          const res = await extractPdfText(file);
          if (res && res.text) {
            chat.addChatAttachment(file.name, res.text);
          } else {
            alert(t("PDF 提取内容为空。", "Extracted PDF content is empty."));
          }
        } catch (err) {
          console.error(err);
          alert(t("PDF 文本提取失败：", "Failed to extract text from PDF: ") + (err instanceof Error ? err.message : String(err)));
        } finally {
          setParsingFiles((prev) => prev.filter((name) => name !== file.name));
        }
      } else {
        // Handle as text file
        const reader = new FileReader();
        reader.onload = (event) => {
          const text = event.target?.result;
          if (typeof text === "string") {
            chat.addChatAttachment(file.name, text);
          }
        };
        reader.onerror = (event) => {
          console.error("Failed to read file:", event);
          alert(t("读取文件失败：", "Failed to read file: ") + file.name);
        };
        reader.readAsText(file);
      }
    }
    // Clear input value so we can upload the same file again
    e.target.value = "";
  };

  return (
    <div className={`vsComposer ${isVoiceActive ? "liveActive" : ""}`}>
      {!isVoiceActive ? (
        <>
          <textarea
            rows={1}
            value={chat.chatInput}
            onChange={(e) => chat.onInputChange(e.target.value)}
            placeholder={t("输入聊天内容，或者点击右下角麦克风开始语音通话...", "Type to chat, or click the microphone in the bottom right to start a voice call...")}
            onKeyDown={chat.onComposerKeyDown}
          />
          {dictationError ? <div className="vsComposerInlineHint">{dictationError}</div> : null}
        </>
      ) : (
        <div className="vsLiveSessionBanner">
          <div className="vsPulseDot vsPulseDotRed" />
          <span className="vsLiveSessionLabel">
            {voiceChat.voiceChatRecording ? t("正在聆听您的声音...", "Listening to your voice...") : t("实时通话连接中...", "Connecting live session...")}
          </span>
        </div>
      )}

      {/* Attachment Preview Section */}
      {((chat.chatAttachments && chat.chatAttachments.length > 0) || parsingFiles.length > 0) && (
        <div className="vsComposerAttachments">
          {chat.chatAttachments?.map((att, index) => (
            <div key={`${index}-${att.name}`} className="vsAttachmentPill">
              <span className="vsAttachmentPillIcon">📄</span>
              <span className="vsAttachmentPillName" title={att.name}>{att.name}</span>
              <button
                type="button"
                className="vsAttachmentPillDelete"
                onClick={() => chat.removeChatAttachment(index)}
                title={t("删除附件", "Delete attachment")}
              >
                ×
              </button>
            </div>
          ))}
          {parsingFiles.map((name) => (
            <div key={name} className="vsAttachmentPill loading">
              <span className="spinner-mini"></span>
              <span className="vsAttachmentPillName" title={name}>{name}</span>
            </div>
          ))}
        </div>
      )}

      <div className="vsComposerToolbar">
        <div className="vsComposerToolbarLeft">
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: "none" }}
            onChange={handleFileChange}
            multiple
          />
          <button
            type="button"
            className="vsToolbarBtn"
            aria-label={t("附件", "Attachment")}
            onClick={() => fileInputRef.current?.click()}
          >
            <PaperclipIcon />
          </button>
          
          {/* Alma-style inline dropdowns */}
          <select
            className="vsComposerPillSelect vsComposerModelSelect"
            value={chat.chatModelChoiceValue || chat.chatModel}
            onChange={(e) => chat.onModelChoiceChange(e.target.value)}
            title={t("切换模型", "Switch model")}
          >
            {chat.chatModelChoices.map((item) => (
              <option key={item.value} value={item.value}>{item.label}</option>
            ))}
            {!chat.chatModelChoices.some((item) => item.value === chat.chatModelChoiceValue) && chat.chatModel && (
              <option value={chat.chatModel}>{chat.chatModel}</option>
            )}
          </select>

          {isRealtime && (
            <select
              className="vsComposerPillSelect vsComposerVoiceSelect"
              value={voiceChat.voiceChatVoice}
              onChange={(e) => voiceChat.onVoiceChange(e.target.value)}
              disabled={isVoiceActive}
              title={t(`当前音色：${voiceChat.voiceChatVoiceLabel}`, `Current voice: ${voiceChat.voiceChatVoiceLabel}`)}
            >
              {voiceChat.voiceChatVoiceOptions.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          )}

          {isRealtime && isLiveTranslate && (
            <>
              <select
                className="vsComposerPillSelect vsComposerLanguageSelect"
                value={voiceChat.voiceChatTargetLanguageCode}
                onChange={(e) => voiceChat.onTargetLanguageCodeChange(e.target.value)}
                disabled={isVoiceActive}
                title={t("翻译目标语言", "Translation target language")}
              >
                {voiceChat.voiceChatTargetLanguageOptions.map((item) => (
                  <option key={item.value} value={item.value}>{item.label}</option>
                ))}
              </select>
              <label className="vsComposerToggle" title={t("输入已经是目标语言时也朗读出来", "Echo speech that is already in the target language")}>
                <input
                  type="checkbox"
                  checked={voiceChat.voiceChatEchoTargetLanguage}
                  onChange={(e) => voiceChat.onEchoTargetLanguageChange(e.target.checked)}
                  disabled={isVoiceActive}
                />
                <span>{t("同语回放", "Echo")}</span>
              </label>
            </>
          )}
        </div>

        <div className="vsComposerToolbarRight">
          <button
            type="button"
            className={`vsToolbarBtn ${dictating ? "recording" : ""}`}
            aria-label={dictating ? t("停止语音转写", "Stop dictation") : t("语音转写", "Dictate")}
            onClick={toggleDictation}
            disabled={isVoiceActive || chat.chatBusy}
            title={dictating ? t("停止语音转写", "Stop dictation") : t("语音转写到输入框", "Dictate into the input")}
          >
            <MicIcon />
          </button>

          <button
            type="button"
            className={`vsComposerCallBtn ${isVoiceActive ? "recording" : ""}`}
            aria-label={isVoiceActive ? t("结束实时通话", "End realtime call") : t("实时通话", "Realtime call")}
            onClick={() => void voiceChat.onToggleRecording()}
            disabled={!voiceChat.voiceChatSupported || voiceChat.voiceChatBusy}
            title={isVoiceActive ? t("结束实时通话", "End realtime call") : (
              isLiveTranslate
                ? t(`实时翻译：${voiceChat.voiceChatProvider} / ${voiceChat.voiceChatModel}`, `Live translate: ${voiceChat.voiceChatProvider} / ${voiceChat.voiceChatModel}`)
                : t(`实时通话：${voiceChat.voiceChatProvider} / ${voiceChat.voiceChatModel}`, `Realtime call: ${voiceChat.voiceChatProvider} / ${voiceChat.voiceChatModel}`)
            )}
          >
            {isVoiceActive ? <StopIcon /> : <PhoneIcon />}
          </button>

          {hasInput && !isVoiceActive ? (
            <button
              type="submit"
              className="vsSendBtn"
              disabled={chat.chatBusy || Boolean(textChatBlockedReason)}
              aria-label={t("发送", "Send")}
              title={textChatBlockedReason || t("发送", "Send")}
            >
              {chat.chatBusy ? <SpinnerIcon /> : <SendIcon />}
            </button>
          ) : (
            null
          )}
        </div>
      </div>
      {textChatBlockedReason ? <div className="vsComposerInlineHint">{textChatBlockedReason}</div> : null}
    </div>
  );
}

export default function ChatPage({ chat, voiceChat, errorRuntimeContext, onResumeAgentRun }: Props) {
  const { t } = useI18n();
  const quickActions: QuickAction[] = getChatQuickActions(t);
  const combinedMessages = [...chat.chatMessages, ...voiceChat.sessionSummary];
  const isEmpty = !combinedMessages.length;
  const bodyRef = useRef<HTMLDivElement>(null);
  const shouldStickToBottomRef = useRef(true);
  const [showVoiceHistory, setShowVoiceHistory] = useState(false);
  const [copiedMessageKey, setCopiedMessageKey] = useState("");
  const copyResetTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showWelcome = isEmpty && !voiceChat.voiceChatRecording && !voiceChat.voiceChatConnected;
  const isVoiceActive = voiceChat.voiceChatRecording || voiceChat.voiceChatConnected;

  useEffect(() => {
    const el = bodyRef.current;
    if (el && shouldStickToBottomRef.current) {
      el.scrollTop = el.scrollHeight;
    }
  }, [combinedMessages.length, voiceChat.voiceChatTranscript, voiceChat.voiceChatReply]);

  useEffect(() => () => {
    if (copyResetTimerRef.current !== null) {
      clearTimeout(copyResetTimerRef.current);
    }
  }, []);

  async function copyMessage(content: string, key: string) {
    const cleanContent = content.trim();
    if (!cleanContent) {
      return;
    }
    try {
      await copyTextToClipboard(cleanContent);
      setCopiedMessageKey(key);
      if (copyResetTimerRef.current !== null) {
        clearTimeout(copyResetTimerRef.current);
      }
      copyResetTimerRef.current = setTimeout(() => {
        copyResetTimerRef.current = null;
        setCopiedMessageKey("");
      }, 1600);
    } catch {
      setCopiedMessageKey("");
    }
  }

  function handleBodyScroll() {
    const el = bodyRef.current;
    if (!el) {
      return;
    }
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    shouldStickToBottomRef.current = distanceFromBottom < 96;
  }

  return (
    <section className="vsChatWorkspace" style={{ position: "relative" }}>
      <div style={{ position: "absolute", top: 12, right: 16, zIndex: 31 }}>
          <button
            type="button"
            className="vsBtnSecondary"
            style={{
              background: "rgba(255, 255, 255, 0.75)",
              backdropFilter: "blur(8px)",
              WebkitBackdropFilter: "blur(8px)",
              borderRadius: "20px",
              boxShadow: "0 2px 8px rgba(0, 0, 0, 0.08)",
              border: "1px solid var(--line)",
              padding: "0 14px",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px"
            }}
            aria-expanded={showVoiceHistory}
            onClick={() => setShowVoiceHistory((value) => !value)}
          >
            <HistoryIcon />
            <span>
              {showVoiceHistory ? t("返回对话", "Back to chat") : t("语音历史", "Voice history")}
            </span>
          </button>
      </div>
      {showVoiceHistory ? (
        <div style={{ position: "absolute", inset: 0, zIndex: 30, overflow: "auto", background: "var(--surface-color)", padding: "64px 18px 24px" }}>
          <VoiceAgentHistoryPanel voiceChat={voiceChat} onResumeAgentRun={onResumeAgentRun} />
        </div>
      ) : null}
      {/* ── Body ── */}
      <div
        ref={bodyRef}
        className={`vsChatBody ${showWelcome ? "empty" : ""} ${isVoiceActive ? "liveActive" : ""}`}
        onScroll={handleBodyScroll}
      >
        {showWelcome ? (
          /* ═══ EMPTY STATE: centered like Claude/Gemini ═══ */
          <div className="vsChatCentered">
            <div className="vsWelcomeHero">
              <div className="vsWelcomeHeroIcon">
                ✨
              </div>
              <div>
                <h1 className="vsWelcomeHeroTitle">{t("声之灵，倾听你的声音", "Voice Spirit, listening to your voice")}</h1>
                <p className="vsWelcomeHeroSubtitle">{t("点击右下角麦克风开启实时通话。", "Click the microphone in the bottom right to start a live voice call.")}</p>
              </div>
            </div>

            <form onSubmit={chat.onSubmit} className="vsComposerWrapCentered">
              <Composer
                chat={chat}
                voiceChat={voiceChat}
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
                className={msg.role === "user" ? "bubble user hasCopyAction" : "bubble assistant hasCopyAction"}
              >
                {msg.memorySaved || msg.memoriesUsed || msg.memorySourceSummary || msg.interrupted ? (
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
                    {msg.interrupted ? (
                      <span className="vsBubbleMemoryTag used">{t("已打断", "Interrupted")}</span>
                    ) : null}
                  </div>
                ) : null}
                {msg.role === "user" && msg.attachments && msg.attachments.length > 0 && (
                  <div className="vsMessageAttachments">
                    {msg.attachments.map((att, aIdx) => (
                      <div key={aIdx} className="vsMessageAttachmentPill">
                        <span className="vsAttachmentIcon">📄</span>
                        <span className="vsAttachmentName" title={att.name}>{att.name}</span>
                      </div>
                    ))}
                  </div>
                )}
                <p>
                  {msg.content ||
                    (chat.chatBusy &&
                      idx === chat.chatMessages.length - 1 &&
                      msg.role === "assistant"
                      ? "..."
                      : "")}
                </p>
                {msg.content ? (
                  <button
                    type="button"
                    className={`vsBubbleCopyBtn${copiedMessageKey === `${idx}-${msg.role}` ? " copied" : ""}`}
                    aria-label={copiedMessageKey === `${idx}-${msg.role}` ? t("已复制", "Copied") : t("复制消息", "Copy message")}
                    title={copiedMessageKey === `${idx}-${msg.role}` ? t("已复制", "Copied") : t("复制消息", "Copy message")}
                    onClick={() => void copyMessage(msg.content, `${idx}-${msg.role}`)}
                  >
                    <CopyIcon />
                    <span>{copiedMessageKey === `${idx}-${msg.role}` ? t("已复制", "Copied") : t("复制", "Copy")}</span>
                  </button>
                ) : null}
              </div>
            ))}

            {/* ── Live Streaming Bubbles ── */}
            {isVoiceActive && voiceChat.voiceChatTranscript && (
              <div className="bubble user live hasCopyAction">
                <div className="vsBubbleMeta">
                  <span className="vsStreamingIndicator">{voiceChat.voiceChatLiveTranslate ? t("原文实时转写", "Live source transcript") : t("(实时输入)", "(live input)")}</span>
                </div>
                <p>{voiceChat.voiceChatTranscript}</p>
                <button
                  type="button"
                  className={`vsBubbleCopyBtn${copiedMessageKey === "live-source" ? " copied" : ""}`}
                  aria-label={copiedMessageKey === "live-source" ? t("已复制", "Copied") : t("复制实时原文", "Copy live source")}
                  title={t("复制实时原文", "Copy live source")}
                  onClick={() => void copyMessage(voiceChat.voiceChatTranscript, "live-source")}
                >
                  <CopyIcon />
                  <span>{copiedMessageKey === "live-source" ? t("已复制", "Copied") : t("复制", "Copy")}</span>
                </button>
              </div>
            )}
            {isVoiceActive && voiceChat.voiceChatReply && (
              <div className="bubble assistant live hasCopyAction">
                <div className="vsBubbleMeta">
                  <span className="vsStreamingIndicator">{voiceChat.voiceChatLiveTranslate ? t(`译文：${voiceChat.voiceChatTargetLanguageLabel}`, `Translation: ${voiceChat.voiceChatTargetLanguageLabel}`) : t("(正在回复)", "(replying)")}</span>
                </div>
                <p>{voiceChat.voiceChatReply}</p>
                <button
                  type="button"
                  className={`vsBubbleCopyBtn${copiedMessageKey === "live-target" ? " copied" : ""}`}
                  aria-label={copiedMessageKey === "live-target" ? t("已复制", "Copied") : t("复制实时译文", "Copy live translation")}
                  title={t("复制实时译文", "Copy live translation")}
                  onClick={() => void copyMessage(voiceChat.voiceChatReply, "live-target")}
                >
                  <CopyIcon />
                  <span>{copiedMessageKey === "live-target" ? t("已复制", "Copied") : t("复制", "Copy")}</span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Bottom composer (visible when not in welcome mode or when voice active) ── */}
      {(!showWelcome || isVoiceActive) && (
        <div className={`vsComposerWrap ${isVoiceActive ? "liveActive" : ""}`}>
          <form onSubmit={chat.onSubmit}>
            <Composer
              chat={chat}
              voiceChat={voiceChat}
            />
          </form>

          {!isVoiceActive ? (
            <p className="vsChatDisclaimer">{t("AI 生成内容可能存在误差，请按需核对关键信息。", "AI-generated content may contain mistakes. Verify important details when needed.")}</p>
          ) : null}
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
