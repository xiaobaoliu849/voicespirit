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
});
