import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import VoiceCallSettingsPopover from "./VoiceCallSettingsPopover";
import { createVoiceChatController } from "../test/factories";

const t = (zh: string, _en: string) => zh;

afterEach(() => {
  vi.restoreAllMocks();
  Object.defineProperty(window, "innerHeight", { writable: true, configurable: true, value: 768 });
});

function renderPopover(overrides: Parameters<typeof createVoiceChatController>[0] = {}) {
  const voiceChat = createVoiceChatController({
    voiceChatProvider: "DashScope",
    voiceChatModel: "qwen3.5-omni-plus-realtime",
    voiceChatModelOptions: ["qwen3.5-omni-plus-realtime", "qwen-audio-3.0-realtime-plus"],
    voiceChatRealtimeChoicesByProvider: [
      { provider: "DashScope", models: ["qwen3.5-omni-plus-realtime", "qwen-audio-3.0-realtime-plus"] },
      { provider: "Google", models: ["gemini-2.5-flash-native-audio-preview-12-2025"] },
    ],
    voiceChatVoice: "Tina",
    voiceChatVoiceLabel: "Tina · 甜甜 · 女声",
    voiceChatVoiceOptions: [
      { value: "Tina", label: "Tina · 甜甜 · 女声", description: "像温热的奶茶，甜甜的暖暖的" },
      { value: "Ethan", label: "Ethan · 晨煦 · 男声", description: "标准普通话，阳光温暖有活力" },
    ],
    ...overrides,
  });
  render(<VoiceCallSettingsPopover voiceChat={voiceChat} t={t} />);
  return voiceChat;
}

function openPanel() {
  fireEvent.click(screen.getByTitle("通话设置"));
  return screen.getByRole("dialog", { name: "通话设置" });
}

describe("VoiceCallSettingsPopover", () => {
  it("shows the current model and voice in the summary button", () => {
    renderPopover();
    const summary = screen.getByTitle("通话设置");
    expect(summary).toHaveTextContent("qwen3.5-omni-plus-realtime · Tina · 甜甜 · 女声");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("lists models with hints and voices with descriptions when opened", () => {
    renderPopover();
    openPanel();
    expect(screen.getByText("全模态实时")).toBeInTheDocument();
    expect(screen.getByText("Qwen-Audio 原生实时")).toBeInTheDocument();
    expect(screen.getByText("像温热的奶茶，甜甜的暖暖的")).toBeInTheDocument();
    // The selected voice row is marked.
    const selectedVoice = screen.getByText("Tina · 甜甜 · 女声").closest("button");
    expect(selectedVoice).toHaveClass("selected");
  });

  it("calls onVoiceChange and closes when a voice is picked", () => {
    const voiceChat = renderPopover();
    openPanel();
    fireEvent.click(screen.getByText("Ethan · 晨煦 · 男声"));
    expect(voiceChat.onVoiceChange).toHaveBeenCalledWith("Ethan");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("switches the model without closing the panel", () => {
    const voiceChat = renderPopover();
    openPanel();
    fireEvent.click(screen.getByText("qwen-audio-3.0-realtime-plus"));
    expect(voiceChat.onModelChange).toHaveBeenCalledWith("qwen-audio-3.0-realtime-plus");
    expect(voiceChat.onProviderChange).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("expands another provider and switches across providers", () => {
    const voiceChat = renderPopover();
    openPanel();
    // Only the active provider's models are visible initially.
    expect(screen.queryByText("gemini-2.5-flash-native-audio-preview-12-2025")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Google"));
    fireEvent.click(screen.getByText("gemini-2.5-flash-native-audio-preview-12-2025"));
    expect(voiceChat.onProviderChange).toHaveBeenCalledWith("Google");
    expect(voiceChat.onModelChange).toHaveBeenCalledWith("gemini-2.5-flash-native-audio-preview-12-2025");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("opens model management from the footer and closes the panel", () => {
    const voiceChat = createVoiceChatController();
    const onOpenSettings = vi.fn();
    render(<VoiceCallSettingsPopover voiceChat={voiceChat} t={t} onOpenSettings={onOpenSettings} />);
    openPanel();
    fireEvent.click(screen.getByText("管理模型"));
    expect(onOpenSettings).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("hides the translation section for non-live-translate models", () => {
    renderPopover();
    openPanel();
    expect(screen.queryByText("翻译")).not.toBeInTheDocument();
  });

  it("shows the translation section for live-translate models with mode toggle, preset pills, and swap button", () => {
    const voiceChat = renderPopover({
      voiceChatModel: "gemini-3.5-live-translate-preview",
      voiceChatLiveTranslate: true,
      voiceChatTranslationMode: "bidirectional",
      voiceChatSourceLanguageCode: "zh-Hans",
      voiceChatTargetLanguageCode: "en",
      voiceChatTargetLanguageOptions: [
        { value: "zh-Hans", label: "中文 / Chinese (Simplified) (zh-Hans)" },
        { value: "en", label: "英语 / English (en)" },
        { value: "ja", label: "日语 / Japanese (ja)" },
      ],
      voiceChatEchoTargetLanguage: true,
    });
    openPanel();
    expect(screen.getByText("翻译配置")).toBeInTheDocument();
    expect(screen.getByText("双向互翻 ⇄")).toBeInTheDocument();
    expect(screen.getByText("常用语对")).toBeInTheDocument();
    
    // Preset pill click
    fireEvent.click(screen.getByText("中 ⇄ 日"));
    expect(voiceChat.onPresetLanguagePairSelect).toHaveBeenCalledWith("zh-Hans", "ja");

    // Swap button click
    fireEvent.click(screen.getByTitle("一键颠倒语言"));
    expect(voiceChat.onSwapLanguages).toHaveBeenCalledTimes(1);

    // Mode switch click
    fireEvent.click(screen.getByText("单向翻译 →"));
    expect(voiceChat.onTranslationModeChange).toHaveBeenCalledWith("unidirectional");
  });

  it("toggles the echo switch in unidirectional mode", () => {
    const voiceChat = renderPopover({
      voiceChatLiveTranslate: true,
      voiceChatTranslationMode: "unidirectional",
      voiceChatEchoTargetLanguage: true,
    });
    openPanel();
    fireEvent.click(screen.getByRole("checkbox"));
    expect(voiceChat.onEchoTargetLanguageChange).toHaveBeenCalledWith(false);
  });

  it("closes on Escape and on outside click", () => {
    renderPopover();
    openPanel();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    openPanel();
    fireEvent.mouseDown(document.body);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("caps the panel height to the space above the button", () => {
    Object.defineProperty(window, "innerHeight", { writable: true, configurable: true, value: 500 });
    vi.spyOn(Element.prototype, "getBoundingClientRect").mockReturnValue({
      top: 380, bottom: 414, left: 0, right: 320, width: 320, height: 34, x: 0, y: 380, toJSON: () => ({}),
    } as DOMRect);
    renderPopover();
    const dialog = openPanel();
    // 380 - 16 margin = 364px of space above: more than the 70px below, so the
    // panel opens upward and is capped so its top never leaves the container.
    expect(dialog.className).not.toContain("below");
    expect(dialog.style.maxHeight).toBe("364px");
  });

  it("opens downward when there is more space below the button", () => {
    Object.defineProperty(window, "innerHeight", { writable: true, configurable: true, value: 500 });
    vi.spyOn(Element.prototype, "getBoundingClientRect").mockReturnValue({
      top: 60, bottom: 94, left: 0, right: 320, width: 320, height: 34, x: 0, y: 60, toJSON: () => ({}),
    } as DOMRect);
    renderPopover();
    const dialog = openPanel();
    expect(dialog.className).toContain("below");
    expect(dialog.style.maxHeight).toBe("390px");
  });

  it("does not open when disabled", () => {
    const voiceChat = createVoiceChatController();
    render(<VoiceCallSettingsPopover voiceChat={voiceChat} t={t} disabled />);
    const summary = screen.getByTitle("通话设置");
    expect(summary).toBeDisabled();
    fireEvent.click(summary);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
