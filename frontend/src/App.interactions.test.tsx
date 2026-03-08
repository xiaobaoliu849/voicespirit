import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import * as api from "./api";

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    fetchApiRuntimeInfo: vi.fn(),
    fetchVoices: vi.fn(),
    fetchSpeakAudio: vi.fn(),
    fetchSettings: vi.fn(),
    listCustomVoices: vi.fn(),
    listAudioOverviewPodcasts: vi.fn(),
    getAudioOverviewPodcast: vi.fn(),
    fetchAudioOverviewPodcastAudio: vi.fn(),
    generateAudioOverviewScript: vi.fn(),
    createAudioOverviewPodcast: vi.fn(),
    updateAudioOverviewPodcast: vi.fn(),
    deleteAudioOverviewPodcast: vi.fn(),
    saveAudioOverviewScript: vi.fn(),
    synthesizeAudioOverviewPodcast: vi.fn(),
    updateSettings: vi.fn(),
    translateText: vi.fn(),
    streamChatCompletion: vi.fn()
  };
});

const mockedFetchApiRuntimeInfo = vi.mocked(api.fetchApiRuntimeInfo);
const mockedFetchVoices = vi.mocked(api.fetchVoices);
const mockedFetchSpeakAudio = vi.mocked(api.fetchSpeakAudio);
const mockedFetchSettings = vi.mocked(api.fetchSettings);
const mockedUpdateSettings = vi.mocked(api.updateSettings);
const mockedListCustomVoices = vi.mocked(api.listCustomVoices);
const mockedListAudioOverviewPodcasts = vi.mocked(api.listAudioOverviewPodcasts);
const mockedGetAudioOverviewPodcast = vi.mocked(api.getAudioOverviewPodcast);
const mockedFetchAudioOverviewPodcastAudio = vi.mocked(api.fetchAudioOverviewPodcastAudio);
const mockedGenerateAudioOverviewScript = vi.mocked(api.generateAudioOverviewScript);
const mockedCreateAudioOverviewPodcast = vi.mocked(api.createAudioOverviewPodcast);
const mockedTranslateText = vi.mocked(api.translateText);
const mockedStreamChatCompletion = vi.mocked(api.streamChatCompletion);

function setClipboardWriteText(writeText: (value: string) => Promise<void>) {
  Object.defineProperty(globalThis.navigator, "clipboard", {
    value: { writeText },
    configurable: true
  });
}

describe("App interactions", () => {
  beforeEach(() => {
    mockedFetchApiRuntimeInfo.mockResolvedValue({
      status: "ok",
      phase: "B",
      auth_mode: "write-only-with-admin-settings",
      auth_enabled: false,
      version: "test",
      raw: {
        name: "VoiceSpirit",
        status: "ok",
        auth_mode: "write-only-with-admin-settings"
      }
    });
    mockedFetchVoices.mockResolvedValue({
      count: 2,
      voices: [
        {
          name: "zh-CN-XiaoxiaoNeural",
          short_name: "Xiaoxiao",
          locale: "zh-CN",
          gender: "Female"
        },
        {
          name: "zh-CN-YunxiNeural",
          short_name: "Yunxi",
          locale: "zh-CN",
          gender: "Male"
        }
      ]
    });
    mockedFetchSettings.mockResolvedValue({
      config_path: "/tmp/config.json",
      providers: ["DashScope", "Google"],
      settings: {
        api_keys: { dashscope_api_key: "" },
        api_urls: { DashScope: "" },
        default_models: { DashScope: { default: "qwen-plus", available: ["qwen-plus"] } },
        general_settings: {},
        output_directory: "/tmp",
        tts_settings: {},
        qwen_tts_settings: {},
        minimax: {},
        ui_settings: {},
        shortcuts: {}
      }
    });
    mockedListCustomVoices.mockResolvedValue({
      voice_type: "voice_design",
      count: 0,
      voices: []
    });
    mockedFetchSpeakAudio.mockResolvedValue(new Blob(["tts"], { type: "audio/mpeg" }));
    mockedTranslateText.mockResolvedValue({
      provider: "DashScope",
      model: "qwen-plus",
      translated_text: "This is the translated result."
    });
    mockedStreamChatCompletion.mockImplementation(async (_payload, handlers) => {
      handlers.onDelta("这是助手的回复。");
      handlers.onDone?.({ memoriesRetrieved: 2, memorySaved: true });
    });
    mockedListAudioOverviewPodcasts.mockResolvedValue({
      count: 1,
      podcasts: [
        {
          id: 12,
          topic: "播客脚本测试",
          language: "zh",
          audio_path: "/tmp/podcast.mp3",
          created_at: "2026-03-07T10:00:00Z",
          updated_at: "2026-03-07T10:00:00Z",
          script_lines: [
            { role: "A", text: "第一段内容" },
            { role: "B", text: "第二段内容" }
          ]
        }
      ]
    });
    mockedGetAudioOverviewPodcast.mockResolvedValue({
      id: 12,
      topic: "播客脚本测试",
      language: "zh",
      audio_path: "/tmp/podcast.mp3",
      created_at: "2026-03-07T10:00:00Z",
      updated_at: "2026-03-07T10:00:00Z",
      script_lines: [
        { role: "A", text: "第一段内容" },
        { role: "B", text: "第二段内容" }
      ]
    });
    mockedFetchAudioOverviewPodcastAudio.mockResolvedValue(
      new Blob(["audio"], { type: "audio/mpeg" })
    );
    Object.defineProperty(globalThis.URL, "createObjectURL", {
      value: vi.fn(() => "blob:test-url"),
      configurable: true
    });
    Object.defineProperty(globalThis.URL, "revokeObjectURL", {
      value: vi.fn(),
      configurable: true
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("sends a quick chat prompt and renders the streamed reply", async () => {
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "写一封邮件" }));
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    await waitFor(() => {
      expect(mockedStreamChatCompletion).toHaveBeenCalledWith(
        expect.objectContaining({
          provider: "Google",
          messages: [
            {
              role: "user",
              content: "请帮我起草一封语气专业但不生硬的项目进度更新邮件。"
            }
          ]
        }),
        expect.any(Object)
      );
    });
    expect(await screen.findByText("这是助手的回复。")).toBeInTheDocument();

    // EverMem UI Badges verification
    expect(await screen.findByText("✓ 已记忆")).toBeInTheDocument();
    expect(await screen.findByText(/🧠 回忆了 2 条/)).toBeInTheDocument();
    expect(await screen.findByText("已存入记忆")).toBeInTheDocument();
  });

  it("generates TTS audio preview from the current text", async () => {
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "语音" }));
    fireEvent.click(screen.getByRole("button", { name: "生成语音" }));

    await waitFor(() => {
      expect(mockedFetchSpeakAudio).toHaveBeenCalledWith(
        expect.objectContaining({
          text: "你好，这是 VoiceSpirit Web 迁移阶段的语音测试。",
          rate: "+0%"
        })
      );
    });
    expect(await screen.findByText("预览音频")).toBeInTheDocument();
    expect(document.querySelector("audio")).toHaveAttribute("src", "blob:test-url");
  });

  it("submits translation with the edited target language", async () => {
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "翻译" }));
    fireEvent.change(screen.getByLabelText("目标语言"), {
      target: { value: "日本語" }
    });
    fireEvent.click(screen.getByRole("button", { name: "开始翻译" }));

    await waitFor(() => {
      expect(mockedTranslateText).toHaveBeenCalledWith(
        expect.objectContaining({
          source_language: "auto",
          target_language: "日本語"
        })
      );
    });
    expect(await screen.findByText("This is the translated result.")).toBeInTheDocument();
  });

  it("reveals and copies backend runtime details", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    setClipboardWriteText(writeText);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "设置" }));
    fireEvent.click(screen.getByRole("button", { name: "显示运行时信息" }));

    expect(screen.getByText(/"name": "VoiceSpirit"/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "复制运行时信息" }));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(
        JSON.stringify(
          {
            name: "VoiceSpirit",
            status: "ok",
            auth_mode: "write-only-with-admin-settings"
          },
          null,
          2
        )
      );
    });
    expect(screen.getByRole("button", { name: "已复制运行时信息" })).toBeInTheDocument();
  });

  it("loads a podcast and reveals the script editor and synth bar", async () => {
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "播客" }));
    expect(await screen.findByRole("heading", { name: "播客工作台" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "编辑播客脚本" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "载入" }));

    await waitFor(() => {
      expect(screen.getByText("已载入播客 #12。")).toBeInTheDocument();
    });
    expect(screen.getByRole("heading", { name: "编辑播客脚本" })).toBeInTheDocument();
    expect(screen.getByDisplayValue("第一段内容")).toBeInTheDocument();
    expect(screen.getByDisplayValue("第二段内容")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /合成/ })).toBeInTheDocument();
  });

  it("copies the loaded podcast script to the clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    setClipboardWriteText(writeText);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "播客" }));
    fireEvent.click(screen.getByRole("button", { name: "载入" }));

    await waitFor(() => {
      expect(screen.getByText("已载入播客 #12。")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTitle("复制脚本"));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith("1. 主播 A：第一段内容\n\n2. 主播 B：第二段内容");
    });
    expect(screen.getByText("脚本已复制到剪贴板。")).toBeInTheDocument();
  });

  it("exports the loaded podcast script as a text file", async () => {
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => { });

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "播客" }));
    fireEvent.click(screen.getByRole("button", { name: "载入" }));

    await waitFor(() => {
      expect(screen.getByText("已载入播客 #12。")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTitle("导出脚本"));

    expect(clickSpy).toHaveBeenCalled();
    expect(screen.getByText("脚本已导出为文本文件。")).toBeInTheDocument();
  });
  it("saves settings and shows success message", async () => {
    mockedFetchSettings.mockResolvedValueOnce({
      config_path: "/tmp/config.json",
      providers: ["DashScope", "Google"],
      settings: {
        api_keys: { dashscope_api_key: "" },
        api_urls: { DashScope: "" },
        default_models: { DashScope: { default: "qwen-plus", available: ["qwen-plus"] } },
        general_settings: {},
        output_directory: "/tmp",
        tts_settings: {},
        qwen_tts_settings: {},
        minimax: {},
        ui_settings: {},
        shortcuts: {}
      }
    });

    mockedUpdateSettings.mockResolvedValue({
      config_path: "/tmp/config.json",
      providers: ["DashScope", "Google"],
      settings: {
        api_keys: { dashscope_api_key: "new-key" },
        api_urls: { DashScope: "" },
        default_models: { DashScope: { default: "qwen-max", available: ["qwen-plus", "qwen-max"] } },
        general_settings: {},
        output_directory: "/tmp",
        tts_settings: {},
        qwen_tts_settings: {},
        minimax: {},
        ui_settings: {},
        shortcuts: {}
      }
    });

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "设置" }));

    const apiKeyInput = screen.getByPlaceholderText("输入供应商 API Key");
    fireEvent.change(apiKeyInput, { target: { value: "new-key" } });

    const modelInput = screen.getByPlaceholderText("例如：qwen-plus / deepseek-chat");
    fireEvent.change(modelInput, { target: { value: "qwen-max" } });

    fireEvent.click(screen.getByRole("button", { name: "保存供应商设置" }));

    await waitFor(() => {
      expect(mockedUpdateSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          api_keys: { dashscope_api_key: "new-key" },
          default_models: { DashScope: { default: "qwen-max", available: ["qwen-plus"] } }
        })
      );
    });

    expect(await screen.findByText("已保存 DashScope 的设置。")).toBeInTheDocument();
  });

  it("generates an audio overview script", async () => {
    mockedGenerateAudioOverviewScript.mockResolvedValue({
      topic: "新主题",
      language: "zh",
      script_lines: [
        { role: "A", text: "测试生成1" },
        { role: "B", text: "测试生成2" }
      ],
      turn_count: 8,
      provider: "DashScope",
      model: ""
    });
    mockedCreateAudioOverviewPodcast.mockResolvedValue({
      id: 99,
      topic: "新主题",
      language: "zh",
      audio_path: "",
      script_lines: [
        { role: "A", text: "测试生成1" },
        { role: "B", text: "测试生成2" }
      ],
      created_at: "2026-03-07T10:00:00Z",
      updated_at: "2026-03-07T10:00:00Z"
    });

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "播客" }));

    const topicInput = screen.getByPlaceholderText("输入你想讨论的话题，例如：AI 如何改变个人学习习惯？");
    fireEvent.change(topicInput, { target: { value: "新主题" } });

    fireEvent.click(screen.getByRole("button", { name: "生成脚本" }));

    await waitFor(() => {
      expect(mockedGenerateAudioOverviewScript).toHaveBeenCalled();
      expect(mockedCreateAudioOverviewPodcast).toHaveBeenCalled();
    });

    expect(await screen.findByText("脚本已生成，并保存为播客 #99。")).toBeInTheDocument();
    expect(screen.getByDisplayValue("测试生成1")).toBeInTheDocument();
  });
});
