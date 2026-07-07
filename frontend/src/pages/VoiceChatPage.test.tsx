import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { createVoiceChatController } from "../test/factories";
import VoiceChatPage from "./VoiceChatPage";

describe("VoiceChatPage", () => {
  it("shows retrieved memory status for the current turn", () => {
    render(
      <VoiceChatPage
        voiceChat={createVoiceChatController({
          voiceChatConnected: true,
          voiceChatStatus: "已回忆 2 条长期记忆，准备回答…",
          voiceChatTranscript: "还是按之前那个比赛提交流程继续。",
          voiceChatReply: "好的，我按你之前的偏好继续整理。",
          voiceChatMemoriesRetrieved: 2,
        })}
        errorRuntimeContext={{}}
      />
    );

    expect(screen.getByText("已回忆 2 条记忆")).toBeInTheDocument();
    expect(
      screen.getByText("本轮已回忆 2 条长期记忆。")
    ).toBeInTheDocument();
  });

  it("shows memory write status for the completed turn", () => {
    render(
      <VoiceChatPage
        voiceChat={createVoiceChatController({
          voiceChatMemoryWriteStatus: "本轮已提交 EverMind 1 条记忆，并加入本地待同步缓存",
        })}
        errorRuntimeContext={{}}
      />
    );

    expect(screen.getByText("本轮已提交 EverMind 1 条记忆，并加入本地待同步缓存")).toBeInTheDocument();
  });

  it("shows memory source status for the current recall attempt", () => {
    render(
      <VoiceChatPage
        voiceChat={createVoiceChatController({
          voiceChatMemorySourceStatus: "已回忆 1 条长期记忆（本地待同步 1，云端 0）",
        })}
        errorRuntimeContext={{}}
      />
    );

    expect(screen.getByText("已回忆 1 条长期记忆（本地待同步 1，云端 0）")).toBeInTheDocument();
  });

  it("shows voice agent tool status and sources", () => {
    render(
      <VoiceChatPage
        voiceChat={createVoiceChatController({
          voiceChatAgentToolStatus: "已基于 1 个来源生成搜索摘要",
          voiceChatAgentRunMeta: "voice-tool-1 · search_web · 1 sources · 320ms",
          voiceChatAgentSources: [
            {
              title: "Research source",
              uri: "https://example.com/research",
              snippet: "Fetched research content",
              source_type: "web_search",
            },
          ],
        })}
        errorRuntimeContext={{}}
      />
    );

    expect(screen.getByText("已基于 1 个来源生成搜索摘要")).toBeInTheDocument();
    expect(screen.getByText("voice-tool-1 · search_web · 1 sources · 320ms")).toBeInTheDocument();
    expect(screen.getByText("工具来源")).toBeInTheDocument();
    expect(screen.getByText("Research source")).toBeInTheDocument();
    expect(screen.getByText("Fetched research content")).toBeInTheDocument();
  });

  it("shows persisted voice agent sessions and export controls", () => {
    const onLoadVoiceAgentHistory = vi.fn();
    const onOpenVoiceAgentSession = vi.fn();
    const onExportVoiceAgentSession = vi.fn();

    render(
      <VoiceChatPage
        voiceChat={createVoiceChatController({
          voiceAgentHistorySessions: [
            {
              id: "voice-session-1",
              provider: "DashScope",
              model: "qwen3-omni-flash-realtime-2025-12-01",
              voice: "Cherry",
              status: "closed",
              started_at: "2026-07-07 10:00:00",
              ended_at: "2026-07-07 10:01:00",
              meta: { transport: "websocket" },
            },
          ],
          voiceAgentHistoryDetail: {
            id: "voice-session-1",
            provider: "DashScope",
            model: "qwen3-omni-flash-realtime-2025-12-01",
            voice: "Cherry",
            status: "closed",
            started_at: "2026-07-07 10:00:00",
            ended_at: "2026-07-07 10:01:00",
            meta: { transport: "websocket" },
            turns: [
              {
                id: 1,
                session_id: "voice-session-1",
                turn_id: "voice-tool-1",
                user_text: "帮我搜索 voice agent",
                assistant_text: "已整理来源。",
                memory_payload: {},
                completed: true,
                started_at: "2026-07-07 10:00:01",
                completed_at: "2026-07-07 10:00:04",
              },
            ],
            tool_events: [
              {
                id: 2,
                session_id: "voice-session-1",
                turn_id: "voice-tool-1",
                event_type: "agent_result",
                tool_name: "search_web",
                query: "voice agent",
                payload: { answer: "已整理来源。" },
                created_at: "2026-07-07 10:00:03",
              },
            ],
          },
          voiceAgentHistoryExportText: "{\n  \"session\": \"voice-session-1\"\n}",
          onLoadVoiceAgentHistory,
          onOpenVoiceAgentSession,
          onExportVoiceAgentSession,
        })}
        errorRuntimeContext={{}}
      />
    );

    expect(screen.getByText("历史语音 Agent 会话")).toBeInTheDocument();
    fireEvent.click(screen.getByText("刷新历史"));
    expect(onLoadVoiceAgentHistory).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByText("DashScope · closed"));
    expect(onOpenVoiceAgentSession).toHaveBeenCalledWith("voice-session-1");

    expect(screen.getByText("已打开历史会话: voice-session-1")).toBeInTheDocument();
    expect(screen.getByText("轮次 1，工具事件 1")).toBeInTheDocument();
    expect(screen.getByText("用户: 帮我搜索 voice agent")).toBeInTheDocument();
    expect(screen.getByText("agent_result · search_web")).toBeInTheDocument();

    fireEvent.click(screen.getByText("导出 JSON"));
    expect(onExportVoiceAgentSession).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText("历史会话 JSON 导出")).toHaveValue("{\n  \"session\": \"voice-session-1\"\n}");
  });
});
