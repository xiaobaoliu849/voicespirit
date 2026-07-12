import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { createVoiceChatController } from "../test/factories";
import VoiceAgentHistoryPanel from "./VoiceAgentHistoryPanel";

describe("VoiceAgentHistoryPanel", () => {
  it("renders aggregate metrics, filters timeline events, and resumes linked runs", async () => {
    const onLoadVoiceAgentHistory = vi.fn();
    const onResumeAgentRun = vi.fn();
    render(
      <VoiceAgentHistoryPanel
        onResumeAgentRun={onResumeAgentRun}
        voiceChat={createVoiceChatController({
          onLoadVoiceAgentHistory,
          voiceAgentMetricsSummary: {
            provider: "all",
            session_count: 3,
            turn_count: 8,
            completed_turn_count: 7,
            interrupted_turn_count: 1,
            decision_count: 2,
            classifications: { TRUE_BARGE_IN: 1, BACKCHANNEL: 1, NOISE_OR_SILENCE: 0 },
            false_interruption_rate: 0.5,
            first_audio_ms: { count: 3, avg: 90, p50: 88, p95: 120, min: 70, max: 125 },
            interruption_decision_ms: { count: 2, avg: 42, p50: 42, p95: 50, min: 35, max: 51 },
            interruption_stop_ms: { count: 1, avg: 61, p50: 61, p95: 61, min: 61, max: 61 },
            turn_completion_ms: { count: 7, avg: 1200, p50: 1100, p95: 1800, min: 700, max: 2000 },
            providers: [],
          },
          voiceAgentHistorySessions: [{
            id: "session-1",
            provider: "OpenAI",
            model: "gpt-realtime",
            voice: "alloy",
            status: "closed",
            started_at: "2026-07-12T10:00:00Z",
          }],
          voiceAgentHistoryDetail: {
            id: "session-1",
            provider: "OpenAI",
            model: "gpt-realtime",
            voice: "alloy",
            status: "closed",
            started_at: "2026-07-12T10:00:00Z",
            turns: [],
            tool_events: [],
            timeline: [
              {
                id: "event-1",
                event_type: "user_transcript",
                source: "turn",
                turn_id: "voice-turn-1",
                tool_name: "",
                query: "",
                text: "创建播客",
                timestamp: "2026-07-12T10:00:01Z",
                payload: {},
              },
              {
                id: "event-2",
                event_type: "interruption_decision",
                source: "interruption",
                turn_id: "voice-turn-1",
                tool_name: "",
                query: "",
                text: "等一下",
                timestamp: "2026-07-12T10:00:02Z",
                payload: { classification: "TRUE_BARGE_IN", decision: "cancel", rule: "non_backchannel_speech" },
              },
              {
                id: "event-3",
                event_type: "agent_run_linked",
                source: "agent_run",
                turn_id: "voice-turn-1",
                tool_name: "",
                query: "",
                text: "AI 播客",
                timestamp: "2026-07-12T10:00:03Z",
                payload: { agent_run_id: "audio_agent:9" },
              },
            ],
            agent_run_links: [{
              id: 1,
              agent_run_id: "audio_agent:9",
              voice_session_id: "session-1",
              voice_turn_id: "voice-turn-1",
              relation_type: "created_by",
              created_at: "2026-07-12T10:00:03Z",
              run: {
                id: "audio_agent:9",
                run_type: "audio_agent",
                source_kind: "audio_agent",
                source_run_id: "9",
                title: "AI 播客",
                status: "queued",
                current_step: "retrieve",
                provider: "DashScope",
                model: "",
                created_at: "2026-07-12T10:00:03Z",
                updated_at: "2026-07-12T10:00:03Z",
              },
            }],
          },
        })}
      />
    );

    await waitFor(() => expect(onLoadVoiceAgentHistory).toHaveBeenCalledTimes(1));
    expect(screen.getByText("会话: 3")).toBeInTheDocument();
    expect(screen.getByText("P95 停止: 61ms")).toBeInTheDocument();
    expect(screen.getAllByText("AI 播客")).toHaveLength(2);

    fireEvent.change(screen.getByLabelText("时间线类型筛选"), { target: { value: "interruption" } });
    expect(screen.queryByText("创建播客")).not.toBeInTheDocument();
    expect(screen.getByText("TRUE_BARGE_IN · cancel · non_backchannel_speech")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "在播客工作台继续" }));
    expect(onResumeAgentRun).toHaveBeenCalledWith(expect.objectContaining({ agent_run_id: "audio_agent:9" }));
  });
});
