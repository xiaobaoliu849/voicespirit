import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  configureEverMemRuntime,
  fetchDesktopStatus,
  getEverMemRuntimeConfig,
  fetchApiRuntimeInfo,
  fetchSettings,
  updateSettings,
  type AppSettings,
  type DesktopStatusResponse,
  type SettingsModelValue
} from "../api";
import type { FormatErrorMessage } from "../utils/errorFormatting";

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

type Options = {
  formatErrorMessage: FormatErrorMessage;
};

function trimOrEmpty(value: string) {
  return value.trim();
}

type ProviderModelCatalog = Record<
  string,
  {
    defaultModel: string;
    availableModels: string[];
  }
>;

export default function useSettings({ formatErrorMessage }: Options) {
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
  const [transcriptionUploadMode, setTranscriptionUploadMode] = useState("static");
  const [transcriptionPublicBaseUrl, setTranscriptionPublicBaseUrl] = useState("");
  const [transcriptionS3Bucket, setTranscriptionS3Bucket] = useState("");
  const [transcriptionS3Region, setTranscriptionS3Region] = useState("");
  const [transcriptionS3EndpointUrl, setTranscriptionS3EndpointUrl] = useState("");
  const [transcriptionS3AccessKeyId, setTranscriptionS3AccessKeyId] = useState("");
  const [transcriptionS3SecretAccessKey, setTranscriptionS3SecretAccessKey] = useState("");
  const [transcriptionS3KeyPrefix, setTranscriptionS3KeyPrefix] = useState("transcription");

  const [evermemEnabled, setEvermemEnabled] = useState(false);
  const [evermemApiUrl, setEvermemApiUrl] = useState("");
  const [evermemApiKey, setEvermemApiKey] = useState("");
  const [evermemScopeId, setEvermemScopeId] = useState("");
  const [evermemTempSession, setEvermemTempSession] = useState(false);
  const [evermemRememberChat, setEvermemRememberChat] = useState(true);
  const [evermemRememberVoiceChat, setEvermemRememberVoiceChat] = useState(true);
  const [evermemRememberRecordings, setEvermemRememberRecordings] = useState(true);
  const [evermemRememberPodcast, setEvermemRememberPodcast] = useState(true);
  const [evermemRememberTts, setEvermemRememberTts] = useState(false);
  const [evermemStoreTranscript, setEvermemStoreTranscript] = useState(false);

  const [backendPhase, setBackendPhase] = useState("");
  const [backendAuthMode, setBackendAuthMode] = useState("");
  const [backendAuthEnabled, setBackendAuthEnabled] = useState<boolean | null>(null);
  const [backendVersion, setBackendVersion] = useState("");
  const [backendStatus, setBackendStatus] = useState("");
  const [backendRuntimeRaw, setBackendRuntimeRaw] = useState("{}");
  const [backendRuntimeOpen, setBackendRuntimeOpen] = useState(false);
  const [runtimeCopyStatus, setRuntimeCopyStatus] = useState<"idle" | "ok" | "fail">("idle");
  const [desktopRememberWindowPosition, setDesktopRememberWindowPosition] = useState(false);
  const [desktopAlwaysOnTop, setDesktopAlwaysOnTop] = useState(false);
  const [desktopShowTrayIcon, setDesktopShowTrayIcon] = useState(false);
  const [desktopWakeShortcut, setDesktopWakeShortcut] = useState("Alt+Shift+S");
  const [desktopPreflightStatus, setDesktopPreflightStatus] = useState<DesktopStatusResponse["preflight"]>({
    available: false,
    ok: null,
    timestamp: "",
    failed_checks: [],
    failed_count: 0,
  });
  const [desktopLatestError, setDesktopLatestError] = useState<DesktopStatusResponse["latest_error"]>({
    available: false,
    timestamp: "",
    error_type: "",
    message: "",
    recovery_hints: [],
  });
  const [desktopDiagnosticsDir, setDesktopDiagnosticsDir] = useState("");
  const [desktopRuntimeDir, setDesktopRuntimeDir] = useState("");

  useEffect(() => {
    let disposed = false;

    async function loadApiRuntimeInfo() {
      try {
        const [info, desktopStatus] = await Promise.all([
          fetchApiRuntimeInfo(),
          fetchDesktopStatus().catch(() => null)
        ]);
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
        setDesktopPreflightStatus(desktopStatus?.preflight || {
          available: false,
          ok: null,
          timestamp: "",
          failed_checks: [],
          failed_count: 0,
        });
        setDesktopLatestError(desktopStatus?.latest_error || {
          available: false,
          timestamp: "",
          error_type: "",
          message: "",
          recovery_hints: [],
        });
        setDesktopDiagnosticsDir(desktopStatus?.diagnostics_dir || "");
        setDesktopRuntimeDir(desktopStatus?.runtime_dir || "");
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
        setDesktopPreflightStatus({
          available: false,
          ok: null,
          timestamp: "",
          failed_checks: [],
          failed_count: 0,
        });
        setDesktopLatestError({
          available: false,
          timestamp: "",
          error_type: "",
          message: "",
          recovery_hints: [],
        });
        setDesktopDiagnosticsDir("");
        setDesktopRuntimeDir("");
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

  const providerSection = useMemo(() => {
    const availableModels = settingsAvailableModelsText
      .split(/\r?\n/)
      .map((item) => item.trim())
      .filter(Boolean);
    return {
      provider: settingsProvider,
      apiKeyConfigured: Boolean(trimOrEmpty(settingsApiKey)),
      apiUrlConfigured: Boolean(trimOrEmpty(settingsApiUrl)),
      defaultModelConfigured: Boolean(trimOrEmpty(settingsDefaultModel)),
      availableModelCount: availableModels.length,
      availableModels
    };
  }, [
    settingsApiKey,
    settingsApiUrl,
    settingsAvailableModelsText,
    settingsDefaultModel,
    settingsProvider
  ]);

  const providerModelCatalog = useMemo<ProviderModelCatalog>(() => {
    if (!settingsData) {
      return {};
    }
    return Object.fromEntries(
      Object.entries(settingsData.default_models || {}).map(([provider, value]) => {
        const parsed = parseModelValue(value);
        return [provider, parsed];
      })
    );
  }, [settingsData]);

  const memorySection = useMemo(() => {
    return {
      enabled: evermemEnabled,
      configured:
        evermemEnabled &&
        Boolean(trimOrEmpty(evermemApiUrl)) &&
        Boolean(trimOrEmpty(evermemApiKey)),
      temporarySession: evermemTempSession,
      scopeIdConfigured: Boolean(trimOrEmpty(evermemScopeId)),
      scenes: [
        { id: "chat", enabled: evermemRememberChat, label: "聊天" },
        { id: "voice_chat", enabled: evermemRememberVoiceChat, label: "语音聊天" },
        { id: "transcription", enabled: evermemRememberRecordings, label: "录音转写" },
        { id: "podcast", enabled: evermemRememberPodcast, label: "播客脚本" },
        { id: "tts", enabled: evermemRememberTts, label: "语音合成" }
      ],
      storeTranscriptFulltext: evermemStoreTranscript
    };
  }, [
    evermemApiKey,
    evermemApiUrl,
    evermemEnabled,
    evermemRememberChat,
    evermemRememberPodcast,
    evermemRememberRecordings,
    evermemRememberTts,
    evermemRememberVoiceChat,
    evermemScopeId,
    evermemStoreTranscript,
    evermemTempSession
  ]);

  const transcriptionSection = useMemo(() => {
    const missingS3Fields = [
      ["s3_bucket", transcriptionS3Bucket],
      ["s3_region", transcriptionS3Region],
      ["s3_access_key_id", transcriptionS3AccessKeyId],
      ["s3_secret_access_key", transcriptionS3SecretAccessKey]
    ]
      .filter(([, value]) => !trimOrEmpty(value))
      .map(([key]) => key);

    return {
      uploadMode: transcriptionUploadMode,
      publicBaseUrlConfigured: Boolean(trimOrEmpty(transcriptionPublicBaseUrl)),
      s3Configured:
        transcriptionUploadMode === "s3" ? missingS3Fields.length === 0 : false,
      s3MissingFields: missingS3Fields,
      s3KeyPrefix: trimOrEmpty(transcriptionS3KeyPrefix) || "transcription"
    };
  }, [
    transcriptionPublicBaseUrl,
    transcriptionS3AccessKeyId,
    transcriptionS3Bucket,
    transcriptionS3KeyPrefix,
    transcriptionS3Region,
    transcriptionS3SecretAccessKey,
    transcriptionUploadMode
  ]);

  const desktopSection = useMemo(() => {
    return {
      configPath: settingsConfigPath,
      backendPhase,
      backendAuthMode,
      backendAuthEnabled,
      backendVersion,
      backendStatus,
      rememberWindowPosition: desktopRememberWindowPosition,
      alwaysOnTop: desktopAlwaysOnTop,
      showTrayIcon: desktopShowTrayIcon,
      wakeShortcut: trimOrEmpty(desktopWakeShortcut),
      runtimeDir: desktopRuntimeDir,
      diagnosticsDir: desktopDiagnosticsDir,
      preflight: desktopPreflightStatus,
      latestError: desktopLatestError,
      runtimeVisible: backendRuntimeOpen,
      runtimeCopyStatus
    };
  }, [
    backendAuthEnabled,
    backendAuthMode,
    backendPhase,
    backendRuntimeOpen,
    backendStatus,
    backendVersion,
    desktopDiagnosticsDir,
    desktopAlwaysOnTop,
    desktopLatestError,
    desktopPreflightStatus,
    desktopRememberWindowPosition,
    desktopRuntimeDir,
    desktopShowTrayIcon,
    desktopWakeShortcut,
    runtimeCopyStatus,
    settingsConfigPath
  ]);

  useEffect(() => {
    if (runtimeCopyStatus !== "ok") {
      return;
    }
    const timer = window.setTimeout(() => {
      setRuntimeCopyStatus("idle");
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [runtimeCopyStatus]);

  async function onCopyBackendRuntime() {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(backendRuntimeRaw || "{}");
      } else {
        throw new Error("剪贴板接口不可用");
      }
      setRuntimeCopyStatus("ok");
    } catch {
      setRuntimeCopyStatus("fail");
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
      setSettingsError(formatErrorMessage(err, "加载设置失败。"));
    } finally {
      setSettingsBusy(false);
    }
  }

  useEffect(() => {
    void loadSettings();
    const runtimeConfig = getEverMemRuntimeConfig();

    setEvermemEnabled(runtimeConfig.enabled);
    setEvermemApiUrl(runtimeConfig.api_url);
    setEvermemApiKey(runtimeConfig.api_key);
    setEvermemScopeId(runtimeConfig.scope_id);
    setEvermemTempSession(runtimeConfig.temporary_session);
    setEvermemRememberChat(runtimeConfig.remember_chat);
    setEvermemRememberVoiceChat(runtimeConfig.remember_voice_chat);
    setEvermemRememberRecordings(runtimeConfig.remember_recordings);
    setEvermemRememberPodcast(runtimeConfig.remember_podcast);
    setEvermemRememberTts(runtimeConfig.remember_tts);
    setEvermemStoreTranscript(runtimeConfig.store_transcript_fulltext);

    configureEverMemRuntime({
      enabled: runtimeConfig.enabled,
      api_url: runtimeConfig.api_url,
      api_key: runtimeConfig.api_key,
      scope_id: runtimeConfig.scope_id,
      temporary_session: runtimeConfig.temporary_session,
      remember_chat: runtimeConfig.remember_chat,
      remember_voice_chat: runtimeConfig.remember_voice_chat,
      remember_recordings: runtimeConfig.remember_recordings,
      remember_podcast: runtimeConfig.remember_podcast,
      remember_tts: runtimeConfig.remember_tts,
      store_transcript_fulltext: runtimeConfig.store_transcript_fulltext,
    });
    localStorage.removeItem("evermem_key");
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

    const memorySettings = settingsData.memory_settings || {};
    const transcriptionSettings = settingsData.transcription_settings || {};
    const uiSettings = settingsData.ui_settings || {};
    const shortcuts = settingsData.shortcuts || {};
    if (typeof memorySettings.enabled === "boolean") setEvermemEnabled(memorySettings.enabled);
    if (typeof memorySettings.api_url === "string") setEvermemApiUrl(memorySettings.api_url);
    if (typeof memorySettings.api_key === "string") setEvermemApiKey(memorySettings.api_key);
    if (typeof memorySettings.scope_id === "string") setEvermemScopeId(memorySettings.scope_id);
    if (typeof memorySettings.temporary_session === "boolean") setEvermemTempSession(memorySettings.temporary_session);
    if (typeof memorySettings.remember_chat === "boolean") setEvermemRememberChat(memorySettings.remember_chat);
    if (typeof memorySettings.remember_voice_chat === "boolean") setEvermemRememberVoiceChat(memorySettings.remember_voice_chat);
    if (typeof memorySettings.remember_recordings === "boolean") setEvermemRememberRecordings(memorySettings.remember_recordings);
    if (typeof memorySettings.remember_podcast === "boolean") setEvermemRememberPodcast(memorySettings.remember_podcast);
    if (typeof memorySettings.remember_tts === "boolean") setEvermemRememberTts(memorySettings.remember_tts);
    if (typeof memorySettings.store_transcript_fulltext === "boolean") setEvermemStoreTranscript(memorySettings.store_transcript_fulltext);
    if (typeof transcriptionSettings.upload_mode === "string" && transcriptionSettings.upload_mode.trim()) {
      setTranscriptionUploadMode(transcriptionSettings.upload_mode);
    }
    if (typeof transcriptionSettings.public_base_url === "string") {
      setTranscriptionPublicBaseUrl(transcriptionSettings.public_base_url);
    }
    if (typeof transcriptionSettings.s3_bucket === "string") setTranscriptionS3Bucket(transcriptionSettings.s3_bucket);
    if (typeof transcriptionSettings.s3_region === "string") setTranscriptionS3Region(transcriptionSettings.s3_region);
    if (typeof transcriptionSettings.s3_endpoint_url === "string") setTranscriptionS3EndpointUrl(transcriptionSettings.s3_endpoint_url);
    if (typeof transcriptionSettings.s3_access_key_id === "string") setTranscriptionS3AccessKeyId(transcriptionSettings.s3_access_key_id);
    if (typeof transcriptionSettings.s3_secret_access_key === "string") setTranscriptionS3SecretAccessKey(transcriptionSettings.s3_secret_access_key);
    if (typeof transcriptionSettings.s3_key_prefix === "string" && transcriptionSettings.s3_key_prefix.trim()) {
      setTranscriptionS3KeyPrefix(transcriptionSettings.s3_key_prefix);
    }
    if (typeof uiSettings.remember_window_position === "boolean") {
      setDesktopRememberWindowPosition(uiSettings.remember_window_position);
    }
    if (typeof uiSettings.always_on_top === "boolean") {
      setDesktopAlwaysOnTop(uiSettings.always_on_top);
    }
    if (typeof uiSettings.show_tray_icon === "boolean") {
      setDesktopShowTrayIcon(uiSettings.show_tray_icon);
    }
    if (typeof shortcuts.wake_app === "string" && shortcuts.wake_app.trim()) {
      setDesktopWakeShortcut(shortcuts.wake_app);
    }

    // push to runtime to keep consistent
    configureEverMemRuntime({
      enabled: typeof memorySettings.enabled === "boolean" ? memorySettings.enabled : evermemEnabled,
      api_url: typeof memorySettings.api_url === "string" ? memorySettings.api_url : evermemApiUrl,
      api_key: typeof memorySettings.api_key === "string" ? memorySettings.api_key : evermemApiKey,
      scope_id: typeof memorySettings.scope_id === "string" ? memorySettings.scope_id : evermemScopeId,
      temporary_session: typeof memorySettings.temporary_session === "boolean" ? memorySettings.temporary_session : evermemTempSession,
      remember_chat: typeof memorySettings.remember_chat === "boolean" ? memorySettings.remember_chat : evermemRememberChat,
      remember_voice_chat: typeof memorySettings.remember_voice_chat === "boolean" ? memorySettings.remember_voice_chat : evermemRememberVoiceChat,
      remember_recordings: typeof memorySettings.remember_recordings === "boolean" ? memorySettings.remember_recordings : evermemRememberRecordings,
      remember_podcast: typeof memorySettings.remember_podcast === "boolean" ? memorySettings.remember_podcast : evermemRememberPodcast,
      remember_tts: typeof memorySettings.remember_tts === "boolean" ? memorySettings.remember_tts : evermemRememberTts,
      store_transcript_fulltext: typeof memorySettings.store_transcript_fulltext === "boolean" ? memorySettings.store_transcript_fulltext : evermemStoreTranscript
    });
  }, [settingsData, settingsProvider]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSettingsError("");
    setSettingsInfo("");

    const keyField = PROVIDER_API_KEY_FIELD[settingsProvider];
    if (!keyField) {
      setSettingsError(`暂不支持该供应商的密钥映射：${settingsProvider}`);
      return;
    }

    const availableModels = settingsAvailableModelsText
      .split(/\r?\n/)
      .map((item) => item.trim())
      .filter(Boolean);

    setSettingsSaving(true);
    try {
      configureEverMemRuntime({
        enabled: evermemEnabled,
        api_url: evermemApiUrl,
        api_key: evermemApiKey,
        scope_id: evermemScopeId,
        temporary_session: evermemTempSession,
        remember_chat: evermemRememberChat,
        remember_voice_chat: evermemRememberVoiceChat,
        remember_recordings: evermemRememberRecordings,
        remember_podcast: evermemRememberPodcast,
        remember_tts: evermemRememberTts,
        store_transcript_fulltext: evermemStoreTranscript
      });

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
        },
        memory_settings: {
          enabled: evermemEnabled,
          api_url: evermemApiUrl,
          api_key: evermemApiKey,
          scope_id: evermemScopeId,
          temporary_session: evermemTempSession,
          remember_chat: evermemRememberChat,
          remember_voice_chat: evermemRememberVoiceChat,
          remember_recordings: evermemRememberRecordings,
          remember_podcast: evermemRememberPodcast,
          remember_tts: evermemRememberTts,
          store_transcript_fulltext: evermemStoreTranscript
        },
        transcription_settings: {
          upload_mode: transcriptionUploadMode.trim() || "static",
          public_base_url: transcriptionPublicBaseUrl.trim(),
          s3_bucket: transcriptionS3Bucket.trim(),
          s3_region: transcriptionS3Region.trim(),
          s3_endpoint_url: transcriptionS3EndpointUrl.trim(),
          s3_access_key_id: transcriptionS3AccessKeyId.trim(),
          s3_secret_access_key: transcriptionS3SecretAccessKey.trim(),
          s3_key_prefix: transcriptionS3KeyPrefix.trim() || "transcription"
        },
        ui_settings: {
          remember_window_position: desktopRememberWindowPosition,
          always_on_top: desktopAlwaysOnTop,
          show_tray_icon: desktopShowTrayIcon
        },
        shortcuts: {
          wake_app: desktopWakeShortcut.trim()
        }
      });
      setSettingsData(result.settings);
      setSettingsConfigPath(result.config_path);
      setSettingsProviders(result.providers);
      setSettingsInfo(`已保存 ${settingsProvider} 的设置。`);
    } catch (err) {
      setSettingsError(formatErrorMessage(err, "保存设置失败。"));
    } finally {
      setSettingsSaving(false);
    }
  }

  return {
    settingsBusy,
    settingsSaving,
    settingsError,
    settingsInfo,
    settingsConfigPath,
    settingsProvider,
    settingsApiKey,
    settingsApiUrl,
    settingsDefaultModel,
    settingsAvailableModelsText,
    transcriptionUploadMode,
    transcriptionPublicBaseUrl,
    transcriptionS3Bucket,
    transcriptionS3Region,
    transcriptionS3EndpointUrl,
    transcriptionS3AccessKeyId,
    transcriptionS3SecretAccessKey,
    transcriptionS3KeyPrefix,
    evermemEnabled,
    evermemApiUrl,
    evermemApiKey,
    evermemScopeId,
    evermemTempSession,
    evermemRememberChat,
    evermemRememberVoiceChat,
    evermemRememberRecordings,
    evermemRememberPodcast,
    evermemRememberTts,
    evermemStoreTranscript,
    backendRuntimeRaw,
    backendRuntimeOpen,
    runtimeCopyStatus,
    desktopRememberWindowPosition,
    desktopAlwaysOnTop,
    desktopShowTrayIcon,
    desktopWakeShortcut,
    errorRuntimeContext,
    providerSection,
    providerModelCatalog,
    memorySection,
    transcriptionSection,
    desktopSection,
    providerOptions: settingsProviders.length
      ? settingsProviders
      : Object.keys(PROVIDER_API_KEY_FIELD),
    onSubmit,
    onReload: loadSettings,
    onProviderChange: setSettingsProvider,
    onApiKeyChange: setSettingsApiKey,
    onApiUrlChange: setSettingsApiUrl,
    onDefaultModelChange: setSettingsDefaultModel,
    onAvailableModelsChange: setSettingsAvailableModelsText,
    onTranscriptionUploadModeChange: setTranscriptionUploadMode,
    onTranscriptionPublicBaseUrlChange: setTranscriptionPublicBaseUrl,
    onTranscriptionS3BucketChange: setTranscriptionS3Bucket,
    onTranscriptionS3RegionChange: setTranscriptionS3Region,
    onTranscriptionS3EndpointUrlChange: setTranscriptionS3EndpointUrl,
    onTranscriptionS3AccessKeyIdChange: setTranscriptionS3AccessKeyId,
    onTranscriptionS3SecretAccessKeyChange: setTranscriptionS3SecretAccessKey,
    onTranscriptionS3KeyPrefixChange: setTranscriptionS3KeyPrefix,
    onEvermemEnabledChange: setEvermemEnabled,
    onEvermemApiUrlChange: setEvermemApiUrl,
    onEvermemApiKeyChange: setEvermemApiKey,
    onEvermemScopeIdChange: setEvermemScopeId,
    onEvermemTempSessionChange: setEvermemTempSession,
    onEvermemRememberChatChange: setEvermemRememberChat,
    onEvermemRememberVoiceChatChange: setEvermemRememberVoiceChat,
    onEvermemRememberRecordingsChange: setEvermemRememberRecordings,
    onEvermemRememberPodcastChange: setEvermemRememberPodcast,
    onEvermemRememberTtsChange: setEvermemRememberTts,
    onEvermemStoreTranscriptChange: setEvermemStoreTranscript,
    onDesktopRememberWindowPositionChange: setDesktopRememberWindowPosition,
    onDesktopAlwaysOnTopChange: setDesktopAlwaysOnTop,
    onDesktopShowTrayIconChange: setDesktopShowTrayIcon,
    onDesktopWakeShortcutChange: setDesktopWakeShortcut,
    onToggleRuntimeOpen: () => setBackendRuntimeOpen((value) => !value),
    onCopyBackendRuntime
  };
}

export type UseSettingsResult = ReturnType<typeof useSettings>;
