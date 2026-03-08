import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createAudioOverviewController } from "../../test/factories";
import PodcastScriptEditor from "./PodcastScriptEditor";

describe("PodcastScriptEditor", () => {
  it("renders script lines", () => {
    render(<PodcastScriptEditor audioOverview={createAudioOverviewController()} />);

    expect(screen.getByText("编辑播客脚本")).toBeInTheDocument();
    expect(screen.getByDisplayValue("第一段内容")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /添加台词/ })).toBeInTheDocument();
  });

  it("renders nothing when no script exists", () => {
    const { container } = render(
      <PodcastScriptEditor
        audioOverview={createAudioOverviewController({ audioOverviewScriptLines: [] })}
      />
    );

    expect(container).toBeEmptyDOMElement();
  });
});
