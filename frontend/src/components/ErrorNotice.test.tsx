import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ErrorNotice from "./ErrorNotice";

const BASE_ERROR = "AUTH_TOKEN_INVALID: Invalid token (request_id: req_test_001)";

function setClipboardWriteText(writeText: (value: string) => Promise<void>) {
  Object.defineProperty(globalThis.navigator, "clipboard", {
    value: { writeText },
    configurable: true
  });
}

describe("ErrorNotice", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it("renders null for empty message", () => {
    const { container } = render(<ErrorNotice message="" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders code and request_id meta", () => {
    render(<ErrorNotice message={BASE_ERROR} scope="chat" />);
    expect(screen.getByText("code: AUTH_TOKEN_INVALID")).toBeInTheDocument();
    expect(screen.getByText("request_id: req_test_001")).toBeInTheDocument();
  });

  it("renders request_id as log link when log url is configured", () => {
    vi.stubEnv("VITE_LOG_SEARCH_BASE_URL", "https://logs.example/search");
    render(<ErrorNotice message={BASE_ERROR} scope="chat" />);

    const link = screen.getByRole("link", { name: "request_id: req_test_001" });
    expect(link).toHaveAttribute("href", "https://logs.example/search?request_id=req_test_001");
  });

  it("copies request_id and resets button label after timeout", async () => {
    vi.useFakeTimers();
    const writeText = vi.fn().mockResolvedValue(undefined);
    setClipboardWriteText(writeText);

    render(<ErrorNotice message={BASE_ERROR} scope="chat" />);
    const button = screen.getByRole("button", { name: "Copy request_id" });
    await act(async () => {
      fireEvent.click(button);
      await Promise.resolve();
    });

    expect(writeText).toHaveBeenCalledWith("req_test_001");
    expect(screen.getByRole("button", { name: "Copied" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("request_id copied.");

    await act(async () => {
      vi.advanceTimersByTime(1500);
    });
    expect(screen.getByRole("button", { name: "Copy request_id" })).toBeInTheDocument();
  });

  it("shows fallback text when clipboard copy fails", async () => {
    const writeText = vi.fn().mockRejectedValue(new Error("denied"));
    setClipboardWriteText(writeText);

    render(<ErrorNotice message={BASE_ERROR} scope="chat" />);
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Copy request_id" }));
      await Promise.resolve();
    });

    expect(screen.getByRole("status")).toHaveTextContent("Copy failed. Please copy manually.");
  });

  it("copies diagnostics payload", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-05T13:14:15.000Z"));
    const writeText = vi.fn().mockResolvedValue(undefined);
    setClipboardWriteText(writeText);

    render(
      <ErrorNotice
        message={BASE_ERROR}
        scope="chat"
        context={{
          provider: "DashScope",
          model: "qwen-plus",
          backend_auth_enabled: false
        }}
      />
    );
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Copy diagnostics" }));
      await Promise.resolve();
    });

    expect(writeText).toHaveBeenCalledTimes(1);
    const payload = writeText.mock.calls[0][0] as string;
    expect(payload).toContain("scope=chat");
    expect(payload).toContain("path=/");
    expect(payload).toMatch(/frontend_version=\S+/);
    expect(payload).toContain("user_agent=");
    expect(payload).toContain("code=AUTH_TOKEN_INVALID");
    expect(payload).toContain("request_id=req_test_001");
    expect(payload).toContain("log_search_url=N/A");
    expect(payload).toContain("context.model=qwen-plus");
    expect(payload).toContain("context.provider=DashScope");
    expect(payload).toContain("context.backend_auth_enabled=false");
    expect(payload).toContain("generated_at=2026-03-05T13:14:15.000Z");
    expect(screen.getByRole("status")).toHaveTextContent("Diagnostic details copied.");
  });

  it("toggles diagnostic details panel", async () => {
    render(<ErrorNotice message={BASE_ERROR} scope="chat" />);
    expect(screen.queryByText("Diagnostic details")).not.toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Show details" }));
    });
    expect(screen.getByText("Diagnostic details")).toBeInTheDocument();
    expect(screen.getByText(/code=AUTH_TOKEN_INVALID/)).toBeInTheDocument();
    expect(screen.getByText(/scope=chat/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Hide details" })).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Hide details" }));
    });
    expect(screen.queryByText("Diagnostic details")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Show details" })).toBeInTheDocument();
  });

  it("copies markdown issue template payload", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-05T15:16:17.000Z"));
    const writeText = vi.fn().mockResolvedValue(undefined);
    setClipboardWriteText(writeText);

    render(
      <ErrorNotice
        message={BASE_ERROR}
        scope="chat"
        context={{
          provider: "DashScope",
          model: "qwen-plus",
          backend_auth_enabled: false
        }}
      />
    );
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Copy issue template" }));
      await Promise.resolve();
    });

    expect(writeText).toHaveBeenCalledTimes(1);
    const payload = writeText.mock.calls[0][0] as string;
    expect(payload).toContain("## VoiceSpirit Error Report");
    expect(payload).toContain("- generated_at: 2026-03-05T15:16:17.000Z");
    expect(payload).toContain("- scope: chat");
    expect(payload).toContain("- path: /");
    expect(payload).toMatch(/- frontend_version: \S+/);
    expect(payload).toContain("- user_agent: ");
    expect(payload).toContain("- code: AUTH_TOKEN_INVALID");
    expect(payload).toContain("- request_id: req_test_001");
    expect(payload).toContain("### Context");
    expect(payload).toContain("- model=qwen-plus");
    expect(payload).toContain("- backend_auth_enabled=false");
    expect(payload).toContain("- provider=DashScope");
    expect(screen.getByRole("status")).toHaveTextContent("Issue template copied.");
  });
});
