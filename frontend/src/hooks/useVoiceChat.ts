import { useEffect, useMemo, useRef, useState } from "react";
import {
  buildVoiceChatSessionConfig,
  buildVoiceChatWebSocketUrl,
  type ChatMessage,
  type VoiceChatServerEvent,
} from "../api";
import type { FormatErrorMessage } from "../utils/errorFormatting";

type ProviderModelCatalog = Record<
  string,
  {
    defaultModel: string;
    availableModels: string[];
  }
>;

type Options = {
  formatErrorMessage: FormatErrorMessage;
  providerOptions?: string[];
  providerModelCatalog?: ProviderModelCatalog;
  preferredProvider?: string;
  preferredModel?: string;
};

type AudioContextWindow = Window & {
  webkitAudioContext?: typeof AudioContext;
};

const GOOGLE_PROVIDER = "Google";
const DASHSCOPE_PROVIDER = "DashScope";
const DEFAULT_GOOGLE_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025";
const DEFAULT_DASHSCOPE_MODEL = "qwen3-omni-flash-realtime-2025-12-01";

const GOOGLE_REALTIME_VOICES = [
  "Puck",
  "Aoede",
  "Zephyr",
  "Lyra",
  "Leda",
  "Achird",
  "Autonoe",
  "Despina",
  "Fenrir",
  "Sadachbia",
].map((name) => ({ value: name, label: name }));

const DASHSCOPE_REALTIME_VOICES = [
  { value: "Cherry", label: "Cherry (Female)" },
  { value: "Bella", label: "Bella (Female)" },
  { value: "Luna", label: "Luna (Female)" },
  { value: "Stella", label: "Stella (Female)" },
  { value: "Raya", label: "Raya (Female)" },
  { value: "Zita", label: "Zita (Female)" },
  { value: "Arda", label: "Arda (Male)" },
  { value: "Kall", label: "Kall (Male)" },
  { value: "Ollo", label: "Ollo (Male)" },
  { value: "Vrom", label: "Vrom (Male)" },
  { value: "Bale", label: "Bale (Male)" },
  { value: "Gale", label: "Gale (Male)" },
];

function resolveRealtimeProvider(preferredProvider: string | undefined, providerOptions: string[]): string {
  if (preferredProvider && (preferredProvider === GOOGLE_PROVIDER || preferredProvider === DASHSCOPE_PROVIDER) && providerOptions.includes(preferredProvider)) {
    return preferredProvider;
  }
  if (providerOptions.includes(DASHSCOPE_PROVIDER)) {
    return DASHSCOPE_PROVIDER;
  }
  if (providerOptions.includes(GOOGLE_PROVIDER)) {
    return GOOGLE_PROVIDER;
  }
  return providerOptions[0] || GOOGLE_PROVIDER;
}

function resolveDefaultModel(provider: string, providerModelCatalog: ProviderModelCatalog): string {
  if (provider === DASHSCOPE_PROVIDER) {
    return providerModelCatalog[provider]?.defaultModel || DEFAULT_DASHSCOPE_MODEL;
  }
  if (provider !== GOOGLE_PROVIDER) {
    return providerModelCatalog[provider]?.defaultModel || "";
  }
  const providerMeta = providerModelCatalog[provider];
  if (!providerMeta) {
    return DEFAULT_GOOGLE_MODEL;
  }
  return providerMeta.defaultModel || providerMeta.availableModels[0] || DEFAULT_GOOGLE_MODEL;
}

function getAudioContextCtor(): typeof AudioContext | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }
  const audioWindow = window as AudioContextWindow;
  return window.AudioContext || audioWindow.webkitAudioContext;
}

function encodePcm16k(input: Float32Array, inputRate: number): ArrayBuffer {
  if (!input.length) {
    return new ArrayBuffer(0);
  }
  const targetRate = 16000;
  if (inputRate === targetRate) {
    const direct = new Int16Array(input.length);
    for (let i = 0; i < input.length; i += 1) {
      const clamped = Math.max(-1, Math.min(1, input[i]));
      direct[i] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
    }
    return direct.buffer;
  }

  const ratio = inputRate / targetRate;
  const targetLength = Math.max(1, Math.round(input.length / ratio));
  const output = new Int16Array(targetLength);
  let sourceIndex = 0;

  for (let i = 0; i < targetLength; i += 1) {
    const nextSourceIndex = Math.min(input.length, Math.round((i + 1) * ratio));
    let total = 0;
    let count = 0;
    while (sourceIndex < nextSourceIndex) {
      total += input[sourceIndex];
      count += 1;
      sourceIndex += 1;
    }
    const sample = count > 0 ? total / count : input[Math.min(sourceIndex, input.length - 1)] || 0;
    const clamped = Math.max(-1, Math.min(1, sample));
    output[i] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
  }

  return output.buffer;
}

function decodeBase64Pcm(base64Audio: string): Int16Array {
  const binary = atob(base64Audio);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new Int16Array(bytes.buffer);
}

function mergeAssistantText(previous: string, incoming: string): string {
  const next = incoming.trim();
  if (!next) {
    return previous;
  }
  if (!previous) {
    return next;
  }
  if (next.startsWith(previous)) {
    return next;
  }
  if (previous.endsWith(next)) {
    return previous;
  }
  return `${previous}${next}`;
}

function normalizeVoiceCaptureError(error: unknown, fallback: string): string {
  if (!(error instanceof Error)) {
    return fallback;
  }

  const name = (error.name || "").trim();
  const message = (error.message || "").trim();
  const lowerMessage = message.toLowerCase();

  if (
    name === "NotFoundError" ||
    name === "DevicesNotFoundError" ||
    lowerMessage.includes("requested device not found") ||
    lowerMessage.includes("device not found")
  ) {
    return "未检测到可用麦克风设备。若你在 Ubuntu/WSL 中运行桌面版，请改用 Windows 的 run_web_desktop.bat，或先配置麦克风透传。";
  }

  if (name === "NotAllowedError" || lowerMessage.includes("permission denied")) {
    return "麦克风权限被拒绝。请允许当前应用访问麦克风后重试。";
  }

  if (name === "NotReadableError" || lowerMessage.includes("could not start audio source")) {
    return "麦克风当前不可读，可能被其他应用占用。请关闭占用麦克风的软件后重试。";
  }

  return message || fallback;
}

export default function useVoiceChat({
  formatErrorMessage,
  providerOptions = [],
  providerModelCatalog = {},
  preferredProvider,
  preferredModel,
}: Options) {
  const resolvedProviders = [GOOGLE_PROVIDER, DASHSCOPE_PROVIDER].filter(p => providerOptions.includes(p));

  const initialProvider = resolveRealtimeProvider(preferredProvider, resolvedProviders);
  const [voiceChatProvider, setVoiceChatProvider] = useState(initialProvider);
  const [voiceChatModel, setVoiceChatModel] = useState(
    resolveDefaultModel(initialProvider, providerModelCatalog)
  );
  const [voiceChatVoice, setVoiceChatVoice] = useState(
    initialProvider === DASHSCOPE_PROVIDER ? "Cherry" : "Puck"
  );
  const [voiceChatBusy, setVoiceChatBusy] = useState(false);
  const [voiceChatRecording, setVoiceChatRecording] = useState(false);
  const [voiceChatSupported, setVoiceChatSupported] = useState(true);
  const [voiceChatStatus, setVoiceChatStatus] = useState("点击开始实时语音聊天");
  const [voiceChatError, setVoiceChatError] = useState("");
  const [voiceChatTranscript, setVoiceChatTranscript] = useState("");
  const [voiceChatReply, setVoiceChatReply] = useState("");
  const [voiceChatMessages, setVoiceChatMessages] = useState<ChatMessage[]>([]);
  const [voiceChatConnected, setVoiceChatConnected] = useState(false);
  const [voiceChatMemoriesRetrieved, setVoiceChatMemoriesRetrieved] = useState(0);
  const [voiceChatMemoryWriteStatus, setVoiceChatMemoryWriteStatus] = useState("");
  const [voiceChatMemorySourceStatus, setVoiceChatMemorySourceStatus] = useState("");
  const [voiceChatMemoryScope, setVoiceChatMemoryScope] = useState("");

  const websocketRef = useRef<WebSocket | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const muteGainRef = useRef<GainNode | null>(null);
  const playingSourcesRef = useRef<AudioBufferSourceNode[]>([]);
  const nextPlaybackTimeRef = useRef(0);
  const currentUserTurnRef = useRef("");
  const currentAssistantTurnRef = useRef("");
  const currentMemoriesRetrievedRef = useRef(0);
  const currentMemorySavedRef = useRef(false);
  const currentMemoryRetrieveAttemptedRef = useRef(false);
  const currentLocalPendingCountRef = useRef(0);
  const currentCloudCountRef = useRef(0);
  const lastPreferredProviderRef = useRef(preferredProvider);
  const lastPreferredModelRef = useRef(preferredModel);
  const sessionEpochRef = useRef(0);

  const voiceChatModelOptions = providerModelCatalog[voiceChatProvider]?.availableModels || [];

  useEffect(() => {
    const preferredProviderChanged = lastPreferredProviderRef.current !== preferredProvider;
    lastPreferredProviderRef.current = preferredProvider;
    const preferredModelChanged = lastPreferredModelRef.current !== preferredModel;
    lastPreferredModelRef.current = preferredModel;

    const nextProvider = resolveRealtimeProvider(preferredProvider, resolvedProviders);
    if (preferredProviderChanged && voiceChatProvider !== nextProvider) {
      setVoiceChatProvider(nextProvider);
      const nextModel = preferredModel && (preferredModelChanged || nextProvider !== voiceChatProvider)
        ? preferredModel
        : resolveDefaultModel(nextProvider, providerModelCatalog);
      setVoiceChatModel(nextModel);
      return;
    }

    if (preferredModel && preferredModelChanged && preferredModel !== voiceChatModel) {
      const availableModels = providerModelCatalog[voiceChatProvider]?.availableModels || [];
      if (availableModels.length === 0 || availableModels.includes(preferredModel)) {
        setVoiceChatModel(preferredModel);
        return;
      }
    }

    const defaultModel = resolveDefaultModel(voiceChatProvider, providerModelCatalog);
    const availableModels = providerModelCatalog[voiceChatProvider]?.availableModels || [];
    const currentModelValid =
      availableModels.length === 0 ||
      !voiceChatModel.trim() ||
      availableModels.includes(voiceChatModel.trim());
    if (!voiceChatModel.trim() || !currentModelValid) {
      setVoiceChatModel(defaultModel);
    }
  }, [
    preferredProvider,
    preferredModel,
    providerModelCatalog,
    resolvedProviders,
    voiceChatModel,
    voiceChatProvider,
  ]);

  useEffect(() => {
    if (voiceChatProvider === DASHSCOPE_PROVIDER) {
      if (!DASHSCOPE_REALTIME_VOICES.some(v => v.value === voiceChatVoice)) {
        setVoiceChatVoice("Cherry");
      }
    } else if (voiceChatProvider === GOOGLE_PROVIDER) {
      if (!GOOGLE_REALTIME_VOICES.some(v => v.value === voiceChatVoice)) {
        setVoiceChatVoice("Puck");
      }
    }
  }, [voiceChatProvider, voiceChatVoice]);

  useEffect(() => {
    return () => {
      stopSessionResources();
    };
  }, []);

  function stopAssistantPlayback() {
    playingSourcesRef.current.forEach((source) => {
      try {
        source.stop();
      } catch {
        // Ignore already-finished nodes.
      }
    });
    playingSourcesRef.current = [];
    if (audioContextRef.current) {
      nextPlaybackTimeRef.current = audioContextRef.current.currentTime;
    }
  }

  function stopSessionResources() {
    const ws = websocketRef.current;
    websocketRef.current = null;
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      try {
        ws.close();
      } catch {
        // Ignore close failures.
      }
    }

    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();
    muteGainRef.current?.disconnect();
    processorRef.current = null;
    sourceRef.current = null;
    muteGainRef.current = null;

    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;

    stopAssistantPlayback();
    if (audioContextRef.current) {
      const context = audioContextRef.current;
      audioContextRef.current = null;
      void context.close().catch(() => { });
    }

    setVoiceChatConnected(false);
    setVoiceChatRecording(false);
    setVoiceChatBusy(false);
  }

  function markNewSessionEpoch(): number {
    sessionEpochRef.current += 1;
    return sessionEpochRef.current;
  }

  function commitCompletedTurn() {
    const userText = currentUserTurnRef.current.trim();
    const assistantText = currentAssistantTurnRef.current.trim();
    const memorySaved = currentMemorySavedRef.current;
    const memoriesUsed = currentMemoriesRetrievedRef.current;
    const memorySourceSummary = buildMemorySourceSummary({
      attempted: currentMemoryRetrieveAttemptedRef.current,
      total: memoriesUsed,
      localPendingCount: currentLocalPendingCountRef.current,
      cloudCount: currentCloudCountRef.current,
    });
    if (!userText && !assistantText) {
      return;
    }
    setVoiceChatMessages((prev) => {
      const next = [...prev];
      if (userText) {
        next.push({ role: "user", content: userText, memorySaved });
      }
      if (assistantText) {
        next.push({
          role: "assistant",
          content: assistantText,
          memoriesUsed: memoriesUsed > 0 ? memoriesUsed : undefined,
          memorySourceSummary: memorySourceSummary || undefined,
          memoryRetrievalAttempted: currentMemoryRetrieveAttemptedRef.current,
        });
      }
      return next.slice(-12);
    });
    currentUserTurnRef.current = "";
    currentAssistantTurnRef.current = "";
    currentMemorySavedRef.current = false;
    currentMemoryRetrieveAttemptedRef.current = false;
    currentLocalPendingCountRef.current = 0;
    currentCloudCountRef.current = 0;
    setVoiceChatTranscript("");
    setVoiceChatReply("");
  }

  function describeMemoryWriteResult(event: Extract<VoiceChatServerEvent, { type: "memory_write" }>): string {
    if (event.saved_count > 0 && event.failed_count === 0) {
      if ((event.local_pending_count || 0) > 0) {
        return `本轮已提交 EverMind ${event.saved_count} 条记忆，并加入本地待同步缓存`;
      }
      return `本轮已提交 EverMind ${event.saved_count} 条记忆`;
    }
    if (event.saved_count > 0 && event.failed_count > 0) {
      return `本轮部分提交 EverMind（${event.saved_count}/${event.attempted_count}）`;
    }
    if (event.attempted_count === 0 && event.reason === "no_candidate_memory") {
      return "本轮未提炼出可保存的长期记忆";
    }
    if (event.attempted_count === 0) {
      return "";
    }
    return "本轮写入 EverMind 失败";
  }

  function buildMemorySourceSummary(params: {
    attempted: boolean;
    total: number;
    localPendingCount: number;
    cloudCount: number;
  }): string {
    const local = Math.max(0, params.localPendingCount);
    const cloud = Math.max(0, params.cloudCount);
    if (!params.attempted) {
      return "";
    }
    if (params.total > 0) {
      return `来源：本地待同步 ${local} 条，云端 ${cloud} 条`;
    }
    return `已尝试回忆：本地待同步 ${local} 条，云端 ${cloud} 条`;
  }

  function describeMemoryContext(event: Extract<VoiceChatServerEvent, { type: "memory_context" }>): string {
    const local = Math.max(0, event.local_pending_count || 0);
    const cloud = Math.max(0, event.cloud_count || 0);
    if (event.memories_retrieved > 0) {
      return `已回忆 ${event.memories_retrieved} 条长期记忆（本地待同步 ${local}，云端 ${cloud}）`;
    }
    if (event.attempted) {
      return `已尝试回忆，但未命中匹配记忆（本地待同步 ${local}，云端 ${cloud}）`;
    }
    return "";
  }

  async function playAssistantAudio(base64Audio: string, sampleRate: number) {
    const context = audioContextRef.current;
    if (!context) {
      return;
    }
    if (context.state === "suspended") {
      await context.resume();
    }

    const pcm = decodeBase64Pcm(base64Audio);
    if (!pcm.length) {
      return;
    }

    const buffer = context.createBuffer(1, pcm.length, sampleRate);
    const channel = buffer.getChannelData(0);
    for (let i = 0; i < pcm.length; i += 1) {
      channel[i] = pcm[i] / 32768;
    }

    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(context.destination);
    const startAt = Math.max(context.currentTime + 0.02, nextPlaybackTimeRef.current);
    source.start(startAt);
    nextPlaybackTimeRef.current = startAt + buffer.duration;
    playingSourcesRef.current.push(source);
    source.addEventListener("ended", () => {
      playingSourcesRef.current = playingSourcesRef.current.filter((item) => item !== source);
    });
  }

  function handleRealtimeEvent(event: VoiceChatServerEvent) {
    switch (event.type) {
      case "session_open":
        setVoiceChatConnected(true);
        setVoiceChatRecording(true);
        setVoiceChatBusy(false);
        setVoiceChatStatus(`实时会话已连接：${event.model}`);
        return;
      case "memory_config":
        setVoiceChatMemoryScope(event.enabled ? event.scope : "");
        return;
      case "user_transcript":
        currentUserTurnRef.current = event.text;
        currentMemorySavedRef.current = false;
        currentMemoryRetrieveAttemptedRef.current = false;
        currentLocalPendingCountRef.current = 0;
        currentCloudCountRef.current = 0;
        setVoiceChatTranscript(event.text);
        currentMemoriesRetrievedRef.current = 0;
        setVoiceChatMemoriesRetrieved(0);
        setVoiceChatMemoryWriteStatus("");
        setVoiceChatMemorySourceStatus("");
        setVoiceChatStatus("正在听你说话…");
        return;
      case "memory_context":
        currentMemoryRetrieveAttemptedRef.current = Boolean(event.attempted);
        currentMemoriesRetrievedRef.current = event.memories_retrieved;
        currentLocalPendingCountRef.current = event.local_pending_count || 0;
        currentCloudCountRef.current = event.cloud_count || 0;
        setVoiceChatMemoriesRetrieved(event.memories_retrieved);
        setVoiceChatMemorySourceStatus(describeMemoryContext(event));
        setVoiceChatStatus(
          event.memories_retrieved > 0
            ? `已回忆 ${event.memories_retrieved} 条长期记忆，准备回答…`
            : "已尝试回忆，准备继续回答…"
        );
        return;
      case "memory_write":
        currentMemorySavedRef.current = event.saved_count > 0;
        setVoiceChatMemoryWriteStatus(describeMemoryWriteResult(event));
        return;
      case "assistant_text":
        currentAssistantTurnRef.current = mergeAssistantText(currentAssistantTurnRef.current, event.text);
        setVoiceChatReply(currentAssistantTurnRef.current);
        setVoiceChatStatus("助手正在说话…");
        return;
      case "assistant_audio":
        void playAssistantAudio(event.audio, event.sample_rate);
        return;
      case "interrupted":
        stopAssistantPlayback();
        setVoiceChatStatus("已打断助手，继续说话中…");
        return;
      case "turn_complete":
        {
          const retrievedCount = currentMemoriesRetrievedRef.current;
          const retrieveAttempted = currentMemoryRetrieveAttemptedRef.current;
          commitCompletedTurn();
          setVoiceChatStatus(
            retrievedCount > 0
              ? `本轮已完成，回忆了 ${retrievedCount} 条长期记忆`
              : retrieveAttempted
                ? "本轮已完成，已尝试回忆但未命中"
                : "本轮已完成，继续说话即可"
          );
          return;
        }
      case "error":
        setVoiceChatError(event.message);
        setVoiceChatStatus("实时语音会话出错");
        stopSessionResources();
        return;
      case "pong":
      default:
        return;
    }
  }

  async function startSession() {
    setVoiceChatError("");
    const AudioContextCtor = getAudioContextCtor();
    if (
      !navigator.mediaDevices?.getUserMedia ||
      typeof WebSocket === "undefined" ||
      !AudioContextCtor
    ) {
      setVoiceChatSupported(false);
      setVoiceChatError("当前环境不支持实时语音聊天。");
      return;
    }

    try {
      const sessionEpoch = markNewSessionEpoch();
      setVoiceChatBusy(true);
      setVoiceChatStatus("正在连接实时语音会话…");
      currentUserTurnRef.current = "";
      currentAssistantTurnRef.current = "";
      currentMemoriesRetrievedRef.current = 0;
      currentMemorySavedRef.current = false;
      currentMemoryRetrieveAttemptedRef.current = false;
      currentLocalPendingCountRef.current = 0;
      currentCloudCountRef.current = 0;
      setVoiceChatTranscript("");
      setVoiceChatReply("");
      setVoiceChatMemoriesRetrieved(0);
      setVoiceChatMemoryWriteStatus("");
      setVoiceChatMemorySourceStatus("");
      setVoiceChatMemoryScope("");

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      mediaStreamRef.current = stream;

      const audioContext = new AudioContextCtor();
      audioContextRef.current = audioContext;
      await audioContext.resume();

      const ws = new WebSocket(
        buildVoiceChatWebSocketUrl({
          provider: voiceChatProvider,
          model: voiceChatModel.trim() || undefined,
          voice: voiceChatVoice,
        })
      );
      const memoryConfig = buildVoiceChatSessionConfig();
      ws.binaryType = "arraybuffer";
      websocketRef.current = ws;

      ws.onmessage = (message) => {
        if (sessionEpochRef.current !== sessionEpoch) {
          return;
        }
        if (typeof message.data !== "string") {
          return;
        }
        try {
          handleRealtimeEvent(JSON.parse(message.data) as VoiceChatServerEvent);
        } catch {
          setVoiceChatError("实时语音消息解析失败。");
        }
      };

      ws.onerror = () => {
        if (sessionEpochRef.current !== sessionEpoch) {
          return;
        }
        setVoiceChatError("实时语音连接失败。");
        setVoiceChatStatus("实时语音连接失败");
      };

      ws.onclose = () => {
        if (sessionEpochRef.current !== sessionEpoch) {
          return;
        }
        stopSessionResources();
        setVoiceChatStatus((prev) => (prev.includes("出错") ? prev : "实时语音会话已结束"));
      };

      ws.onopen = () => {
        if (sessionEpochRef.current !== sessionEpoch || websocketRef.current !== ws) {
          return;
        }
        if (memoryConfig) {
          ws.send(JSON.stringify({ type: "config", memory: memoryConfig }));
        }
        const source = audioContext.createMediaStreamSource(stream);
        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        const muteGain = audioContext.createGain();
        muteGain.gain.value = 0;

        processor.onaudioprocess = (audioEvent) => {
          if (sessionEpochRef.current !== sessionEpoch || ws.readyState !== WebSocket.OPEN) {
            return;
          }
          const input = audioEvent.inputBuffer.getChannelData(0);
          const pcm = encodePcm16k(input, audioContext.sampleRate);
          if (pcm.byteLength > 0) {
            ws.send(pcm);
          }
        };

        source.connect(processor);
        processor.connect(muteGain);
        muteGain.connect(audioContext.destination);

        sourceRef.current = source;
        processorRef.current = processor;
        muteGainRef.current = muteGain;
      };
    } catch (err) {
      stopSessionResources();
      setVoiceChatError(normalizeVoiceCaptureError(err, formatErrorMessage(err, "启动实时语音聊天失败。")));
      setVoiceChatStatus("实时语音不可用");
    }
  }

  function stopSession() {
    const ws = websocketRef.current;
    markNewSessionEpoch();
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "stop" }));
    }
    commitCompletedTurn();
    stopSessionResources();
    setVoiceChatStatus("实时语音会话已结束");
  }

  async function onToggleRecording() {
    if (voiceChatBusy) {
      return;
    }
    if (voiceChatConnected || voiceChatRecording) {
      stopSession();
      return;
    }
    await startSession();
  }

  const sessionSummary = useMemo(() => voiceChatMessages.slice(-6), [voiceChatMessages]);

  return {
    voiceChatProvider,
    voiceChatProviderOptions: resolvedProviders,
    voiceChatModel,
    voiceChatModelOptions,
    voiceChatVoice,
    voiceChatVoiceOptions: voiceChatProvider === DASHSCOPE_PROVIDER ? DASHSCOPE_REALTIME_VOICES : GOOGLE_REALTIME_VOICES,
    voiceChatBusy,
    voiceChatRecording,
    voiceChatConnected,
    voiceChatSupported,
    voiceChatStatus,
    voiceChatError,
    voiceChatTranscript,
    voiceChatReply,
    voiceChatMemoriesRetrieved,
    voiceChatMessages,
    sessionSummary,
    onToggleRecording,
    onProviderChange: (provider: string) => {
      setVoiceChatProvider(provider);
      setVoiceChatModel(resolveDefaultModel(provider, providerModelCatalog));
    },
    onModelChange: setVoiceChatModel,
    onVoiceChange: setVoiceChatVoice,
    onResetSession: () => {
      markNewSessionEpoch();
      stopSessionResources();
      currentUserTurnRef.current = "";
      currentAssistantTurnRef.current = "";
      currentMemoriesRetrievedRef.current = 0;
      currentMemoryRetrieveAttemptedRef.current = false;
      currentLocalPendingCountRef.current = 0;
      currentCloudCountRef.current = 0;
      setVoiceChatTranscript("");
      setVoiceChatReply("");
      setVoiceChatMemoriesRetrieved(0);
      setVoiceChatMessages([]);
      setVoiceChatError("");
      setVoiceChatStatus("点击开始实时语音聊天");
      setVoiceChatMemoryWriteStatus("");
      setVoiceChatMemorySourceStatus("");
      setVoiceChatMemoryScope("");
    },
    voiceChatMemoryWriteStatus,
    voiceChatMemorySourceStatus,
    voiceChatMemoryScope,
  };
}

export type UseVoiceChatResult = ReturnType<typeof useVoiceChat>;
