import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  createAudioOverviewPodcast,
  fetchApiRuntimeInfo,
  fetchSettings,
  fetchAudioOverviewPodcastAudio,
  createVoiceClone,
  createVoiceDesign,
  deleteAudioOverviewPodcast,
  deleteCustomVoice,
  fetchSpeakAudio,
  fetchVoices,
  generateAudioOverviewScript,
  getAudioOverviewPodcast,
  listAudioOverviewPodcasts,
  saveAudioOverviewScript,
  synthesizeAudioOverviewPodcast,
  listCustomVoices,
  streamChatCompletion,
  translateText,
  updateAudioOverviewPodcast,
  updateSettings,
  ApiRequestError,
  type AudioOverviewPodcast,
  type AudioOverviewScriptLine,
  type AppSettings,
  type ChatMessage,
  type CustomVoice,
  type SettingsModelValue,
  type VoiceType,
  type VoiceInfo
} from "./api";
import ErrorNotice from "./components/ErrorNotice";

const DEFAULT_TEXT = "你好，这是 VoiceSpirit Web 迁移阶段的语音测试。";
const PROVIDERS = ["Google", "DashScope", "DeepSeek", "OpenRouter", "SiliconFlow", "Groq"];
type ActiveTab =
  | "tts"
  | "chat"
  | "translate"
  | "voice_design"
  | "voice_clone"
  | "audio_overview"
  | "settings";

const SIDEBAR_ITEMS: Array<{ tab: ActiveTab; label: string; icon: string }> = [
  { tab: "chat", label: "聊天", icon: "聊" },
  { tab: "translate", label: "翻译", icon: "译" },
  { tab: "tts", label: "语音", icon: "声" },
  { tab: "audio_overview", label: "播客", icon: "播" },
  { tab: "settings", label: "设置", icon: "设" }
];

const CHAT_QUICK_ACTIONS: Array<{ title: string; icon: string; prompt: string }> = [
  {
    title: "起草邮件",
    icon: "邮",
    prompt: "请帮我起草一封语气专业但不生硬的项目进度更新邮件。"
  },
  {
    title: "编写代码",
    icon: "码",
    prompt: "请帮我写一个 TypeScript 工具函数，用于安全解析 JSON 并返回默认值。"
  },
  {
    title: "头脑风暴",
    icon: "想",
    prompt: "围绕语音类 AI 应用，给我 10 个可以快速上线验证的产品想法。"
  },
  {
    title: "总结文本",
    icon: "总",
    prompt: "请把下面内容总结为 5 个要点，并给出 2 条可执行建议。"
  }
];

const PROVIDER_API_KEY_FIELD: Record<string, string> = {
  DeepSeek: "deepseek_api_key",
  OpenRouter: "openrouter_api_key",
  SiliconFlow: "siliconflow_api_key",
  Groq: "groq_api_key",
  DashScope: "dashscope_api_key",
  Google: "google_api_key"
};

function parseModelValue(
  value: SettingsModelValue | undefined
): { defaultModel: string; availableModels: string[] } {
  if (typeof value === "string") {
    return { defaultModel: value, availableModels: [] };
  }
  if (!value || typeof value !== "object") {
    return { defaultModel: "", availableModels: [] };
  }
  const defaultModel =
    typeof value.default === "string" ? value.default : "";
  const availableModels = Array.isArray(value.available)
    ? value.available.filter((item) => typeof item === "string")
    : [];
  return { defaultModel, availableModels };
}

function formatErrorMessage(error: unknown, fallback: string): string {
  if (!(error instanceof Error)) {
    return fallback;
  }
  let message = error.message || fallback;
  if (error instanceof ApiRequestError) {
    const requestId = error.detail?.meta?.request_id;
    if (typeof requestId === "string" && requestId.trim() && !message.includes("request_id:")) {
      message = `${message} (request_id: ${requestId.trim()})`;
    }
  }
  return message;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("chat");

  const [text, setText] = useState(DEFAULT_TEXT);
  const [voices, setVoices] = useState<VoiceInfo[]>([]);
  const [voice, setVoice] = useState("");
  const [rate, setRate] = useState("+0%");
  const [audioUrl, setAudioUrl] = useState("");
  const [loadingVoices, setLoadingVoices] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [ttsError, setTtsError] = useState("");

  const [chatProvider, setChatProvider] = useState("Google");
  const [chatModel, setChatModel] = useState("");
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatBusy, setChatBusy] = useState(false);
  const [chatError, setChatError] = useState("");

  const [translateProvider, setTranslateProvider] = useState("DashScope");
  const [translateModel, setTranslateModel] = useState("");
  const [sourceLanguage, setSourceLanguage] = useState("auto");
  const [targetLanguage, setTargetLanguage] = useState("English");
  const [translateInput, setTranslateInput] = useState("这是一个翻译接口测试。");
  const [translateResult, setTranslateResult] = useState("");
  const [translateBusy, setTranslateBusy] = useState(false);
  const [translateError, setTranslateError] = useState("");

  const [designPrompt, setDesignPrompt] = useState(
    "温柔、清晰、语速适中，适合讲解和对话。"
  );
  const [designPreviewText, setDesignPreviewText] = useState(
    "你好，我是 VoiceSpirit 新创建的音色，很高兴为你服务。"
  );
  const [designName, setDesignName] = useState("voice_design_demo");
  const [designLanguage, setDesignLanguage] = useState("zh");
  const [designBusy, setDesignBusy] = useState(false);
  const [designListBusy, setDesignListBusy] = useState(false);
  const [designError, setDesignError] = useState("");
  const [designInfo, setDesignInfo] = useState("");
  const [designPreviewAudio, setDesignPreviewAudio] = useState("");
  const [designVoices, setDesignVoices] = useState<CustomVoice[]>([]);

  const [cloneName, setCloneName] = useState("voice_clone_demo");
  const [cloneAudioFile, setCloneAudioFile] = useState<File | null>(null);
  const [cloneBusy, setCloneBusy] = useState(false);
  const [cloneListBusy, setCloneListBusy] = useState(false);
  const [cloneError, setCloneError] = useState("");
  const [cloneInfo, setCloneInfo] = useState("");
  const [cloneVoices, setCloneVoices] = useState<CustomVoice[]>([]);

  const [settingsBusy, setSettingsBusy] = useState(false);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsError, setSettingsError] = useState("");
  const [settingsInfo, setSettingsInfo] = useState("");
  const [settingsConfigPath, setSettingsConfigPath] = useState("");
  const [settingsProviders, setSettingsProviders] = useState<string[]>([]);
  const [settingsData, setSettingsData] = useState<AppSettings | null>(null);
  const [settingsProvider, setSettingsProvider] = useState("DashScope");
  const [settingsApiKey, setSettingsApiKey] = useState("");
  const [settingsApiUrl, setSettingsApiUrl] = useState("");
  const [settingsDefaultModel, setSettingsDefaultModel] = useState("");
  const [settingsAvailableModelsText, setSettingsAvailableModelsText] = useState("");

  const [audioOverviewTopic, setAudioOverviewTopic] = useState("AI 对个人学习习惯的影响");
  const [audioOverviewLanguage, setAudioOverviewLanguage] = useState("zh");
  const [audioOverviewProvider, setAudioOverviewProvider] = useState("DashScope");
  const [audioOverviewModel, setAudioOverviewModel] = useState("");
  const [audioOverviewTurnCount, setAudioOverviewTurnCount] = useState(8);
  const [audioOverviewScriptLines, setAudioOverviewScriptLines] = useState<
    AudioOverviewScriptLine[]
  >([]);
  const [audioOverviewPodcastId, setAudioOverviewPodcastId] = useState<number | null>(null);
  const [audioOverviewPodcasts, setAudioOverviewPodcasts] = useState<AudioOverviewPodcast[]>(
    []
  );
  const [audioOverviewVoiceA, setAudioOverviewVoiceA] = useState("");
  const [audioOverviewVoiceB, setAudioOverviewVoiceB] = useState("");
  const [audioOverviewRate, setAudioOverviewRate] = useState("+0%");
  const [audioOverviewGapMs, setAudioOverviewGapMs] = useState(250);
  const [audioOverviewMergeStrategy, setAudioOverviewMergeStrategy] = useState<
    "auto" | "pydub" | "ffmpeg" | "concat"
  >("auto");
  const [audioOverviewBusy, setAudioOverviewBusy] = useState(false);
  const [audioOverviewSaving, setAudioOverviewSaving] = useState(false);
  const [audioOverviewSynthBusy, setAudioOverviewSynthBusy] = useState(false);
  const [audioOverviewListBusy, setAudioOverviewListBusy] = useState(false);
  const [audioOverviewError, setAudioOverviewError] = useState("");
  const [audioOverviewInfo, setAudioOverviewInfo] = useState("");
  const [audioOverviewAudioUrl, setAudioOverviewAudioUrl] = useState("");
  const [backendPhase, setBackendPhase] = useState("");
  const [backendAuthMode, setBackendAuthMode] = useState("");
  const [backendAuthEnabled, setBackendAuthEnabled] = useState<boolean | null>(null);
  const [backendVersion, setBackendVersion] = useState("");
  const [backendStatus, setBackendStatus] = useState("");
  const [backendRuntimeRaw, setBackendRuntimeRaw] = useState("{}");
  const [backendRuntimeOpen, setBackendRuntimeOpen] = useState(false);
  const [runtimeCopyStatus, setRuntimeCopyStatus] = useState<"idle" | "ok" | "fail">("idle");

  useEffect(() => {
    let disposed = false;

    async function loadVoices() {
      try {
        setLoadingVoices(true);
        const data = await fetchVoices();
        if (disposed) {
          return;
        }
        setVoices(data.voices);
        if (data.voices.length > 0) {
          setVoice(data.voices[0].name);
        }
      } catch (err) {
        if (!disposed) {
          setTtsError(formatErrorMessage(err, "Unknown error"));
        }
      } finally {
        if (!disposed) {
          setLoadingVoices(false);
        }
      }
    }

    loadVoices();
    return () => {
      disposed = true;
    };
  }, []);

  useEffect(() => {
    let disposed = false;

    async function loadApiRuntimeInfo() {
      try {
        const info = await fetchApiRuntimeInfo();
        if (disposed) {
          return;
        }
        setBackendPhase(typeof info.phase === "string" ? info.phase : "");
        setBackendAuthMode(typeof info.auth_mode === "string" ? info.auth_mode : "");
        setBackendAuthEnabled(
          typeof info.auth_enabled === "boolean" ? info.auth_enabled : null
        );
        setBackendVersion(typeof info.version === "string" ? info.version : "");
        setBackendStatus(typeof info.status === "string" ? info.status : "");
        setBackendRuntimeRaw(JSON.stringify(info.raw || {}, null, 2));
      } catch {
        if (disposed) {
          return;
        }
        setBackendPhase("");
        setBackendAuthMode("");
        setBackendAuthEnabled(null);
        setBackendVersion("");
        setBackendStatus("");
        setBackendRuntimeRaw("{}");
      }
    }

    void loadApiRuntimeInfo();
    return () => {
      disposed = true;
    };
  }, []);

  const errorRuntimeContext = useMemo(
    () => ({
      backend_phase: backendPhase,
      backend_auth_mode: backendAuthMode,
      backend_auth_enabled: backendAuthEnabled,
      backend_version: backendVersion,
      backend_status: backendStatus
    }),
    [backendPhase, backendAuthMode, backendAuthEnabled, backendVersion, backendStatus]
  );

  const chatHistoryItems = useMemo(() => {
    const items: Array<{ id: string; content: string }> = [];
    chatMessages.forEach((msg, idx) => {
      if (msg.role !== "user") {
        return;
      }
      const clean = msg.content.trim();
      if (!clean) {
        return;
      }
      const short = clean.length > 26 ? `${clean.slice(0, 26)}...` : clean;
      items.push({
        id: `${idx}-${msg.role}`,
        content: short
      });
    });
    return items.slice(-40).reverse();
  }, [chatMessages]);

  useEffect(() => {
    if (runtimeCopyStatus !== "ok") {
      return;
    }
    const timer = window.setTimeout(() => {
      setRuntimeCopyStatus("idle");
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [runtimeCopyStatus]);

  async function handleCopyBackendRuntime() {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(backendRuntimeRaw || "{}");
      } else {
        throw new Error("clipboard api unavailable");
      }
      setRuntimeCopyStatus("ok");
    } catch {
      setRuntimeCopyStatus("fail");
    }
  }

  const voiceOptions = useMemo(() => {
    return voices.map((item) => ({
      value: item.name,
      label: `${item.short_name || item.name} (${item.locale})`
    }));
  }, [voices]);

  const audioOverviewVoiceOptions = useMemo(() => {
    const localePrefix = audioOverviewLanguage === "en" ? "en-US" : "zh-CN";
    const preferred = voices.filter((item) =>
      item.locale.toLowerCase().startsWith(localePrefix.toLowerCase())
    );
    return preferred.length ? preferred : voices;
  }, [voices, audioOverviewLanguage]);

  useEffect(() => {
    return () => {
      if (audioUrl.startsWith("blob:")) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  useEffect(() => {
    return () => {
      if (audioOverviewAudioUrl.startsWith("blob:")) {
        URL.revokeObjectURL(audioOverviewAudioUrl);
      }
    };
  }, [audioOverviewAudioUrl]);

  useEffect(() => {
    if (!audioOverviewVoiceOptions.length) {
      return;
    }
    const male = audioOverviewVoiceOptions.find((item) =>
      item.gender.toLowerCase().includes("male")
    );
    const female = audioOverviewVoiceOptions.find((item) =>
      item.gender.toLowerCase().includes("female")
    );
    const defaultA = male?.name || audioOverviewVoiceOptions[0].name;
    const defaultB = female?.name || audioOverviewVoiceOptions[0].name;

    const hasA = audioOverviewVoiceOptions.some((item) => item.name === audioOverviewVoiceA);
    const hasB = audioOverviewVoiceOptions.some((item) => item.name === audioOverviewVoiceB);
    if (!hasA) {
      setAudioOverviewVoiceA(defaultA);
    }
    if (!hasB) {
      setAudioOverviewVoiceB(defaultB);
    }
  }, [audioOverviewVoiceA, audioOverviewVoiceB, audioOverviewVoiceOptions]);

  useEffect(() => {
    void refreshCustomVoices("voice_design");
    void refreshCustomVoices("voice_clone");
    void loadSettings();
    void loadAudioOverviewPodcasts();
  }, []);

  useEffect(() => {
    if (!settingsData) {
      return;
    }
    const keyField = PROVIDER_API_KEY_FIELD[settingsProvider];
    const apiKey = keyField ? settingsData.api_keys[keyField] || "" : "";
    const apiUrl = settingsData.api_urls[settingsProvider] || "";
    const modelValue = settingsData.default_models[settingsProvider];
    const { defaultModel, availableModels } = parseModelValue(modelValue);

    setSettingsApiKey(apiKey);
    setSettingsApiUrl(apiUrl);
    setSettingsDefaultModel(defaultModel);
    setSettingsAvailableModelsText(availableModels.join("\n"));
  }, [settingsData, settingsProvider]);

  async function handleSpeak(event: FormEvent) {
    event.preventDefault();
    setTtsError("");
    if (!text.trim()) {
      setTtsError("Text is required.");
      return;
    }
    setGenerating(true);
    try {
      const blob = await fetchSpeakAudio({
        text: text.trim(),
        voice: voice || undefined,
        rate
      });
      if (audioUrl.startsWith("blob:")) {
        URL.revokeObjectURL(audioUrl);
      }
      setAudioUrl(URL.createObjectURL(blob));
    } catch (err) {
      setTtsError(formatErrorMessage(err, "TTS request failed."));
    } finally {
      setGenerating(false);
    }
  }

  async function handleChatSubmit(event: FormEvent) {
    event.preventDefault();
    const userText = chatInput.trim();
    if (!userText) {
      return;
    }
    setChatError("");
    setChatBusy(true);

    const nextHistory: ChatMessage[] = [
      ...chatMessages,
      { role: "user", content: userText }
    ];
    setChatMessages([...nextHistory, { role: "assistant", content: "" }]);
    setChatInput("");

    try {
      let streamedReply = "";
      await streamChatCompletion({
        provider: chatProvider,
        model: chatModel.trim() || undefined,
        messages: nextHistory,
        temperature: 0.7,
        max_tokens: 1024
      }, {
        onDelta: (chunk) => {
          streamedReply += chunk;
          setChatMessages((prev) => {
            if (!prev.length) {
              return prev;
            }
            const next = [...prev];
            const lastIdx = next.length - 1;
            const last = next[lastIdx];
            if (last.role !== "assistant") {
              return prev;
            }
            next[lastIdx] = { ...last, content: streamedReply };
            return next;
          });
        }
      });
    } catch (err) {
      setChatMessages((prev) => {
        if (!prev.length) {
          return prev;
        }
        const last = prev[prev.length - 1];
        if (last.role === "assistant" && !last.content.trim()) {
          return prev.slice(0, -1);
        }
        return prev;
      });
      setChatError(formatErrorMessage(err, "Chat request failed."));
    } finally {
      setChatBusy(false);
    }
  }

  function handleNewChatSession() {
    setChatMessages([]);
    setChatInput("");
    setChatError("");
    setActiveTab("chat");
  }

  async function handleTranslateSubmit(event: FormEvent) {
    event.preventDefault();
    const sourceText = translateInput.trim();
    if (!sourceText) {
      setTranslateError("Text is required.");
      return;
    }

    setTranslateError("");
    setTranslateBusy(true);
    try {
      const result = await translateText({
        text: sourceText,
        source_language: sourceLanguage.trim() || "auto",
        target_language: targetLanguage.trim(),
        provider: translateProvider,
        model: translateModel.trim() || undefined
      });
      setTranslateResult(result.translated_text);
    } catch (err) {
      setTranslateError(
        formatErrorMessage(err, "Translate request failed.")
      );
    } finally {
      setTranslateBusy(false);
    }
  }

  async function refreshCustomVoices(voiceType: VoiceType) {
    try {
      if (voiceType === "voice_design") {
        setDesignListBusy(true);
      } else {
        setCloneListBusy(true);
      }
      const result = await listCustomVoices(voiceType);
      if (voiceType === "voice_design") {
        setDesignVoices(result.voices);
      } else {
        setCloneVoices(result.voices);
      }
    } catch (err) {
      const message = formatErrorMessage(err, "Load voices failed.");
      if (voiceType === "voice_design") {
        setDesignError(message);
      } else {
        setCloneError(message);
      }
    } finally {
      if (voiceType === "voice_design") {
        setDesignListBusy(false);
      } else {
        setCloneListBusy(false);
      }
    }
  }

  async function loadSettings() {
    setSettingsBusy(true);
    setSettingsError("");
    try {
      const result = await fetchSettings();
      setSettingsData(result.settings);
      setSettingsConfigPath(result.config_path);
      setSettingsProviders(result.providers);
      if (result.providers.length > 0 && !result.providers.includes(settingsProvider)) {
        setSettingsProvider(result.providers[0]);
      }
    } catch (err) {
      setSettingsError(formatErrorMessage(err, "Load settings failed."));
    } finally {
      setSettingsBusy(false);
    }
  }

  async function handleSaveProviderSettings(event: FormEvent) {
    event.preventDefault();
    setSettingsError("");
    setSettingsInfo("");

    const keyField = PROVIDER_API_KEY_FIELD[settingsProvider];
    if (!keyField) {
      setSettingsError(`Unsupported provider key mapping: ${settingsProvider}`);
      return;
    }

    const availableModels = settingsAvailableModelsText
      .split(/\r?\n/)
      .map((item) => item.trim())
      .filter(Boolean);

    setSettingsSaving(true);
    try {
      const result = await updateSettings({
        api_keys: {
          [keyField]: settingsApiKey.trim()
        },
        api_urls: {
          [settingsProvider]: settingsApiUrl.trim()
        },
        default_models: {
          [settingsProvider]: {
            default: settingsDefaultModel.trim(),
            available: availableModels
          }
        }
      });
      setSettingsData(result.settings);
      setSettingsConfigPath(result.config_path);
      setSettingsProviders(result.providers);
      setSettingsInfo(`Saved ${settingsProvider} settings.`);
    } catch (err) {
      setSettingsError(formatErrorMessage(err, "Save settings failed."));
    } finally {
      setSettingsSaving(false);
    }
  }

  async function handleVoiceDesignCreate(event: FormEvent) {
    event.preventDefault();
    setDesignError("");
    setDesignInfo("");
    setDesignBusy(true);
    try {
      const result = await createVoiceDesign({
        voice_prompt: designPrompt,
        preview_text: designPreviewText,
        preferred_name: designName,
        language: designLanguage.trim() || "zh"
      });
      setDesignInfo(`Created: ${result.voice}`);
      const previewAudioData = result.preview_audio_data || "";
      setDesignPreviewAudio(
        previewAudioData ? `data:audio/wav;base64,${previewAudioData}` : ""
      );
      await refreshCustomVoices("voice_design");
    } catch (err) {
      setDesignError(formatErrorMessage(err, "Create design voice failed."));
    } finally {
      setDesignBusy(false);
    }
  }

  async function handleVoiceCloneCreate(event: FormEvent) {
    event.preventDefault();
    setCloneError("");
    setCloneInfo("");
    if (!cloneAudioFile) {
      setCloneError("Please choose an audio file.");
      return;
    }
    setCloneBusy(true);
    try {
      const result = await createVoiceClone({
        preferred_name: cloneName,
        audio_file: cloneAudioFile
      });
      setCloneInfo(`Created: ${result.voice}`);
      await refreshCustomVoices("voice_clone");
    } catch (err) {
      setCloneError(formatErrorMessage(err, "Create clone voice failed."));
    } finally {
      setCloneBusy(false);
    }
  }

  async function handleDeleteVoice(voiceName: string, voiceType: VoiceType) {
    try {
      await deleteCustomVoice(voiceName, voiceType);
      if (voiceType === "voice_design") {
        await refreshCustomVoices("voice_design");
      } else {
        await refreshCustomVoices("voice_clone");
      }
    } catch (err) {
      const message = formatErrorMessage(err, "Delete voice failed.");
      if (voiceType === "voice_design") {
        setDesignError(message);
      } else {
        setCloneError(message);
      }
    }
  }

  function setAudioOverviewAudioBlob(blob: Blob) {
    if (audioOverviewAudioUrl.startsWith("blob:")) {
      URL.revokeObjectURL(audioOverviewAudioUrl);
    }
    setAudioOverviewAudioUrl(URL.createObjectURL(blob));
  }

  function clearAudioOverviewAudio() {
    if (audioOverviewAudioUrl.startsWith("blob:")) {
      URL.revokeObjectURL(audioOverviewAudioUrl);
    }
    setAudioOverviewAudioUrl("");
  }

  function normalizeAudioOverviewScriptLines(
    lines: AudioOverviewScriptLine[]
  ): AudioOverviewScriptLine[] {
    return lines
      .map((line) => ({
        role: line.role === "B" ? "B" : "A",
        text: line.text.trim()
      }))
      .filter((line) => line.text.length > 0);
  }

  function applyAudioOverviewPodcast(podcast: AudioOverviewPodcast) {
    setAudioOverviewPodcastId(podcast.id);
    setAudioOverviewTopic(podcast.topic);
    setAudioOverviewLanguage(podcast.language?.toLowerCase().startsWith("en") ? "en" : "zh");
    setAudioOverviewScriptLines(
      podcast.script_lines.length > 0
        ? podcast.script_lines
        : [
            { role: "A", text: "" },
            { role: "B", text: "" }
          ]
    );
  }

  async function loadAudioOverviewPodcasts() {
    setAudioOverviewListBusy(true);
    try {
      const data = await listAudioOverviewPodcasts(30);
      setAudioOverviewPodcasts(data.podcasts);
    } catch (err) {
      setAudioOverviewError(
        formatErrorMessage(err, "Load audio overview podcasts failed.")
      );
    } finally {
      setAudioOverviewListBusy(false);
    }
  }

  async function loadAudioOverviewPodcastById(podcastId: number) {
    setAudioOverviewError("");
    setAudioOverviewInfo("");
    try {
      const podcast = await getAudioOverviewPodcast(podcastId);
      applyAudioOverviewPodcast(podcast);
      if (podcast.audio_path) {
        const blob = await fetchAudioOverviewPodcastAudio(podcastId);
        setAudioOverviewAudioBlob(blob);
      } else {
        clearAudioOverviewAudio();
      }
      setAudioOverviewInfo(`Loaded podcast #${podcast.id}.`);
    } catch (err) {
      setAudioOverviewError(
        formatErrorMessage(err, "Load podcast detail failed.")
      );
    }
  }

  async function ensureAudioOverviewPodcastSaved(): Promise<number> {
    const topic = audioOverviewTopic.trim();
    const scriptLines = normalizeAudioOverviewScriptLines(audioOverviewScriptLines);
    if (!topic) {
      throw new Error("Topic is required.");
    }
    if (scriptLines.length < 2) {
      throw new Error("Script must contain at least 2 non-empty lines.");
    }

    if (audioOverviewPodcastId === null) {
      const created = await createAudioOverviewPodcast({
        topic,
        language: audioOverviewLanguage,
        script_lines: scriptLines
      });
      applyAudioOverviewPodcast(created);
      return created.id;
    }

    const updated = await updateAudioOverviewPodcast(audioOverviewPodcastId, {
      topic,
      language: audioOverviewLanguage,
      script_lines: scriptLines
    });
    applyAudioOverviewPodcast(updated);
    return updated.id;
  }

  async function handleGenerateAudioOverviewScript(event: FormEvent) {
    event.preventDefault();
    const topic = audioOverviewTopic.trim();
    if (!topic) {
      setAudioOverviewError("Topic is required.");
      return;
    }

    setAudioOverviewError("");
    setAudioOverviewInfo("");
    setAudioOverviewBusy(true);
    try {
      const generated = await generateAudioOverviewScript({
        topic,
        language: audioOverviewLanguage,
        turn_count: audioOverviewTurnCount,
        provider: audioOverviewProvider,
        model: audioOverviewModel.trim() || undefined
      });
      const normalized = normalizeAudioOverviewScriptLines(generated.script_lines);
      setAudioOverviewLanguage(generated.language);
      setAudioOverviewScriptLines(normalized);

      if (audioOverviewPodcastId === null) {
        const created = await createAudioOverviewPodcast({
          topic,
          language: generated.language,
          script_lines: normalized
        });
        applyAudioOverviewPodcast(created);
        setAudioOverviewInfo(`Script generated and saved as podcast #${created.id}.`);
      } else {
        const updated = await updateAudioOverviewPodcast(audioOverviewPodcastId, {
          topic,
          language: generated.language,
          script_lines: normalized
        });
        applyAudioOverviewPodcast(updated);
        setAudioOverviewInfo(`Script regenerated for podcast #${updated.id}.`);
      }

      await loadAudioOverviewPodcasts();
    } catch (err) {
      setAudioOverviewError(
        formatErrorMessage(err, "Generate script failed.")
      );
    } finally {
      setAudioOverviewBusy(false);
    }
  }

  async function handleSaveAudioOverviewScript() {
    setAudioOverviewError("");
    setAudioOverviewInfo("");
    setAudioOverviewSaving(true);
    try {
      const podcastId = await ensureAudioOverviewPodcastSaved();
      const scriptLines = normalizeAudioOverviewScriptLines(audioOverviewScriptLines);
      const updated = await saveAudioOverviewScript(podcastId, scriptLines);
      applyAudioOverviewPodcast(updated);
      await loadAudioOverviewPodcasts();
      setAudioOverviewInfo(`Script saved for podcast #${podcastId}.`);
    } catch (err) {
      setAudioOverviewError(formatErrorMessage(err, "Save script failed."));
    } finally {
      setAudioOverviewSaving(false);
    }
  }

  async function handleSynthesizeAudioOverview() {
    setAudioOverviewError("");
    setAudioOverviewInfo("");
    setAudioOverviewSynthBusy(true);
    try {
      const podcastId = await ensureAudioOverviewPodcastSaved();
      const result = await synthesizeAudioOverviewPodcast(podcastId, {
        voice_a: audioOverviewVoiceA || undefined,
        voice_b: audioOverviewVoiceB || undefined,
        rate: audioOverviewRate || "+0%",
        language: audioOverviewLanguage,
        gap_ms: audioOverviewGapMs,
        merge_strategy: audioOverviewMergeStrategy
      });
      const blob = await fetchAudioOverviewPodcastAudio(podcastId);
      setAudioOverviewAudioBlob(blob);
      await loadAudioOverviewPodcasts();
      setAudioOverviewInfo(
        `Audio synthesized (${result.line_count} lines, strategy ${result.merge_strategy}, gap ${result.gap_ms_applied}ms, cache hits ${result.cache_hits}).`
      );
    } catch (err) {
      setAudioOverviewError(
        formatErrorMessage(err, "Synthesize audio failed.")
      );
    } finally {
      setAudioOverviewSynthBusy(false);
    }
  }

  async function handleDeleteAudioOverviewCurrent() {
    if (audioOverviewPodcastId === null) {
      setAudioOverviewError("No current podcast to delete.");
      return;
    }
    setAudioOverviewError("");
    setAudioOverviewInfo("");
    try {
      await deleteAudioOverviewPodcast(audioOverviewPodcastId);
      setAudioOverviewPodcastId(null);
      setAudioOverviewTopic("");
      setAudioOverviewScriptLines([]);
      clearAudioOverviewAudio();
      await loadAudioOverviewPodcasts();
      setAudioOverviewInfo("Current podcast deleted.");
    } catch (err) {
      setAudioOverviewError(
        formatErrorMessage(err, "Delete podcast failed.")
      );
    }
  }

  function handleNewAudioOverviewDraft() {
    setAudioOverviewPodcastId(null);
    setAudioOverviewTopic("");
    setAudioOverviewScriptLines([
      { role: "A", text: "" },
      { role: "B", text: "" }
    ]);
    setAudioOverviewError("");
    setAudioOverviewInfo("Created a new draft.");
    clearAudioOverviewAudio();
  }

  function handleAudioOverviewLineRoleChange(index: number, role: string) {
    setAudioOverviewScriptLines((prev) =>
      prev.map((line, idx) =>
        idx === index
          ? {
              ...line,
              role: role === "B" ? "B" : "A"
            }
          : line
      )
    );
  }

  function handleAudioOverviewLineTextChange(index: number, text: string) {
    setAudioOverviewScriptLines((prev) =>
      prev.map((line, idx) => (idx === index ? { ...line, text } : line))
    );
  }

  function handleAudioOverviewAddLine() {
    const lastRole = audioOverviewScriptLines.length
      ? audioOverviewScriptLines[audioOverviewScriptLines.length - 1].role
      : "B";
    setAudioOverviewScriptLines((prev) => [
      ...prev,
      {
        role: lastRole === "A" ? "B" : "A",
        text: ""
      }
    ]);
  }

  function handleAudioOverviewRemoveLine(index: number) {
    setAudioOverviewScriptLines((prev) => prev.filter((_, idx) => idx !== index));
  }

  return (
    <main className="vsApp">
      <aside className="vsSidebar">
        <div className="vsBrand">
          <div className="vsBrandIcon">VS</div>
          <h1>VoiceSpirit</h1>
        </div>

        <div className="vsSidebarAction">
          <button
            type="button"
            className="vsNewChatBtn"
            onClick={handleNewChatSession}
          >
            + 新建聊天
          </button>
        </div>

        <section className="vsSidebarSection">
          <p className="vsSectionLabel">应用</p>
          <nav className="vsNav">
            {SIDEBAR_ITEMS.map((item) => (
              <button
                key={item.tab}
                type="button"
                className={activeTab === item.tab ? "vsNavItem active" : "vsNavItem"}
                onClick={() => setActiveTab(item.tab)}
              >
                <span className="vsNavIcon" aria-hidden="true">
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </button>
            ))}
          </nav>
        </section>

        <section className="vsSidebarSection vsHistorySection">
          <div className="vsHistoryHead">
            <p className="vsSectionLabel">最近</p>
            <button
              type="button"
              className="vsHistoryClearBtn"
              onClick={handleNewChatSession}
            >
              清除全部
            </button>
          </div>
          <div className="vsHistoryList">
            {chatHistoryItems.map((item) => (
              <button
                key={item.id}
                type="button"
                className="vsHistoryItem"
                onClick={() => {
                  setActiveTab("chat");
                  setChatInput(item.content);
                }}
              >
                {item.content}
              </button>
            ))}
            {!chatHistoryItems.length ? (
              <p className="vsHistoryEmpty">暂无历史会话</p>
            ) : null}
          </div>
        </section>

        <div className="vsProfileCard">
          <div className="vsProfileAvatar">A</div>
          <div>
            <p className="vsProfileName">Alex Chen</p>
            <p className="vsProfilePlan">高级计划</p>
          </div>
        </div>
      </aside>

      <section className="legacyMain">
        {activeTab === "chat" ? (
          <section className="vsChatWorkspace">
            <header className="vsTopbar">
              <div className="vsTopbarLeft">
                <label className="vsTopbarField">
                  <span>提供商</span>
                  <select
                    value={chatProvider}
                    onChange={(e) => setChatProvider(e.target.value)}
                  >
                    {PROVIDERS.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </label>

                <div className="vsTopbarDivider" />

                <label className="vsTopbarField vsTopbarModelField">
                  <span>模型</span>
                  <input
                    value={chatModel}
                    onChange={(e) => setChatModel(e.target.value)}
                    placeholder="gemini-2.5-flash"
                  />
                </label>
              </div>

              <div className="vsTopbarActions">
                <button type="button" className="vsTopbarBtn">
                  分享
                </button>
                <button type="button" className="vsTopbarIconBtn" aria-label="More">
                  ···
                </button>
              </div>
            </header>

            <div className="vsChatBody">
              {!chatMessages.length ? (
                <div className="vsChatEmptyState">
                  <div className="vsEmptyLogo">AI</div>
                  <h2>开始新的对话</h2>
                  <p>有什么我可以帮您的吗？您可以问我任何问题。</p>
                  <div className="vsQuickActions">
                    {CHAT_QUICK_ACTIONS.map((action) => (
                      <button
                        key={action.title}
                        type="button"
                        className="vsQuickActionBtn"
                        onClick={() => {
                          setChatInput(action.prompt);
                        }}
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
                  {chatMessages.map((msg, idx) => (
                    <div
                      key={`${idx}-${msg.role}`}
                      className={msg.role === "user" ? "bubble user" : "bubble assistant"}
                    >
                      <strong>{msg.role === "user" ? "你" : "助手"}</strong>
                      <p>
                        {msg.content ||
                          (chatBusy &&
                          idx === chatMessages.length - 1 &&
                          msg.role === "assistant"
                            ? "..."
                            : "")}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <form onSubmit={handleChatSubmit} className="vsComposerWrap">
              <div className="vsComposer">
                <button type="button" className="vsAttachBtn" aria-label="Attachment">
                  +
                </button>
                <textarea
                  rows={1}
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="问任何问题... (Shift+Enter 换行)"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      if (!chatBusy && chatInput.trim()) {
                        e.currentTarget.form?.requestSubmit();
                      }
                    }
                  }}
                />
                <button type="submit" className="vsSendBtn" disabled={chatBusy}>
                  {chatBusy ? "发送中" : "发送"}
                </button>
              </div>
              <p className="vsChatDisclaimer">AI可能会产生关于人物、地点或事实的不准确信息。</p>
              <ErrorNotice
                message={chatError}
                scope="chat"
                context={{ ...errorRuntimeContext, provider: chatProvider, model: chatModel }}
              />
            </form>
          </section>
        ) : null}

        {activeTab === "tts" ? (
          <section className="legacyPanel">
            <form className="form" onSubmit={handleSpeak}>
              <label>
                Text
                <textarea
                  rows={6}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Enter text for TTS"
                />
              </label>
              <div className="row">
                <label>
                  Voice
                  <select
                    value={voice}
                    onChange={(e) => setVoice(e.target.value)}
                    disabled={loadingVoices || voiceOptions.length === 0}
                  >
                    {voiceOptions.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Rate
                  <input
                    value={rate}
                    onChange={(e) => setRate(e.target.value)}
                    placeholder="+0%"
                  />
                </label>
              </div>
              <button type="submit" disabled={generating}>
                {generating ? "Generating..." : "Generate Speech"}
              </button>
              <ErrorNotice
                message={ttsError}
                scope="tts"
                context={{ ...errorRuntimeContext, voice, rate }}
              />
              {audioUrl ? (
                <div className="audioWrap">
                  <p>Preview</p>
                  <audio controls src={audioUrl} />
                </div>
              ) : null}
            </form>
          </section>
        ) : null}

        {activeTab === "translate" ? (
          <section className="legacyPanel">
            <form className="form" onSubmit={handleTranslateSubmit}>
            <div className="row">
              <label>
                Provider
                <select
                  value={translateProvider}
                  onChange={(e) => setTranslateProvider(e.target.value)}
                >
                  {PROVIDERS.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Model (optional)
                <input
                  value={translateModel}
                  onChange={(e) => setTranslateModel(e.target.value)}
                  placeholder="Use config default if empty"
                />
              </label>
            </div>

            <div className="row3">
              <label>
                Source Language
                <input
                  value={sourceLanguage}
                  onChange={(e) => setSourceLanguage(e.target.value)}
                  placeholder="auto"
                />
              </label>
              <label>
                Target Language
                <input
                  value={targetLanguage}
                  onChange={(e) => setTargetLanguage(e.target.value)}
                  placeholder="English"
                />
              </label>
            </div>

            <label>
              Text
              <textarea
                rows={5}
                value={translateInput}
                onChange={(e) => setTranslateInput(e.target.value)}
                placeholder="Text to translate"
              />
            </label>
            <button type="submit" disabled={translateBusy}>
              {translateBusy ? "Translating..." : "Translate"}
            </button>
            <ErrorNotice
              message={translateError}
              scope="translate"
              context={{
                ...errorRuntimeContext,
                provider: translateProvider,
                model: translateModel,
                source_language: sourceLanguage,
                target_language: targetLanguage
              }}
            />
            {translateResult ? (
              <div className="resultBox">
                <p>Result</p>
                <pre>{translateResult}</pre>
              </div>
            ) : null}
            </form>
          </section>
        ) : null}

        {activeTab === "voice_design" ? (
          <section className="legacyPanel">
            <form className="form" onSubmit={handleVoiceDesignCreate}>
            <div className="row">
              <label>
                Preferred Name
                <input
                  value={designName}
                  onChange={(e) => setDesignName(e.target.value)}
                  placeholder="voice_design_demo"
                />
              </label>
              <label>
                Language
                <input
                  value={designLanguage}
                  onChange={(e) => setDesignLanguage(e.target.value)}
                  placeholder="zh"
                />
              </label>
            </div>

            <label>
              Voice Prompt
              <textarea
                rows={4}
                value={designPrompt}
                onChange={(e) => setDesignPrompt(e.target.value)}
                placeholder="Describe voice style"
              />
            </label>

            <label>
              Preview Text
              <textarea
                rows={3}
                value={designPreviewText}
                onChange={(e) => setDesignPreviewText(e.target.value)}
                placeholder="Preview text for generated voice"
              />
            </label>

            <div className="inlineActions">
              <button type="submit" disabled={designBusy}>
                {designBusy ? "Creating..." : "Create Voice Design"}
              </button>
              <button
                type="button"
                className="ghost"
                onClick={() => void refreshCustomVoices("voice_design")}
                disabled={designListBusy || designBusy}
              >
                {designListBusy ? "Loading..." : "Refresh List"}
              </button>
            </div>

            <ErrorNotice
              message={designError}
              scope="voice_design"
              context={{
                ...errorRuntimeContext,
                preferred_name: designName,
                language: designLanguage
              }}
            />
            {designInfo ? <p className="ok">{designInfo}</p> : null}

            {designPreviewAudio ? (
              <div className="audioWrap">
                <p>Preview Audio</p>
                <audio controls src={designPreviewAudio} />
              </div>
            ) : null}

            <div className="resultBox">
              <p>Voice Design List ({designVoices.length})</p>
              <div className="voiceList">
                {designVoices.map((item) => (
                  <div key={item.voice} className="voiceItem">
                    <div>
                      <strong>{item.voice}</strong>
                      <p>{item.target_model}</p>
                    </div>
                    <button
                      type="button"
                      className="danger"
                      onClick={() => void handleDeleteVoice(item.voice, "voice_design")}
                      disabled={designBusy || designListBusy}
                    >
                      Delete
                    </button>
                  </div>
                ))}
                {!designVoices.length ? <p className="muted">No voices found.</p> : null}
              </div>
            </div>
            </form>
          </section>
        ) : null}

        {activeTab === "voice_clone" ? (
          <section className="legacyPanel">
            <form className="form" onSubmit={handleVoiceCloneCreate}>
            <label>
              Preferred Name
              <input
                value={cloneName}
                onChange={(e) => setCloneName(e.target.value)}
                placeholder="voice_clone_demo"
              />
            </label>

            <label>
              Audio File
              <input
                type="file"
                accept="audio/*"
                onChange={(e) => setCloneAudioFile(e.target.files?.[0] || null)}
              />
            </label>
            {cloneAudioFile ? <p className="muted">Selected: {cloneAudioFile.name}</p> : null}

            <div className="inlineActions">
              <button type="submit" disabled={cloneBusy}>
                {cloneBusy ? "Creating..." : "Create Voice Clone"}
              </button>
              <button
                type="button"
                className="ghost"
                onClick={() => void refreshCustomVoices("voice_clone")}
                disabled={cloneListBusy || cloneBusy}
              >
                {cloneListBusy ? "Loading..." : "Refresh List"}
              </button>
            </div>

            <ErrorNotice
              message={cloneError}
              scope="voice_clone"
              context={{ ...errorRuntimeContext, preferred_name: cloneName }}
            />
            {cloneInfo ? <p className="ok">{cloneInfo}</p> : null}

            <div className="resultBox">
              <p>Voice Clone List ({cloneVoices.length})</p>
              <div className="voiceList">
                {cloneVoices.map((item) => (
                  <div key={item.voice} className="voiceItem">
                    <div>
                      <strong>{item.voice}</strong>
                      <p>{item.target_model}</p>
                    </div>
                    <button
                      type="button"
                      className="danger"
                      onClick={() => void handleDeleteVoice(item.voice, "voice_clone")}
                      disabled={cloneBusy || cloneListBusy}
                    >
                      Delete
                    </button>
                  </div>
                ))}
                {!cloneVoices.length ? <p className="muted">No voices found.</p> : null}
              </div>
            </div>
            </form>
          </section>
        ) : null}

        {activeTab === "audio_overview" ? (
          <section className="legacyPanel">
            <form className="form" onSubmit={handleGenerateAudioOverviewScript}>
            <div className="inlineActions">
              <button type="submit" disabled={audioOverviewBusy}>
                {audioOverviewBusy ? "Generating..." : "Generate Script"}
              </button>
              <button
                type="button"
                className="ghost"
                onClick={() => void handleSaveAudioOverviewScript()}
                disabled={audioOverviewSaving || audioOverviewBusy || audioOverviewSynthBusy}
              >
                {audioOverviewSaving ? "Saving..." : "Save Script"}
              </button>
              <button
                type="button"
                className="ghost"
                onClick={() => void loadAudioOverviewPodcasts()}
                disabled={audioOverviewListBusy}
              >
                {audioOverviewListBusy ? "Loading..." : "Refresh List"}
              </button>
              <button
                type="button"
                className="ghost"
                onClick={handleNewAudioOverviewDraft}
                disabled={audioOverviewBusy || audioOverviewSaving || audioOverviewSynthBusy}
              >
                New Draft
              </button>
              <button
                type="button"
                className="danger"
                onClick={() => void handleDeleteAudioOverviewCurrent()}
                disabled={audioOverviewPodcastId === null}
              >
                Delete Current
              </button>
            </div>

            <ErrorNotice
              message={audioOverviewError}
              scope="audio_overview"
              context={{
                ...errorRuntimeContext,
                provider: audioOverviewProvider,
                model: audioOverviewModel,
                language: audioOverviewLanguage,
                podcast_id: audioOverviewPodcastId,
                merge_strategy: audioOverviewMergeStrategy
              }}
            />
            {audioOverviewInfo ? <p className="ok">{audioOverviewInfo}</p> : null}
            {audioOverviewPodcastId !== null ? (
              <p className="muted">Current Podcast: #{audioOverviewPodcastId}</p>
            ) : (
              <p className="muted">Current Podcast: not saved</p>
            )}

            <label>
              Topic
              <textarea
                rows={4}
                value={audioOverviewTopic}
                onChange={(e) => setAudioOverviewTopic(e.target.value)}
                placeholder="Describe the podcast topic"
              />
            </label>

            <div className="rowOverview">
              <label>
                Language
                <select
                  value={audioOverviewLanguage}
                  onChange={(e) => setAudioOverviewLanguage(e.target.value)}
                >
                  <option value="zh">Chinese</option>
                  <option value="en">English</option>
                </select>
              </label>
              <label>
                Provider
                <select
                  value={audioOverviewProvider}
                  onChange={(e) => setAudioOverviewProvider(e.target.value)}
                >
                  {PROVIDERS.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Model (optional)
                <input
                  value={audioOverviewModel}
                  onChange={(e) => setAudioOverviewModel(e.target.value)}
                  placeholder="Use config default if empty"
                />
              </label>
              <label>
                Turn Count
                <input
                  type="number"
                  min={2}
                  max={40}
                  value={audioOverviewTurnCount}
                  onChange={(e) =>
                    setAudioOverviewTurnCount(
                      Number.isNaN(Number(e.target.value)) ? 8 : Number(e.target.value)
                    )
                  }
                />
              </label>
            </div>

            <div className="resultBox">
              <div className="inlineActions">
                <p>Script Lines ({audioOverviewScriptLines.length})</p>
                <button
                  type="button"
                  className="ghost"
                  onClick={handleAudioOverviewAddLine}
                >
                  Add Line
                </button>
              </div>
              <div className="scriptLineList">
                {audioOverviewScriptLines.map((line, index) => (
                  <div key={`line-${index}`} className="scriptLineItem">
                    <select
                      value={line.role}
                      onChange={(e) =>
                        handleAudioOverviewLineRoleChange(index, e.target.value)
                      }
                    >
                      <option value="A">A</option>
                      <option value="B">B</option>
                    </select>
                    <textarea
                      rows={2}
                      value={line.text}
                      onChange={(e) =>
                        handleAudioOverviewLineTextChange(index, e.target.value)
                      }
                      placeholder="Dialogue content"
                    />
                    <button
                      type="button"
                      className="danger"
                      onClick={() => handleAudioOverviewRemoveLine(index)}
                    >
                      Remove
                    </button>
                  </div>
                ))}
                {!audioOverviewScriptLines.length ? (
                  <p className="muted">No script lines yet.</p>
                ) : null}
              </div>
            </div>

            <div className="resultBox">
              <p>Synthesis</p>
              <div className="rowOverview">
                <label>
                  Voice A
                  <select
                    value={audioOverviewVoiceA}
                    onChange={(e) => setAudioOverviewVoiceA(e.target.value)}
                    disabled={!audioOverviewVoiceOptions.length}
                  >
                    {audioOverviewVoiceOptions.map((item) => (
                      <option key={`a-${item.name}`} value={item.name}>
                        {item.short_name || item.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Voice B
                  <select
                    value={audioOverviewVoiceB}
                    onChange={(e) => setAudioOverviewVoiceB(e.target.value)}
                    disabled={!audioOverviewVoiceOptions.length}
                  >
                    {audioOverviewVoiceOptions.map((item) => (
                      <option key={`b-${item.name}`} value={item.name}>
                        {item.short_name || item.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Rate
                  <input
                    value={audioOverviewRate}
                    onChange={(e) => setAudioOverviewRate(e.target.value)}
                    placeholder="+0%"
                  />
                </label>
                <label>
                  Gap (ms)
                  <input
                    type="number"
                    min={0}
                    max={3000}
                    value={audioOverviewGapMs}
                    onChange={(e) =>
                      setAudioOverviewGapMs(
                        Number.isNaN(Number(e.target.value)) ? 0 : Number(e.target.value)
                      )
                    }
                  />
                </label>
                <label>
                  Merge Strategy
                  <select
                    value={audioOverviewMergeStrategy}
                    onChange={(e) =>
                      setAudioOverviewMergeStrategy(
                        e.target.value as "auto" | "pydub" | "ffmpeg" | "concat"
                      )
                    }
                  >
                    <option value="auto">auto</option>
                    <option value="pydub">pydub</option>
                    <option value="ffmpeg">ffmpeg</option>
                    <option value="concat">concat</option>
                  </select>
                </label>
              </div>

              <button
                type="button"
                onClick={() => void handleSynthesizeAudioOverview()}
                disabled={
                  audioOverviewSynthBusy ||
                  audioOverviewBusy ||
                  audioOverviewSaving ||
                  audioOverviewScriptLines.length < 2
                }
              >
                {audioOverviewSynthBusy ? "Synthesizing..." : "Synthesize Audio"}
              </button>

              {audioOverviewAudioUrl ? (
                <div className="audioWrap">
                  <p>Preview Audio</p>
                  <audio controls src={audioOverviewAudioUrl} />
                </div>
              ) : null}
            </div>

            <div className="resultBox">
              <p>Recent Podcasts ({audioOverviewPodcasts.length})</p>
              <div className="voiceList">
                {audioOverviewPodcasts.map((item) => (
                  <div key={`podcast-${item.id}`} className="voiceItem">
                    <div>
                      <strong>#{item.id} {item.topic}</strong>
                      <p>
                        {item.language} | lines: {item.script_lines.length} | updated: {item.updated_at}
                      </p>
                    </div>
                    <button
                      type="button"
                      className="ghost"
                      onClick={() => void loadAudioOverviewPodcastById(item.id)}
                    >
                      Load
                    </button>
                  </div>
                ))}
                {!audioOverviewPodcasts.length ? (
                  <p className="muted">No podcasts found.</p>
                ) : null}
              </div>
            </div>
            </form>
          </section>
        ) : null}

        {activeTab === "settings" ? (
          <section className="legacyPanel">
            <div className="runtimeActions">
              <button
                type="button"
                className="ghost"
                onClick={() => setBackendRuntimeOpen((value) => !value)}
              >
                {backendRuntimeOpen ? "Hide backend runtime" : "Show backend runtime"}
              </button>
              <button
                type="button"
                className="ghost"
                onClick={() => void handleCopyBackendRuntime()}
              >
                {runtimeCopyStatus === "ok" ? "Runtime copied" : "Copy backend runtime"}
              </button>
            </div>
            {runtimeCopyStatus === "fail" ? (
              <p className="runtimeCopyStatus">Copy failed. Please copy runtime manually.</p>
            ) : null}
            {backendRuntimeOpen ? (
              <pre className="runtimeDetails">{backendRuntimeRaw}</pre>
            ) : null}
            <form className="form" onSubmit={handleSaveProviderSettings}>
            <div className="inlineActions">
              <button type="submit" disabled={settingsSaving || settingsBusy}>
                {settingsSaving ? "Saving..." : "Save Provider Settings"}
              </button>
              <button
                type="button"
                className="ghost"
                onClick={() => void loadSettings()}
                disabled={settingsBusy || settingsSaving}
              >
                {settingsBusy ? "Loading..." : "Reload Settings"}
              </button>
            </div>

            <ErrorNotice
              message={settingsError}
              scope="settings"
              context={{
                ...errorRuntimeContext,
                provider: settingsProvider,
                default_model: settingsDefaultModel
              }}
            />
            {settingsInfo ? <p className="ok">{settingsInfo}</p> : null}
            {settingsConfigPath ? (
              <p className="muted">Config: {settingsConfigPath}</p>
            ) : null}

            <div className="rowWide">
              <label>
                Provider
                <select
                  value={settingsProvider}
                  onChange={(e) => setSettingsProvider(e.target.value)}
                >
                  {(settingsProviders.length ? settingsProviders : Object.keys(PROVIDER_API_KEY_FIELD)).map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                API URL
                <input
                  value={settingsApiUrl}
                  onChange={(e) => setSettingsApiUrl(e.target.value)}
                  placeholder="Leave empty to use default"
                />
              </label>
            </div>

            <label>
              API Key
              <input
                type="password"
                value={settingsApiKey}
                onChange={(e) => setSettingsApiKey(e.target.value)}
                placeholder="Provider API key"
              />
            </label>

            <label>
              Default Model
              <input
                value={settingsDefaultModel}
                onChange={(e) => setSettingsDefaultModel(e.target.value)}
                placeholder="e.g. qwen-plus / deepseek-chat"
              />
            </label>

            <label>
              Available Models (one per line)
              <textarea
                rows={6}
                value={settingsAvailableModelsText}
                onChange={(e) => setSettingsAvailableModelsText(e.target.value)}
                placeholder={"model-a\nmodel-b\nmodel-c"}
              />
            </label>
            </form>
          </section>
        ) : null}
      </section>
    </main>
  );
}
