import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createAudioOverviewController } from "../../test/factories";
import PodcastHeader from "./PodcastHeader";

describe("PodcastHeader", () => {
  it("renders title and status", () => {
    render(<PodcastHeader audioOverview={createAudioOverviewController()} />);

    expect(screen.getByText("播客工作台")).toBeInTheDocument();
    expect(screen.getByText("播客 #12")).toBeInTheDocument();
    expect(screen.getByText("长期记忆未接入")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "新建草稿" })).toBeInTheDocument();
  });

  it("renders agent run status when available", () => {
    render(
      <PodcastHeader
        audioOverview={createAudioOverviewController({
          audioAgentRunId: 7,
          audioAgentStatus: "draft_ready"
        })}
      />
    );

    expect(screen.getByText("Agent Run #7 · draft_ready")).toBeInTheDocument();
  });

  it("renders delete action when menu is open", () => {
    render(
      <PodcastHeader
        audioOverview={createAudioOverviewController({ audioOverviewMenuOpen: true })}
      />
    );

    expect(screen.getByRole("button", { name: "删除当前" })).toBeInTheDocument();
  });
});
