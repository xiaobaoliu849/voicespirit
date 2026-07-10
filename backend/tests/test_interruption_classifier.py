import unittest
from services.interruption_classifier import (
    InterruptionClassifier,
    InterruptionDecisionCoordinator,
    InterruptionIntent,
)

class TestInterruptionClassifier(unittest.TestCase):
    def test_noise_or_silence(self):
        self.assertEqual(InterruptionClassifier.classify_interruption(""), InterruptionIntent.NOISE_OR_SILENCE)
        self.assertEqual(InterruptionClassifier.classify_interruption("   "), InterruptionIntent.NOISE_OR_SILENCE)
        self.assertEqual(InterruptionClassifier.classify_interruption("。，！？"), InterruptionIntent.NOISE_OR_SILENCE)

    def test_backchannel(self):
        self.assertEqual(InterruptionClassifier.classify_interruption("嗯"), InterruptionIntent.BACKCHANNEL)
        self.assertEqual(InterruptionClassifier.classify_interruption("嗯嗯"), InterruptionIntent.BACKCHANNEL)
        self.assertEqual(InterruptionClassifier.classify_interruption("哦哦！"), InterruptionIntent.BACKCHANNEL)
        self.assertEqual(InterruptionClassifier.classify_interruption("对的。"), InterruptionIntent.BACKCHANNEL)
        self.assertEqual(InterruptionClassifier.classify_interruption("是的"), InterruptionIntent.BACKCHANNEL)
        self.assertEqual(InterruptionClassifier.classify_interruption("ok"), InterruptionIntent.BACKCHANNEL)
        self.assertEqual(InterruptionClassifier.classify_interruption("确实"), InterruptionIntent.BACKCHANNEL)
        self.assertEqual(InterruptionClassifier.classify_interruption("原来如此"), InterruptionIntent.BACKCHANNEL)

    def test_true_barge_in(self):
        self.assertEqual(InterruptionClassifier.classify_interruption("等一下"), InterruptionIntent.TRUE_BARGE_IN)
        self.assertEqual(InterruptionClassifier.classify_interruption("停"), InterruptionIntent.TRUE_BARGE_IN)
        self.assertEqual(InterruptionClassifier.classify_interruption("不要这个"), InterruptionIntent.TRUE_BARGE_IN)
        self.assertEqual(InterruptionClassifier.classify_interruption("换一个话题"), InterruptionIntent.TRUE_BARGE_IN)
        self.assertEqual(InterruptionClassifier.classify_interruption("你刚才说什么"), InterruptionIntent.TRUE_BARGE_IN)
        self.assertEqual(InterruptionClassifier.classify_interruption("不对"), InterruptionIntent.TRUE_BARGE_IN)

    def test_structured_rule_and_two_phase_latency(self):
        clock_values = iter((5.0, 5.125))
        coordinator = InterruptionDecisionCoordinator(clock=lambda: next(clock_values))
        pending = coordinator.begin(
            provider="OpenAI",
            interrupted_turn_id="voice-turn-1",
            provider_event_type="input_audio_buffer.speech_started",
        )
        decision = coordinator.decide("嗯嗯")

        self.assertEqual(pending["candidate_id"], "interruption-1")
        self.assertEqual(decision["classification"], "BACKCHANNEL")
        self.assertEqual(decision["decision"], "resume")
        self.assertTrue(str(decision["rule"]).startswith("backchannel_pattern:"))
        self.assertEqual(decision["decision_latency_ms"], 125)
