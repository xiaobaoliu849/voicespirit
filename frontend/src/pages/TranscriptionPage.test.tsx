import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import { TranscriptionPage } from "./TranscriptionPage";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    transcribeAudio: vi.fn(),
    createTranscriptionJobFromUrl: vi.fn(),
    fetchTranscriptionJob: vi.fn(),
    listTranscriptionJobs: vi.fn().mockResolvedValue({ jobs: [] })
  };
});

const mockedTranscribeAudio = vi.mocked(api.transcribeAudio);
const mockedCreateTranscriptionJobFromUrl = vi.mocked(api.createTranscriptionJobFromUrl);
const mockedFetchTranscriptionJob = vi.mocked(api.fetchTranscriptionJob);

describe("TranscriptionPage", () => {
  beforeEach(() => {
    mockedTranscribeAudio.mockResolvedValue({
      transcript: "同步转写结果",
      memory_saved: true
    });
    mockedCreateTranscriptionJobFromUrl.mockResolvedValue({
      job_id: "tx_url_001",
      remote_job_id: "remote-url-job-001",
      mode: "async",
      status: "submitted",
      file_name: "demo.wav",
      memory_saved: false
    });
    mockedFetchTranscriptionJob.mockResolvedValue({
      job_id: "tx_url_001",
      remote_job_id: "remote-url-job-001",
      mode: "async",
      status: "completed",
      file_name: "demo.wav",
      transcript: "异步转写完成",
      memory_saved: true
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("transcribes a local audio file", async () => {
    render(<TranscriptionPage />);

    // Default mode is local
    const fileInput = screen.getByLabelText("选择转写音频");
    const audioFile = new File(["audio"], "note.wav", { type: "audio/wav" });
    fireEvent.change(fileInput, { target: { files: [audioFile] } });
    fireEvent.click(screen.getByRole("button", { name: "开始同步转写" }));

    expect(mockedTranscribeAudio).toHaveBeenCalledWith(audioFile);
    expect(await screen.findByDisplayValue("同步转写结果")).toBeInTheDocument();
    expect(screen.getByText("已入记忆")).toBeInTheDocument();
  });

  it("polls a remote async transcription job until completion", async () => {
    vi.spyOn(window, "setTimeout").mockImplementation(((handler: TimerHandler) => {
      if (typeof handler === "function") {
        handler();
      }
      return 0 as unknown as number;
    }) as typeof window.setTimeout);
    render(<TranscriptionPage />);

    // Switch to Remote mode
    fireEvent.click(screen.getByRole("button", { name: "链式转写" }));

    fireEvent.change(screen.getByPlaceholderText("https://example.com/meeting.wav"), {
      target: { value: "https://example.com/audio/demo.wav" }
    });
    fireEvent.click(screen.getByRole("button", { name: "提交异步任务" }));

    expect(mockedCreateTranscriptionJobFromUrl).toHaveBeenCalledWith(
      "https://example.com/audio/demo.wav"
    );

    await act(async () => {
      await Promise.resolve();
    });

    expect(mockedFetchTranscriptionJob).toHaveBeenCalledWith("tx_url_001", { refresh: true });
    expect(screen.getByDisplayValue("异步转写完成")).toBeInTheDocument();
    expect(screen.getByText("已入记忆")).toBeInTheDocument();
  });
});
