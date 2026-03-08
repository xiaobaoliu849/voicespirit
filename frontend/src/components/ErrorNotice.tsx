import { useEffect, useState } from "react";
import { buildErrorHints, parseErrorCode, parseRequestId } from "../error_hints";

type ErrorNoticeProps = {
  message: string;
  scope?: string;
  context?: Record<string, string | number | boolean | null | undefined>;
};

type ToastState = {
  tone: "ok" | "fail";
  text: string;
};

function buildLogSearchUrl(baseUrl: string, requestId: string): string | null {
  const base = baseUrl.trim();
  if (!base || !requestId) {
    return null;
  }
  const encoded = encodeURIComponent(requestId);
  if (base.includes("{request_id}")) {
    return base.replaceAll("{request_id}", encoded);
  }
  try {
    const origin =
      typeof window !== "undefined" && window.location?.origin
        ? window.location.origin
        : "http://localhost";
    const url = new URL(base, origin);
    url.searchParams.set("request_id", requestId);
    return url.toString();
  } catch {
    const separator = base.includes("?") ? "&" : "?";
    return `${base}${separator}request_id=${encoded}`;
  }
}

export default function ErrorNotice({ message, scope = "", context }: ErrorNoticeProps) {
  const text = String(message || "").trim();
  const [copyState, setCopyState] = useState<"idle" | "ok">("idle");
  const [toast, setToast] = useState<ToastState | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);

  useEffect(() => {
    setCopyState("idle");
    setToast(null);
    setDetailsOpen(false);
  }, [text]);

  useEffect(() => {
    if (copyState !== "ok") {
      return;
    }
    const timer = window.setTimeout(() => {
      setCopyState("idle");
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [copyState]);

  useEffect(() => {
    if (!toast) {
      return;
    }
    const timer = window.setTimeout(() => {
      setToast(null);
    }, 1800);
    return () => window.clearTimeout(timer);
  }, [toast]);

  if (!text) {
    return null;
  }

  const hints = buildErrorHints(text);
  const code = parseErrorCode(text);
  const requestId = parseRequestId(text);
  const scopeLabel = scope.trim() || "unknown";
  const frontendVersion =
    typeof __APP_VERSION__ === "string" && __APP_VERSION__.trim()
      ? __APP_VERSION__.trim()
      : String(import.meta.env.VITE_APP_VERSION || "N/A");
  const logSearchBaseUrl = String(import.meta.env.VITE_LOG_SEARCH_BASE_URL || "");
  const pathname =
    typeof window !== "undefined" && window.location?.pathname
      ? window.location.pathname
      : "N/A";
  const userAgent =
    typeof navigator !== "undefined" && navigator.userAgent
      ? navigator.userAgent
      : "N/A";
  const logSearchUrl = buildLogSearchUrl(logSearchBaseUrl, requestId);
  const contextLines = Object.entries(context || {})
    .filter(([, value]) => {
      if (value === null || value === undefined) {
        return false;
      }
      return String(value).trim() !== "";
    })
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, value]) => `context.${key}=${String(value).trim()}`);
  const contextEntries = contextLines.map((line) => line.replace(/^context\./, ""));
  const diagnostics = [
    `scope=${scopeLabel}`,
    `path=${pathname}`,
    `frontend_version=${frontendVersion}`,
    `user_agent=${userAgent}`,
    `code=${code || "N/A"}`,
    `request_id=${requestId || "N/A"}`,
    `log_search_url=${logSearchUrl || "N/A"}`,
    `message=${text}`,
    ...contextLines,
    `hints=${hints.length ? hints.join(" | ") : "N/A"}`
  ].join("\n");

  function buildIssueTemplate(generatedAt: string): string {
    const hintLines = hints.length
      ? hints.map((tip, idx) => `${idx + 1}. ${tip}`).join("\n")
      : "1. N/A";
    const contextBlock = contextEntries.length
      ? contextEntries.map((item) => `- ${item}`).join("\n")
      : "- N/A";
    return [
      "## VoiceSpirit 错误报告",
      `- 生成时间: ${generatedAt}`,
      `- 模块: ${scopeLabel}`,
      `- 页面路径: ${pathname}`,
      `- 前端版本: ${frontendVersion}`,
      `- 浏览器信息: ${userAgent}`,
      `- 错误代码: ${code || "N/A"}`,
      `- 请求 ID: ${requestId || "N/A"}`,
      `- 日志链接: ${logSearchUrl || "N/A"}`,
      "",
      "### 错误信息",
      "```text",
      text,
      "```",
      "",
      "### 上下文",
      contextBlock,
      "",
      "### 建议处理方式",
      hintLines
    ].join("\n");
  }

  async function copyText(value: string): Promise<boolean> {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
      } else {
        throw new Error("clipboard api unavailable");
      }
      return true;
    } catch {
      return false;
    }
  }

  async function handleCopyRequestId() {
    if (!requestId) {
      return;
    }
    const ok = await copyText(requestId);
    if (ok) {
      setCopyState("ok");
      setToast({ tone: "ok", text: "请求 ID 已复制。" });
      return;
    }
    setToast({ tone: "fail", text: "复制失败，请手动复制。" });
  }

  async function handleCopyDiagnostics() {
    const payload = `${diagnostics}\ngenerated_at=${new Date().toISOString()}`;
    const ok = await copyText(payload);
    if (ok) {
      setToast({ tone: "ok", text: "诊断信息已复制。" });
      return;
    }
    setToast({ tone: "fail", text: "复制失败，请手动复制。" });
  }

  async function handleCopyIssueTemplate() {
    const payload = buildIssueTemplate(new Date().toISOString());
    const ok = await copyText(payload);
    if (ok) {
      setToast({ tone: "ok", text: "问题模板已复制。" });
      return;
    }
    setToast({ tone: "fail", text: "复制失败，请手动复制。" });
  }

  return (
    <>
      <p className="error">{text}</p>
      {code || requestId || text ? (
        <div className="errorMeta">
          {code ? <span className="errorMetaTag">code: {code}</span> : null}
          {requestId ? (
            logSearchUrl ? (
              <a
                href={logSearchUrl}
                target="_blank"
                rel="noreferrer"
                className="errorMetaTag errorMetaTagLink"
              >
                request_id: {requestId}
              </a>
            ) : (
              <span className="errorMetaTag">request_id: {requestId}</span>
            )
          ) : null}
          {requestId ? (
            <button
              type="button"
              className="ghost errorCopyBtn"
              onClick={handleCopyRequestId}
            >
              {copyState === "ok" ? "已复制" : "复制请求 ID"}
            </button>
          ) : null}
          <button
            type="button"
            className="ghost errorCopyBtn"
            onClick={handleCopyDiagnostics}
          >
            复制诊断信息
          </button>
          <button
            type="button"
            className="ghost errorCopyBtn"
            onClick={handleCopyIssueTemplate}
          >
            复制问题模板
          </button>
          <button
            type="button"
            className="ghost errorCopyBtn"
            onClick={() => setDetailsOpen((value) => !value)}
          >
            {detailsOpen ? "隐藏详情" : "查看详情"}
          </button>
        </div>
      ) : null}
      {toast ? (
        <p className={`errorToast ${toast.tone === "ok" ? "ok" : "fail"}`} role="status">
          {toast.text}
        </p>
      ) : null}
      {detailsOpen ? (
        <div className="errorDetails">
          <p>诊断信息</p>
          <pre>{diagnostics}</pre>
        </div>
      ) : null}
      {hints.length > 0 ? (
        <div className="errorHints">
          <p>建议处理方式</p>
          <ul>
            {hints.map((tip, idx) => (
              <li key={`error-hint-${idx}`}>{tip}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </>
  );
}
