import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

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
});
