import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createAudioOverviewController } from "../../test/factories";
import PodcastTopicStep from "./PodcastTopicStep";

describe("PodcastTopicStep", () => {
  it("renders topic form", () => {
    render(<PodcastTopicStep audioOverview={createAudioOverviewController()} />);

    expect(screen.getByText("确定播客主题")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "生成脚本" })).toBeInTheDocument();
  });

  it("renders advanced fields when expanded", () => {
    render(
      <PodcastTopicStep
        audioOverview={createAudioOverviewController({ audioOverviewAdvancedOpen: true })}
      />
    );

    expect(screen.getByText("LLM 供应商")).toBeInTheDocument();
    expect(screen.getByText("对话轮数")).toBeInTheDocument();
    expect(screen.getByText("手动资料")).toBeInTheDocument();
    expect(screen.getByText("来源 URL 列表")).toBeInTheDocument();
    expect(screen.getByText("生成约束")).toBeInTheDocument();
  });
});
