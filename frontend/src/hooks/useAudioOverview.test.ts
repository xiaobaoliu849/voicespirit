import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useAudioOverview from "./useAudioOverview";
import { createFormatErrorMessageStub } from "../test/factories";
import { listAudioOverviewPodcasts } from "../api";

vi.mock("../api", () => ({
  createAudioOverviewPodcast: vi.fn(),
  deleteAudioOverviewPodcast: vi.fn(),
  fetchAudioOverviewPodcastAudio: vi.fn(),
  generateAudioOverviewScript: vi.fn(),
  getEverMemRuntimeConfig: vi.fn(() => ({ enabled: false })),
  getAudioOverviewPodcast: vi.fn(),
  listAudioOverviewPodcasts: vi.fn().mockResolvedValue({ podcasts: [] }),
  saveAudioOverviewScript: vi.fn(),
  synthesizeAudioOverviewPodcast: vi.fn(),
  updateAudioOverviewPodcast: vi.fn()
}));

describe("useAudioOverview", () => {
  beforeEach(() => {
    vi.mocked(listAudioOverviewPodcasts).mockClear();
    Object.defineProperty(globalThis.navigator, "clipboard", {
      value: {
        writeText: vi.fn().mockResolvedValue(undefined)
      },
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
});
