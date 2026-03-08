import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createAudioOverviewController } from "../../test/factories";
import PodcastSidebar from "./PodcastSidebar";

describe("PodcastSidebar", () => {
  it("renders recent podcasts and preview empty state", () => {
    render(<PodcastSidebar audioOverview={createAudioOverviewController()} />);

    expect(screen.getByText("最近播客")).toBeInTheDocument();
    expect(screen.getByText(/播客脚本测试/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "载入" })).toBeInTheDocument();
  });
});
