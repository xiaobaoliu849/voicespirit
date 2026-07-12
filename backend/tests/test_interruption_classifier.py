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
        self.assertIsNotNone(coordinator.pending)
        self.assertIsNone(coordinator.decide("等一下"))

        coordinator.complete_decision()
        self.assertIsNone(coordinator.pending)

    def test_deferred_terminal_clears_shared_active_response(self):
        clock_values = iter((8.0, 8.25))
        coordinator = InterruptionDecisionCoordinator(clock=lambda: next(clock_values))
        coordinator.active_response_id = "response-1"
        coordinator.begin(provider="DashScope", interrupted_turn_id="voice-turn-1")
        coordinator.defer_terminal({"type": "turn_complete", "response_id": "response-1"})
        coordinator.decide("")
        coordinator.complete_decision()

        self.assertIsNotNone(coordinator.take_deferred_terminal())
        self.assertEqual(coordinator.active_response_id, "")

    def test_only_recent_same_provider_transcript_supersedes_timeout(self):
        now = [10.0]
        coordinator = InterruptionDecisionCoordinator(clock=lambda: now[0])
        first = coordinator.begin(provider="OpenAI", provider_event_type="speech_started")
        self.assertEqual(first["candidate_id"], "interruption-1")
        now[0] = 12.5
        coordinator.decide("")
        coordinator.complete_decision(timed_out=True)

        now[0] = 13.0
        late = coordinator.begin(
            provider="OpenAI",
            provider_event_type="transcript_without_vad",
            supersede_timed_out=True,
        )
        self.assertEqual(late["supersedes_candidate_id"], "interruption-1")
        coordinator.decide("等一下")
        coordinator.complete_decision()

        now[0] = 20.0
        second = coordinator.begin(provider="Google", provider_event_type="speech_started")
        coordinator.decide("")
        coordinator.complete_decision(timed_out=True)
        now[0] = 20.1
        wrong_provider = coordinator.begin(
            provider="OpenAI",
            provider_event_type="transcript_without_vad",
            supersede_timed_out=True,
        )
        self.assertNotIn("supersedes_candidate_id", wrong_provider)
