"""Tests for ``services.realtime_constants`` utilities.

Covers:
  - ``_is_text_primarily_cjk`` CJK detection heuristic
  - ``_merge_streaming_text`` streaming text merge (cumulative prefix,
    overlap fallback, CJK-aware separator, substring safety-net)
"""

import unittest

from services.realtime_constants import (
    _is_text_primarily_cjk,
    _merge_streaming_text,
)


# ---------------------------------------------------------------------------
# _is_text_primarily_cjk
# ---------------------------------------------------------------------------


class IsTextPrimarilyCjkTests(unittest.TestCase):
    """Tests for ``_is_text_primarily_cjk``."""

    def test_pure_cjk_returns_true(self):
        """Pure Chinese / Japanese text must return True."""
        self.assertTrue(_is_text_primarily_cjk("你好世界"))
        self.assertTrue(_is_text_primarily_cjk("こんにちは世界"))
        self.assertTrue(_is_text_primarily_cjk("안녕하세요"))

    def test_pure_english_returns_false(self):
        """Pure ASCII / Latin text must return False."""
        self.assertFalse(_is_text_primarily_cjk("Hello world"))
        self.assertFalse(_is_text_primarily_cjk("Dota"))
        self.assertFalse(_is_text_primarily_cjk("abcdefghij"))

    def test_cjk_predominant_with_embedded_latin(self):
        """CJK text with a few embedded Latin proper nouns must return True
        (the Latin fragments don't push the ratio below 30%)."""
        self.assertTrue(_is_text_primarily_cjk("私はDotaが好き"))  # 7 chars, 5 CJK ~71%
        self.assertTrue(_is_text_primarily_cjk("你好World你好"))
        # 2026年FIFA世界杯 — mostly CJK
        self.assertTrue(_is_text_primarily_cjk("2026年FIFA世界杯"))

    def test_latin_dominant_mixed_text_returns_false(self):
        """When Latin script dominates, return False."""
        self.assertFalse(
            _is_text_primarily_cjk("Hello 你好 world")
        )  # 2 CJK out of ~15 chars <= 13%

    def test_empty_string_returns_false(self):
        """Empty string must not trigger CJK detection."""
        self.assertFalse(_is_text_primarily_cjk(""))

    def test_numbers_and_punctuation_not_counted_as_cjk(self):
        """Numbers and punctuation are not CJK; a digit-heavy string with
        few ideographs should return False."""
        self.assertFalse(_is_text_primarily_cjk("12345 hello 世界"))
        # "世界" is 2 CJK out of ~16 chars = 12.5% （below 30%）

    def test_mixed_around_boundary(self):
        """Exactly at or near the 30% threshold."""
        # 3 CJK out of 10 chars = 30% — must be strictly > 30%
        self.assertFalse(_is_text_primarily_cjk("abc你好def"))
        # 3 CJK out of 9 chars ≈ 33% — >30%
        self.assertTrue(_is_text_primarily_cjk("你好你好a"))
        # 4 CJK out of 10 chars = 40%
        self.assertTrue(_is_text_primarily_cjk("你好世界abcdef"))
        # 2 CJK out of 8 chars = 25% — below 30%
        self.assertFalse(_is_text_primarily_cjk("a你好bcdef"))

    def test_kana_only_returns_true(self):
        """Pure hiragana/katakana strings are CJK."""
        self.assertTrue(_is_text_primarily_cjk("あいうえお"))
        self.assertTrue(_is_text_primarily_cjk("アイウエオ"))

    def test_hangul_only_returns_true(self):
        """Pure hangul strings are CJK."""
        self.assertTrue(_is_text_primarily_cjk("한글테스트"))


# ---------------------------------------------------------------------------
# _merge_streaming_text
# ---------------------------------------------------------------------------


class MergeStreamingTextBaseTests(unittest.TestCase):
    """Basic / edge-case tests for ``_merge_streaming_text``."""

    def test_empty_incoming_returns_before_unchanged(self):
        """When incoming is empty, return the previous text and no delta."""
        self.assertEqual(_merge_streaming_text("Hello", ""), ("Hello", ""))
        self.assertEqual(_merge_streaming_text("", ""), ("", ""))

    def test_empty_previous_returns_incoming_as_both(self):
        """When there's no previous text, the full incoming is the delta."""
        before, delta = _merge_streaming_text("", "Hello world")
        self.assertEqual(before, "Hello world")
        self.assertEqual(delta, "Hello world")

    def test_none_inputs_treated_as_empty(self):
        """None inputs should be treated the same as empty strings."""
        before, delta = _merge_streaming_text(None, None)  # type: ignore[arg-type]
        self.assertEqual(before, "")
        self.assertEqual(delta, "")

        before, delta = _merge_streaming_text(None, "Hello")  # type: ignore[arg-type]
        self.assertEqual(before, "Hello")
        self.assertEqual(delta, "Hello")


class MergeCumulativePrefixTests(unittest.TestCase):
    """Case 2: incoming starts with the cleaned previous text (cumulative)."""

    def test_english_inserts_space_between_words(self):
        """Pure English: a space is inserted between words."""
        before, delta = _merge_streaming_text("Hello", "Hello world")
        self.assertEqual(before, "Hello world")
        self.assertEqual(delta, " world")

    def test_cjk_no_space_insertion(self):
        """CJK: no space should be inserted between characters/words."""
        before, delta = _merge_streaming_text("你好", "你好世界")
        self.assertEqual(before, "你好世界")
        self.assertEqual(delta, "世界")
        self.assertNotIn(" ", before)

    def test_cjk_with_embedded_latin_no_space(self):
        """CJK-predominant with embedded Latin proper noun: no space."""
        # "私は" + "Dota" → "私はDota" (not "私は Dota")
        before, delta = _merge_streaming_text("私は", "私はDota")
        self.assertEqual(before, "私はDota")
        self.assertEqual(delta, "Dota")
        self.assertNotIn(" ", before)

    def test_cjk_with_embedded_latin_continued(self):
        """Another CJK + Latin embedding scenario."""
        before, delta = _merge_streaming_text(
            "2026年FIFA世界杯决赛",
            "2026年FIFA世界杯决赛是法国对巴西",
        )
        self.assertEqual(before, "2026年FIFA世界杯决赛是法国对巴西")
        self.assertEqual(delta, "是法国对巴西")
        self.assertNotIn(" ", before)

    def test_punctuation_trailing_handled(self):
        """Trailing punctuation on the cleaned previous is stripped, then
        re-merged correctly."""
        before, delta = _merge_streaming_text("Hello.", "Hello. world")
        self.assertEqual(before, "Hello world")
        self.assertEqual(delta, " world")

    def test_cjk_with_punctuation_no_space(self):
        """CJK with trailing punctuation: still no space."""
        before, delta = _merge_streaming_text("こんにちは。", "こんにちは。元気ですか")
        self.assertEqual(before, "こんにちは元気ですか")
        self.assertEqual(delta, "元気ですか")
        self.assertNotIn(" ", before)


class SubstringContainmentSafetyNetTests(unittest.TestCase):
    """Safety-net: when next_clean is already contained within before_clean."""

    def test_next_clean_in_before_clean_returns_no_delta(self):
        """If the cleaned incoming text is wholly inside the previous text,
        return the previous text unmodified and no delta to emit."""
        before, delta = _merge_streaming_text("Hello world", "Hello")
        self.assertEqual(before, "Hello world")
        self.assertEqual(delta, "")

    def test_next_clean_substring_middle_of_before(self):
        """Substring containment in the middle of before_clean."""
        before, delta = _merge_streaming_text(
            "2026年FIFA世界杯决赛是法国对巴西",
            "FIFA世界杯决赛",
        )
        self.assertEqual(
            before, "2026年FIFA世界杯决赛是法国对巴西"
        )
        self.assertEqual(delta, "")

    def test_next_clean_endswith_before_clean(self):
        """When next_clean ends with before_clean (but is longer), this
        is NOT a containment case — it is handled by the overlap path."""
        # This test verifies that endswith(before_clean) check in the
        # safety-net doesn't falsely trigger when text flows normally.
        # "Hello" does not contain "Hello world" — it's the other direction.
        # So this should go to overlap fallback, not safety-net.
        before, delta = _merge_streaming_text("Hello", "ello world")
        self.assertEqual(before, "Hello world")
        self.assertEqual(delta, " world")

    def test_before_clean_equals_next_clean_returns_no_delta(self):
        """Exact equality of cleaned texts returns no delta."""
        before, delta = _merge_streaming_text("你好世界", "你好世界。")
        self.assertEqual(before, "你好世界")
        self.assertEqual(delta, "")

    def test_next_clean_at_end_of_before_clean(self):
        """next_clean is a suffix match of before_clean."""
        before, delta = _merge_streaming_text(
            "The quick brown fox", "brown fox"
        )
        self.assertEqual(before, "The quick brown fox")
        self.assertEqual(delta, "")


class OverlapFallbackTests(unittest.TestCase):
    """Case 3: overlap fallback when incoming is not a strict prefix extension."""

    def test_english_overlap_no_space_continuation(self):
        """English text with overlap: no space inserted — overlap means the
        texts are a single continuous word/phrase being built character by
        character (e.g. 'Hello w' → 'world' on the 'w' overlap)."""
        before, delta = _merge_streaming_text("Hello w", "world")
        self.assertEqual(before, "Hello world")
        self.assertEqual(delta, "orld")

    def test_cjk_overlap_no_space(self):
        """CJK overlap: no space insertion."""
        before, delta = _merge_streaming_text("你好世", "世界")
        self.assertEqual(before, "你好世界")
        self.assertEqual(delta, "界")
        self.assertNotIn(" ", before)

    def test_no_overlap_english_adds_space(self):
        """When there's no overlap at all, the texts are concatenated with a
        word-boundary space (both sides have Latin alphanumeric chars)."""
        before, delta = _merge_streaming_text("abc", "def")
        self.assertEqual(before, "abc def")
        self.assertEqual(delta, " def")

    def test_overlap_cjk_latin_adjacency_no_space(self):
        """Overlap where CJK text meets Latin but CJK is predominant."""
        before, delta = _merge_streaming_text("你好abc", "abcdef")
        # Overlap on "abc" → novel is "def"
        # before is CJK-predominant → no space insertion
        self.assertEqual(before, "你好abcdef")
        self.assertEqual(delta, "def")
        self.assertNotIn(" ", before)

    def test_english_word_fragment_overlap_no_space(self):
        """English overlap on part of a word: no space for continuation.
        'I like ap' + 'apple' overlaps on 'ap' — single word, no boundary."""
        before, delta = _merge_streaming_text("I like ap", "apple")
        self.assertEqual(before, "I like apple")
        self.assertEqual(delta, "ple")


class SummaryRegressionTests(unittest.TestCase):
    """High-level regression scenarios that exercise the full logic."""

    def test_real_world_cjk_streaming_scenario(self):
        """Simulate a real streaming sequence for CJK text."""
        previous = ""
        for chunk in ["你好", "你好世界", "你好世界！", "你好世界！今天天", "你好世界！今天天气真"]:
            previous, delta = _merge_streaming_text(previous, chunk)
            self.assertIn("你好", previous)
            self.assertNotIn(" ", previous)

    def test_real_world_english_streaming_scenario(self):
        """Simulate a real streaming sequence for English text."""
        previous = ""
        for i, chunk in enumerate([
            "Hello",
            "Hello world",
            "Hello world!",
            "Hello world! How",
            "Hello world! How are",
            "Hello world! How are you",
        ]):
            previous, delta = _merge_streaming_text(previous, chunk)
            self.assertIn("Hello", previous)
            # After "Hello world" and beyond, spaces should be present
            if i >= 1:
                self.assertIn(" ", previous,
                             f"Space expected in '{previous}' at step {i}")

    def test_safety_net_prevents_duplicate_emission(self):
        """When the incoming text is just a prefix of what we already have,
        no new delta should be emitted (avoids duplicate in UI)."""
        before, delta = _merge_streaming_text(
            "The capital of France is Paris.",
            "The capital of France",
        )
        self.assertEqual(before, "The capital of France is Paris.")
        self.assertEqual(delta, "")
        # The incoming didn't add anything new

    def test_japanese_dota_example(self):
        """The motivating example from the issue: Japanese with 'Dota' embedded."""
        before, delta = _merge_streaming_text("私は", "私はDota")
        self.assertEqual(before, "私はDota")
        self.assertEqual(delta, "Dota")
        # Must NOT have a space before Dota
        self.assertNotIn(" ", before)


if __name__ == "__main__":
    unittest.main()
