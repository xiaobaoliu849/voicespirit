import React, { useEffect, useState } from "react";
import {
  createTranscriptionJobFromUrl,
  fetchTranscriptionJob,
  transcribeAudio,
  type TranscriptionJobResponse
} from "../api";
import { AudioDropZone } from "../components/AudioDropZone";
import ErrorNotice from "../components/ErrorNotice";
import { useTranscriptionHistory } from "../hooks/useTranscriptionHistory";
import { useI18n } from "../i18n";

const ASYNC_POLL_INTERVAL_MS = 2500;
const LARGE_FILE_RECOMMENDATION_BYTES = 25 * 1024 * 1024;


function isPollingStatus(status: string | null | undefined): boolean {
  return status === "submitted" || status === "running";
}

function buildJobStatusText(
  job: TranscriptionJobResponse,
  t: (zh: string, en: string) => string
): string {
  if (job.status === "completed") {
    return job.memory_saved
      ? t("异步转写完成，摘要已写入长期记忆。", "Async transcription completed and the summary was saved to long-term memory.")
      : t("异步转写完成。", "Async transcription completed.");
  }
  if (job.status === "failed") {
    return job.error || t("异步转写失败。", "Async transcription failed.");
  }
  if (job.status === "running") {
    return t(`远端任务运行中，正在拉取结果… (${job.job_id})`, `Remote job is running. Fetching results... (${job.job_id})`);
  }
  if (job.status === "submitted") {
    return t(`远端任务已提交，正在轮询状态… (${job.job_id})`, `Remote job submitted. Polling status... (${job.job_id})`);
  }
  if (job.status === "uploaded") {
    return job.error || t("文件已接收，等待后续处理。", "File received. Waiting for further processing.");
  }
  return t(`任务状态: ${job.status}`, `Job status: ${job.status}`);
}

export const TranscriptionPage: React.FC = () => {
  const { t, language } = useI18n();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [remoteUrl, setRemoteUrl] = useState("");
  const [transcript, setTranscript] = useState("");
  const [statusMessage, setStatusMessage] = useState(t("等待上传或输入远端音频地址…", "Waiting for a local upload or remote audio URL..."));
  const [job, setJob] = useState<TranscriptionJobResponse | null>(null);
  const [memorySaved, setMemorySaved] = useState(false);
  const [isSyncBusy, setIsSyncBusy] = useState(false);
  const [isAsyncBusy, setIsAsyncBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [infoMessage, setInfoMessage] = useState("");
  const [inputMode, setInputMode] = useState<"local" | "remote">("local");

  const { history, historyBusy, refreshHistory, addOrUpdateJob } = useTranscriptionHistory();

  useEffect(() => {
    if (!job?.job_id || !isPollingStatus(job.status)) {
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        const nextJob = await fetchTranscriptionJob(job.job_id, { refresh: true });
        if (cancelled) {
          return;
        }
        setJob(nextJob);
        addOrUpdateJob(nextJob);
        setStatusMessage(buildJobStatusText(nextJob, t));
        setMemorySaved(Boolean(nextJob.memory_saved));
        if (nextJob.transcript) {
          setTranscript(nextJob.transcript);
        }
      } catch (err) {
        if (cancelled) {
          return;
        }
        setError(err instanceof Error ? err : new Error(t("转写任务刷新失败。", "Failed to refresh transcription job.")));
        setStatusMessage(t("异步任务刷新失败。", "Async job refresh failed."));
      }
    }, ASYNC_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [job, addOrUpdateJob, t]);

  function resetRunState() {
    setError(null);
    setInfoMessage("");
    setTranscript("");
    setMemorySaved(false);
  }

  function handleFileDrop(file: File) {
    setSelectedFile(file);
    setJob(null);
    setError(null);
    setInfoMessage("");
    setStatusMessage(t(`已选择本地音频: ${file.name}`, `Selected local audio: ${file.name}`));
  }

  function handleRemoteUrlChange(event: React.ChangeEvent<HTMLInputElement>) {
    setRemoteUrl(event.target.value);
    setError(null);
    setInfoMessage("");
  }

  async function handleLocalTranscription() {
    if (!selectedFile) {
      return;
    }

    resetRunState();
    setJob(null);
    setIsSyncBusy(true);
    setStatusMessage(t("正在上传并同步转写本地音频…", "Uploading and transcribing local audio..."));

    try {
      const result = await transcribeAudio(selectedFile);
      setTranscript(result.transcript);
      setMemorySaved(Boolean(result.memory_saved));

      // Mock a job response for history since sync transcription doesn't return a full job ID
      const mockJob: TranscriptionJobResponse = {
        job_id: `sync_${Date.now()}`,
        mode: "sync",
        status: "completed",
        file_name: selectedFile.name,
        transcript: result.transcript,
        has_transcript: true,
        memory_saved: Boolean(result.memory_saved),
        updated_at: new Date().toISOString()
      };
      addOrUpdateJob(mockJob);

      setStatusMessage(
        result.memory_saved
          ? t("同步转写完成，摘要已写入长期记忆。", "Synchronous transcription completed and the summary was saved to long-term memory.")
          : t("同步转写完成。", "Synchronous transcription completed.")
      );
      if (selectedFile.size >= LARGE_FILE_RECOMMENDATION_BYTES) {
        setInfoMessage(t("本地大文件更适合走链式异步任务，稳定性会更高。", "Large local files are better suited for the async pipeline for improved reliability."));
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error(t("本地音频转写失败。", "Local audio transcription failed.")));
      setStatusMessage(t("同步转写失败。", "Synchronous transcription failed."));
    } finally {
      setIsSyncBusy(false);
    }
  }

  async function handleRemoteJobStart() {
    const normalizedUrl = remoteUrl.trim();
    if (!normalizedUrl) {
      return;
    }

    resetRunState();
    setSelectedFile(null);
    setIsAsyncBusy(true);
    setStatusMessage(t("正在创建远端异步转写任务…", "Creating remote async transcription job..."));

    try {
      const createdJob = await createTranscriptionJobFromUrl(normalizedUrl);
      setJob(createdJob);
      addOrUpdateJob(createdJob);
      setStatusMessage(buildJobStatusText(createdJob, t));
      setMemorySaved(Boolean(createdJob.memory_saved));
      if (createdJob.transcript) {
        setTranscript(createdJob.transcript);
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error(t("远端异步任务创建失败。", "Failed to create remote async job.")));
      setStatusMessage(t("异步任务创建失败。", "Async job creation failed."));
    } finally {
      setIsAsyncBusy(false);
    }
  }

  async function handleCopy() {
    if (!transcript) {
      return;
    }
    try {
      await navigator.clipboard.writeText(transcript);
      setInfoMessage(t("转写文本已复制到剪贴板。", "Transcript copied to clipboard."));
    } catch {
      setInfoMessage(t("复制失败，请手动复制。", "Copy failed. Please copy it manually."));
    }
  }

  function handleExport() {
    if (!transcript) {
      return;
    }
    const blob = new Blob([transcript], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "transcript.txt";
    anchor.click();
    URL.revokeObjectURL(url);
    setInfoMessage(t("转写文本已导出为 transcript.txt。", "Transcript exported as transcript.txt."));
  }

  function handleReservedAction(action: string) {
    setInfoMessage(t(`${action} 即将开放，当前版本先保留入口。`, `${action} is coming soon. The entry is reserved for now.`));
  }

  const isBusy = isSyncBusy || isAsyncBusy || isPollingStatus(job?.status);

  return (
    <section className="vsTtsWorkspace">
      <div className="vsTtsLayout">
        {/* ── Left Pane: Logic & History ── */}
        <div className="vsTtsPrimary">
          <header className="vsTtsPrimaryHeader">
            <div>
              <div className="vsModeTabs" style={{ display: "flex", gap: 8, marginBottom: 14 }}>
                <button
                  type="button"
                  className={inputMode === "local" ? "vsBtnPrimary" : "vsBtnSecondary"}
                  onClick={() => setInputMode("local")}
                >
                  {t("本地音频", "Local audio")}
                </button>
                <button
                  type="button"
                  className={inputMode === "remote" ? "vsBtnPrimary" : "vsBtnSecondary"}
                  onClick={() => setInputMode("remote")}
                >
                  {t("链式转写", "Async pipeline")}
                </button>
              </div>
              <h2 className="vsTtsPrimaryTitle">{t("转写控制台", "Transcription console")}</h2>
            </div>
            <div className="vsTtsPrimaryStats">
              <span>{inputMode === "local" ? t("本地同步流", "Local sync flow") : t("异步任务流", "Async job flow")}</span>
            </div>
          </header>

          <div className="vsTtsEditorWrap custom-scrollbar" style={{ padding: "24px", overflowY: "auto" }}>
            {error && <ErrorNotice message={error.message || String(error)} scope="Transcription" />}

            {inputMode === "local" ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                <div>
                  <h3 style={{ fontSize: "16px", fontWeight: "600", color: "var(--text)", margin: 0 }}>
                    {t("上传音频", "Upload audio")}
                  </h3>
                  <p style={{ fontSize: "12px", color: "var(--muted)", marginTop: "4px" }}>
                    {t("适合短音频、语音备忘和快速验证。限制 25MB。", "Best for short clips, voice notes, and quick validation. Limit 25MB.")}
                  </p>
                </div>

                <AudioDropZone
                  onFileDrop={handleFileDrop}
                  selectedFile={selectedFile}
                  isProcessing={isBusy}
                  inputLabel={t("选择转写音频", "Choose transcription audio")}
                  readyText={t("已选中，可开始同步转写", "Selected. Ready for synchronous transcription")}
                  subText={t("支持 MP3, WAV, M4A, FLAC, AAC, OGG", "Supports MP3, WAV, M4A, FLAC, AAC, OGG")}
                />

                <button
                  onClick={handleLocalTranscription}
                  disabled={!selectedFile || isBusy}
                  className="vsBtnPrimary"
                  style={{ width: "100%", height: "44px" }}
                >
                  {isSyncBusy ? (
                    <>
                      <span className="spinner-mini"></span> {t("转写中…", "Transcribing...")}
                    </>
                  ) : (
                    t("开始同步转写", "Start sync transcription")
                  )}
                </button>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                <div>
                  <h3 style={{ fontSize: "16px", fontWeight: "600", color: "var(--text)", margin: 0 }}>
                    {t("输入文件 URL", "Enter file URL")}
                  </h3>
                  <p style={{ fontSize: "12px", color: "var(--muted)", marginTop: "4px" }}>
                    {t("适合长音频。支持公网可访问的 http/https/oss 地址。", "Best for long audio. Supports public http/https/oss URLs.")}
                  </p>
                </div>

                <div className="vsField">
                  <input
                    type="url"
                    value={remoteUrl}
                    onChange={handleRemoteUrlChange}
                    placeholder="https://example.com/meeting.wav"
                    disabled={isBusy}
                    className="vsInput"
                    style={{ width: "100%", height: "44px" }}
                  />
                </div>

                <div style={{ padding: "12px 16px", background: "var(--panel)", borderRadius: "12px", border: "1px dashed var(--line)", fontSize: "12px", color: "var(--muted)", lineHeight: "1.6" }}>
                  {t("系统将创建异步任务并自动轮询状态。完成后可在此处或历史记录中查看结果。", "The system will create an async job and poll automatically. Results will be available here and in history when finished.")}
                </div>

                <button
                  onClick={handleRemoteJobStart}
                  disabled={!remoteUrl.trim() || isBusy}
                  className="vsBtnPrimary"
                  style={{ width: "100%", height: "44px" }}
                >
                  {isAsyncBusy || isPollingStatus(job?.status) ? (
                    <>
                      <span className="spinner-mini"></span> {t("任务处理中…", "Processing job...")}
                    </>
                  ) : (
                    t("提交异步任务", "Submit async job")
                  )}
                </button>
              </div>
            )}

            <div style={{ marginTop: "32px", paddingTop: "24px", borderTop: "1px solid var(--line)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
                <h3 style={{ fontSize: "12px", fontWeight: "700", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>
                  {t("最近记录", "Recent jobs")}
                </h3>
                <button
                  onClick={() => refreshHistory()}
                  className="vsBtnGhost"
                  style={{ fontSize: "11px", padding: "4px 8px" }}
                >
                  {t("刷新列表", "Refresh list")}
                </button>
              </div>

              {historyBusy && history.length === 0 ? (
                <div style={{ textAlign: "center", padding: "32px 0", color: "var(--muted)", fontSize: "14px", fontStyle: "italic" }}>
                  {t("加载历史记录中…", "Loading history...")}
                </div>
              ) : history.length === 0 ? (
                <div style={{ textAlign: "center", padding: "32px 0", color: "var(--muted)", fontSize: "14px", fontStyle: "italic" }}>
                  {t("暂无转写记录", "No transcription history yet")}
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {history.slice(0, 8).map((item) => (
                    <div
                      key={item.job_id}
                      className="vsHistoryItem"
                      style={{ padding: "12px", background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "12px", cursor: "pointer", transition: "all 0.2s" }}
                      onClick={() => {
                        if (item.has_transcript) {
                          setTranscript("");
                          fetchTranscriptionJob(item.job_id).then(j => {
                            setJob(j);
                            if (j.transcript) setTranscript(j.transcript);
                            setStatusMessage(buildJobStatusText(j, t));
                          });
                        }
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <span style={{ fontSize: "14px", fontWeight: "600", color: "var(--text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1, paddingRight: "8px" }}>
                          {item.file_name || t("未知文件", "Unknown file")}
                        </span>
                        <span style={{
                          fontSize: "10px",
                          fontWeight: "700",
                          padding: "2px 8px",
                          borderRadius: "6px",
                          textTransform: "uppercase",
                          background: item.status === "completed" ? "#ecfdf5" : item.status === "failed" ? "#fff1f2" : "#eef2ff",
                          color: item.status === "completed" ? "#10b981" : item.status === "failed" ? "#f43f5e" : "#6366f1"
                        }}>
                          {item.status}
                        </span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "6px" }}>
                        <span style={{ fontSize: "11px", color: "var(--muted)" }}>
                          {item.updated_at
                            ? new Date(item.updated_at).toLocaleString(language === "en-US" ? "en-US" : "zh-CN")
                            : t("未知时间", "Unknown time")}
                        </span>
                        {item.has_transcript && (
                          <span style={{ fontSize: "11px", fontWeight: "600", color: "var(--brand)" }}>
                            {t("载入结果", "Load result")}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── Right Pane: Result ── */}
        <div className="vsTtsSecondary">
          <div className="vsCardSection" style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
              <h3 className="vsCardSubTitle" style={{ margin: 0 }}>{t("转写结果", "Transcription result")}</h3>
              <div style={{ display: "flex", gap: "8px" }}>
                <button
                  onClick={handleCopy}
                  disabled={!transcript}
                  className="vsBtnSecondary"
                  style={{ height: "30px", fontSize: "12px", padding: "0 12px" }}
                >
                  {t("复制", "Copy")}
                </button>
                <button
                  onClick={handleExport}
                  disabled={!transcript}
                  className="vsBtnSecondary"
                  style={{ height: "30px", fontSize: "12px", padding: "0 12px" }}
                >
                  {t("导出", "Export")}
                </button>
              </div>
            </div>

            <div style={{ flex: 1, position: "relative", minHeight: 0 }}>
              <textarea
                value={transcript}
                readOnly
                placeholder={t("结果将在这里实时流式填充或在完成后载入…", "Results will stream here in real time or load once finished...")}
                className="vsTtsEditor custom-scrollbar"
                style={{
                  padding: "0",
                  fontSize: "14px",
                  lineHeight: "1.8",
                  height: "100%",
                  color: "var(--text)"
                }}
              />
              {!transcript && !isBusy && (
                <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", color: "var(--muted)", pointerEvents: "none", opacity: 0.5 }}>
                  <div style={{ fontSize: "40px", marginBottom: "16px" }}>✍️</div>
                  <p style={{ fontSize: "14px", margin: 0, padding: "0 20px", textAlign: "center" }}>
                    {t("等待上传或输入远端音频地址以开始转写", "Upload a file or enter a remote audio URL to start transcription")}
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="vsCardSection border-top">
            <h3 className="vsCardSubTitle">{t("任务状态及后续", "Job status and next steps")}</h3>

            <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "12px", background: "var(--panel)", borderRadius: "12px", border: "1px solid var(--line)", marginBottom: "16px" }}>
              <div style={{ width: "10px", height: "10px", borderRadius: "50%", background: isBusy ? "var(--brand)" : transcript ? "#10b981" : "var(--muted)", animation: isBusy ? "pulse 2s infinite" : "none" }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ margin: 0, fontSize: "13px", fontWeight: "600", color: "var(--text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {statusMessage}
                </p>
              </div>
              {memorySaved && (
                <span style={{ fontSize: "10px", fontWeight: "700", background: "#10b981", color: "#fff", padding: "2px 6px", borderRadius: "999px" }}>
                  {t("已入记忆", "Saved to memory")}
                </span>
              )}
            </div>

            {infoMessage && (
              <div style={{ fontSize: "12px", color: "var(--muted)", background: "#fff9eb", padding: "10px 12px", borderRadius: "8px", border: "1px solid #fee2e2", marginBottom: "16px", fontStyle: "italic" }}>
                💡 {infoMessage}
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>{t("工具箱 (后续动作)", "Toolbox (next actions)")}</span>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                {[
                  t("发送到聊天", "Send to chat"),
                  t("生成摘要", "Generate summary"),
                  t("生成播客脚本", "Generate podcast script")
                ].map((action) => (
                  <button
                    key={action}
                    onClick={() => handleReservedAction(action)}
                    className="vsBtnSecondary"
                    style={{ height: "32px", fontSize: "12px", padding: "0 12px", borderStyle: "dashed" }}
                  >
                    {action}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
