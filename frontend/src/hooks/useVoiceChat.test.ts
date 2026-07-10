import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const {
  ensureEverMemConversationGroupIdMock,
  fetchVoiceAgentSessionMock,
  listVoiceAgentSessionsMock,
} = vi.hoisted(() => ({
  ensureEverMemConversationGroupIdMock: vi.fn(),
  fetchVoiceAgentSessionMock: vi.fn(),
  listVoiceAgentSessionsMock: vi.fn(),
}));

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    ensureEverMemConversationGroupId: ensureEverMemConversationGroupIdMock,
    fetchVoiceAgentSession: fetchVoiceAgentSessionMock,
    listVoiceAgentSessions: listVoiceAgentSessionsMock,
  };
});

import { configureEverMemRuntime, persistEverMemConversationGroupId } from "../api";
import useVoiceChat from "./useVoiceChat";
import { createFormatErrorMessageStub } from "../test/factories";

class FakeTrack {
  stop = vi.fn();
}

class FakeMediaStream {
  private readonly track = new FakeTrack();

  getTracks() {
    return [this.track];
  }
}

class FakeAudioNode {
  disconnect = vi.fn();
  connect = vi.fn();
}

class FakeProcessorNode extends FakeAudioNode {
  onaudioprocess: ((event: { inputBuffer: { getChannelData: () => Float32Array } }) => void) | null = null;
}

class FakeGainNode extends FakeAudioNode {
  gain = {
    value: 1,
    cancelScheduledValues: vi.fn(),
    setTargetAtTime: vi.fn((value: number) => {
      this.gain.value = value;
    }),
  };
}

class FakeBufferSourceNode extends FakeAudioNode {
  buffer: { duration: number } | null = null;
  start = vi.fn();
  stop = vi.fn();
  addEventListener = vi.fn();
}

class FakeAudioContext {
  static processors: FakeProcessorNode[] = [];
  static gains: FakeGainNode[] = [];
  state = "running";
  currentTime = 0;
  sampleRate = 48000;
  destination = {};

  resume = vi.fn(async () => undefined);
  close = vi.fn(async () => undefined);
  createMediaStreamSource = vi.fn(() => new FakeAudioNode());
  createScriptProcessor = vi.fn(() => {
    const processor = new FakeProcessorNode();
    FakeAudioContext.processors.push(processor);
    return processor;
  });
  createGain = vi.fn(() => {
    const gain = new FakeGainNode();
    FakeAudioContext.gains.push(gain);
    return gain;
  });
  createBuffer = vi.fn((_channels: number, length: number, sampleRate: number) => ({
    duration: length / sampleRate,
    getChannelData: () => new Float32Array(length),
  }));
  createBufferSource = vi.fn(() => new FakeBufferSourceNode());
}

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  static OPEN = 1;
  static CONNECTING = 0;
  static CLOSED = 3;

  readyState = FakeWebSocket.CONNECTING;
  binaryType = "";
  sent: Array<string | ArrayBuffer> = [];
  onopen: (() => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: { data: string | ArrayBuffer }) => void) | null = null;

  constructor(public readonly url: string) {
    FakeWebSocket.instances.push(this);
  }

  send(payload: string | ArrayBuffer) {
    this.sent.push(payload);
  }

  close() {
    this.readyState = FakeWebSocket.CLOSED;
  }

  emitOpen() {
    this.readyState = FakeWebSocket.OPEN;
    this.onopen?.();
  }

  emitMessage(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }

  emitClose(code = 1000, reason = "") {
    this.readyState = FakeWebSocket.CLOSED;
    this.onclose?.({ code, reason } as CloseEvent);
  }
}

describe("useVoiceChat", () => {
  beforeEach(() => {
    FakeWebSocket.instances = [];
    FakeAudioContext.processors = [];
    FakeAudioContext.gains = [];
    localStorage.clear();
    configureEverMemRuntime({
      enabled: true,
      api_url: "https://memory.example.com",
      api_key: "memory-key",
      scope_id: "workspace-main",
      temporary_session: false,
      remember_chat: true,
      remember_voice_chat: true,
      remember_recordings: true,
      remember_podcast: true,
      remember_tts: true,
      store_transcript_fulltext: false,
    });
    Object.defineProperty(window, "AudioContext", {
      value: FakeAudioContext,
      configurable: true,
      writable: true,
    });
    Object.defineProperty(globalThis, "WebSocket", {
      value: FakeWebSocket,
      configurable: true,
      writable: true,
    });
    Object.defineProperty(globalThis.navigator, "mediaDevices", {
      value: {
        getUserMedia: vi.fn(async () => new FakeMediaStream()),
      },
      configurable: true,
    });
  });

  afterEach(() => {
    ensureEverMemConversationGroupIdMock.mockReset();
    fetchVoiceAgentSessionMock.mockReset();
    listVoiceAgentSessionsMock.mockReset();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it("waits for session_open before streaming microphone audio", async () => {
    const formatErrorMessage = createFormatErrorMessageStub();
    ensureEverMemConversationGroupIdMock.mockResolvedValue("voice-group-audio-gate");
    const { result } = renderHook(() =>
      useVoiceChat({
        formatErrorMessage,
        providerOptions: ["Google"],
        preferredProvider: "Google",
        preferredModel: "gemini-3.1-flash-live-preview",
        providerModelCatalog: {
          Google: {
            defaultModel: "gemini-3.1-flash-live-preview",
            availableModels: ["gemini-3.1-flash-live-preview"],
          },
        },
      })
    );

    await act(async () => {
      await result.current.onToggleRecording();
    });

    const socket = FakeWebSocket.instances[0];
    act(() => {
      socket.emitOpen();
    });
    const processor = FakeAudioContext.processors[0];
    expect(processor).toBeDefined();

    const audioPayloads = () => socket.sent.filter((item) => typeof item !== "string");
    const beforeAudioPayloadCount = audioPayloads().length;
    act(() => {
      processor.onaudioprocess?.({
        inputBuffer: { getChannelData: () => new Float32Array([0.1, -0.1, 0.05]) },
      });
    });
    expect(audioPayloads()).toHaveLength(beforeAudioPayloadCount);

    act(() => {
      socket.emitMessage({
        type: "session_open",
        provider: "Google",
        model: "gemini-3.1-flash-live-preview",
        voice: "Puck",
      });
      processor.onaudioprocess?.({
        inputBuffer: { getChannelData: () => new Float32Array([0.1, -0.1, 0.05]) },
      });
    });

    expect(audioPayloads().length).toBeGreaterThan(beforeAudioPayloadCount);
  });

  it("ignores stale websocket close events after a new realtime session starts", async () => {
    const formatErrorMessage = createFormatErrorMessageStub();
    ensureEverMemConversationGroupIdMock.mockResolvedValue("voice-group-001");
    const { result } = renderHook(() =>
      useVoiceChat({
        formatErrorMessage,
        providerOptions: ["DashScope", "Google"],
        preferredProvider: "DashScope",
        preferredModel: "qwen3-omni-flash-realtime-2025-12-01",
        providerModelCatalog: {
          DashScope: {
            defaultModel: "qwen3-omni-flash-realtime-2025-12-01",
            availableModels: ["qwen3-omni-flash-realtime-2025-12-01"],
          },
          Google: {
            defaultModel: "gemini-2.5-flash-native-audio-preview-12-2025",
            availableModels: ["gemini-2.5-flash-native-audio-preview-12-2025"],
          },
        },
      })
    );

    await act(async () => {
      await result.current.onToggleRecording();
    });

    const firstSocket = FakeWebSocket.instances[0];
    expect(firstSocket).toBeDefined();

    act(() => {
      firstSocket.emitOpen();
      firstSocket.emitMessage({
        type: "session_open",
        provider: "DashScope",
        model: "qwen3-omni-flash-realtime-2025-12-01",
        voice: "Cherry",
      });
    });

    expect(result.current.voiceChatConnected).toBe(true);

    act(() => {
      result.current.onToggleRecording();
    });

    expect(result.current.voiceChatConnected).toBe(false);

    await act(async () => {
      await result.current.onToggleRecording();
    });

    const secondSocket = FakeWebSocket.instances[1];
    expect(secondSocket).toBeDefined();

    act(() => {
      secondSocket.emitOpen();
      secondSocket.emitMessage({
        type: "session_open",
        provider: "DashScope",
        model: "qwen3-omni-flash-realtime-2025-12-01",
        voice: "Cherry",
      });
    });

    expect(result.current.voiceChatConnected).toBe(true);

    act(() => {
      firstSocket.emitClose();
    });

    expect(result.current.voiceChatConnected).toBe(true);
    expect(result.current.voiceChatStatus).toContain("实时会话已连接");
  });

  it("sends the current EverMem group_id in websocket config and refreshes it after reset", async () => {
    const formatErrorMessage = createFormatErrorMessageStub();
    ensureEverMemConversationGroupIdMock
      .mockResolvedValueOnce("voice-group-001")
      .mockResolvedValueOnce("voice-group-002");

    const { result } = renderHook(() =>
      useVoiceChat({
        formatErrorMessage,
        providerOptions: ["DashScope"],
        preferredProvider: "DashScope",
        preferredModel: "qwen3-omni-flash-realtime-2025-12-01",
        providerModelCatalog: {
          DashScope: {
            defaultModel: "qwen3-omni-flash-realtime-2025-12-01",
            availableModels: ["qwen3-omni-flash-realtime-2025-12-01"],
          },
        },
      })
    );

    await act(async () => {
      await result.current.onToggleRecording();
    });
    const firstSocket = FakeWebSocket.instances[0];
    act(() => {
      firstSocket.emitOpen();
    });
    expect(JSON.parse(String(firstSocket.sent[0]))).toMatchObject({
      type: "config",
      memory: {
        group_id: "voice-group-001",
      },
    });

    act(() => {
      result.current.onResetSession();
    });

    await act(async () => {
      await result.current.onToggleRecording();
    });
    const secondSocket = FakeWebSocket.instances[1];
    act(() => {
      secondSocket.emitOpen();
    });
    expect(JSON.parse(String(secondSocket.sent[0]))).toMatchObject({
      type: "config",
      memory: {
        group_id: "voice-group-002",
      },
    });
    expect(ensureEverMemConversationGroupIdMock.mock.calls).toEqual([
      ["voice_chat", ""],
      ["voice_chat", ""],
    ]);
  });

  it("restores a persisted EverMem group_id after remount", async () => {
    const formatErrorMessage = createFormatErrorMessageStub();
    persistEverMemConversationGroupId("voice_chat", "voice-group-restore");
    ensureEverMemConversationGroupIdMock.mockImplementation(async (_scene, currentGroupId) => currentGroupId);

    const { result } = renderHook(() =>
      useVoiceChat({
        formatErrorMessage,
        providerOptions: ["DashScope"],
        preferredProvider: "DashScope",
        preferredModel: "qwen3-omni-flash-realtime-2025-12-01",
        providerModelCatalog: {
          DashScope: {
            defaultModel: "qwen3-omni-flash-realtime-2025-12-01",
            availableModels: ["qwen3-omni-flash-realtime-2025-12-01"],
          },
        },
      })
    );

    await act(async () => {
      await result.current.onToggleRecording();
    });
    const socket = FakeWebSocket.instances[0];
    act(() => {
      socket.emitOpen();
    });

    expect(ensureEverMemConversationGroupIdMock).toHaveBeenCalledWith("voice_chat", "voice-group-restore");
    expect(JSON.parse(String(socket.sent[0]))).toMatchObject({
      type: "config",
      memory: {
        group_id: "voice-group-restore",
      },
    });
  });

  it("falls back to a realtime voice model even when provider defaults point to text models", () => {
    const formatErrorMessage = createFormatErrorMessageStub();

    const { result } = renderHook(() =>
      useVoiceChat({
        formatErrorMessage,
        providerOptions: ["DashScope"],
        preferredProvider: "DashScope",
        preferredModel: "qwen-plus",
        providerModelCatalog: {
          DashScope: {
            defaultModel: "qwen-plus",
            availableModels: ["qwen-plus", "qwen-max"],
          },
        },
      })
    );

    expect(result.current.voiceChatModel).toBe("qwen3-omni-flash-realtime-2025-12-01");
    expect(result.current.voiceChatModelOptions).toEqual(["qwen3-omni-flash-realtime-2025-12-01"]);
  });

  it("keeps configured DashScope realtime models outside the built-in defaults", () => {
    const formatErrorMessage = createFormatErrorMessageStub();

    const { result } = renderHook(() =>
      useVoiceChat({
        formatErrorMessage,
        providerOptions: ["DashScope"],
        preferredProvider: "DashScope",
        preferredModel: "qwen3.5-omni-plus-realtime-2026-03-15",
        providerModelCatalog: {
          DashScope: {
            defaultModel: "qwen3.5-omni-plus-realtime-2026-03-15",
            availableModels: ["qwen3.5-omni-plus-realtime-2026-03-15"],
          },
        },
      })
    );

    expect(result.current.voiceChatModel).toBe("qwen3.5-omni-plus-realtime-2026-03-15");
    expect(result.current.voiceChatModelOptions).toContain("qwen3.5-omni-plus-realtime-2026-03-15");
  });

  it("adds Live Translate target language parameters to the websocket URL", async () => {
    const formatErrorMessage = createFormatErrorMessageStub();
    ensureEverMemConversationGroupIdMock.mockResolvedValue("voice-group-live-translate");

    const { result } = renderHook(() =>
      useVoiceChat({
        formatErrorMessage,
        providerOptions: ["Google"],
        preferredProvider: "Google",
        preferredModel: "gemini-3.5-live-translate-preview",
        providerModelCatalog: {
          Google: {
            defaultModel: "gemini-3.5-live-translate-preview",
            availableModels: ["gemini-3.5-live-translate-preview"],
          },
        },
      })
    );

    act(() => {
      result.current.onTargetLanguageCodeChange("zh-Hans");
      result.current.onEchoTargetLanguageChange(false);
    });

    await act(async () => {
      await result.current.onToggleRecording();
    });

    const socketUrl = new URL(FakeWebSocket.instances[0].url);
    expect(socketUrl.searchParams.get("provider")).toBe("Google");
    expect(socketUrl.searchParams.get("model")).toBe("gemini-3.5-live-translate-preview");
    expect(socketUrl.searchParams.get("target_language_code")).toBe("zh-Hans");
    expect(socketUrl.searchParams.get("echo_target_language")).toBe("false");
  });

  it("exposes the full Google Live Translate target language list", () => {
    const formatErrorMessage = createFormatErrorMessageStub();

    const { result } = renderHook(() =>
      useVoiceChat({
        formatErrorMessage,
        providerOptions: ["Google"],
        preferredProvider: "Google",
        preferredModel: "gemini-3.5-live-translate-preview",
        providerModelCatalog: {
          Google: {
            defaultModel: "gemini-3.5-live-translate-preview",
            availableModels: ["gemini-3.5-live-translate-preview"],
          },
        },
      })
    );

    const values = result.current.voiceChatTargetLanguageOptions.map((item) => item.value);
    expect(values.length).toBeGreaterThanOrEqual(70);
    expect(values).toEqual(expect.arrayContaining(["af", "en", "ja", "ko", "pl", "pt-PT", "zh-Hans", "zh-Hant", "zu"]));
  });

  it("uses Chinese-friendly Live Translate language labels", () => {
    const formatErrorMessage = createFormatErrorMessageStub();

    const { result } = renderHook(() =>
      useVoiceChat({
        formatErrorMessage,
        providerOptions: ["Google"],
        preferredProvider: "Google",
        preferredModel: "gemini-3.5-live-translate-preview",
        providerModelCatalog: {
          Google: {
            defaultModel: "gemini-3.5-live-translate-preview",
            availableModels: ["gemini-3.5-live-translate-preview"],
          },
        },
        language: "zh-CN",
      })
    );

    expect(result.current.voiceChatTargetLanguageOptions[0].value).toBe("zh-Hans");
    expect(result.current.voiceChatTargetLanguageOptions.find((item) => item.value === "ja")?.label).toContain("日语");
  });

  it("commits completed Live Translate pairs when a new source segment starts", async () => {
    const formatErrorMessage = createFormatErrorMessageStub();
    ensureEverMemConversationGroupIdMock.mockResolvedValue("voice-group-live-translate");

    const { result } = renderHook(() =>
      useVoiceChat({
        formatErrorMessage,
        providerOptions: ["Google"],
        preferredProvider: "Google",
        preferredModel: "gemini-3.5-live-translate-preview",
        providerModelCatalog: {
          Google: {
            defaultModel: "gemini-3.5-live-translate-preview",
            availableModels: ["gemini-3.5-live-translate-preview"],
          },
        },
      })
    );

    await act(async () => {
      await result.current.onToggleRecording();
    });

    const socket = FakeWebSocket.instances[0];
    act(() => {
      socket.emitOpen();
      socket.emitMessage({
        type: "session_open",
        provider: "Google",
        model: "gemini-3.5-live-translate-preview",
        voice: "Puck",
        mode: "live_translate",
        target_language_code: "zh-Hans",
        echo_target_language: true,
      });
      socket.emitMessage({ type: "user_transcript", text: "あ、もしもし。" });
      socket.emitMessage({ type: "assistant_text", text: "喂，你好。" });
      socket.emitMessage({ type: "user_transcript", text: "今何時ですか？" });
    });

    expect(result.current.sessionSummary).toEqual([
      { role: "user", content: "あ、もしもし。", memorySaved: false },
      {
        role: "assistant",
        content: "喂，你好。",
        memoriesUsed: undefined,
        memorySourceSummary: undefined,
        memoryRetrievalAttempted: false,
      },
    ]);
    expect(result.current.voiceChatTranscript).toBe("今何時ですか？");
    expect(result.current.voiceChatReply).toBe("");
  });

  it("coalesces short Latin Live Translate fragments into one active turn", async () => {
    const formatErrorMessage = createFormatErrorMessageStub();
    ensureEverMemConversationGroupIdMock.mockResolvedValue("voice-group-live-translate");

    const { result } = renderHook(() =>
      useVoiceChat({
        formatErrorMessage,
        providerOptions: ["Google"],
        preferredProvider: "Google",
        preferredModel: "gemini-3.5-live-translate-preview",
        providerModelCatalog: {
          Google: {
            defaultModel: "gemini-3.5-live-translate-preview",
            availableModels: ["gemini-3.5-live-translate-preview"],
          },
        },
      })
    );

    await act(async () => {
      await result.current.onToggleRecording();
    });

    const socket = FakeWebSocket.instances[0];
    act(() => {
      socket.emitOpen();
      socket.emitMessage({
        type: "session_open",
        provider: "Google",
        model: "gemini-3.5-live-translate-preview",
        voice: "Puck",
        mode: "live_translate",
        target_language_code: "ja",
        echo_target_language: true,
      });
      socket.emitMessage({ type: "user_transcript", text: "Um, do you know" });
      socket.emitMessage({ type: "assistant_text", text: "あの、" });
      socket.emitMessage({ type: "user_transcript", text: "the" });
      socket.emitMessage({ type: "assistant_text", text: "ご存知ですか？" });
      socket.emitMessage({ type: "user_transcript", text: "Longcha?" });
      socket.emitMessage({ type: "assistant_text", text: "ロンチャを。" });
    });

    expect(result.current.sessionSummary).toEqual([]);
    expect(result.current.voiceChatTranscript).toBe("Um, do you know the Longcha?");
    expect(result.current.voiceChatReply).toBe("あの、ご存知ですか？ロンチャを。");
  });

  it("exposes the first active Live Translate pair for sidebar archiving before turn completion", async () => {
    const formatErrorMessage = createFormatErrorMessageStub();
    ensureEverMemConversationGroupIdMock.mockResolvedValue("voice-group-first-live");

    const { result } = renderHook(() =>
      useVoiceChat({
        formatErrorMessage,
        providerOptions: ["Google"],
        preferredProvider: "Google",
        preferredModel: "gemini-3.5-live-translate-preview",
        providerModelCatalog: {
          Google: {
            defaultModel: "gemini-3.5-live-translate-preview",
            availableModels: ["gemini-3.5-live-translate-preview"],
          },
        },
      })
    );

    await act(async () => {
      await result.current.onToggleRecording();
    });

    const socket = FakeWebSocket.instances[0];
    act(() => {
      socket.emitOpen();
      socket.emitMessage({
        type: "session_open",
        provider: "Google",
        model: "gemini-3.5-live-translate-preview",
        voice: "Puck",
        mode: "live_translate",
        target_language_code: "zh-Hans",
        echo_target_language: true,
      });
      socket.emitMessage({ type: "user_transcript", text: "Hello, can you hear me?" });
      socket.emitMessage({ type: "assistant_text", text: "你好，听得到。" });
    });

    expect(result.current.sessionSummary).toEqual([]);
    expect(result.current.voiceChatArchiveMessages).toEqual([
      { role: "user", content: "Hello, can you hear me?", memorySaved: false },
      {
        role: "assistant",
        content: "你好，听得到。",
        memoriesUsed: undefined,
        memorySourceSummary: undefined,
        memoryRetrievalAttempted: false,
      },
    ]);
  });

  it("keeps the full voice session history instead of truncating older turns", async () => {
    const formatErrorMessage = createFormatErrorMessageStub();
    ensureEverMemConversationGroupIdMock.mockResolvedValue("voice-group-full-history");

    const { result } = renderHook(() =>
      useVoiceChat({
        formatErrorMessage,
        providerOptions: ["DashScope"],
        preferredProvider: "DashScope",
        preferredModel: "qwen3-omni-flash-realtime-2025-12-01",
        providerModelCatalog: {
          DashScope: {
            defaultModel: "qwen3-omni-flash-realtime-2025-12-01",
            availableModels: ["qwen3-omni-flash-realtime-2025-12-01"],
          },
        },
      })
    );

    await act(async () => {
      await result.current.onToggleRecording();
    });

    const socket = FakeWebSocket.instances[0];
    act(() => {
      socket.emitOpen();
      socket.emitMessage({
        type: "session_open",
        provider: "DashScope",
        model: "qwen3-omni-flash-realtime-2025-12-01",
        voice: "Cherry",
        mode: "voice_chat",
      });
      for (let i = 1; i <= 8; i += 1) {
        socket.emitMessage({ type: "user_transcript", text: `第 ${i} 轮用户` });
        socket.emitMessage({ type: "assistant_text", text: `第 ${i} 轮助手` });
        socket.emitMessage({ type: "turn_complete" });
      }
    });

    expect(result.current.voiceChatMessages).toHaveLength(16);
    expect(result.current.sessionSummary).toHaveLength(16);
    expect(result.current.sessionSummary[0]).toMatchObject({ role: "user", content: "第 1 轮用户" });
  });

  it("tracks voice agent tool progress and grounded search sources", async () => {
    const formatErrorMessage = createFormatErrorMessageStub();
    ensureEverMemConversationGroupIdMock.mockResolvedValue("voice-group-001");

    const { result } = renderHook(() =>
      useVoiceChat({
        formatErrorMessage,
        providerOptions: ["DashScope"],
        preferredProvider: "DashScope",
        preferredModel: "qwen3-omni-flash-realtime-2025-12-01",
        providerModelCatalog: {
          DashScope: {
            defaultModel: "qwen3-omni-flash-realtime-2025-12-01",
            availableModels: ["qwen3-omni-flash-realtime-2025-12-01"],
          },
        },
      })
    );

    await act(async () => {
      await result.current.onToggleRecording();
    });

    const toolSocket = FakeWebSocket.instances[0];
    act(() => {
      toolSocket.emitOpen();
      toolSocket.emitMessage({
        type: "user_transcript",
        text: "帮我搜索 AI voice agent 的资料",
      });
      toolSocket.emitMessage({
        type: "tool_call_started",
        tool_name: "search_web",
        turn_id: "voice-tool-1",
        query: "AI voice agent",
        message: "正在搜索相关资料...",
      });
    });

    expect(result.current.voiceChatAgentToolStatus).toBe("正在搜索相关资料...");
    expect(result.current.voiceChatAgentRunMeta).toBe("voice-tool-1 · search_web");
    expect(result.current.voiceChatAgentSources).toEqual([]);

    act(() => {
      toolSocket.emitMessage({
        type: "response_gated",
        provider: "DashScope",
        tool_name: "search_web",
        turn_id: "voice-tool-1",
        query: "AI voice agent",
        message: "检测到工具请求，已暂停直接回答，等待工具结果。",
      });
    });

    expect(result.current.voiceChatAgentToolStatus).toBe("检测到工具请求，已暂停直接回答，等待工具结果。");
    expect(result.current.voiceChatAgentRunMeta).toBe("voice-tool-1 · search_web");
    expect(result.current.voiceChatStatus).toBe("正在等待搜索工具结果…");

    act(() => {
      toolSocket.emitMessage({
        type: "agent_result",
        turn_id: "voice-tool-1",
        query: "AI voice agent",
        answer: "我查到这些信息，可以先按来源做一个简要整合。",
        source_count: 1,
        elapsed_ms: 320,
        sources: [
          {
            title: "Research source",
            uri: "https://example.com/research",
            snippet: "Fetched research content",
            source_type: "web_search",
          },
        ],
      });
    });

    expect(result.current.voiceChatReply).toContain("我查到这些信息");
    expect(result.current.voiceChatAgentToolStatus).toBe("已基于 1 个来源生成搜索摘要");
    expect(result.current.voiceChatAgentRunMeta).toBe("voice-tool-1 · 1 sources · 320ms");
    expect(result.current.voiceChatAgentSources).toEqual([
      {
        title: "Research source",
        uri: "https://example.com/research",
        snippet: "Fetched research content",
        source_type: "web_search",
      },
    ]);

    act(() => {
      toolSocket.emitMessage({
        type: "tool_context_injected",
        provider: "DashScope",
        tool_name: "search_web",
        turn_id: "voice-tool-1",
        query: "AI voice agent",
        source_count: 1,
        elapsed_ms: 320,
      });
    });

    expect(result.current.voiceChatAgentToolStatus).toBe("已将搜索结果交给 DashScope 生成语音回答");
    expect(result.current.voiceChatAgentRunMeta).toBe("voice-tool-1 · search_web · 1 sources · 320ms");
    expect(result.current.voiceChatStatus).toBe("正在基于搜索结果语音回答…");

    act(() => {
      toolSocket.emitMessage({ type: "turn_complete" });
    });

    expect(result.current.voiceChatMessages).toHaveLength(2);
    expect(result.current.voiceChatMessages[0]).toMatchObject({
      role: "user",
      content: "帮我搜索 AI voice agent 的资料",
    });
    expect(result.current.voiceChatMessages[1]).toMatchObject({
      role: "assistant",
      content: expect.stringContaining("我查到这些信息"),
      toolCalls: expect.arrayContaining([
        expect.objectContaining({
          status: "started",
          tool_name: "search_web",
          turn_id: "voice-tool-1",
          query: "AI voice agent",
        }),
        expect.objectContaining({
          status: "response_gated",
          provider: "DashScope",
          tool_name: "search_web",
        }),
        expect.objectContaining({
          status: "result",
          query: "AI voice agent",
          source_count: 1,
          sources: [
            expect.objectContaining({
              title: "Research source",
              uri: "https://example.com/research",
            }),
          ],
        }),
        expect.objectContaining({
          status: "context_injected",
          provider: "DashScope",
          tool_name: "search_web",
        }),
      ]),
    });
  });

  it("loads persisted voice agent sessions and exports the selected detail as JSON", async () => {
    const formatErrorMessage = createFormatErrorMessageStub();
    listVoiceAgentSessionsMock.mockResolvedValue({
      count: 1,
      sessions: [
        {
          id: "voice-session-1",
          provider: "DashScope",
          model: "qwen3-omni-flash-realtime-2025-12-01",
          voice: "Cherry",
          status: "closed",
          started_at: "2026-07-07 10:00:00",
          ended_at: "2026-07-07 10:01:00",
          meta: { transport: "websocket" },
        },
      ],
    });
    fetchVoiceAgentSessionMock.mockResolvedValue({
      id: "voice-session-1",
      provider: "DashScope",
      model: "qwen3-omni-flash-realtime-2025-12-01",
      voice: "Cherry",
      status: "closed",
      started_at: "2026-07-07 10:00:00",
      ended_at: "2026-07-07 10:01:00",
      meta: { transport: "websocket" },
      turns: [
        {
          id: 1,
          session_id: "voice-session-1",
          turn_id: "voice-tool-1",
          user_text: "帮我搜索 voice agent",
          assistant_text: "已整理来源。",
          memory_payload: { saved_count: 1 },
          completed: true,
          started_at: "2026-07-07 10:00:01",
          completed_at: "2026-07-07 10:00:04",
        },
      ],
      tool_events: [
        {
          id: 2,
          session_id: "voice-session-1",
          turn_id: "voice-tool-1",
          event_type: "agent_result",
          tool_name: "search_web",
          query: "voice agent",
          payload: { answer: "已整理来源。" },
          created_at: "2026-07-07 10:00:03",
        },
      ],
      timeline: [
        {
          id: "session:voice-session-1:open",
          event_type: "session_open",
          source: "session",
          turn_id: "",
          tool_name: "",
          query: "",
          text: "",
          timestamp: "2026-07-07 10:00:00",
          payload: { provider: "DashScope" },
        },
        {
          id: "turn:1:user",
          event_type: "user_transcript",
          source: "turn",
          turn_id: "voice-tool-1",
          tool_name: "",
          query: "",
          text: "帮我搜索 voice agent",
          timestamp: "2026-07-07 10:00:01",
          payload: { completed: true },
        },
        {
          id: "tool_event:2",
          event_type: "agent_result",
          source: "tool_event",
          turn_id: "voice-tool-1",
          tool_name: "search_web",
          query: "voice agent",
          text: "已整理来源。",
          timestamp: "2026-07-07 10:00:03",
          payload: { answer: "已整理来源。" },
        },
      ],
    });

    const { result } = renderHook(() =>
      useVoiceChat({
        formatErrorMessage,
        providerOptions: ["DashScope"],
        preferredProvider: "DashScope",
        preferredModel: "qwen3-omni-flash-realtime-2025-12-01",
        providerModelCatalog: {
          DashScope: {
            defaultModel: "qwen3-omni-flash-realtime-2025-12-01",
            availableModels: ["qwen3-omni-flash-realtime-2025-12-01"],
          },
        },
      })
    );

    await act(async () => {
      await result.current.onLoadVoiceAgentHistory();
    });

    expect(listVoiceAgentSessionsMock).toHaveBeenCalledWith(20);
    expect(result.current.voiceAgentHistorySessions).toHaveLength(1);
    expect(result.current.voiceAgentHistorySessions[0].id).toBe("voice-session-1");

    await act(async () => {
      await result.current.onOpenVoiceAgentSession("voice-session-1");
    });

    expect(fetchVoiceAgentSessionMock).toHaveBeenCalledWith("voice-session-1");
    expect(result.current.voiceAgentHistoryDetail?.turns[0].user_text).toBe("帮我搜索 voice agent");
    expect(result.current.voiceAgentHistoryDetail?.tool_events[0].event_type).toBe("agent_result");

    let exported = "";
    act(() => {
      exported = result.current.onExportVoiceAgentSession();
    });

    const parsed = JSON.parse(exported);
    expect(parsed.session.id).toBe("voice-session-1");
    expect(parsed.session.turns[0].assistant_text).toBe("已整理来源。");
    expect(parsed.session.timeline[2].event_type).toBe("agent_result");
    expect(result.current.voiceAgentHistoryExportText).toContain("\"voice-session-1\"");

    fetchVoiceAgentSessionMock.mockRejectedValueOnce(new Error("not found"));
    await act(async () => {
      await result.current.onOpenVoiceAgentSession("missing-session");
    });

    expect(fetchVoiceAgentSessionMock).toHaveBeenCalledWith("missing-session");
    expect(result.current.voiceAgentHistoryDetail).toBeNull();
    expect(result.current.voiceAgentHistoryExportText).toBe("");
    expect(result.current.voiceAgentHistoryError).toBe("加载历史语音 Agent 会话详情失败。");
  });

  it("ducks on a candidate, resumes backchannels, and archives confirmed interruptions", async () => {
    ensureEverMemConversationGroupIdMock.mockResolvedValue("voice-group-interruption");
    const { result } = renderHook(() =>
      useVoiceChat({
        formatErrorMessage: createFormatErrorMessageStub(),
        providerOptions: ["OpenAI"],
        preferredProvider: "OpenAI",
        preferredModel: "gpt-realtime-2",
        providerModelCatalog: {
          OpenAI: { defaultModel: "gpt-realtime-2", availableModels: ["gpt-realtime-2"] },
        },
      })
    );

    await act(async () => {
      await result.current.onToggleRecording();
    });
    const socket = FakeWebSocket.instances[0];
    act(() => {
      socket.emitOpen();
      socket.emitMessage({ type: "session_open", provider: "OpenAI", model: "gpt-realtime-2", voice: "alloy" });
      socket.emitMessage({ type: "user_transcript", text: "继续解释", turn_id: "voice-turn-1" });
      socket.emitMessage({ type: "assistant_text", text: "这是还没说完的回答", turn_id: "voice-turn-1" });
      socket.emitMessage({
        type: "interruption_pending",
        candidate_id: "interruption-1",
        provider: "OpenAI",
        interrupted_turn_id: "voice-turn-1",
      });
    });

    expect(result.current.voiceChatInterruptionState.phase).toBe("evaluating");
    expect(FakeAudioContext.gains[0].gain.value).toBe(0.18);

    act(() => {
      socket.emitMessage({
        type: "interruption_decision",
        candidate_id: "interruption-1",
        classification: "BACKCHANNEL",
        rule: "backchannel_pattern:^嗯(嗯)?$",
        decision: "resume",
        transcript: "嗯嗯",
        provider: "OpenAI",
        interrupted_turn_id: "voice-turn-1",
        elapsed_ms: 37,
      });
    });

    expect(result.current.voiceChatMessages).toHaveLength(0);
    expect(result.current.voiceChatReply).toBe("这是还没说完的回答");
    expect(result.current.voiceChatMetrics.falseInterruptionRate).toBe(1);
    expect(FakeAudioContext.gains[0].gain.value).toBe(1);

    await act(async () => {
      socket.emitMessage({
        type: "assistant_audio",
        audio: "AAA=",
        encoding: "pcm_s16le",
        sample_rate: 24000,
        turn_id: "voice-turn-1",
        first_audio_ms: 84,
      });
      socket.emitMessage({
        type: "interruption_pending",
        candidate_id: "interruption-2",
        provider: "OpenAI",
        interrupted_turn_id: "voice-turn-1",
      });
      socket.emitMessage({
        type: "interruption_decision",
        candidate_id: "interruption-2",
        classification: "TRUE_BARGE_IN",
        rule: "non_backchannel_speech",
        decision: "cancel",
        transcript: "等一下",
        provider: "OpenAI",
        interrupted_turn_id: "voice-turn-1",
        elapsed_ms: 42,
        stop_latency_ms: 42,
      });
      socket.emitMessage({
        type: "interrupted",
        turn_id: "voice-turn-1",
        interrupted: true,
        stop_latency_ms: 42,
      });
      await Promise.resolve();
    });

    expect(result.current.voiceChatAssistantInterrupted).toBe(true);
    expect(result.current.voiceChatMetrics.firstAudioMs).toBe(84);
    expect(result.current.voiceChatMetrics.decisionCount).toBe(2);
    expect(result.current.voiceChatMetrics.falseInterruptionRate).toBe(0.5);
    expect(result.current.voiceChatMetrics.interruptionStopMs).not.toBeNull();
    expect(result.current.voiceChatMessages).toEqual([
      expect.objectContaining({ role: "user", content: "继续解释", turnId: "voice-turn-1" }),
      expect.objectContaining({
        role: "assistant",
        content: "这是还没说完的回答",
        turnId: "voice-turn-1",
        interrupted: true,
      }),
    ]);
  });
});
