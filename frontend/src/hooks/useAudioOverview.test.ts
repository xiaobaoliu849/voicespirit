import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useAudioOverview from "./useAudioOverview";
import { createFormatErrorMessageStub } from "../test/factories";
import {
  createAudioOverviewPodcast,
  fetchAudioOverviewPodcastAudio,
  listAudioOverviewPodcasts,
  synthesizeAudioOverviewPodcast
} from "../api";

vi.mock("../api", () => ({
  createAudioAgentRun: vi.fn(),
  createAudioOverviewPodcast: vi.fn(),
  deleteAudioOverviewPodcast: vi.fn(),
  fetchAudioOverviewPodcastAudio: vi.fn(),
  fetchVoices: vi.fn().mockResolvedValue({ voices: [] }),
  generateAudioOverviewScript: vi.fn(),
  getEverMemRuntimeConfig: vi.fn(() => ({ enabled: false })),
  getAudioAgentRun: vi.fn(),
  getAudioOverviewPodcast: vi.fn(),
  listAudioAgentRunEvents: vi.fn(),
  listAudioAgentRuns: vi.fn(),
  listCustomVoices: vi.fn().mockResolvedValue({ voices: [] }),
  listAudioOverviewPodcasts: vi.fn().mockResolvedValue({ podcasts: [] }),
  saveAudioOverviewScript: vi.fn(),
  synthesizeAudioAgentRun: vi.fn(),
  synthesizeAudioOverviewPodcast: vi.fn(),
  updateAudioOverviewPodcast: vi.fn()
}));

describe("useAudioOverview", () => {
  beforeEach(() => {
    vi.mocked(listAudioOverviewPodcasts).mockClear();
    vi.mocked(createAudioOverviewPodcast).mockReset();
    vi.mocked(synthesizeAudioOverviewPodcast).mockReset();
    vi.mocked(fetchAudioOverviewPodcastAudio).mockReset();
    Object.defineProperty(globalThis.navigator, "clipboard", {
      value: {
        writeText: vi.fn().mockResolvedValue(undefined)
      },
      configurable: true
    });
    Object.defineProperty(globalThis.URL, "createObjectURL", {
      value: vi.fn(() => "blob:audio-test"),
      configurable: true
    });
    Object.defineProperty(globalThis.URL, "revokeObjectURL", {
      value: vi.fn(),
      configurable: true
    });
  });

  it("switches workspace mode to multi-dialogue", async () => {
    const formatErrorMessage = createFormatErrorMessageStub();
    const voices = [
      { name: "voice-a", short_name: "A", locale: "zh-CN", gender: "Male" },
      { name: "voice-b", short_name: "B", locale: "zh-CN", gender: "Female" }
    ];

    const { result } = renderHook(() =>
      useAudioOverview({ voices, formatErrorMessage })
    );

    await act(async () => {
      result.current.onWorkspaceModeChange("multi_dialogue");
    });

    expect(result.current.audioOverviewWorkspaceMode).toBe("multi_dialogue");
    expect(result.current.audioOverviewWorkspaceTitle).toBe("多人对话工作台");
    expect(result.current.audioOverviewWorkspaceDescription).toContain("角色讨论");
  });

  it("copies exported script using custom speaker labels", async () => {
    const formatErrorMessage = createFormatErrorMessageStub();
    const voices = [
      { name: "voice-a", short_name: "A", locale: "zh-CN", gender: "Male" },
      { name: "voice-b", short_name: "B", locale: "zh-CN", gender: "Female" }
    ];

    const { result } = renderHook(() =>
      useAudioOverview({ voices, formatErrorMessage })
    );

    act(() => {
      result.current.onSpeakerAChange("主持人晨");
      result.current.onSpeakerBChange("主持人林");
      result.current.onAddLine();
      result.current.onLineTextChange(0, "今天我们聊聊记忆系统。");
      result.current.onAddLine();
      result.current.onLineRoleChange(1, "B");
      result.current.onLineTextChange(1, "那就从长期记忆如何融入工作流开始。");
    });

    await act(async () => {
      await result.current.onCopyScript();
    });

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      expect.stringContaining("主持人晨")
    );
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      expect.stringContaining("主持人林")
    );
  });

  it("passes intro music options when synthesizing a podcast", async () => {
    const formatErrorMessage = createFormatErrorMessageStub();
    vi.mocked(createAudioOverviewPodcast).mockResolvedValue({
      id: 9,
      topic: "片头测试",
      language: "zh",
      audio_path: null,
      created_at: "2026-01-01",
      updated_at: "2026-01-01",
      script_lines: [
        { role: "A", text: "开场" },
        { role: "B", text: "回应" }
      ]
    });
    vi.mocked(synthesizeAudioOverviewPodcast).mockResolvedValue({
      podcast_id: 9,
      audio_path: "audio.mp3",
      audio_download_url: "/api/audio-overview/podcasts/9/audio",
      line_count: 2,
      voice_a: "voice-a",
      voice_b: "voice-b",
      rate: "+0%",
      cache_hits: 0,
      gap_ms: 250,
      gap_ms_applied: 250,
      merge_strategy: "pydub",
      intro_music: true,
      intro_music_style: "calm",
      intro_music_duration_ms: 3000
    });
    vi.mocked(fetchAudioOverviewPodcastAudio).mockResolvedValue(
      new Blob(["audio"], { type: "audio/mpeg" })
    );

    const { result } = renderHook(() =>
      useAudioOverview({ voices: [], formatErrorMessage })
    );

    act(() => {
      result.current.onTopicChange("片头测试");
      result.current.onAddLine();
      result.current.onLineTextChange(0, "开场");
      result.current.onAddLine();
      result.current.onLineRoleChange(1, "B");
      result.current.onLineTextChange(1, "回应");
      result.current.onToggleSynthAdvanced();
      result.current.onIntroMusicChange(true);
      result.current.onIntroMusicStyleChange("calm");
      result.current.onIntroMusicDurationChange("3000");
    });

    await act(async () => {
      await result.current.onSynthesize();
    });

    expect(synthesizeAudioOverviewPodcast).toHaveBeenCalledWith(
      9,
      expect.objectContaining({
        intro_music: true,
        intro_music_style: "calm",
        intro_music_duration_ms: 3000
      })
    );
  });
});
