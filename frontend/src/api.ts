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

export type TtsAudioResponse = {
  blob: Blob;
  memorySaved: boolean;
};

export type TtsEngine = "edge" | "qwen_flash" | "minimax";

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
  memory_settings: Record<string, unknown>;
  output_directory: string;
  tts_settings: Record<string, unknown>;
  qwen_tts_settings: Record<string, unknown>;
  transcription_settings: Record<string, unknown>;
  minimax: Record<string, unknown>;
  ui_settings: Record<string, unknown>;
  shortcuts: Record<string, unknown>;
};

export type SettingsResponse = {
  config_path: string;
  providers: string[];
  settings: AppSettings;
};

export type DesktopStatusResponse = {
  runtime_dir: string;
  diagnostics_dir: string;
  preflight: {
    available: boolean;
    ok: boolean | null;
    timestamp: string;
    failed_checks: Array<{ name: string; detail: string }>;
    failed_count: number;
  };
  latest_error: {
    available: boolean;
    timestamp: string;
    error_type: string;
    message: string;
    recovery_hints: string[];
  };
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
  memories_retrieved?: number;
  memory_saved?: boolean;
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

export type TranscriptionResponse = {
  transcript: string;
  memory_saved?: boolean;
};

export type TranscriptionJobResponse = {
  job_id: string;
  remote_job_id?: string | null;
  mode: string;
  status: string;
  file_name: string;
  created_at?: string | null;
  updated_at?: string | null;
  transcript?: string | null;
  has_transcript?: boolean;
  transcript_download_url?: string | null;
  source_url?: string | null;
  error?: string | null;
  memory_saved?: boolean;
};

export type TranscriptionJobListResponse = {
  count: number;
  jobs: TranscriptionJobResponse[];
};

export type VoiceChatServerEvent =
  | { type: "session_open"; provider: string; model: string; voice: string }
  | { type: "user_transcript"; text: string }
  | { type: "assistant_text"; text: string }
  | { type: "assistant_audio"; audio: string; encoding: string; sample_rate: number }
  | { type: "interrupted" }
  | { type: "turn_complete" }
  | { type: "pong" }
  | { type: "error"; message: string; provider?: string };

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
const EVERMEM_API_URL_STORAGE_KEY = "evermem_api_url";
const EVERMEM_SCOPE_ID_STORAGE_KEY = "evermem_scope_id";
const EVERMEM_TEMP_SESSION_STORAGE_KEY = "evermem_temporary_session";
const EVERMEM_REMEMBER_CHAT_STORAGE_KEY = "evermem_remember_chat";
const EVERMEM_REMEMBER_VOICE_CHAT_STORAGE_KEY = "evermem_remember_voice_chat";
const EVERMEM_REMEMBER_RECORDINGS_STORAGE_KEY = "evermem_remember_recordings";
const EVERMEM_REMEMBER_PODCAST_STORAGE_KEY = "evermem_remember_podcast";
const EVERMEM_REMEMBER_TTS_STORAGE_KEY = "evermem_remember_tts";
const EVERMEM_STORE_TRANSCRIPT_FULLTEXT_STORAGE_KEY = "evermem_store_transcript_fulltext";
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
  api_url: string;
  api_key?: string;
  scope_id?: string;
  temporary_session?: boolean;
  remember_chat?: boolean;
  remember_voice_chat?: boolean;
  remember_recordings?: boolean;
  remember_podcast?: boolean;
  remember_tts?: boolean;
  store_transcript_fulltext?: boolean;
}): void {
  safeStorageSet(EVERMEM_ENABLED_STORAGE_KEY, String(config.enabled));
  safeStorageSet(EVERMEM_API_URL_STORAGE_KEY, config.api_url.trim());
  safeStorageSet(EVERMEM_SCOPE_ID_STORAGE_KEY, (config.scope_id || "").trim());
  safeStorageSet(EVERMEM_TEMP_SESSION_STORAGE_KEY, String(config.temporary_session ?? false));
  safeStorageSet(EVERMEM_REMEMBER_CHAT_STORAGE_KEY, String(config.remember_chat ?? true));
  safeStorageSet(EVERMEM_REMEMBER_VOICE_CHAT_STORAGE_KEY, String(config.remember_voice_chat ?? true));
  safeStorageSet(EVERMEM_REMEMBER_RECORDINGS_STORAGE_KEY, String(config.remember_recordings ?? true));
  safeStorageSet(EVERMEM_REMEMBER_PODCAST_STORAGE_KEY, String(config.remember_podcast ?? true));
  safeStorageSet(EVERMEM_REMEMBER_TTS_STORAGE_KEY, String(config.remember_tts ?? false));
  safeStorageSet(EVERMEM_STORE_TRANSCRIPT_FULLTEXT_STORAGE_KEY, String(config.store_transcript_fulltext ?? false));

  safeStorageRemove(EVERMEM_LEGACY_KEY_STORAGE_KEY);
  evermemRuntimeKey = (config.api_key || "").trim();
}

export function getEverMemRuntimeConfig() {
  return {
    enabled: safeStorageGet(EVERMEM_ENABLED_STORAGE_KEY) === "true",
    api_url: safeStorageGet(EVERMEM_API_URL_STORAGE_KEY),
    api_key: evermemRuntimeKey,
    scope_id: safeStorageGet(EVERMEM_SCOPE_ID_STORAGE_KEY),
    temporary_session: safeStorageGet(EVERMEM_TEMP_SESSION_STORAGE_KEY) === "true",
    remember_chat: safeStorageGet(EVERMEM_REMEMBER_CHAT_STORAGE_KEY) !== "false", // Default true
    remember_voice_chat: safeStorageGet(EVERMEM_REMEMBER_VOICE_CHAT_STORAGE_KEY) !== "false", // Default true
    remember_recordings: safeStorageGet(EVERMEM_REMEMBER_RECORDINGS_STORAGE_KEY) !== "false", // Default true
    remember_podcast: safeStorageGet(EVERMEM_REMEMBER_PODCAST_STORAGE_KEY) !== "false", // Default true
    remember_tts: safeStorageGet(EVERMEM_REMEMBER_TTS_STORAGE_KEY) === "true", // Default false
    store_transcript_fulltext: safeStorageGet(EVERMEM_STORE_TRANSCRIPT_FULLTEXT_STORAGE_KEY) === "true",
  };
}

export type EverMemScene = "chat" | "voice_chat" | "transcription" | "podcast" | "tts";

function buildEverMemHeaders(useMemory: boolean, scene?: EverMemScene): Record<string, string> {
  if (!useMemory) {
    return {};
  }
  const evermem = getEverMemRuntimeConfig();
  if (!evermem.enabled || evermem.temporary_session) {
    return {};
  }
  if (scene === "chat" && !evermem.remember_chat) return {};
  if (scene === "voice_chat" && !evermem.remember_voice_chat) return {};
  if (scene === "transcription" && !evermem.remember_recordings) return {};
  if (scene === "podcast" && !evermem.remember_podcast) return {};
  if (scene === "tts" && !evermem.remember_tts) return {};

  return {
    "X-EverMem-Enabled": "true",
    "X-EverMem-Url": evermem.api_url || "",
    ...(evermem.api_key ? { "X-EverMem-Key": evermem.api_key } : {}),
    ...(evermem.scope_id ? { "X-EverMem-Scope": evermem.scope_id } : {})
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

export function buildVoiceChatWebSocketUrl(params: {
  provider?: string;
  model?: string;
  voice?: string;
}): string {
  const httpUrl = new URL(API_BASE_URL);
  const protocol = httpUrl.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = new URL(`${protocol}//${httpUrl.host}/api/voice-chat/ws`);
  if (params.provider) {
    wsUrl.searchParams.set("provider", params.provider);
  }
  if (params.model) {
    wsUrl.searchParams.set("model", params.model);
  }
  if (params.voice) {
    wsUrl.searchParams.set("voice", params.voice);
  }
  return wsUrl.toString();
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

export async function fetchVoices(locale?: string, engine?: TtsEngine): Promise<VoicesResponse> {
  const params = new URLSearchParams();
  if (locale) {
    params.set("locale", locale);
  }
  if (engine) {
    params.set("engine", engine);
  }
  const query = params.toString();
  const response = await apiFetch(`${API_BASE_URL}/api/tts/voices${query ? `?${query}` : ""}`);
  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export function buildSpeakUrl(params: {
  text: string;
  voice?: string;
  rate?: string;
  engine?: TtsEngine;
}): string {
  const url = new URL(`${API_BASE_URL}/api/tts/speak`);
  url.searchParams.set("text", params.text);
  if (params.voice) {
    url.searchParams.set("voice", params.voice);
  }
  if (params.rate) {
    url.searchParams.set("rate", params.rate);
  }
  if (params.engine) {
    url.searchParams.set("engine", params.engine);
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
  engine?: TtsEngine;
}): Promise<TtsAudioResponse> {
  const url = buildSpeakUrl(params);
  const response = await apiFetch(url, {
    headers: buildEverMemHeaders(true, "tts")
  });
  if (!response.ok) {
    await throwApiError(response);
  }
  return {
    blob: await response.blob(),
    memorySaved: response.headers.get("X-EverMem-Saved") === "true"
  };
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
  const response = await apiFetch(`${API_BASE_URL}/api/chat/completions/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      ...buildEverMemHeaders(true, "chat")
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

export async function fetchDesktopStatus(): Promise<DesktopStatusResponse> {
  const response = await apiFetch(`${API_BASE_URL}/api/settings/desktop-status`);
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

export async function transcribeAudio(file: File): Promise<TranscriptionResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiFetch(`${API_BASE_URL}/api/transcription/`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export async function createTranscriptionJob(file: File): Promise<TranscriptionJobResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiFetch(`${API_BASE_URL}/api/transcription/jobs`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export async function createTranscriptionJobFromUrl(fileUrl: string): Promise<TranscriptionJobResponse> {
  const response = await apiFetch(`${API_BASE_URL}/api/transcription/jobs/from-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_url: fileUrl }),
  });

  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export async function listTranscriptionJobs(
  options: { statuses?: string[]; limit?: number } = {}
): Promise<TranscriptionJobListResponse> {
  const search = new URLSearchParams();
  if (options.statuses && options.statuses.length > 0) {
    search.set("status", options.statuses.join(","));
  }
  if (typeof options.limit === "number") {
    search.set("limit", String(options.limit));
  }

  const response = await apiFetch(
    `${API_BASE_URL}/api/transcription/jobs${search.toString() ? `?${search.toString()}` : ""}`
  );

  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export async function fetchTranscriptionJob(
  jobId: string,
  options: { refresh?: boolean } = {}
): Promise<TranscriptionJobResponse> {
  const refresh = options.refresh !== false;
  const response = await apiFetch(
    `${API_BASE_URL}/api/transcription/jobs/${encodeURIComponent(jobId)}?refresh=${refresh ? "true" : "false"}`
  );

  if (!response.ok) {
    await throwApiError(response);
  }
  return response.json();
}

export async function retryTranscriptionJob(jobId: string): Promise<TranscriptionJobResponse> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/transcription/jobs/${encodeURIComponent(jobId)}/retry`,
    {
      method: "POST",
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
  payload: AudioOverviewScriptGenerateRequest,
  options: { useMemory?: boolean } = {}
): Promise<AudioOverviewScriptGenerateResponse> {
  const response = await apiFetch(`${API_BASE_URL}/api/audio-overview/scripts/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...buildEverMemHeaders(options.useMemory ?? true, "podcast")
    },
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
