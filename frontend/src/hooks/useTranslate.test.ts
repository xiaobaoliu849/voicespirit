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
});
