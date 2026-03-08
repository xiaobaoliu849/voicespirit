import type { AudioOverviewPodcast, VoiceInfo } from "../api";
import type { UseAudioOverviewResult } from "../hooks/useAudioOverview";
import { vi } from "vitest";
import type { UseChatResult } from "../hooks/useChat";
import type { UseTranslateResult } from "../hooks/useTranslate";
import type { UseTtsResult } from "../hooks/useTts";
import type { FormatErrorMessage } from "../utils/errorFormatting";
import type { VoiceDesignController, VoiceCloneController } from "../hooks/useVoiceManagement";

export function createFormatErrorMessageStub(): FormatErrorMessage {
  return (_error, fallback) => fallback;
}

export function createChatController(
  overrides: Partial<UseChatResult> = {}
): UseChatResult {
  return {
    chatProvider: "Google",
    chatModel: "",
    chatInput: "",
    chatMessages: [],
    chatBusy: false,
    chatError: "",
    chatHistoryItems: [],
    onSubmit: vi.fn(),
    onProviderChange: vi.fn(),
    onModelChange: vi.fn(),
    onInputChange: vi.fn(),
    onQuickAction: vi.fn(),
    onComposerKeyDown: vi.fn(),
    onNewSession: vi.fn(),
    onSelectHistory: vi.fn(),
    ...overrides
  };
}

export function createTtsController(
  overrides: Partial<UseTtsResult> = {}
): UseTtsResult {
  return {
    text: "Sample test text",
    voices: [],
    voice: "zh-CN-XiaoxiaoNeural",
    rate: "+0%",
    audioUrl: "",
    loadingVoices: false,
    generating: false,
    ttsError: "",
    voiceOptions: [{ value: "zh-CN-XiaoxiaoNeural", label: "Xiaoxiao (zh-CN)" }],
    onSubmit: vi.fn(),
    onTextChange: vi.fn(),
    onVoiceChange: vi.fn(),
    onRateChange: vi.fn(),
    ...overrides
  };
}

export function createTranslateController(
  overrides: Partial<UseTranslateResult> = {}
): UseTranslateResult {
  return {
    translateProvider: "TestProvider",
    translateModel: "",
    translateInput: "",
    sourceLanguage: "auto",
    targetLanguage: "en",
    translateBusy: false,
    translateError: "",
    translateResult: "Mock translation",
    onSubmit: vi.fn(),
    onProviderChange: vi.fn(),
    onModelChange: vi.fn(),
    onInputChange: vi.fn(),
    onSourceLanguageChange: vi.fn(),
    onTargetLanguageChange: vi.fn(),
    ...overrides
  };
}

const defaultVoiceOptions: VoiceInfo[] = [
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
];

const defaultPodcasts: AudioOverviewPodcast[] = [
  {
    id: 12,
    topic: "播客脚本测试",
    language: "zh",
    audio_path: null,
    created_at: "2026-03-07T10:00:00Z",
    updated_at: "2026-03-07T10:00:00Z",
    script_lines: [
      { role: "A", text: "第一段内容" },
      { role: "B", text: "第二段内容" }
    ]
  }
];

export function createAudioOverviewController(
  overrides: Partial<UseAudioOverviewResult> = {}
): UseAudioOverviewResult {
  return {
    audioOverviewBusy: false,
    audioOverviewSaving: false,
    audioOverviewSynthBusy: false,
    audioOverviewListBusy: false,
    audioOverviewError: "",
    audioOverviewInfo: "",
    audioOverviewProvider: "DashScope",
    audioOverviewModel: "",
    audioOverviewLanguage: "zh",
    audioOverviewPodcastId: 12,
    audioOverviewMergeStrategy: "auto",
    audioOverviewTopic: "AI 对个人学习习惯的影响",
    audioOverviewTurnCount: 8,
    audioOverviewAdvancedOpen: false,
    audioOverviewMenuOpen: false,
    synthBarAdvancedOpen: false,
    audioOverviewScriptLines: [
      { role: "A", text: "第一段内容" },
      { role: "B", text: "第二段内容" }
    ],
    audioOverviewVoiceOptions: defaultVoiceOptions,
    audioOverviewVoiceA: "zh-CN-YunxiNeural",
    audioOverviewVoiceB: "zh-CN-XiaoxiaoNeural",
    audioOverviewRate: "+0%",
    audioOverviewGapMs: 250,
    audioOverviewAudioUrl: "",
    audioOverviewPodcasts: defaultPodcasts,
    currentAudioOverviewLabel: "播客 #12",
    onGenerateScript: vi.fn(),
    onNewDraft: vi.fn(),
    onToggleMenu: vi.fn(),
    onDeleteCurrent: vi.fn(),
    onTopicChange: vi.fn(),
    onToggleAdvanced: vi.fn(),
    onLanguageChange: vi.fn(),
    onProviderChange: vi.fn(),
    onModelChange: vi.fn(),
    onTurnCountChange: vi.fn(),
    onSaveScript: vi.fn(),
    onCopyScript: vi.fn(),
    onExportScript: vi.fn(),
    onLineRoleChange: vi.fn(),
    onRemoveLine: vi.fn(),
    onLineTextChange: vi.fn(),
    onAddLine: vi.fn(),
    onVoiceAChange: vi.fn(),
    onVoiceBChange: vi.fn(),
    onToggleSynthAdvanced: vi.fn(),
    onSynthesize: vi.fn(),
    onRateChange: vi.fn(),
    onGapMsChange: vi.fn(),
    onMergeStrategyChange: vi.fn(),
    onRefreshList: vi.fn(),
    onLoadPodcast: vi.fn(),
    ...overrides
  };
}

export function createVoiceDesignController(
  overrides: Partial<VoiceDesignController> = {}
): VoiceDesignController {
  return {
    designName: "",
    designLanguage: "zh",
    designPrompt: "",
    designPreviewText: "",
    designPreviewAudio: "",
    designBusy: false,
    designError: "",
    designInfo: "",
    designVoices: [],
    designListBusy: false,
    onNameChange: vi.fn(),
    onLanguageChange: vi.fn(),
    onPromptChange: vi.fn(),
    onPreviewTextChange: vi.fn(),
    onSubmit: vi.fn(),
    onRefresh: vi.fn(),
    onDeleteVoice: vi.fn(),
    ...overrides
  };
}

export function createVoiceCloneController(
  overrides: Partial<VoiceCloneController> = {}
): VoiceCloneController {
  return {
    cloneName: "",
    cloneAudioFile: null as any,
    cloneBusy: false,
    cloneError: "",
    cloneInfo: "",
    cloneVoices: [],
    cloneListBusy: false,
    onNameChange: vi.fn(),
    onAudioFileChange: vi.fn(),
    onSubmit: vi.fn(),
    onRefresh: vi.fn(),
    onDeleteVoice: vi.fn(),
    ...overrides
  };
}
