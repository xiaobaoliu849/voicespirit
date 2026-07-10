import re
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class InterruptionIntent(str, Enum):
    TRUE_BARGE_IN = "TRUE_BARGE_IN"
    BACKCHANNEL = "BACKCHANNEL"
    NOISE_OR_SILENCE = "NOISE_OR_SILENCE"

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
    def classify_interruption(cls, text: str) -> InterruptionIntent:
        cleaned_text = str(text or "").strip()

        # Remove common punctuation for evaluation
        eval_text = re.sub(r"[,.;:，。；：！？!?\s]+", "", cleaned_text)

        # Noise or silence
        if not eval_text:
            logger.info("interruption_classification result=NOISE_OR_SILENCE text=%r", cleaned_text)
            return InterruptionIntent.NOISE_OR_SILENCE

        # Check backchannels
        for pattern in cls._BACKCHANNEL_PATTERNS:
            if re.match(pattern, eval_text, re.IGNORECASE):
                logger.info("interruption_classification result=BACKCHANNEL text=%r pattern=%r", cleaned_text, pattern)
                return InterruptionIntent.BACKCHANNEL

        # If it's very short but not in backchannel list, maybe it's an unrecognized backchannel,
        # but safely we can treat it as barge-in if it's substantial, or we can just treat everything else as barge-in.
        # Actually, if the user says "等一下" (Wait), it's 3 chars. "停" is 1 char.
        # "停" is a clear barge-in command, so anything not in backchannel is a true barge-in.
        logger.info("interruption_classification result=TRUE_BARGE_IN text=%r", cleaned_text)
        return InterruptionIntent.TRUE_BARGE_IN
