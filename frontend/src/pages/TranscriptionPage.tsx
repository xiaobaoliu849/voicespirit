import React, { useEffect, useState, useMemo } from "react";
import {
  createTranscriptionJobFromUrl,
  fetchTranscriptionJob,
  transcribeAudio,
  type TranscriptionJobResponse,
} from "../api";
import ErrorNotice from "../components/ErrorNotice";
import { TranscriptionCard } from "../components/TranscriptionCard";
import { NewTranscriptionModal } from "../components/NewTranscriptionModal";
import { useTranscriptionHistory } from "../hooks/useTranscriptionHistory";
import { useI18n } from "../i18n";

const ASYNC_POLL_INTERVAL_MS = 2500;

interface Props {
  onSendToChat?: (text: string) => void;
}

type ViewMode = "library" | "detail";

function isPollingStatus(status: string | null | undefined): boolean {
  return status === "submitted" || status === "running";
}

function buildJobStatusText(
  job: TranscriptionJobResponse,
  t: (zh: string, en: string) => string
): string {
  if (job.status === "completed") {
    return job.memory_saved
      ? t(
          "异步转写完成，摘要已写入长期记忆。",
          "Async transcription completed and the summary was saved to long-term memory."
        )
      : t("异步转写完成。", "Async transcription completed.");
  }
  if (job.status === "failed") {
    return job.error || t("异步转写失败。", "Async transcription failed.");
  }
  if (job.status === "running") {
    return t(
      `远端任务运行中，正在拉取结果… (${job.job_id})`,
      `Remote job is running. Fetching results... (${job.job_id})`
    );
  }
  if (job.status === "submitted") {
    return t(
      `远端任务已提交，正在轮询状态… (${job.job_id})`,
      `Remote job submitted. Polling status... (${job.job_id})`
    );
  }
  if (job.status === "uploaded") {
    return (
      job.error ||
      t(
        "文件已接收，等待后续处理。",
        "File received. Waiting for further processing."
      )
    );
  }
  return t(`任务状态: ${job.status}`, `Job status: ${job.status}`);
}

export const TranscriptionPage: React.FC<Props> = ({ onSendToChat }) => {
  const { t, language } = useI18n();

  // ── View state ──
  const [viewMode, setViewMode] = useState<ViewMode>("library");
  const [showNewModal, setShowNewModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<"all" | "completed" | "running" | "failed">("all");

  // ── Job state ──
  const [transcript, setTranscript] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [job, setJob] = useState<TranscriptionJobResponse | null>(null);
  const [memorySaved, setMemorySaved] = useState(false);
  const [isSyncBusy, setIsSyncBusy] = useState(false);
  const [isAsyncBusy, setIsAsyncBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [modalError, setModalError] = useState<Error | null>(null);
  const [infoMessage, setInfoMessage] = useState("");
  const [detailLoading, setDetailLoading] = useState(false);

  const {
    history,
    historyBusy,
    refreshHistory,
    addOrUpdateJob,
    removeJob,
    setActiveFilter: setHistoryFilter,
  } = useTranscriptionHistory();

  // ── Polling for active async jobs ──
  useEffect(() => {
    if (!job?.job_id || !isPollingStatus(job.status)) {
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        const nextJob = await fetchTranscriptionJob(job.job_id, {
          refresh: true,
        });
        if (cancelled) return;
        setJob(nextJob);
        addOrUpdateJob(nextJob);
        setStatusMessage(buildJobStatusText(nextJob, t));
        setMemorySaved(Boolean(nextJob.memory_saved));
        if (nextJob.transcript) {
          setTranscript(nextJob.transcript);
        }
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof Error
            ? err
            : new Error(t("转写任务刷新失败。", "Failed to refresh transcription job."))
        );
        setStatusMessage(t("异步任务刷新失败。", "Async job refresh failed."));
      }
    }, ASYNC_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [job, addOrUpdateJob, t]);

  // ── Filtered & searched history ──
  const filteredHistory = useMemo(() => {
    let items = history;
    if (activeFilter !== "all") {
      items = items.filter((item) => {
        if (activeFilter === "running")
          return (
            item.status === "running" ||
            item.status === "submitted" ||
            item.status === "uploaded"
          );
        return item.status === activeFilter;
      });
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      items = items.filter(
        (item) =>
          (item.file_name || "").toLowerCase().includes(q) ||
          (item.error || "").toLowerCase().includes(q)
      );
    }
    return items;
  }, [history, activeFilter, searchQuery]);

  // ── Handlers ──
  async function handleLocalTranscription(file: File) {
    setModalError(null);
    setError(null);
    setJob(null);
    setTranscript("");
    setIsSyncBusy(true);
    setStatusMessage(
      t("正在上传并同步转写本地音频…", "Uploading and transcribing local audio...")
    );

    try {
      const result = await transcribeAudio(file);
      setTranscript(result.transcript);
      setMemorySaved(Boolean(result.memory_saved));
      setShowNewModal(false);
      setViewMode("detail");

      if (result.job_id) {
        fetchTranscriptionJob(result.job_id, { refresh: false })
          .then((fullJob) => {
            addOrUpdateJob(fullJob);
            setJob(fullJob);
          })
          .catch((err) => {
            console.error("Failed to fetch sync job info:", err);
            const mockJob: TranscriptionJobResponse = {
              job_id: result.job_id || `sync_${Date.now()}`,
              mode: "sync",
              status: "completed",
              file_name: file.name,
              transcript: result.transcript,
              has_transcript: true,
              memory_saved: Boolean(result.memory_saved),
              updated_at: new Date().toISOString(),
            };
            addOrUpdateJob(mockJob);
          });
      }

      setStatusMessage(
        result.memory_saved
          ? t(
              "同步转写完成，摘要已写入长期记忆。",
              "Synchronous transcription completed and the summary was saved to long-term memory."
            )
          : t("同步转写完成。", "Synchronous transcription completed.")
      );
    } catch (err) {
      setModalError(
        err instanceof Error
          ? err
          : new Error(t("本地音频转写失败。", "Local audio transcription failed."))
      );
      setStatusMessage(t("同步转写失败。", "Synchronous transcription failed."));
    } finally {
      setIsSyncBusy(false);
    }
  }

  async function handleRemoteJobStart(url: string) {
    setModalError(null);
    setError(null);
    setIsAsyncBusy(true);
    setTranscript("");
    setStatusMessage(
      t("正在创建远端异步转写任务…", "Creating remote async transcription job...")
    );

    try {
      const createdJob = await createTranscriptionJobFromUrl(url);
      setJob(createdJob);
      addOrUpdateJob(createdJob);
      setStatusMessage(buildJobStatusText(createdJob, t));
      setMemorySaved(Boolean(createdJob.memory_saved));
      setShowNewModal(false);
      setViewMode("detail");
      if (createdJob.transcript) {
        setTranscript(createdJob.transcript);
      }
    } catch (err) {
      setModalError(
        err instanceof Error
          ? err
          : new Error(
              t(
                "远端异步任务创建失败。",
                "Failed to create remote async job."
              )
            )
      );
      setStatusMessage(t("异步任务创建失败。", "Async job creation failed."));
    } finally {
      setIsAsyncBusy(false);
    }
  }

  async function handleCardClick(item: typeof history[0]) {
    if (!item.has_transcript && item.status !== "completed") {
      // For running/submitted jobs, just show status
      setJob(null);
      setTranscript("");
      setError(null);
      setDetailLoading(true);
      setViewMode("detail");
      try {
        const j = await fetchTranscriptionJob(item.job_id, { refresh: true });
        setJob(j);
        addOrUpdateJob(j);
        if (j.transcript) setTranscript(j.transcript);
        setStatusMessage(buildJobStatusText(j, t));
        setMemorySaved(Boolean(j.memory_saved));
      } catch (err) {
        setError(
          err instanceof Error
            ? err
            : new Error(t("载入记录失败。", "Failed to load record."))
        );
      } finally {
        setDetailLoading(false);
      }
      return;
    }

    if (item.job_id.startsWith("sync_")) {
      setError(
        new Error(
          t(
            "找不到该转写记录。这是由于旧版本的不兼容记录，请重新进行转写或将其删除。",
            "Transcription job not found. This is a legacy record from an older version; please re-transcribe or delete it."
          )
        )
      );
      return;
    }

    setJob(null);
    setTranscript("");
    setError(null);
    setDetailLoading(true);
    setViewMode("detail");

    try {
      const j = await fetchTranscriptionJob(item.job_id);
      setJob(j);
      if (j.transcript) setTranscript(j.transcript);
      setStatusMessage(buildJobStatusText(j, t));
      setMemorySaved(Boolean(j.memory_saved));
    } catch (err) {
      setError(
        err instanceof Error
          ? err
          : new Error(t("载入历史记录失败。", "Failed to load history record."))
      );
      setStatusMessage(t("历史记录载入失败。", "History record load failed."));
    } finally {
      setDetailLoading(false);
    }
  }

  function handleBackToLibrary() {
    setViewMode("library");
    setJob(null);
    setTranscript("");
    setError(null);
    setInfoMessage("");
    setStatusMessage("");
    setMemorySaved(false);
  }

  async function handleCopy() {
    if (!transcript) return;
    try {
      await navigator.clipboard.writeText(transcript);
      setInfoMessage(t("转写文本已复制到剪贴板。", "Transcript copied to clipboard."));
    } catch {
      setInfoMessage(t("复制失败，请手动复制。", "Copy failed. Please copy it manually."));
    }
  }

  function handleExport() {
    if (!transcript) return;
    const blob = new Blob([transcript], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "transcript.txt";
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
    setInfoMessage(
      t("转写文本已导出为 transcript.txt。", "Transcript exported as transcript.txt.")
    );
  }

  function handleSendToChat() {
    if (!transcript || !onSendToChat) return;
    const combined = `[Transcription Result]\n${transcript}`;
    onSendToChat(combined);
  }

  function handleReservedAction(action: string) {
    if (action === t("发送到聊天", "Send to chat") && onSendToChat) {
      handleSendToChat();
      return;
    }
    setInfoMessage(
      t(
        `${action} 即将开放，当前版本先保留入口。`,
        `${action} is coming soon. The entry is reserved for now.`
      )
    );
  }

  function handleFilterChange(filter: "all" | "completed" | "running" | "failed") {
    setActiveFilter(filter);
    setHistoryFilter(filter);
  }

  const isBusy = isSyncBusy || isAsyncBusy || isPollingStatus(job?.status);

  // ═══════════════════════════════════════════════════
  // RENDER: Detail / Reader View
  // ═══════════════════════════════════════════════════
  if (viewMode === "detail") {
    const fileName = job?.file_name || t("转写详情", "Transcription Detail");
    const detailStatusClass =
      job?.status === "completed"
        ? "completed"
        : job?.status === "failed"
        ? "failed"
        : "";

    return (
      <section className="vsTranscribeDetail">
        {/* Header */}
        <div className="vsTranscribeDetailHeader">
          <button
            className="vsTranscribeBackBtn"
            onClick={handleBackToLibrary}
            title={t("返回列表", "Back to list")}
          >
            ←
          </button>
          <div className="vsTranscribeDetailInfo">
            <h2 className="vsTranscribeDetailFileName">{fileName}</h2>
            <div className="vsTranscribeDetailMeta">
              {job?.updated_at
                ? new Date(job.updated_at).toLocaleString(
                    language === "en-US" ? "en-US" : "zh-CN"
                  )
                : ""}
              {job?.mode && (
                <span style={{ marginLeft: 8, opacity: 0.7 }}>
                  ({job.mode === "sync" ? t("同步", "Sync") : t("异步", "Async")})
                </span>
              )}
            </div>
          </div>
          <div className="vsTranscribeDetailActions">
            <button
              onClick={handleCopy}
              disabled={!transcript}
              className="vsBtnSecondary"
              style={{ height: 34, fontSize: 13, padding: "0 14px" }}
            >
              {t("复制", "Copy")}
            </button>
            <button
              onClick={handleExport}
              disabled={!transcript}
              className="vsBtnSecondary"
              style={{ height: 34, fontSize: 13, padding: "0 14px" }}
            >
              {t("导出 TXT", "Export TXT")}
            </button>
          </div>
        </div>

        {/* Audio Player */}
        {job?.source_url && (
          <div style={{ padding: "16px 24px 0", flexShrink: 0, display: "flex", justifyContent: "center" }}>
            <audio 
              controls 
              src={job.source_url} 
              style={{ width: "100%", maxWidth: "720px", height: "40px", borderRadius: "8px", outline: "none" }}
              controlsList="nodownload"
            />
          </div>
        )}

        {/* Status Banner */}
        {statusMessage && (
          <div className={`vsTranscribeStatusBanner ${detailStatusClass}`}>
            <div
              className="vsTranscribeStatusDot"
              style={{
                background: isBusy
                  ? "var(--brand)"
                  : transcript
                  ? "#10b981"
                  : "var(--muted)",
                animation: isBusy ? "pulsingDot 2s infinite" : "none",
              }}
            />
            <span className="vsTranscribeStatusText">{statusMessage}</span>
            {memorySaved && (
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  background: "#10b981",
                  color: "#fff",
                  padding: "2px 8px",
                  borderRadius: 999,
                  flexShrink: 0,
                }}
              >
                {t("已入记忆", "Saved to memory")}
              </span>
            )}
          </div>
        )}

        {/* Transcript Content */}
        <div className="vsTranscribeDetailContent custom-scrollbar">
          {detailLoading ? (
            <div className="vsTranscribeDetailTranscript loading">
              <div
                className="spinner"
                style={{
                  width: 40,
                  height: 40,
                  border: "4px solid var(--line)",
                  borderTopColor: "var(--brand)",
                  borderRadius: "50%",
                }}
              />
              <p style={{ fontSize: 14, fontWeight: 600 }}>
                {t("加载中…", "Loading...")}
              </p>
            </div>
          ) : transcript ? (
            <div className="vsTranscribeDetailTranscript">{transcript}</div>
          ) : isBusy ? (
            <div className="vsTranscribeDetailTranscript loading">
              <div
                className="spinner"
                style={{
                  width: 40,
                  height: 40,
                  border: "4px solid var(--line)",
                  borderTopColor: "var(--brand)",
                  borderRadius: "50%",
                }}
              />
              <p style={{ fontSize: 14, fontWeight: 600 }}>
                {t("转写处理中，请稍候...", "Transcribing audio, please wait...")}
              </p>
            </div>
          ) : (
            <div className="vsTranscribeDetailTranscript loading">
              <p style={{ fontSize: 14 }}>
                {t("暂无转写内容", "No transcript content available")}
              </p>
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div style={{ padding: "0 24px 12px" }}>
            <ErrorNotice message={error.message || String(error)} scope="Transcription" />
          </div>
        )}

        {/* Info Message */}
        {infoMessage && (
          <div
            style={{
              margin: "0 24px 12px",
              fontSize: 12,
              color: "#b45309",
              background: "#fef3c7",
              padding: "8px 12px",
              borderRadius: 8,
              border: "1px solid #fde68a",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <span>💡</span>
            <span style={{ flex: 1 }}>{infoMessage}</span>
          </div>
        )}

        {/* Footer Toolbox */}
        <div className="vsTranscribeDetailFooter">
          <span className="vsTranscribeFooterLabel">
            {t("工具箱", "Toolbox")}:
          </span>
          {[
            t("发送到聊天", "Send to chat"),
            t("生成摘要", "Generate summary"),
            t("生成播客脚本", "Generate podcast script"),
          ].map((action) => (
            <button
              key={action}
              onClick={() => handleReservedAction(action)}
              className="vsBtnSecondary"
              style={{
                height: 30,
                fontSize: 12,
                padding: "0 12px",
                borderStyle: "dashed",
              }}
            >
              {action}
            </button>
          ))}
        </div>
      </section>
    );
  }

  // ═══════════════════════════════════════════════════
  // RENDER: Library / Grid View (default)
  // ═══════════════════════════════════════════════════
  const filters = [
    { key: "all" as const, label: t("全部", "All") },
    { key: "completed" as const, label: t("已完成", "Completed") },
    { key: "running" as const, label: t("进行中", "In Progress") },
    { key: "failed" as const, label: t("失败", "Failed") },
  ];

  return (
    <section className="vsTranscribeLibrary">
      {/* Toolbar */}
      <div className="vsTranscribeToolbar">
        {/* Search */}
        <div className="vsTranscribeSearchBox">
          <span className="vsTranscribeSearchIcon">🔍</span>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t("搜索转写记录…", "Search transcriptions...")}
          />
        </div>

        {/* Filter Tabs */}
        <div className="vsTranscribeFilterTabs">
          {filters.map((f) => (
            <button
              key={f.key}
              type="button"
              className={`vsTranscribeFilterTab ${activeFilter === f.key ? "active" : ""}`}
              onClick={() => handleFilterChange(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Actions */}
        <div className="vsTranscribeToolbarActions">
          <button
            onClick={() => refreshHistory()}
            className="vsBtnGhost"
            style={{ fontSize: 12, padding: "6px 12px" }}
            title={t("刷新", "Refresh")}
          >
            ↻ {t("刷新", "Refresh")}
          </button>
          <button
            onClick={() => {
              setModalError(null);
              setShowNewModal(true);
            }}
            className="vsBtnPrimary"
            style={{
              height: 36,
              fontSize: 13,
              padding: "0 18px",
              borderRadius: 10,
              fontWeight: 600,
            }}
          >
            ✨ {t("新建转写", "New Transcription")}
          </button>
        </div>
      </div>

      {/* Card Grid */}
      <div className="vsTranscribeGridWrap custom-scrollbar">
        {historyBusy && history.length === 0 ? (
          <div className="vsTranscribeEmpty">
            <div className="vsTranscribeEmptyIcon">
              <div
                className="spinner"
                style={{
                  width: 32,
                  height: 32,
                  border: "3px solid var(--line)",
                  borderTopColor: "var(--brand)",
                  borderRadius: "50%",
                }}
              />
            </div>
            <p className="vsTranscribeEmptyDesc">
              {t("加载历史记录中…", "Loading transcription history...")}
            </p>
          </div>
        ) : filteredHistory.length === 0 ? (
          <div className="vsTranscribeEmpty">
            <div className="vsTranscribeEmptyIcon">🎙️</div>
            <h3 className="vsTranscribeEmptyTitle">
              {searchQuery || activeFilter !== "all"
                ? t("没有匹配的记录", "No matching records")
                : t("暂无转写记录", "No transcriptions yet")}
            </h3>
            <p className="vsTranscribeEmptyDesc">
              {searchQuery || activeFilter !== "all"
                ? t(
                    "尝试调整搜索条件或筛选条件。",
                    "Try adjusting your search or filter criteria."
                  )
                : t(
                    "点击「新建转写」上传音频文件或输入远程 URL，开始你的第一次转写。",
                    "Click 'New Transcription' to upload audio or enter a remote URL and start your first transcription."
                  )}
            </p>
            {!searchQuery && activeFilter === "all" && (
              <button
                onClick={() => {
                  setModalError(null);
                  setShowNewModal(true);
                }}
                className="vsBtnPrimary"
                style={{
                  height: 40,
                  fontSize: 14,
                  padding: "0 24px",
                  borderRadius: 10,
                  marginTop: 8,
                }}
              >
                ✨ {t("新建转写", "New Transcription")}
              </button>
            )}
          </div>
        ) : (
          <div className="vsTranscribeGrid">
            {filteredHistory.map((item) => (
              <TranscriptionCard
                key={item.job_id}
                item={item}
                isActive={job?.job_id === item.job_id}
                onClick={() => handleCardClick(item)}
                onDelete={(e) => {
                  e.stopPropagation();
                  if (
                    confirm(
                      t(
                        "确定要删除这条记录吗？",
                        "Are you sure you want to delete this record?"
                      )
                    )
                  ) {
                    removeJob(item.job_id);
                  }
                }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Global Error */}
      {error && (
        <div style={{ padding: "0 24px 12px" }}>
          <ErrorNotice message={error.message || String(error)} scope="Transcription" />
        </div>
      )}

      {/* New Transcription Modal */}
      <NewTranscriptionModal
        open={showNewModal}
        onClose={() => setShowNewModal(false)}
        onLocalTranscribe={handleLocalTranscription}
        onRemoteSubmit={handleRemoteJobStart}
        isBusy={isBusy}
        isSyncBusy={isSyncBusy}
        isAsyncBusy={isAsyncBusy}
        error={modalError}
      />
    </section>
  );
};
