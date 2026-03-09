import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import SettingsPage from "./SettingsPage";
import { createSettingsController } from "../test/factories";

describe("SettingsPage", () => {
  it("renders provider settings by default", () => {
    render(<SettingsPage settings={createSettingsController()} errorRuntimeContext={{}} />);

    expect(screen.getByText("AI 供应商参数")).toBeInTheDocument();
    expect(screen.getByText("默认服务商")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "保存全部修改" })).toBeInTheDocument();
  });

  it("switches between memory, transcription, and desktop categories", () => {
    render(<SettingsPage settings={createSettingsController()} errorRuntimeContext={{}} />);

    fireEvent.click(screen.getByRole("button", { name: /记忆中心/i }));
    expect(screen.getByText("EverMem 长期记忆中心")).toBeInTheDocument();
    expect(screen.getByText("启用长期记忆支持")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /文件转写/i }));
    expect(screen.getByText("文件转写与上传配置")).toBeInTheDocument();
    expect(screen.getByText("文件上传模式")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /系统与运行时/i }));
    expect(screen.getByText("系统与运行时状态")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "显示系统运行时日志" })).toBeInTheDocument();
  });

  it("wires desktop runtime actions to settings handlers", () => {
    const settings = createSettingsController();
    render(<SettingsPage settings={settings} errorRuntimeContext={{}} />);

    fireEvent.click(screen.getByRole("button", { name: /系统与运行时/i }));
    fireEvent.click(screen.getByRole("button", { name: "显示系统运行时日志" }));
    fireEvent.click(screen.getByRole("button", { name: "复制运行时信息" }));

    expect(settings.onToggleRuntimeOpen).toHaveBeenCalledTimes(1);
    expect(settings.onCopyBackendRuntime).toHaveBeenCalledTimes(1);
  });

  it("submits the settings form through the primary action", () => {
    const settings = createSettingsController();
    render(<SettingsPage settings={settings} errorRuntimeContext={{}} />);

    fireEvent.click(screen.getByRole("button", { name: "保存全部修改" }));

    expect(settings.onSubmit).toHaveBeenCalledTimes(1);
    expect(settings.onSubmit).toHaveBeenCalledWith(expect.any(Object));
  });
});
