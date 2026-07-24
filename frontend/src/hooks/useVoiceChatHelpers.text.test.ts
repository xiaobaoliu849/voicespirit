import { describe, it, expect } from "vitest";
import {
  isCJKPredominant,
  appendStreamingText,
  mergeAssistantText,
  containsLatinText,
} from "./useVoiceChatHelpers";

// ---------------------------------------------------------------------------
// isCJKPredominant
// ---------------------------------------------------------------------------
describe("isCJKPredominant", () => {
  it("returns true for Japanese text (hiragana + kanji)", () => {
    expect(isCJKPredominant("こんにちは今日はいい天気ですね")).toBe(true);
  });

  it("returns true for Japanese text (katakana)", () => {
    expect(isCJKPredominant("コンニチハ")).toBe(true);
  });

  it("returns true for Chinese text", () => {
    expect(isCJKPredominant("这是一个中文测试句子")).toBe(true);
  });

  it("returns true for Korean text (hangul)", () => {
    expect(isCJKPredominant("안녕하세요 오늘 날씨가 좋네요")).toBe(true);
  });

  it("returns false for pure English text", () => {
    expect(isCJKPredominant("Hello, how are you today?")).toBe(false);
  });

  it("returns true for mixed CJK+Latin when CJK exceeds 30%", () => {
    // "Dota 是一款非常有趣的游戏" — CJK chars > 30% of total
    expect(isCJKPredominant("Dota 是一款非常有趣的游戏")).toBe(true);
  });

  it("returns false for mixed CJK+Latin when CJK is below 30%", () => {
    // "Hello world 你好" — only 2 CJK chars out of 14 total = ~14%
    expect(isCJKPredominant("Hello world 你好")).toBe(false);
  });

  it("returns false for empty string", () => {
    expect(isCJKPredominant("")).toBe(false);
  });

  it("returns false for whitespace-only string", () => {
    expect(isCJKPredominant("   \t\n  ")).toBe(false);
  });

  it("returns true when CJK is exactly at the threshold boundary (just over 30%)", () => {
    // 4 chars total: 2 CJK + 2 Latin = 50% → true
    // 10 chars total: need 4 CJK out of 10 = 40% → true
    expect(isCJKPredominant("AB测试CD")).toBe(true); // 2 CJK out of 6 = 33%
  });

  it("handles CJK compatibility ideographs", () => {
    // U+F900..U+FAFF range — these are rare CJK compat chars
    expect(isCJKPredominant("これは豈テストです")).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// appendStreamingText
// ---------------------------------------------------------------------------
describe("appendStreamingText", () => {
  it("inserts a space between two pure Latin segments", () => {
    expect(appendStreamingText("Hello", "world")).toBe("Hello world");
  });

  it("does not insert a space inside a CJK-predominant sentence", () => {
    // Surrounding text is CJK-heavy → no space even for Latin token
    expect(appendStreamingText("今天我们要聊", "Dota")).toBe("今天我们要聊Dota");
  });

  it("does not insert a space when the second segment is CJK-predominant", () => {
    expect(appendStreamingText("Dota", "是一款好玩的游戏")).toBe("Dota是一款好玩的游戏");
  });

  it("does not insert a space for pure CJK segments", () => {
    expect(appendStreamingText("你好", "世界")).toBe("你好世界");
  });

  it("inserts a space when both segments are Latin and neither is CJK-predominant", () => {
    expect(appendStreamingText("The quick brown fox", "jumps over")).toBe(
      "The quick brown fox jumps over"
    );
  });

  it("handles empty previous gracefully", () => {
    expect(appendStreamingText("", "Hello")).toBe("Hello");
  });

  it("handles empty incoming gracefully", () => {
    expect(appendStreamingText("Hello", "")).toBe("Hello");
  });

  it("handles both empty gracefully", () => {
    expect(appendStreamingText("", "")).toBe("");
  });

  it("does not insert a leading space when Latin token follows CJK text", () => {
    // Japanese text ending with a Latin proper noun
    expect(appendStreamingText("今日の", "Dota2の試合")).toBe("今日のDota2の試合");
  });

  it("does not insert a space when Chinese text contains an English name", () => {
    expect(appendStreamingText("我叫", "John")).toBe("我叫John");
  });

  it("removes space before punctuation in Latin text", () => {
    expect(appendStreamingText("Hello world", ".")).toBe("Hello world.");
    expect(appendStreamingText("Hello world", ",")).toBe("Hello world,");
  });
});

// ---------------------------------------------------------------------------
// mergeAssistantText — substring containment safety net
// ---------------------------------------------------------------------------
describe("mergeAssistantText", () => {
  it("returns previous unchanged when incoming text is already contained in previous", () => {
    // Simulate a duplicate streaming delta: the previous already contains
    // the incoming text as a substring.
    const previous = "今日の試合はとても面白かったです";
    const incoming = "試合はとても面白か";
    expect(mergeAssistantText(previous, incoming)).toBe(previous);
  });

  it("appends novel text that is not contained in previous", () => {
    const previous = "Hello world";
    const incoming = "how are you";
    expect(mergeAssistantText(previous, incoming)).toBe("Hello world how are you");
  });

  it("handles the case where incoming extends previous (overlap merge)", () => {
    const previous = "今日の試合は";
    const incoming = "試合はとても面白かったです";
    // "試合は" overlaps, so it should merge
    const result = mergeAssistantText(previous, incoming);
    expect(result).toBe("今日の試合はとても面白かったです");
  });

  it("returns previous when incoming is empty after trimming", () => {
    expect(mergeAssistantText("Hello", "   ")).toBe("Hello");
  });

  it("returns incoming when previous is empty", () => {
    expect(mergeAssistantText("", "Hello world")).toBe("Hello world");
  });

  it("returns previous when cleaned incoming is empty (only punctuation)", () => {
    expect(mergeAssistantText("Hello", "!")).toBe("Hello");
  });

  it("safety net: prevents duplicate CJK appends even with trailing punctuation variation", () => {
    // The cleaned previous already contains the whole cleaned incoming
    const previous = "これはテストです。";
    const incoming = "テストです";
    expect(mergeAssistantText(previous, incoming)).toBe(previous);
  });

  it("handles the exact equality case (clean versions equal)", () => {
    const previous = "Hello world";
    const incoming = "Hello world.";
    // cleanPrev = "Hello world", cleanNext = "Hello world" → equal → return previous
    expect(mergeAssistantText(previous, incoming)).toBe(previous);
  });

  it("handles prefix containment: if cleanPrev.startsWith(cleanNext), return previous", () => {
    // This would be an edge case where incoming is a prefix of previous
    const previous = "Hello world and more";
    const incoming = "Hello world";
    expect(mergeAssistantText(previous, incoming)).toBe(previous);
  });

  it("handles the 'ends with' check: if cleanPrev ends with cleanNext, return previous", () => {
    const previous = "This is a test message";
    const incoming = "test message";
    expect(mergeAssistantText(previous, incoming)).toBe(previous);
  });
});
