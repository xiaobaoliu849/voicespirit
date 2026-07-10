import re
import time
from dataclasses import dataclass
from enum import Enum
import logging
from typing import Callable

logger = logging.getLogger(__name__)

class InterruptionIntent(str, Enum):
    TRUE_BARGE_IN = "TRUE_BARGE_IN"
    BACKCHANNEL = "BACKCHANNEL"
    NOISE_OR_SILENCE = "NOISE_OR_SILENCE"


@dataclass(frozen=True)
class InterruptionClassification:
    intent: InterruptionIntent
    rule: str


@dataclass(frozen=True)
class PendingInterruption:
    candidate_id: str
    provider: str
    interrupted_turn_id: str
    provider_event_type: str
    started_at: float


class InterruptionDecisionCoordinator:
    """Provider-neutral state for the detect -> transcribe -> decide flow."""

    _MAX_BUFFERED_OUTPUT_EVENTS = 256

    def __init__(self, *, clock: Callable[[], float] = time.perf_counter) -> None:
        self._clock = clock
        self._candidate_index = 0
        self._pending: PendingInterruption | None = None
        self._buffered_output: list[dict[str, object]] = []
        self._deferred_terminal: dict[str, object] | None = None

    @property
    def pending(self) -> PendingInterruption | None:
        return self._pending

    def begin(
        self,
        *,
        provider: str,
        interrupted_turn_id: str = "",
        provider_event_type: str = "speech_started",
    ) -> dict[str, object] | None:
        if self._pending is not None:
            return None
        self._candidate_index += 1
        self._buffered_output = []
        self._deferred_terminal = None
        self._pending = PendingInterruption(
            candidate_id=f"interruption-{self._candidate_index}",
            provider=str(provider or ""),
            interrupted_turn_id=str(interrupted_turn_id or ""),
            provider_event_type=str(provider_event_type or "speech_started"),
            started_at=self._clock(),
        )
        return {
            "candidate_id": self._pending.candidate_id,
            "provider": self._pending.provider,
            "interrupted_turn_id": self._pending.interrupted_turn_id,
            "provider_event_type": self._pending.provider_event_type,
        }

    def buffer_output(self, event: dict[str, object]) -> None:
        if self._pending is not None:
            self._buffered_output.append(dict(event))
            if len(self._buffered_output) > self._MAX_BUFFERED_OUTPUT_EVENTS:
                self._buffered_output.pop(0)

    def take_buffered_output(self) -> list[dict[str, object]]:
        buffered = self._buffered_output
        self._buffered_output = []
        return buffered

    def discard_buffered_output(self) -> None:
        self._buffered_output = []

    def defer_terminal(self, event: dict[str, object]) -> None:
        if self._pending is not None:
            self._deferred_terminal = dict(event)

    def has_deferred_terminal(self) -> bool:
        return self._deferred_terminal is not None

    def take_deferred_terminal(self) -> dict[str, object] | None:
        terminal = self._deferred_terminal
        self._deferred_terminal = None
        return terminal

    def discard_deferred_terminal(self) -> None:
        self._deferred_terminal = None

    def decide(self, text: str) -> dict[str, object] | None:
        pending = self._pending
        if pending is None:
            return None
        classification = InterruptionClassifier.classify_with_rule(text)
        elapsed_ms = max(0, int((self._clock() - pending.started_at) * 1000))
        action = {
            InterruptionIntent.TRUE_BARGE_IN: "cancel",
            InterruptionIntent.BACKCHANNEL: "resume",
            InterruptionIntent.NOISE_OR_SILENCE: "ignore",
        }[classification.intent]
        self._pending = None
        return {
            "candidate_id": pending.candidate_id,
            "classification": classification.intent.value,
            "rule": classification.rule,
            "decision": action,
            "transcript": str(text or "").strip(),
            "provider": pending.provider,
            "interrupted_turn_id": pending.interrupted_turn_id,
            "provider_event_type": pending.provider_event_type,
            "elapsed_ms": elapsed_ms,
            "decision_latency_ms": elapsed_ms,
        }

class InterruptionClassifier:
    """
    Classifies user speech transcript to determine if it is a true interruption,
    a backchannel affirmation, or noise.
    """

    # Common backchannels in Chinese
    _BACKCHANNEL_PATTERNS = [
        r"^嗯(嗯)?$",
        r"^哦(哦)?$",
        r"^啊$",
        r"^对(的)?$",
        r"^好(的)?$",
        r"^是(的)?$",
        r"^确实$",
        r"^没毛病$",
        r"^(OK|ok)$",
        r"^我知道了$",
        r"^明白(了)?$",
        r"^原来如此$"
    ]

    @classmethod
    def classify_with_rule(cls, text: str) -> InterruptionClassification:
        cleaned_text = str(text or "").strip()

        # Remove common punctuation for evaluation
        eval_text = re.sub(r"[,.;:，。；：！？!?\s]+", "", cleaned_text)

        # Noise or silence
        if not eval_text:
            logger.info("interruption_classification result=NOISE_OR_SILENCE text=%r", cleaned_text)
            return InterruptionClassification(
                intent=InterruptionIntent.NOISE_OR_SILENCE,
                rule="empty_or_punctuation",
            )

        # Check backchannels
        for pattern in cls._BACKCHANNEL_PATTERNS:
            if re.match(pattern, eval_text, re.IGNORECASE):
                logger.info("interruption_classification result=BACKCHANNEL text=%r pattern=%r", cleaned_text, pattern)
                return InterruptionClassification(
                    intent=InterruptionIntent.BACKCHANNEL,
                    rule=f"backchannel_pattern:{pattern}",
                )

        # If it's very short but not in backchannel list, maybe it's an unrecognized backchannel,
        # but safely we can treat it as barge-in if it's substantial, or we can just treat everything else as barge-in.
        # Actually, if the user says "等一下" (Wait), it's 3 chars. "停" is 1 char.
        # "停" is a clear barge-in command, so anything not in backchannel is a true barge-in.
        logger.info("interruption_classification result=TRUE_BARGE_IN text=%r", cleaned_text)
        return InterruptionClassification(
            intent=InterruptionIntent.TRUE_BARGE_IN,
            rule="non_backchannel_speech",
        )

    @classmethod
    def classify_interruption(cls, text: str) -> InterruptionIntent:
        """Backward-compatible enum-only classifier used by existing callers."""
        return cls.classify_with_rule(text).intent
