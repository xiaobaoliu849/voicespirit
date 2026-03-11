import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildVoiceChatSessionConfig,
  configureEverMemRuntime,
  fetchTranscriptionJob,
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
