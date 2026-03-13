import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildVoiceChatSessionConfig,
  clearPersistedEverMemConversationGroupId,
  createEverMemConversationMeta,
  configureEverMemRuntime,
  fetchTranscriptionJob,
  getPersistedEverMemConversationGroupId,
  persistEverMemConversationGroupId,
  transcribeAudio,
} from "./api";

describe("EverMem API wiring", () => {
  beforeEach(() => {
    localStorage.clear();
    configureEverMemRuntime({
      enabled: true,
      api_url: "https://memory.example.com",
      api_key: "memory-key",
      scope_id: "workspace-main",
      remember_chat: true,
      remember_voice_chat: true,
      remember_recordings: true,
      remember_podcast: true,
      remember_tts: true,
      temporary_session: false,
      store_transcript_fulltext: false,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("builds a voice chat session config from runtime settings", () => {
    expect(buildVoiceChatSessionConfig()).toEqual({
      enabled: true,
      api_url: "https://memory.example.com",
      api_key: "memory-key",
      scope_id: "workspace-main",
    });
  });

  it("includes group_id in voice chat session config when provided", () => {
    expect(buildVoiceChatSessionConfig("group-chat-001")).toEqual({
      enabled: true,
      api_url: "https://memory.example.com",
      api_key: "memory-key",
      scope_id: "workspace-main",
      group_id: "group-chat-001",
    });
  });

  it("creates EverMem conversation metadata through the backend proxy", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ group_id: "group-chat-001", user_id: "workspace-main" }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await createEverMemConversationMeta("chat");

    expect(result).toEqual({ group_id: "group-chat-001", user_id: "workspace-main" });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/api/evermem/conversation-meta");
    const headers = new Headers(init.headers);
    expect(headers.get("X-EverMem-Enabled")).toBe("true");
    expect(headers.get("X-EverMem-Key")).toBe("memory-key");
    expect(headers.get("X-EverMem-Scope")).toBe("workspace-main");
  });

  it("persists and clears conversation group ids per scene", () => {
    expect(getPersistedEverMemConversationGroupId("chat")).toBe("");
    expect(getPersistedEverMemConversationGroupId("voice_chat")).toBe("");

    persistEverMemConversationGroupId("chat", "group-chat-001");
    persistEverMemConversationGroupId("voice_chat", "group-voice-001");

    expect(getPersistedEverMemConversationGroupId("chat")).toBe("group-chat-001");
    expect(getPersistedEverMemConversationGroupId("voice_chat")).toBe("group-voice-001");

    clearPersistedEverMemConversationGroupId("chat");
    expect(getPersistedEverMemConversationGroupId("chat")).toBe("");
    expect(getPersistedEverMemConversationGroupId("voice_chat")).toBe("group-voice-001");
  });

  it("sends EverMem headers for sync transcription", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ transcript: "ok", memory_saved: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    await transcribeAudio(new File(["audio"], "note.wav", { type: "audio/wav" }));

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(init.headers);
    expect(headers.get("X-EverMem-Enabled")).toBe("true");
    expect(headers.get("X-EverMem-Key")).toBe("memory-key");
    expect(headers.get("X-EverMem-Scope")).toBe("workspace-main");
  });

  it("sends EverMem headers when refreshing transcription jobs", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          job_id: "tx_001",
          mode: "async",
          status: "completed",
          file_name: "note.wav",
          memory_saved: true,
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchTranscriptionJob("tx_001");

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(init.headers);
    expect(headers.get("X-EverMem-Enabled")).toBe("true");
    expect(headers.get("X-EverMem-Key")).toBe("memory-key");
  });
});
