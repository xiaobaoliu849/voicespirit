import type { VoiceAgentTimelineEventHistory } from "../api";

export type VoiceTimelineMetrics = {
  firstAudioMs: number | null;
  interruptionDecisionMs: number | null;
  decisionCount: number;
  falseInterruptionRate: number | null;
};

function finiteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function buildVoiceTimelineMetrics(
  timeline: VoiceAgentTimelineEventHistory[]
): VoiceTimelineMetrics {
  const firstAudioSamples: number[] = [];
  const decisionSamples: number[] = [];
  let decisionCount = 0;
  let nonBargeInCount = 0;

  timeline.forEach((event) => {
    if (event.event_type === "assistant_audio_started") {
      const sample = finiteNumber(event.payload.first_audio_ms ?? event.payload.elapsed_ms);
      if (sample !== null) {
        firstAudioSamples.push(sample);
      }
    }
    if (event.event_type === "interruption_decision") {
      decisionCount += 1;
      const classification = String(event.payload.classification || "");
      if (classification !== "TRUE_BARGE_IN") {
        nonBargeInCount += 1;
      }
      const sample = finiteNumber(event.payload.decision_latency_ms ?? event.payload.elapsed_ms);
      if (sample !== null) {
        decisionSamples.push(sample);
      }
    }
  });

  const average = (values: number[]) => (
    values.length > 0 ? Math.round(values.reduce((sum, value) => sum + value, 0) / values.length) : null
  );

  return {
    firstAudioMs: average(firstAudioSamples),
    interruptionDecisionMs: average(decisionSamples),
    decisionCount,
    falseInterruptionRate: decisionCount > 0 ? nonBargeInCount / decisionCount : null,
  };
}
