import { describe, it, expect } from "vitest";
import {
  isLiveTranslateModel,
  isRealtimeVoiceModel,
  DASHSCOPE_PROVIDER,
  GOOGLE_PROVIDER,
} from "./useVoiceChatHelpers";

describe("isLiveTranslateModel", () => {
  it("recognizes Google live-translate models", () => {
    expect(isLiveTranslateModel(GOOGLE_PROVIDER, "gemini-3.5-live-translate-preview")).toBe(true);
  });

  it("recognizes DashScope livetranslate models (current + legacy)", () => {
    expect(isLiveTranslateModel(DASHSCOPE_PROVIDER, "qwen3.5-livetranslate-flash-realtime")).toBe(true);
    expect(isLiveTranslateModel(DASHSCOPE_PROVIDER, "qwen3-livetranslate-flash-realtime")).toBe(true);
  });

  it("rejects non-translate realtime models", () => {
    expect(isLiveTranslateModel(DASHSCOPE_PROVIDER, "qwen3.5-omni-plus-realtime")).toBe(false);
    expect(isLiveTranslateModel(GOOGLE_PROVIDER, "gemini-2.5-flash-native-audio-preview-12-2025")).toBe(false);
    expect(isLiveTranslateModel(DASHSCOPE_PROVIDER, "")).toBe(false);
  });
});

describe("isRealtimeVoiceModel (DashScope livetranslate)", () => {
  it("treats livetranslate as a realtime voice model", () => {
    expect(isRealtimeVoiceModel(DASHSCOPE_PROVIDER, "qwen3.5-livetranslate-flash-realtime")).toBe(true);
    expect(isRealtimeVoiceModel(DASHSCOPE_PROVIDER, "qwen3-livetranslate-flash-realtime")).toBe(true);
    expect(
      isRealtimeVoiceModel(DASHSCOPE_PROVIDER, "qwen3.5-livetranslate-flash-realtime-2026-05-19")
    ).toBe(true);
  });

  it("still recognizes omni and qwen-audio realtime models", () => {
    expect(isRealtimeVoiceModel(DASHSCOPE_PROVIDER, "qwen3.5-omni-plus-realtime")).toBe(true);
    expect(isRealtimeVoiceModel(DASHSCOPE_PROVIDER, "qwen-audio-3.0-realtime-plus")).toBe(true);
  });

  it("rejects non-realtime DashScope models", () => {
    expect(isRealtimeVoiceModel(DASHSCOPE_PROVIDER, "qwen-mt-plus")).toBe(false);
    expect(isRealtimeVoiceModel(DASHSCOPE_PROVIDER, "qwen-plus")).toBe(false);
  });
});
