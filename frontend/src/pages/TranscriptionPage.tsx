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

interface Props {
  onSendToChat?: (text: string) => void;
}

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

export const TranscriptionPage: React.FC<Props> = ({ onSendToChat }) => {
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
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const { history, historyBusy, refreshHistory, addOrUpdateJob, removeJob } = useTranscriptionHistory();

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

      if (result.job_id) {
        fetchTranscriptionJob(result.job_id, { refresh: false })
          .then(fullJob => {
            addOrUpdateJob(fullJob);
            setJob(fullJob);
          })
          .catch(err => {
            console.error("Failed to fetch sync job info:", err);
            const mockJob: TranscriptionJobResponse = {
              job_id: result.job_id || `sync_${Date.now()}`,
              mode: "sync",
              status: "completed",
              file_name: selectedFile.name,
              transcript: result.transcript,
              has_transcript: true,
              memory_saved: Boolean(result.memory_saved),
              updated_at: new Date().toISOString()
            };
            addOrUpdateJob(mockJob);
          });
      }

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

  function handleNewJob() {
    setSelectedFile(null);
    setRemoteUrl("");
    setTranscript("");
    setJob(null);
    setError(null);
    setInfoMessage("");
    setStatusMessage(t("等待上传或输入远端音频地址…", "Waiting for a local upload or remote audio URL..."));
    setMemorySaved(false);
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

  function handleSendToChat() {
    if (!transcript || !onSendToChat) {
      return;
    }
    const combined = `[Transcription Result]\n${transcript}`;
    onSendToChat(combined);
  }

  function handleReservedAction(action: string) {
    if (action === t("发送到聊天", "Send to chat") && onSendToChat) {
      handleSendToChat();
      return;
    }
    setInfoMessage(t(`${action} 即将开放，当前版本先保留入口。`, `${action} is coming soon. The entry is reserved for now.`));
  }

  const isBusy = isSyncBusy || isAsyncBusy || isPollingStatus(job?.status);
  const hasResult = transcript.length > 0 || isBusy;

  return (
    <section className="vsTtsWorkspace vsTranscribeWorkspace" style={{ height: "100%", width: "100%" }}>
      <div className="vsTtsLayout" style={{ display: "flex", height: "100%" }}>
        
        {/* ── Left Pane: Pure History Sidebar ── */}
        <div 
          className={`vsTtsSecondary vsTranscribeSidebar vsCollapsibleSidebar ${isSidebarOpen ? "open" : "collapsed"}`} 
          style={{ 
            borderRight: isSidebarOpen ? "1px solid var(--line)" : "none", 
            borderLeft: "none",
            width: isSidebarOpen ? "320px" : "0px",
            padding: isSidebarOpen ? "20px" : "0px",
            flexShrink: 0,
            overflow: "hidden",
            display: "flex",
            flexDirection: "column"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px", flexShrink: 0 }}>
            <h3 className="vsCardSubTitle" style={{ margin: 0, fontSize: "14px", fontWeight: "700" }}>
              {t("历史转写记录", "Transcription History")}
            </h3>
            <button
              onClick={() => refreshHistory()}
              className="vsBtnGhost"
              style={{ fontSize: "11px", padding: "2px 8px" }}
            >
              {t("刷新", "Refresh")}
            </button>
          </div>

          <div 
            className="custom-scrollbar" 
            style={{ 
              flex: 1, 
              overflowY: "auto", 
              display: "flex", 
              flexDirection: "column", 
              gap: "8px", 
              paddingRight: "4px" 
            }}
          >
            {historyBusy && history.length === 0 ? (
              <div style={{ textAlign: "center", padding: "20px 0", color: "var(--muted)", fontSize: "13px", fontStyle: "italic" }}>
                {t("加载历史记录中…", "Loading history...")}
              </div>
            ) : history.length === 0 ? (
              <div style={{ textAlign: "center", padding: "20px 0", color: "var(--muted)", fontSize: "13px", fontStyle: "italic" }}>
                {t("暂无转写记录", "No transcription history yet")}
              </div>
            ) : (
              history.slice(0, 20).map((item) => (
                <div
                  key={item.job_id}
                  className={`vsHistoryItem ${job?.job_id === item.job_id ? "active" : ""}`}
                  style={{ 
                    padding: "10px", 
                    background: job?.job_id === item.job_id ? "var(--brand-soft)" : "var(--surface)", 
                    border: job?.job_id === item.job_id ? "1px solid var(--brand)" : "1px solid var(--line)", 
                    borderRadius: "8px", 
                    cursor: "pointer", 
                    transition: "all 0.2s" 
                  }}
                  onClick={() => {
                    if (item.has_transcript) {
                      if (item.job_id.startsWith("sync_")) {
                        setError(new Error(t("找不到该转写记录。这是由于旧版本的不兼容记录，请重新进行转写或将其删除。", "Transcription job not found. This is a legacy record from an older version; please re-transcribe or delete it.")));
                        return;
                      }
                      setTranscript("");
                      fetchTranscriptionJob(item.job_id)
                        .then(j => {
                          setJob(j);
                          if (j.transcript) setTranscript(j.transcript);
                          setStatusMessage(buildJobStatusText(j, t));
                        })
                        .catch(err => {
                          console.error("Failed to load transcription record:", err);
                          setError(err instanceof Error ? err : new Error(t("载入历史记录失败。", "Failed to load history record.")));
                          setStatusMessage(t("历史记录载入失败。", "History record load failed."));
                        });
                    }
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span style={{ fontSize: "13px", fontWeight: "600", color: "var(--text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1, paddingRight: "8px" }}>
                      {item.file_name || t("未知文件", "Unknown file")}
                    </span>
                    <span style={{
                      fontSize: "9px",
                      fontWeight: "700",
                      padding: "1px 5px",
                      borderRadius: "4px",
                      textTransform: "uppercase",
                      background: item.status === "completed" ? "#ecfdf5" : item.status === "failed" ? "#fff1f2" : "#eef2ff",
                      color: item.status === "completed" ? "#10b981" : item.status === "failed" ? "#f43f5e" : "#6366f1"
                    }}>
                      {item.status}
                    </span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "4px" }}>
                    <span style={{ fontSize: "10px", color: "var(--muted)" }}>
                      {item.updated_at
                        ? new Date(item.updated_at).toLocaleString(language === "en-US" ? "en-US" : "zh-CN")
                        : t("未知时间", "Unknown time")}
                    </span>
                    {item.has_transcript && (
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontSize: "10px", fontWeight: "600", color: "var(--brand)", cursor: "pointer" }}>
                          {t("载入", "Load")}
                        </span>
                        <span 
                          style={{ fontSize: "10px", color: "#f43f5e", cursor: "pointer" }}
                          onClick={(e) => {
                            e.stopPropagation();
                            if (confirm(t("确定要删除这条记录吗？", "Are you sure you want to delete this record?"))) {
                              removeJob(item.job_id);
                            }
                          }}
                        >
                          {t("删除", "Delete")}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* ── Right Pane: Unified Main Workspace ── */}
        <div className="vsTtsPrimary vsTranscribeMain" style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
          
          {hasResult ? (
            /* State B: Editor layout when active transcript or busy processing */
            <>
              <header className="vsTtsPrimaryHeader" style={{ padding: "12px 24px", minHeight: "56px", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <button
                    type="button"
                    className="vsBtnSecondary"
                    onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                    style={{ height: "32px", width: "32px", padding: 0, display: "flex", alignItems: "center", justifyContent: "center", borderRadius: "6px" }}
                    title={isSidebarOpen ? t("隐藏历史", "Hide history") : t("显示历史", "Show history")}
                  >
                    {isSidebarOpen ? "◀" : "▶"}
                  </button>
                  <span style={{ fontSize: "14px", fontWeight: "600", color: "var(--text)" }}>
                    {t("音频转写结果", "Transcription Result")}
                  </span>
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    onClick={handleNewJob}
                    className="vsBtnSecondary"
                    style={{ height: "32px", fontSize: "13px", padding: "0 14px", borderColor: "var(--brand)", color: "var(--brand)", fontWeight: "600" }}
                  >
                    ✨ {t("新建转写", "New Job")}
                  </button>
                  <button
                    onClick={handleCopy}
                    disabled={!transcript}
                    className="vsBtnSecondary"
                    style={{ height: "32px", fontSize: "13px", padding: "0 14px" }}
                  >
                    {t("复制文本", "Copy text")}
                  </button>
                  <button
                    onClick={handleExport}
                    disabled={!transcript}
                    className="vsBtnSecondary"
                    style={{ height: "32px", fontSize: "13px", padding: "0 14px" }}
                  >
                    {t("导出为 TXT", "Export TXT")}
                  </button>
                </div>
              </header>

              <div className="vsTtsEditorWrap" style={{ flex: 1, minHeight: 0, padding: "16px 24px" }}>
                <div className="vsTtsEditorCard" style={{ height: "100%", width: "100%", position: "relative" }}>
                  <textarea
                    value={transcript}
                    readOnly
                    placeholder={t("结果将在这里实时流式填充或在完成后载入…", "Results will stream here in real time or load once finished...")}
                    className="vsTtsEditor custom-scrollbar"
                    style={{
                      padding: "24px",
                      fontSize: "15px",
                      lineHeight: "1.8",
                      height: "100%",
                      width: "100%",
                      color: "var(--text)",
                      border: "none",
                      background: "transparent",
                      resize: "none",
                      outline: "none"
                    }}
                  />
                  {!transcript && isBusy && (
                    <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", color: "var(--muted)" }}>
                      <div className="spinner" style={{ width: "40px", height: "40px", border: "4px solid var(--line)", borderTopColor: "var(--brand)", borderRadius: "50%", animation: "spin 1s linear infinite" }} />
                      <p style={{ marginTop: "16px", fontSize: "14px", fontWeight: "600" }}>{t("转写处理中，请稍候...", "Transcribing audio, please wait...")}</p>
                    </div>
                  )}
                </div>
              </div>

              <div className="vsTtsEditorFooter" style={{ display: "flex", flexDirection: "column", alignItems: "stretch", gap: "12px", background: "rgba(255, 251, 245, 0.45)", flexShrink: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "10px 14px", background: "var(--panel)", borderRadius: "10px", border: "1px solid var(--line)" }}>
                  <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: isBusy ? "var(--brand)" : transcript ? "#10b981" : "var(--muted)", animation: isBusy ? "pulse 2s infinite" : "none" }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ margin: 0, fontSize: "13px", fontWeight: "600", color: "var(--text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {statusMessage}
                    </p>
                  </div>
                  {memorySaved && (
                    <span style={{ fontSize: "10px", fontWeight: "700", background: "#10b981", color: "#fff", padding: "2px 8px", borderRadius: "999px" }}>
                      {t("已入记忆", "Saved to memory")}
                    </span>
                  )}
                </div>

                {infoMessage && (
                  <div style={{ fontSize: "12px", color: "#b45309", background: "#fef3c7", padding: "8px 12px", borderRadius: "8px", border: "1px solid #fde68a", display: "flex", alignItems: "center", gap: "6px" }}>
                    <span>💡</span>
                    <span style={{ flex: 1 }}>{infoMessage}</span>
                  </div>
                )}

                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "10px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                      {t("工具箱", "Toolbox")}:
                    </span>
                    <div style={{ display: "flex", gap: "8px" }}>
                      {[
                        t("发送到聊天", "Send to chat"),
                        t("生成摘要", "Generate summary"),
                        t("生成播客脚本", "Generate podcast script")
                      ].map((action) => (
                        <button
                          key={action}
                          onClick={() => handleReservedAction(action)}
                          className="vsBtnSecondary"
                          style={{ height: "30px", fontSize: "12px", padding: "0 12px", borderStyle: "dashed" }}
                        >
                          {action}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            /* State A: Centered file drag-drop & URL input area when empty */
            <div style={{ display: "flex", flex: 1, alignItems: "center", justifyContent: "center", padding: "40px 24px", background: "var(--panel)", overflowY: "auto" }}>
              <div 
                className="vsTtsEditorCard" 
                style={{ 
                  maxWidth: "580px", 
                  width: "100%", 
                  padding: "32px", 
                  display: "flex", 
                  flexDirection: "column", 
                  gap: "24px",
                  borderRadius: "16px",
                  border: "1px solid rgba(98, 76, 54, 0.12)",
                  boxShadow: "var(--shadow-md)"
                }}
              >
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: "36px", marginBottom: "8px" }}>🎙️</div>
                  <h2 style={{ fontSize: "20px", fontWeight: "700", margin: "0 0 6px 0", color: "var(--text)" }}>
                    {t("一键转写中心", "Audio Transcription Center")}
                  </h2>
                  <p style={{ fontSize: "13px", color: "var(--muted)", margin: 0, lineHeight: "1.5" }}>
                    {t("上传您的本地音频文件，或输入公开的网络音频链接，立即开始转写。", "Upload a local audio file or enter a public web link to begin transcription immediately.")}
                  </p>
                </div>

                <div 
                  className="vsModeTabs" 
                  style={{ 
                    display: "flex", 
                    gap: "8px",
                    background: "var(--surface)",
                    padding: "4px",
                    borderRadius: "8px",
                    flexShrink: 0
                  }}
                >
                  <button
                    type="button"
                    className={inputMode === "local" ? "vsBtnPrimary" : "vsBtnSecondary"}
                    onClick={() => setInputMode("local")}
                    style={{ flex: 1, height: "36px", fontSize: "12px", border: "none", boxShadow: inputMode === "local" ? "var(--shadow-sm)" : "none" }}
                  >
                    {t("本地音频", "Local audio")}
                  </button>
                  <button
                    type="button"
                    className={inputMode === "remote" ? "vsBtnPrimary" : "vsBtnSecondary"}
                    onClick={() => setInputMode("remote")}
                    style={{ flex: 1, height: "36px", fontSize: "12px", border: "none", boxShadow: inputMode === "remote" ? "var(--shadow-sm)" : "none" }}
                  >
                    {t("链式转写", "Async pipeline")}
                  </button>
                </div>

                {inputMode === "local" ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                    <AudioDropZone
                      onFileDrop={handleFileDrop}
                      selectedFile={selectedFile}
                      isProcessing={isBusy}
                      inputLabel={t("选择转写音频", "Choose transcription audio")}
                      readyText={t("已选中，可开始同步转写", "Selected. Ready for synchronous transcription")}
                      subText={t("支持 MP3, WAV, M4A, FLAC, AAC, OGG 格式 (最大 25MB)", "Supports MP3, WAV, M4A, FLAC, AAC, OGG formats (max 25MB)")}
                    />

                    <button
                      onClick={handleLocalTranscription}
                      disabled={!selectedFile || isBusy}
                      className="vsBtnPrimary"
                      style={{ width: "100%", height: "42px", fontSize: "14px", borderRadius: "8px" }}
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
                    <div className="vsField" style={{ gap: "6px" }}>
                      <label className="vsFieldLabel" style={{ fontSize: "13px", fontWeight: "600", color: "var(--text)" }}>
                        {t("音频 URL 地址", "Audio URL Address")}
                      </label>
                      <input
                        type="url"
                        value={remoteUrl}
                        onChange={handleRemoteUrlChange}
                        placeholder="https://example.com/meeting.wav"
                        disabled={isBusy}
                        className="vsInput"
                        style={{ width: "100%", height: "42px", borderRadius: "8px" }}
                      />
                      <span style={{ fontSize: "12px", color: "var(--muted)", lineHeight: "1.4" }}>
                        {t("支持直接可下载的公网 http/https/oss 格式音频。大文件推荐走此通道。", "Supports publicly accessible and downloadable http/https/oss links. Best for larger files.")}
                      </span>
                    </div>

                    <button
                      onClick={handleRemoteJobStart}
                      disabled={!remoteUrl.trim() || isBusy}
                      className="vsBtnPrimary"
                      style={{ width: "100%", height: "42px", fontSize: "14px", borderRadius: "8px" }}
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

                {error && <ErrorNotice message={error.message || String(error)} scope="Transcription" />}
              </div>
            </div>
          )}

        </div>
      </div>
    </section>
  );
};
