export type VoiceInfo = {
  name: string;
  short_name: string;
  locale: string;
  gender: string;
};

export type VoicesResponse = {
  count: number;
  voices: VoiceInfo[];
};

export type ChatMessage = {
  role: "system" | "user" | "assistant";
  content: string;
  memoriesUsed?: number;
  memorySaved?: boolean;
};

export type ChatRequest = {
  provider: string;
  model?: string;
  messages: ChatMessage[];
  temperature?: number;
  max_tokens?: number;
};

export type ChatResponse = {
  provider: string;
  model: string;
  reply: string;
  raw: Record<string, unknown>;
};

type StreamEventHandlers = {
  onDelta: (chunk: string) => void;
  onDone?: (meta?: { memoriesRetrieved: number; memorySaved: boolean }) => void;
};

export type TranslateRequest = {
  text: string;
  target_language: string;
  source_language?: string;
  provider?: string;
  model?: string;
};

export type TranslateResponse = {
  provider: string;
  model: string;
  translated_text: string;
};

export type VoiceType = "voice_design" | "voice_clone";

export type CustomVoice = {
  voice: string;
  type: VoiceType;
  target_model: string;
  language?: string;
  name?: string;
  gender?: string;
};

export type CustomVoiceListResponse = {
  voice_type: VoiceType;
  count: number;
  voices: CustomVoice[];
};

export type VoiceDesignRequest = {
  voice_prompt: string;
  preview_text: string;
  preferred_name: string;
  language?: string;
};

export type VoiceCreateResponse = {
  voice: string;
  type: VoiceType;
  target_model: string;
  preferred_name: string;
  language?: string;
  preview_audio_data?: string;
};

export type SettingsModelValue =
  | string
  | {
    default?: string;
    available?: string[];
  };

export type AppSettings = {
  api_keys: Record<string, string>;
  api_urls: Record<string, string>;
  default_models: Record<string, SettingsModelValue>;
  general_settings: Record<string, unknown>;
  output_directory: string;
  tts_settings: Record<string, unknown>;
  qwen_tts_settings: Record<string, unknown>;
  minimax: Record<string, unknown>;
  ui_settings: Record<string, unknown>;
  shortcuts: Record<string, unknown>;
};

export type SettingsResponse = {
  config_path: string;
  providers: string[];
  settings: AppSettings;
};

export type AudioOverviewScriptLine = {
  role: string;
  text: string;
};

export type AudioOverviewPodcast = {
  id: number;
  topic: string;
  language: string;
  audio_path: string | null;
  created_at: string;
  updated_at: string;
  script_lines: AudioOverviewScriptLine[];
};

export type AudioOverviewPodcastListResponse = {
  count: number;
  podcasts: AudioOverviewPodcast[];
};

export type AudioOverviewScriptGenerateRequest = {
  topic: string;
  language?: string;
  turn_count?: number;
  provider?: string;
  model?: string;
};

export type AudioOverviewScriptGenerateResponse = {
  topic: string;
  language: string;
  turn_count: number;
  provider: string;
  model: string;
  script_lines: AudioOverviewScriptLine[];
};

export type AudioOverviewSynthesizeRequest = {
  voice_a?: string;
  voice_b?: string;
  rate?: string;
  language?: string;
  gap_ms?: number;
  merge_strategy?: "auto" | "pydub" | "ffmpeg" | "concat";
};

export type AudioOverviewSynthesizeResponse = {
  podcast_id: number;
  audio_path: string;
  audio_download_url: string;
  line_count: number;
  voice_a: string;
  voice_b: string;
  rate: string;
  cache_hits: number;
  gap_ms: number;
  gap_ms_applied: number;
  merge_strategy: string;
};

export type ApiRuntimeInfo = {
  name?: string;
  version?: string;
  status?: string;
  phase?: string;
  auth_enabled?: boolean;
  auth_mode?: string;
  raw?: Record<string, unknown>;
};

export type ApiErrorDetail = {
  code?: string;
  message?: string;
  meta?: Record<string, unknown>;
};

export class ApiRequestError extends Error {
  status: number;
  detail?: ApiErrorDetail;

  constructor(message: string, status: number, detail?: ApiErrorDetail) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.detail = detail;
  }
}

export const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
export const API_TOKEN = import.meta.env.VITE_API_TOKEN || "";
export const API_ADMIN_TOKEN = import.meta.env.VITE_API_ADMIN_TOKEN || "";
const CLIENT_ID_STORAGE_KEY = "voicespirit_client_id";
const EVERMEM_ENABLED_STORAGE_KEY = "evermem_enabled";
const EVERMEM_URL_STORAGE_KEY = "evermem_url";
const EVERMEM_LEGACY_KEY_STORAGE_KEY = "evermem_key";

let evermemRuntimeKey = "";

function safeStorageGet(key: string): string {
  try {
    return localStorage.getItem(key) || "";
  } catch {
    return "";
  }
}

function safeStorageSet(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Ignore storage failures in non-browser contexts.
  }
}

function safeStorageRemove(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    // Ignore storage failures in non-browser contexts.
  }
}

function createClientId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `vs-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function getClientId(): string {
  const existing = safeStorageGet(CLIENT_ID_STORAGE_KEY).trim();
  if (existing) {
    return existing;
  }
  const next = createClientId();
  safeStorageSet(CLIENT_ID_STORAGE_KEY, next);
  return next;
}

export function configureEverMemRuntime(config: {
  enabled: boolean;
  url: string;
  key?: string;
}): void {
  safeStorageSet(EVERMEM_ENABLED_STORAGE_KEY, String(config.enabled));
  safeStorageSet(EVERMEM_URL_STORAGE_KEY, config.url.trim());
  safeStorageRemove(EVERMEM_LEGACY_KEY_STORAGE_KEY);
  evermemRuntimeKey = (config.key || "").trim();
}

export function getEverMemRuntimeConfig(): {
  enabled: boolean;
  url: string;
  key: string;
} {
  return {
    enabled: safeStorageGet(EVERMEM_ENABLED_STORAGE_KEY) === "true",
    url: safeStorageGet(EVERMEM_URL_STORAGE_KEY),
    key: evermemRuntimeKey
  };
}

function apiFetch(
  input: RequestInfo | URL,
  init: RequestInit = {},
  options: { useAdminToken?: boolean } = {}
): Promise<Response> {
  const headers = new Headers(init.headers || {});
  const token =
    options.useAdminToken && API_ADMIN_TOKEN
      ? API_ADMIN_TOKEN
      : API_TOKEN;
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!headers.has("X-Client-ID")) {
    headers.set("X-Client-ID", getClientId());
  }
  return fetch(input, { ...init, headers });
}

export async function fetchApiRuntimeInfo(): Promise<ApiRuntimeInfo> {
  const response = await apiFetch(`${API_BASE_URL}/`);
  if (!response.ok) {
    await throwApiError(response);
  }
  const data = (await response.json()) as unknown;
  if (!data || typeof data !== "object") {
    return {};
  }
  const obj = data as Record<string, unknown>;
  return {
    name: typeof obj.name === "string" ? obj.name : undefined,
    version: typeof obj.version === "string" ? obj.version : undefined,
    status: typeof obj.status === "string" ? obj.status : undefined,
    phase: typeof obj.phase === "string" ? obj.phase : undefined,
    auth_enabled:
      typeof obj.auth_enabled === "boolean" ? obj.auth_enabled : undefined,
    auth_mode: typeof obj.auth_mode === "string" ? obj.auth_mode : undefined,
    raw: obj
  };
}

export async function fetchVoices(locale?: string): Promise<VoicesResponse> {
  const query = locale ? `?locale=${encodeURIComponent(locale)}` : "";
  const response = await apiFetch(`${API_BASE_URL}/api/tts/voices${query}`);
  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export function buildSpeakUrl(params: {
  text: string;
  voice?: string;
  rate?: string;
}): string {
  const url = new URL(`${API_BASE_URL}/api/tts/speak`);
  url.searchParams.set("text", params.text);
  if (params.voice) {
    url.searchParams.set("voice", params.voice);
  }
  if (params.rate) {
    url.searchParams.set("rate", params.rate);
  }
  return url.toString();
}

type ParsedError = {
  message: string;
  detail?: ApiErrorDetail;
};

function parseDetail(value: unknown): ApiErrorDetail | undefined {
  if (!value || typeof value !== "object") {
    return undefined;
  }
  const obj = value as Record<string, unknown>;
  const code = typeof obj.code === "string" ? obj.code : undefined;
  const message = typeof obj.message === "string" ? obj.message : undefined;
  const meta =
    obj.meta && typeof obj.meta === "object"
      ? (obj.meta as Record<string, unknown>)
      : undefined;
  if (!code && !message && !meta) {
    return undefined;
  }
  return { code, message, meta };
}

function detailToMessage(detail: ApiErrorDetail): string {
  const code = (detail.code || "").trim();
  const message = (detail.message || "").trim();
  if (code && message) {
    return `${code}: ${message}`;
  }
  if (message) {
    return message;
  }
  if (code) {
    return code;
  }
  return "Request failed.";
}

async function parseError(response: Response): Promise<ParsedError> {
  try {
    const data = (await response.json()) as unknown;
    if (data && typeof data === "object") {
      const dataObj = data as Record<string, unknown>;
      if (typeof dataObj.detail === "string") {
        return { message: dataObj.detail };
      }
      const detail = parseDetail(dataObj.detail);
      if (detail) {
        return { message: detailToMessage(detail), detail };
      }
      const directDetail = parseDetail(dataObj);
      if (directDetail) {
        return { message: detailToMessage(directDetail), detail: directDetail };
      }
    }
  } catch {
    // ignore parse failure
  }
  return { message: `Request failed: ${response.status}` };
}

async function throwApiError(response: Response): Promise<never> {
  const parsed = await parseError(response);
  throw new ApiRequestError(parsed.message, response.status, parsed.detail);
}

export async function fetchSpeakAudio(params: {
  text: string;
  voice?: string;
  rate?: string;
}): Promise<Blob> {
  const url = buildSpeakUrl(params);
  const response = await apiFetch(url);
  if (!response.ok) {
    await throwApiError(response);
  }
  return response.blob();
}

export async function createChatCompletion(
  payload: ChatRequest
): Promise<ChatResponse> {
  const response = await apiFetch(`${API_BASE_URL}/api/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

function parseSseBlock(block: string): { event: string; data: string } | null {
  const lines = block.split("\n");
  let eventName = "message";
  const dataLines: string[] = [];

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (!line) {
      continue;
    }
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim() || "message";
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }

  if (!dataLines.length) {
    return null;
  }
  return { event: eventName, data: dataLines.join("\n") };
}

function handleSseChunk(chunk: string, handlers: StreamEventHandlers): boolean {
  const parsed = parseSseBlock(chunk);
  if (!parsed) {
    return false;
  }

  const payload = JSON.parse(parsed.data) as Record<string, unknown>;
  if (parsed.event === "delta") {
    const content = payload.content;
    if (typeof content === "string" && content.length > 0) {
      handlers.onDelta(content);
    }
    return false;
  }
  if (parsed.event === "done") {
    const meta = {
      memoriesRetrieved: typeof payload.memories_retrieved === "number" ? payload.memories_retrieved : 0,
      memorySaved: typeof payload.memory_saved === "boolean" ? payload.memory_saved : false
    };
    handlers.onDone?.(meta);
    return true;
  }
  if (parsed.event === "error") {
    const detail =
      typeof payload.detail === "string" ? payload.detail : "Chat stream failed.";
    throw new Error(detail);
  }
  return false;
}

export async function streamChatCompletion(
  payload: ChatRequest,
  handlers: StreamEventHandlers
): Promise<void> {
  const evermem = getEverMemRuntimeConfig();
  const response = await apiFetch(`${API_BASE_URL}/api/chat/completions/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      ...(evermem.enabled && {
        "X-EverMem-Enabled": "true",
        "X-EverMem-Url": evermem.url || "",
        ...(evermem.key ? { "X-EverMem-Key": evermem.key } : {})
      })
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    await throwApiError(response);
  }
  if (!response.body) {
    throw new Error("Chat stream is unavailable: empty response body.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() || "";
    for (const block of blocks) {
      const isDone = handleSseChunk(block, handlers);
      if (isDone) {
        return;
      }
    }
  }

  const finalChunk = buffer.trim();
  if (finalChunk) {
    handleSseChunk(finalChunk, handlers);
  }
  handlers.onDone?.();
}

export async function translateText(
  payload: TranslateRequest
): Promise<TranslateResponse> {
  const response = await apiFetch(`${API_BASE_URL}/api/translate/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export async function translateImage(params: {
  image_file: File;
  target_language: string;
  source_language?: string;
  provider?: string;
  model?: string;
}): Promise<TranslateResponse> {
  const formData = new FormData();
  formData.append("image_file", params.image_file);
  formData.append("target_language", params.target_language);
  formData.append("source_language", params.source_language || "auto");
  formData.append("provider", params.provider || "DashScope");
  if (params.model) {
    formData.append("model", params.model);
  }

  const response = await apiFetch(`${API_BASE_URL}/api/translate/image`, {
    method: "POST",
    body: formData
  });
  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export async function listCustomVoices(
  voiceType: VoiceType
): Promise<CustomVoiceListResponse> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/voices/?voice_type=${encodeURIComponent(voiceType)}`
  );
  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export async function createVoiceDesign(
  payload: VoiceDesignRequest
): Promise<VoiceCreateResponse> {
  const response = await apiFetch(`${API_BASE_URL}/api/voices/design`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export async function createVoiceClone(params: {
  preferred_name: string;
  audio_file: File;
}): Promise<VoiceCreateResponse> {
  const formData = new FormData();
  formData.append("preferred_name", params.preferred_name);
  formData.append("audio_file", params.audio_file);

  const response = await apiFetch(`${API_BASE_URL}/api/voices/clone`, {
    method: "POST",
    body: formData
  });
  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export async function deleteCustomVoice(
  voiceName: string,
  voiceType: VoiceType
): Promise<void> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/voices/${encodeURIComponent(voiceName)}?voice_type=${encodeURIComponent(voiceType)}`,
    { method: "DELETE" }
  );
  if (!response.ok) {
    await throwApiError(response);
  }
}

export async function fetchSettings(): Promise<SettingsResponse> {
  const response = await apiFetch(`${API_BASE_URL}/api/settings/`);
  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export async function updateSettings(
  settingsPatch: Record<string, unknown>,
  merge: boolean = true
): Promise<SettingsResponse> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/settings/`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        merge,
        settings: settingsPatch
      })
    },
    { useAdminToken: true }
  );
  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export async function listAudioOverviewPodcasts(
  limit: number = 20
): Promise<AudioOverviewPodcastListResponse> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/audio-overview/podcasts?limit=${encodeURIComponent(String(limit))}`
  );
  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export async function getLatestAudioOverviewPodcast(): Promise<AudioOverviewPodcast> {
  const response = await apiFetch(`${API_BASE_URL}/api/audio-overview/podcasts/latest`);
  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export async function getAudioOverviewPodcast(
  podcastId: number
): Promise<AudioOverviewPodcast> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/audio-overview/podcasts/${encodeURIComponent(String(podcastId))}`
  );
  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export async function createAudioOverviewPodcast(payload: {
  topic: string;
  language?: string;
  audio_path?: string | null;
  script_lines?: AudioOverviewScriptLine[];
}): Promise<AudioOverviewPodcast> {
  const response = await apiFetch(`${API_BASE_URL}/api/audio-overview/podcasts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export async function updateAudioOverviewPodcast(
  podcastId: number,
  payload: {
    topic?: string;
    language?: string;
    audio_path?: string | null;
    script_lines?: AudioOverviewScriptLine[];
  }
): Promise<AudioOverviewPodcast> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/audio-overview/podcasts/${encodeURIComponent(String(podcastId))}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }
  );
  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export async function saveAudioOverviewScript(
  podcastId: number,
  scriptLines: AudioOverviewScriptLine[]
): Promise<AudioOverviewPodcast> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/audio-overview/podcasts/${encodeURIComponent(String(podcastId))}/script`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ script_lines: scriptLines })
    }
  );
  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export async function deleteAudioOverviewPodcast(podcastId: number): Promise<void> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/audio-overview/podcasts/${encodeURIComponent(String(podcastId))}`,
    {
      method: "DELETE"
    }
  );
  if (!response.ok) {
    await throwApiError(response);
  }
}

export async function generateAudioOverviewScript(
  payload: AudioOverviewScriptGenerateRequest
): Promise<AudioOverviewScriptGenerateResponse> {
  const response = await apiFetch(`${API_BASE_URL}/api/audio-overview/scripts/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export async function synthesizeAudioOverviewPodcast(
  podcastId: number,
  payload: AudioOverviewSynthesizeRequest
): Promise<AudioOverviewSynthesizeResponse> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/audio-overview/podcasts/${encodeURIComponent(String(podcastId))}/synthesize`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }
  );
  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export async function fetchAudioOverviewPodcastAudio(
  podcastId: number
): Promise<Blob> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/audio-overview/podcasts/${encodeURIComponent(String(podcastId))}/audio`
  );
  if (!response.ok) {
    await throwApiError(response);
  }
  return response.blob();
}
