import unittest
from services.interruption_classifier import InterruptionClassifier, InterruptionIntent

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
