import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  configureEverMemRuntime,
  fetchApiRuntimeInfo,
  fetchSettings,
  updateSettings,
  type AppSettings,
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

  const [evermemEnabled, setEvermemEnabled] = useState(false);
  const [evermemUrl, setEvermemUrl] = useState("");
  const [evermemKey, setEvermemKey] = useState("");

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
    const savedEnabled = localStorage.getItem("evermem_enabled") === "true";
    const savedUrl = localStorage.getItem("evermem_url") || "";
    const legacyKey = localStorage.getItem("evermem_key") || "";

    setEvermemEnabled(savedEnabled);
    setEvermemUrl(savedUrl);
    setEvermemKey(legacyKey);
    configureEverMemRuntime({
      enabled: savedEnabled,
      url: savedUrl,
      key: legacyKey
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
        url: evermemUrl,
        key: evermemKey
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
    evermemEnabled,
    evermemUrl,
    evermemKey,
    backendRuntimeRaw,
    backendRuntimeOpen,
    runtimeCopyStatus,
    errorRuntimeContext,
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
    onEvermemEnabledChange: setEvermemEnabled,
    onEvermemUrlChange: setEvermemUrl,
    onEvermemKeyChange: setEvermemKey,
    onToggleRuntimeOpen: () => setBackendRuntimeOpen((value) => !value),
    onCopyBackendRuntime
  };
}

export type UseSettingsResult = ReturnType<typeof useSettings>;
