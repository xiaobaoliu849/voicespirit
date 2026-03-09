import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { listTranscriptionJobs, retryTranscriptionJob } from "../api";
import { useTranscriptionHistory } from "./useTranscriptionHistory";

vi.mock("../api", () => ({
  listTranscriptionJobs: vi.fn(),
  retryTranscriptionJob: vi.fn(),
}));

describe("useTranscriptionHistory", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.mocked(listTranscriptionJobs).mockReset();
    vi.mocked(retryTranscriptionJob).mockReset();
    vi.mocked(listTranscriptionJobs).mockResolvedValue({
      count: 1,
      jobs: [
        {
          job_id: "tx_001",
          mode: "async",
          status: "completed",
          file_name: "meeting.wav",
          updated_at: "2026-03-09T12:00:00Z",
          has_transcript: true,
          memory_saved: true,
        },
      ],
    });
  });

  it("loads history from backend and persists it locally", async () => {
    const { result } = renderHook(() => useTranscriptionHistory());

    await waitFor(() => {
      expect(result.current.historyBusy).toBe(false);
    });

    expect(vi.mocked(listTranscriptionJobs)).toHaveBeenCalledWith({
      statuses: undefined,
      limit: 50,
    });
    expect(result.current.history).toHaveLength(1);
    expect(result.current.history[0]?.job_id).toBe("tx_001");
    expect(JSON.parse(localStorage.getItem("vs_transcription_history") || "[]")).toHaveLength(1);
  });

  it("retries a failed job and updates cached history", async () => {
    vi.mocked(retryTranscriptionJob).mockResolvedValue({
      job_id: "tx_001",
      mode: "async",
      status: "submitted",
      file_name: "meeting.wav",
      updated_at: "2026-03-09T12:05:00Z",
      has_transcript: false,
      memory_saved: false,
      remote_job_id: "remote_retry_001",
    });

    const { result } = renderHook(() => useTranscriptionHistory());

    await waitFor(() => {
      expect(result.current.historyBusy).toBe(false);
    });

    await act(async () => {
      await result.current.retryJob("tx_001");
    });

    expect(vi.mocked(retryTranscriptionJob)).toHaveBeenCalledWith("tx_001");
    expect(result.current.history[0]?.status).toBe("submitted");
    expect(result.current.history[0]?.remote_job_id).toBe("remote_retry_001");
  });

  it("switches filters and requests matching backend statuses", async () => {
    const { result } = renderHook(() => useTranscriptionHistory());

    await waitFor(() => {
      expect(result.current.historyBusy).toBe(false);
    });

    vi.mocked(listTranscriptionJobs).mockClear();

    await act(async () => {
      result.current.setActiveFilter("failed");
    });

    await waitFor(() => {
      expect(vi.mocked(listTranscriptionJobs)).toHaveBeenCalledWith({
        statuses: ["failed"],
        limit: 50,
      });
    });
  });
});
