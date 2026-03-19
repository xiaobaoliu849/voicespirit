import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createAudioOverviewController } from "../../test/factories";
import PodcastSidebar from "./PodcastSidebar";

describe("PodcastSidebar", () => {
  it("renders recent podcasts and preview empty state", () => {
    render(<PodcastSidebar audioOverview={createAudioOverviewController()} />);

    expect(screen.getByText("最近播客")).toBeInTheDocument();
    expect(screen.getByText("Agent 执行")).toBeInTheDocument();
    expect(screen.getByText("资料来源")).toBeInTheDocument();
    expect(screen.getByText("最近事件")).toBeInTheDocument();
    expect(screen.getByText(/播客脚本测试/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "载入" })).toBeInTheDocument();
  });

  it("renders agent steps and sources when available", () => {
    render(
      <PodcastSidebar
        audioOverview={createAudioOverviewController({
          audioAgentRunId: 3,
          audioAgentStatus: "draft_ready",
          audioAgentCurrentStep: "persist_draft",
          audioAgentResultProvider: "DashScope",
          audioAgentResultModel: "qwen-plus",
          audioAgentSteps: [
            {
              id: 1,
              run_id: 3,
              step_name: "retrieve",
              status: "completed",
              attempt_index: 1,
              started_at: "",
              finished_at: "",
              meta: {},
              error_code: "",
              error_message: ""
            }
          ],
          audioAgentSources: [
            {
              id: 1,
              run_id: 3,
              source_type: "manual_text",
              title: "User provided context",
              uri: "",
              snippet: "用户希望内容更贴近年轻上班族。",
              content: "",
              score: 1,
              meta: {},
              created_at: ""
            }
          ],
          audioAgentEvents: [
            {
              id: 1,
              run_id: 3,
              event_type: "draft_created",
              payload: {},
              created_at: "2026-03-19T22:20:00Z"
            }
          ]
        })}
      />
    );

    expect(screen.getByText("#3 draft_ready")).toBeInTheDocument();
    expect(screen.getByText("检索")).toBeInTheDocument();
    expect(screen.getByText("User provided context")).toBeInTheDocument();
    expect(screen.getByText("草稿已生成")).toBeInTheDocument();
  });
});
