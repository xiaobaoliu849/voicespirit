import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useTranslate from "./useTranslate";
import { createFormatErrorMessageStub } from "../test/factories";
import { translateText } from "../api";

vi.mock("../api", () => ({
  translateText: vi.fn()
}));

describe("useTranslate", () => {
  beforeEach(() => {
    vi.mocked(translateText).mockReset();
    Object.defineProperty(globalThis.navigator, "clipboard", {
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
        readText: vi.fn().mockResolvedValue("Clipboard text")
      },
      configurable: true
    });
    Object.defineProperty(globalThis, "speechSynthesis", {
      value: {
        speak: vi.fn(),
        cancel: vi.fn()
      },
      configurable: true
    });
    Object.defineProperty(globalThis, "SpeechSynthesisUtterance", {
      value: class {
        text: string;
        lang = "";
        onend: (() => void) | null = null;
        onerror: (() => void) | null = null;

        constructor(text: string) {
          this.text = text;
        }
      },
      configurable: true
    });
  });

  it("swaps languages and reuses the translated result as the next input", () => {
    const formatErrorMessage = createFormatErrorMessageStub();
    const { result } = renderHook(() => useTranslate({ formatErrorMessage }));

    act(() => {
      result.current.onSourceLanguageChange("中文");
      result.current.onTargetLanguageChange("英文");
      result.current.onInputChange("你好");
    });

    act(() => {
      result.current.onSwapLanguages();
    });

    expect(result.current.sourceLanguage).toBe("英文");
    expect(result.current.targetLanguage).toBe("中文");
    expect(result.current.translateInfo).toBe("已交换语言方向。");
  });

  it("copies the translated text and reports success", async () => {
    const formatErrorMessage = createFormatErrorMessageStub();
    const { result } = renderHook(() =>
      useTranslate({ formatErrorMessage })
    );

    vi.mocked(translateText).mockResolvedValue({
      provider: "DashScope",
      model: "qwen",
      translated_text: "Mock translation"
    });

    await act(async () => {
      await result.current.onSubmit({
        preventDefault() {}
      } as any);
    });

    await act(async () => {
      await result.current.onCopyResult();
    });

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("Mock translation");
    expect(result.current.translateInfo).toBe("已复制译文。");
  });

  it("pastes clipboard content into the source editor", async () => {
    const formatErrorMessage = createFormatErrorMessageStub();
    const { result } = renderHook(() =>
      useTranslate({ formatErrorMessage })
    );

    await act(async () => {
      await result.current.onPasteInput();
    });

    expect(navigator.clipboard.readText).toHaveBeenCalled();
    expect(result.current.translateInput).toBe("Clipboard text");
    expect(result.current.translateInfo).toBe("已粘贴到原文输入区。");
  });

  it("starts speech playback for the translated result", async () => {
    const formatErrorMessage = createFormatErrorMessageStub();
    const { result } = renderHook(() =>
      useTranslate({ formatErrorMessage })
    );

    act(() => {
      result.current.onInputChange("hello");
    });

    vi.mocked(translateText).mockResolvedValue({
      provider: "DashScope",
      model: "qwen",
      translated_text: "Mock translation"
    });

    await act(async () => {
      await result.current.onSubmit({
        preventDefault() {}
      } as any);
    });

    act(() => {
      result.current.onSpeakResult();
    });

    expect(globalThis.speechSynthesis.speak).toHaveBeenCalledTimes(1);
    expect(result.current.speakingTarget).toBe("result");
    expect(result.current.translateInfo).toBe("正在朗读译文。");
  });

  it("clears source and result independently", () => {
    const formatErrorMessage = createFormatErrorMessageStub();
    const { result } = renderHook(() =>
      useTranslate({ formatErrorMessage })
    );

    act(() => {
      result.current.onInputChange("Hello world");
      result.current.onClearSource();
    });

    expect(result.current.translateInput).toBe("");
    expect(result.current.translateInfo).toBe("已清空原文。");

    act(() => {
      result.current.onClearResult();
    });

    expect(result.current.translateResult).toBe("");
    expect(result.current.translateInfo).toBe("已清空译文。");
  });
});
