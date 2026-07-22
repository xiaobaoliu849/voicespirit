import { useEffect, useRef, useState } from "react";
import { extractPdfText, fetchSpeakAudio, type TtsEngine } from "../api";
import ErrorNotice from "../components/ErrorNotice";
import VoiceCallSettingsPopover from "../components/VoiceCallSettingsPopover";
import type { UseChatResult } from "../hooks/useChat";
import type { UseVoiceChatResult } from "../hooks/useVoiceChat";
import type { UseSettingsResult } from "../hooks/useSettings";
import { useI18n } from "../i18n";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  chat: UseChatResult;
  voiceChat: UseVoiceChatResult;
  settings?: UseSettingsResult;
  errorRuntimeContext: ErrorRuntimeContext;
  onOpenSettings?: () => void;
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
const SpeakerIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path></svg>
);
const StopTtsIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect></svg>
);
const TrashIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"></path><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path></svg>
);
const RefreshIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"></path><path d="M16 3h5v5"></path><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"></path><path d="M8 21H3v-5"></path></svg>
);

function mapProviderToEngine(provider?: string): TtsEngine {
  if (!provider) return "edge";
  const p = provider.toLowerCase();
  if (p.includes("edge")) return "edge";
  if (p.includes("qwen")) return "qwen_flash";
  if (p.includes("minimax")) return "minimax";
  if (p.includes("xiaomi")) return "xiaomi";
  if (p.includes("openai")) return "openai";
  if (p.includes("elevenlabs")) return "elevenlabs";
  if (p.includes("chattts")) return "chattts";
  if (p.includes("gpt_sovits")) return "gpt_sovits";
  return "edge"; // Fallback to edge
}

function cleanMarkdownForTts(text: string): string {
  if (!text) return "";
  let clean = text;
  // Remove code blocks
  clean = clean.replace(/```[\s\S]*?```/g, "");
  // Remove inline code
  clean = clean.replace(/`([^`]+)`/g, "$1");
  // Remove bold/italic markers
  clean = clean.replace(/\*\*([^*]+)\*\*/g, "$1");
  clean = clean.replace(/\*([^*]+)\*/g, "$1");
  clean = clean.replace(/__([^_]+)__/g, "$1");
  clean = clean.replace(/_([^_]+)_/g, "$1");
  // Remove heading marks
  clean = clean.replace(/^#+\s+/gm, "");
  // Remove HTML tags
  clean = clean.replace(/<[^>]*>/g, "");
  // Trim spaces and newlines
  clean = clean.trim();
  return clean;
}

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
  onOpenSettings,
}: {
  chat: UseChatResult;
  voiceChat: UseVoiceChatResult;
  onOpenSettings?: () => void;
}) {
  const { t } = useI18n();
  const isVoiceActive = voiceChat.voiceChatRecording || voiceChat.voiceChatConnected;
  const hasInput = chat.chatInput.trim().length > 0;
  const isRealtime = isVoiceRealtimeModel(chat.chatProvider, chat.chatModel);
  const isLiveTranslate = voiceChat.voiceChatLiveTranslate;
  const textChatBlockedReason = (isRealtime && !isVoiceActive)
    ? t(
      "当前是实时语音/实时翻译模型。请点击实时通话按钮开始语音会话，或切换到普通文本模型后再发送文字。",
      "The current model is realtime voice/live translation only. Start a realtime call, or switch to a text model before sending."
    )
    : "";
  const [dictating, setDictating] = useState(false);
  const [dictationError, setDictationError] = useState("");
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  // Soundwave visualizer requestAnimationFrame animation loop
  useEffect(() => {
    if (!voiceChat.voiceChatConnected) return;

    const micAnalyser = voiceChat.micAnalyser;
    const assistantAnalyser = voiceChat.assistantAnalyser;

    if (!micAnalyser && !assistantAnalyser) return;

    let animationFrameId: number;
    const micDataArray = micAnalyser ? new Uint8Array(micAnalyser.frequencyBinCount) : null;
    const assistantDataArray = assistantAnalyser ? new Uint8Array(assistantAnalyser.frequencyBinCount) : null;

    const updateVisualizer = () => {
      let micVolume = 0;
      let assistantVolume = 0;

      if (micAnalyser && micDataArray) {
        micAnalyser.getByteFrequencyData(micDataArray);
        let sum = 0;
        for (let i = 0; i < micDataArray.length; i++) {
          sum += micDataArray[i];
        }
        micVolume = sum / micDataArray.length;
      }

      if (assistantAnalyser && assistantDataArray) {
        assistantAnalyser.getByteFrequencyData(assistantDataArray);
        let sum = 0;
        for (let i = 0; i < assistantDataArray.length; i++) {
          sum += assistantDataArray[i];
        }
        assistantVolume = sum / assistantDataArray.length;
      }

      const visualizerEl = document.getElementById("vs-voice-visualizer");
      if (visualizerEl) {
        const activeVolume = assistantVolume > 0 ? assistantVolume : micVolume;
        const dataArray = assistantVolume > 0 ? assistantDataArray : micDataArray;
        
        // Dynamic background glow scaling and opacity based on active volume
        const glowEl = visualizerEl.querySelector(".vsVoiceGlow") as HTMLElement;
        if (glowEl) {
          const scale = 0.9 + (activeVolume / 255) * 0.5;
          const opacity = 0.5 + (activeVolume / 255) * 0.5;
          glowEl.style.transform = `scale(${scale})`;
          glowEl.style.opacity = `${opacity}`;
        }

        const bars = visualizerEl.querySelectorAll(".vsWaveBar");
        if (activeVolume > 2 && dataArray && bars.length > 0) {
          const step = Math.floor(dataArray.length / bars.length) || 1;
          bars.forEach((bar, index) => {
            const val = dataArray[index * step] || 0;
            // Scale bar height: map 0-255 to 15% - 100%
            const height = 15 + (val / 255) * 85;
            (bar as HTMLElement).style.height = `${height}%`;
          });
        } else {
          // Reset style so CSS keyframe animations breathe during silence
          bars.forEach((bar) => {
            (bar as HTMLElement).style.height = "";
          });
          if (glowEl) {
            glowEl.style.transform = "";
            glowEl.style.opacity = "";
          }
        }
      }

      animationFrameId = requestAnimationFrame(updateVisualizer);
    };

    const timerId = setTimeout(() => {
      updateVisualizer();
    }, 100);

    return () => {
      clearTimeout(timerId);
      cancelAnimationFrame(animationFrameId);
    };
  }, [voiceChat.voiceChatConnected, voiceChat.micAnalyser, voiceChat.assistantAnalyser]);

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
            disabled={isRealtime}
            onChange={(e) => chat.onInputChange(e.target.value)}
            placeholder={isRealtime
              ? t("当前模型仅支持实时通话，请点击右侧电话按钮开始...", "This model only supports realtime calls. Click the phone button in the bottom right to start...")
              : t("输入聊天内容，或者点击右侧麦克风语音转写...", "Type to chat, or click the microphone on the right to dictate...")}
            onKeyDown={chat.onComposerKeyDown}
          />
          {dictationError ? <div className="vsComposerInlineHint">{dictationError}</div> : null}
        </>
      ) : (
        <div className="vsLiveVoicePanel">
          <div className="vsVoiceStatusSection">
            <span className="vsVoiceStatusText">
              <span className={`vsVoiceStatusDot ${voiceChat.voiceChatConnected ? "connected" : "connecting"}`} />
              {voiceChat.voiceChatConnected
                ? (voiceChat.voiceChatReply 
                    ? t("正在回复...", "Replying...") 
                    : (voiceChat.voiceChatTranscript 
                        ? t("正在聆听...", "Listening...") 
                        : t("已连接，您可以说话", "Connected, feel free to speak")))
                : t("正在建立安全连接...", "Connecting live session...")}
            </span>
            {voiceChat.voiceChatConnected && (
              <span className="vsVoiceModelBadge">
                {voiceChat.voiceChatProvider} / {voiceChat.voiceChatModel} · {voiceChat.voiceChatVoiceLabel}
              </span>
            )}
          </div>
          
          <div className="vsVoiceVisualizerContainer" id="vs-voice-visualizer">
            <div className="vsVoiceVisualizerWave">
              <div className="vsWaveBar bar-1"></div>
              <div className="vsWaveBar bar-2"></div>
              <div className="vsWaveBar bar-3"></div>
              <div className="vsWaveBar bar-4"></div>
              <div className="vsWaveBar bar-5"></div>
              <div className="vsWaveBar bar-6"></div>
              <div className="vsWaveBar bar-7"></div>
            </div>
            <div className="vsVoiceGlow"></div>
          </div>
          


          <div className="vsVoiceCallControlRow">
            <button
              type="button"
              className="vsVoiceCallHangupBtn"
              onClick={() => void voiceChat.onToggleRecording()}
              title={t("结束实时通话", "End realtime call")}
            >
              <StopIcon />
              <span>{t("挂断", "Hang up")}</span>
            </button>
          </div>
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
            {!isRealtime && (
              <button
                type="button"
                className="vsToolbarBtn"
                aria-label={t("附件", "Attachment")}
                onClick={() => fileInputRef.current?.click()}
              >
                <PaperclipIcon />
              </button>
            )}
            
            {/* Alma-style inline dropdowns */}
            {!isRealtime && (
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
            )}

            {isRealtime && (
              <VoiceCallSettingsPopover voiceChat={voiceChat} t={t} disabled={isVoiceActive} onOpenSettings={onOpenSettings} />
            )}
          </div>

          <div className="vsComposerToolbarRight">
            {!isRealtime && (
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
            )}

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
    </div>
  );
}

export default function ChatPage({ chat, voiceChat, settings, errorRuntimeContext, onOpenSettings }: Props) {
  const { t } = useI18n();
  const combinedMessages = [...chat.chatMessages, ...voiceChat.sessionSummary];
  const isEmpty = !combinedMessages.length;
  const bodyRef = useRef<HTMLDivElement>(null);
  const shouldStickToBottomRef = useRef(true);
  const [copiedMessageKey, setCopiedMessageKey] = useState("");
  const [playingMessageKey, setPlayingMessageKey] = useState<string | null>(null);
  const [loadingTtsMessageKey, setLoadingTtsMessageKey] = useState<string | null>(null);
  const [ttsPlaybackError, setTtsPlaybackError] = useState("");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const activeBlobUrlRef = useRef<string | null>(null);
  const copyResetTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showWelcome = isEmpty && !voiceChat.voiceChatRecording && !voiceChat.voiceChatConnected;
  const isVoiceActive = voiceChat.voiceChatRecording || voiceChat.voiceChatConnected;

  useEffect(() => {
    return () => {
      stopTts();
    };
  }, []);

  function stopTts() {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (activeBlobUrlRef.current) {
      URL.revokeObjectURL(activeBlobUrlRef.current);
      activeBlobUrlRef.current = null;
    }
    setPlayingMessageKey(null);
    setLoadingTtsMessageKey(null);
  }

  async function playTts(content: string, key: string) {
    if (playingMessageKey === key || loadingTtsMessageKey === key) {
      stopTts();
      return;
    }
    stopTts();

    const cleanText = cleanMarkdownForTts(content);
    if (!cleanText) return;

    setTtsPlaybackError("");
    const ttsSettings = settings?.settingsData?.tts_settings;
    const rawProvider = typeof ttsSettings?.provider === "string" ? ttsSettings.provider : undefined;
    const engine = mapProviderToEngine(rawProvider);
    const configuredVoice = typeof ttsSettings?.default_voice === "string" && ttsSettings.default_voice ? ttsSettings.default_voice : undefined;

    let voice = configuredVoice;
    if (engine === "edge") {
      const hasCjk = /[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]/.test(cleanText);
      const hasEnglish = /[a-zA-Z]/.test(cleanText);
      const isZhVoice = configuredVoice ? /zh-cn|zh-tw|zh-hk/i.test(configuredVoice) : false;
      const isEnVoice = configuredVoice ? /en-us|en-gb|en-au|en-ca/i.test(configuredVoice) : false;

      if (hasEnglish && !hasCjk && (isZhVoice || !configuredVoice)) {
        voice = "en-US-AvaNeural";
      } else if (hasCjk && isEnVoice) {
        voice = "zh-CN-XiaoxiaoNeural";
      }
    }

    setLoadingTtsMessageKey(key);

    try {
      const { blob } = await fetchSpeakAudio({
        text: cleanText,
        voice,
        engine,
      });

      const objectUrl = URL.createObjectURL(blob);
      activeBlobUrlRef.current = objectUrl;

      const audio = new Audio(objectUrl);
      audioRef.current = audio;
      setLoadingTtsMessageKey(null);
      setPlayingMessageKey(key);

      audio.onended = () => {
        if (audioRef.current === audio) {
          stopTts();
        }
      };

      audio.onerror = (err) => {
        console.error("TTS audio playback error:", err);
        setTtsPlaybackError(t("浏览器播放音频失败，请重试。", "Failed to play audio in browser. Please retry."));
        if (audioRef.current === audio) {
          stopTts();
        }
      };

      await audio.play();
    } catch (err) {
      console.error("Failed to generate or play TTS audio:", err);
      const msg = err instanceof Error ? err.message : String(err);
      setTtsPlaybackError(t(`语音合成朗读失败：${msg}`, `Failed to synthesize speech: ${msg}`));
      stopTts();
    }
  }

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
                <h1 className="vsWelcomeHeroTitle">{t("声之灵", "Voice Spirit")}</h1>
                <p className="vsWelcomeHeroSubtitle">{t("双向实时语音与 AI 智能助理", "Realtime two-way voice & AI assistant")}</p>
              </div>
            </div>

            <form onSubmit={chat.onSubmit} className="vsComposerWrapCentered">
              <Composer
                chat={chat}
                voiceChat={voiceChat}
                onOpenSettings={onOpenSettings}
              />
            </form>


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
                  <div className="vsBubbleActions">
                    {/* Copy Button */}
                    <button
                      type="button"
                      className={`vsBubbleActionBtn${copiedMessageKey === `${idx}-${msg.role}` ? " copied" : ""}`}
                      aria-label={copiedMessageKey === `${idx}-${msg.role}` ? t("已复制", "Copied") : t("复制消息", "Copy message")}
                      title={copiedMessageKey === `${idx}-${msg.role}` ? t("已复制", "Copied") : t("复制消息", "Copy message")}
                      onClick={() => void copyMessage(msg.content, `${idx}-${msg.role}`)}
                    >
                      <CopyIcon />
                    </button>

                    {/* Play/Stop TTS Button (only for assistant messages) */}
                    {msg.role === "assistant" && (
                      <button
                        type="button"
                        className={`vsBubbleActionBtn${playingMessageKey === `${idx}-${msg.role}` ? " active" : ""}`}
                        disabled={loadingTtsMessageKey === `${idx}-${msg.role}`}
                        aria-label={
                          loadingTtsMessageKey === `${idx}-${msg.role}`
                            ? t("生成中...", "Generating...")
                            : playingMessageKey === `${idx}-${msg.role}`
                            ? t("停止播放", "Stop")
                            : t("朗读回答", "Play response")
                        }
                        title={
                          loadingTtsMessageKey === `${idx}-${msg.role}`
                            ? t("生成中...", "Generating...")
                            : playingMessageKey === `${idx}-${msg.role}`
                            ? t("停止播放", "Stop")
                            : t("朗读回答", "Play response")
                        }
                        onClick={() => void playTts(msg.content, `${idx}-${msg.role}`)}
                      >
                        {loadingTtsMessageKey === `${idx}-${msg.role}` ? (
                          <SpinnerIcon />
                        ) : playingMessageKey === `${idx}-${msg.role}` ? (
                          <StopTtsIcon />
                        ) : (
                          <SpeakerIcon />
                        )}
                      </button>
                    )}

                    {/* Regenerate Button (only for assistant messages) */}
                    {msg.role === "assistant" && (
                      <button
                        type="button"
                        className="vsBubbleActionBtn"
                        disabled={chat.chatBusy}
                        aria-label={t("重新生成", "Regenerate")}
                        title={t("重新生成", "Regenerate")}
                        onClick={() => void chat.onRegenerateMessage?.(idx)}
                      >
                        <RefreshIcon />
                      </button>
                    )}

                    {/* Delete Button */}
                    <button
                      type="button"
                      className="vsBubbleActionBtn"
                      aria-label={t("删除消息", "Delete message")}
                      title={t("删除消息", "Delete message")}
                      onClick={() => chat.onDeleteMessage?.(idx)}
                    >
                      <TrashIcon />
                    </button>
                  </div>
                ) : null}
              </div>
            ))}

            {/* ── Live Streaming Bubbles ── */}
            {isVoiceActive && voiceChat.voiceChatTranscript && (
              <div className="bubble user live">
                <div className="vsBubbleMeta">
                  <span className="vsStreamingIndicator">{voiceChat.voiceChatLiveTranslate ? t("原文实时转写", "Live source transcript") : t("(实时输入)", "(live input)")}</span>
                </div>
                <p>{voiceChat.voiceChatTranscript}</p>
                <div className="vsBubbleActions">
                  <button
                    type="button"
                    className={`vsBubbleActionBtn${copiedMessageKey === "live-source" ? " copied" : ""}`}
                    aria-label={copiedMessageKey === "live-source" ? t("已复制", "Copied") : t("复制实时原文", "Copy live source")}
                    title={t("复制实时原文", "Copy live source")}
                    onClick={() => void copyMessage(voiceChat.voiceChatTranscript, "live-source")}
                  >
                    <CopyIcon />
                  </button>
                </div>
              </div>
            )}
            {isVoiceActive && voiceChat.voiceChatAgentToolStatus && (
              <div className="vsVoiceToolStatus" role="status" aria-live="polite">
                <span className="vsPulseDot" aria-hidden="true" />
                <div>
                  <strong>{voiceChat.voiceChatAgentToolStatus}</strong>
                  {voiceChat.voiceChatAgentRunMeta ? <small>{voiceChat.voiceChatAgentRunMeta}</small> : null}
                </div>
              </div>
            )}
            {isVoiceActive && voiceChat.voiceChatAgentSources.length > 0 && (
              <div className="vsVoiceToolSources" aria-label={t("工具来源", "Tool sources")}>
                {voiceChat.voiceChatAgentSources.map((source, index) => (
                  <a
                    key={`${source.uri}-${index}`}
                    href={source.uri}
                    target="_blank"
                    rel="noreferrer"
                    title={source.snippet}
                  >
                    {source.title || t(`来源 ${index + 1}`, `Source ${index + 1}`)}
                  </a>
                ))}
              </div>
            )}
            {isVoiceActive && voiceChat.voiceChatReply && (
              <div className="bubble assistant live">
                <div className="vsBubbleMeta">
                  <span className="vsStreamingIndicator">{voiceChat.voiceChatLiveTranslate ? t(`译文：${voiceChat.voiceChatTargetLanguageLabel}`, `Translation: ${voiceChat.voiceChatTargetLanguageLabel}`) : t("(正在回复)", "(replying)")}</span>
                </div>
                <p>{voiceChat.voiceChatReply}</p>
                <div className="vsBubbleActions">
                  <button
                    type="button"
                    className={`vsBubbleActionBtn${copiedMessageKey === "live-target" ? " copied" : ""}`}
                    aria-label={copiedMessageKey === "live-target" ? t("已复制", "Copied") : t("复制实时译文", "Copy live translation")}
                    title={t("复制实时译文", "Copy live translation")}
                    onClick={() => void copyMessage(voiceChat.voiceChatReply, "live-target")}
                  >
                    <CopyIcon />
                  </button>
                </div>
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
              onOpenSettings={onOpenSettings}
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
          {ttsPlaybackError && (
            <div className="vsTtsErrorSection" style={{ marginTop: 8 }}>
              <ErrorNotice
                message={ttsPlaybackError}
                scope="tts"
                context={errorRuntimeContext as Record<string, string | number | boolean | null | undefined>}
              />
            </div>
          )}
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
