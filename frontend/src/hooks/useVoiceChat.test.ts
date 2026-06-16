import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { ensureEverMemConversationGroupIdMock } = vi.hoisted(() => ({
  ensureEverMemConversationGroupIdMock: vi.fn(),
}));

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    ensureEverMemConversationGroupId: ensureEverMemConversationGroupIdMock,
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
  gain = { value: 1 };
}

class FakeAudioContext {
  state = "running";
  currentTime = 0;
  destination = {};

  resume = vi.fn(async () => undefined);
  close = vi.fn(async () => undefined);
  createMediaStreamSource = vi.fn(() => new FakeAudioNode());
  createScriptProcessor = vi.fn(() => new FakeProcessorNode());
  createGain = vi.fn(() => new FakeGainNode());
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
  onclose: (() => void) | null = null;
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

  emitClose() {
    this.readyState = FakeWebSocket.CLOSED;
    this.onclose?.();
  }
}

describe("useVoiceChat", () => {
  beforeEach(() => {
    FakeWebSocket.instances = [];
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
    vi.clearAllMocks();
    vi.restoreAllMocks();
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
    const socket = FakeWebSocket.instances[0];
    act(() => {
      socket.emitOpen();
      socket.emitMessage({
        type: "user_transcript",
        text: "帮我搜索 AI voice agent 的资料",
      });
      socket.emitMessage({
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
      socket.emitMessage({
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
      socket.emitMessage({
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
      socket.emitMessage({
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
      socket.emitMessage({ type: "turn_complete" });
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
});
