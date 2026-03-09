export type ActiveTab =
  | "tts"
  | "chat"
  | "translate"
  | "voice_design"
  | "voice_clone"
  | "audio_overview"
  | "transcription"
  | "settings";

export type SidebarItem = {
  tab: ActiveTab;
  label: string;
  icon: string;
};

export type QuickAction = {
  title: string;
  icon: string;
  prompt: string;
};

export type HistoryItem = {
  id: string;
  content: string;
};

export const DEFAULT_TEXT = "你好，这是 VoiceSpirit Web 迁移阶段的语音测试。";

export const PROVIDERS = [
  "Google",
  "DashScope",
  "DeepSeek",
  "OpenRouter",
  "SiliconFlow",
  "Groq"
];

export const SIDEBAR_ITEMS: SidebarItem[] = [
  { tab: "chat", label: "聊天", icon: "聊" },
  { tab: "translate", label: "翻译", icon: "译" },
  { tab: "tts", label: "语音", icon: "声" },
  { tab: "voice_design", label: "设计音色", icon: "设" },
  { tab: "voice_clone", label: "音色克隆", icon: "克" },
  { tab: "audio_overview", label: "播客/多人对话", icon: "播" },
  { tab: "transcription", label: "转写", icon: "转" },
  { tab: "settings", label: "设置", icon: "置" }
];

export const CHAT_QUICK_ACTIONS: QuickAction[] = [
  {
    title: "写一封邮件",
    icon: "邮",
    prompt: "请帮我起草一封语气专业但不生硬的项目进度更新邮件。"
  },
  {
    title: "写段代码",
    icon: "码",
    prompt: "请帮我写一个 TypeScript 工具函数，用于安全解析 JSON 并返回默认值。"
  },
  {
    title: "想想方案",
    icon: "想",
    prompt: "围绕语音类 AI 应用，给我 10 个可以快速上线验证的产品想法。"
  },
  {
    title: "提炼要点",
    icon: "总",
    prompt: "请把下面内容总结为 5 个要点，并给出 2 条可执行建议。"
  }
];
