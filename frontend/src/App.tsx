import { useRef, useState } from "react";
import type { ChatMessage } from "./api";
import {
  getDefaultText,
  type ActiveTab
} from "./appConfig";
import AppSidebar from "./components/AppSidebar";
import useChat from "./hooks/useChat";
import useAudioOverview from "./hooks/useAudioOverview";
import useSettings from "./hooks/useSettings";
import useTts from "./hooks/useTts";
import useTranslate from "./hooks/useTranslate";
import useVoiceChat from "./hooks/useVoiceChat";
import useVoiceManagement from "./hooks/useVoiceManagement";
import AudioOverviewPage from "./pages/AudioOverviewPage";
import ChatPage from "./pages/ChatPage";
import SettingsPage from "./pages/SettingsPage";
import TranslatePage from "./pages/TranslatePage";
import VoiceCenterPage from "./pages/VoiceCenterPage";
import { I18nProvider, createInlineTranslator, localizeText, type UiLanguage } from "./i18n";
import { formatErrorMessage } from "./utils/errorFormatting";

type ConversationArchiveEntry = {
  id: string;
  content: string;
  chatMessages: ChatMessage[];
  voiceMessages: ChatMessage[];
  chatGroupId: string;
  voiceGroupId: string;
  updatedAt: number;
};

const CONVERSATION_HISTORY_STORAGE_KEY = "vs_conversation_history";
const MAX_CONVERSATION_HISTORY = 30;

function createLocalArchiveId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `conv-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function loadConversationHistory(): ConversationArchiveEntry[] {
  try {
    const raw = localStorage.getItem(CONVERSATION_HISTORY_STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveConversationHistory(entries: ConversationArchiveEntry[]): void {
  try {
    localStorage.setItem(CONVERSATION_HISTORY_STORAGE_KEY, JSON.stringify(entries));
  } catch {
    // Ignore storage failures in browser-restricted contexts.
  }
}

function firstMeaningfulMessage(messages: ChatMessage[]): string {
  const preferred = messages.find((item) => item.role === "user" && item.content.trim());
  if (preferred) {
    return preferred.content.trim();
  }
  const fallback = messages.find((item) => item.content.trim());
  return fallback ? fallback.content.trim() : "";
}

function buildConversationHistoryEntry(params: {
  chatMessages: ChatMessage[];
  voiceMessages: ChatMessage[];
  chatGroupId: string;
  voiceGroupId: string;
  language: UiLanguage;
}): ConversationArchiveEntry | null {
  const chatMessages = Array.isArray(params.chatMessages) ? params.chatMessages : [];
  const voiceMessages = Array.isArray(params.voiceMessages) ? params.voiceMessages : [];
  if (chatMessages.length === 0 && voiceMessages.length === 0) {
    return null;
  }

  const baseText = firstMeaningfulMessage(chatMessages) || firstMeaningfulMessage(voiceMessages);
  const preview = baseText.length > 30
    ? `${baseText.slice(0, 30)}...`
    : baseText || localizeText(params.language, "未命名会话", "Untitled Conversation");
  const isVoiceOnly = chatMessages.length === 0 && voiceMessages.length > 0;
  const label = isVoiceOnly
    ? `${createInlineTranslator(params.language)("[语音]", "[Voice]")} ${preview}`
    : preview;

  return {
    id: createLocalArchiveId(),
    content: label,
    chatMessages: chatMessages.map((item) => ({ ...item })),
    voiceMessages: voiceMessages.map((item) => ({ ...item })),
    chatGroupId: params.chatGroupId.trim(),
    voiceGroupId: params.voiceGroupId.trim(),
    updatedAt: Date.now(),
  };
}

function areMessageListsEqual(left: ChatMessage[], right: ChatMessage[]): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

function areArchiveEntriesEquivalent(
  left: ConversationArchiveEntry | null,
  right: ConversationArchiveEntry | null
): boolean {
  if (!left || !right) {
    return false;
  }
  return (
    left.chatGroupId === right.chatGroupId &&
    left.voiceGroupId === right.voiceGroupId &&
    areMessageListsEqual(left.chatMessages, right.chatMessages) &&
    areMessageListsEqual(left.voiceMessages, right.voiceMessages)
  );
}

function resolveVoiceCenterTab(activeTab: ActiveTab): "tts" | "design" | "clone" | "transcribe" {
  switch (activeTab) {
    case "voice_design":
      return "design";
    case "voice_clone":
      return "clone";
    case "transcription":
      return "transcribe";
    case "tts":
    case "voice_center":
    default:
      return "tts";
  }
}

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("chat");
  const [conversationHistory, setConversationHistory] = useState<ConversationArchiveEntry[]>(
    () => loadConversationHistory()
  );
  const currentArchiveBaselineRef = useRef<ConversationArchiveEntry | null>(null);
  const isDesktopEmbedded =
    typeof window !== "undefined" &&
    Object.prototype.hasOwnProperty.call(window, "pywebview");
  const settings = useSettings({ formatErrorMessage });
  const uiLanguage = settings.displayLanguage;
  const tts = useTts({
    defaultText: getDefaultText(createInlineTranslator(uiLanguage)),
    formatErrorMessage,
    language: uiLanguage,
  });
  const chat = useChat({
    formatErrorMessage,
    providerOptions: settings.providerOptions,
    providerModelCatalog: settings.providerModelCatalog,
    preferredProvider: settings.settingsProvider,
    language: uiLanguage,
  });
  const voiceChat = useVoiceChat({
    formatErrorMessage,
    providerOptions: settings.providerOptions,
    providerModelCatalog: settings.providerModelCatalog,
    preferredProvider: settings.settingsProvider,
    language: uiLanguage,
  });
  const audioOverview = useAudioOverview({ voices: tts.voices, formatErrorMessage, language: uiLanguage });
  const voiceManagement = useVoiceManagement({ formatErrorMessage, language: uiLanguage });
  const { errorRuntimeContext } = settings;

  const translate = useTranslate({ formatErrorMessage, language: uiLanguage });
  const workspaceClassName = `vsWorkspaceViewportInner is-${activeTab.replace(/_/g, "-")}`;
  const shouldShowVoiceCenter =
    activeTab === "voice_center" ||
    activeTab === "tts" ||
    activeTab === "voice_design" ||
    activeTab === "voice_clone" ||
    activeTab === "transcription";

  function pushConversationHistory(entry: ConversationArchiveEntry | null) {
    if (!entry) {
      return;
    }
    setConversationHistory((prev) => {
      const baseline = currentArchiveBaselineRef.current;
      if (baseline && areArchiveEntriesEquivalent(entry, baseline)) {
        return prev;
      }
      const duplicate = prev.find((item) => areArchiveEntriesEquivalent(item, entry));
      const nextEntry = baseline
        ? { ...entry, id: baseline.id }
        : duplicate
          ? { ...entry, id: duplicate.id }
          : entry;
      const filtered = prev.filter((item) => item.id !== nextEntry.id);
      const next = [nextEntry, ...filtered].slice(0, MAX_CONVERSATION_HISTORY);
      saveConversationHistory(next);
      currentArchiveBaselineRef.current = nextEntry;
      return next;
    });
  }

  function archiveActiveConversation() {
    pushConversationHistory(
      buildConversationHistoryEntry({
        chatMessages: chat.chatMessages,
        voiceMessages: voiceChat.voiceChatMessages,
        chatGroupId: chat.chatMemoryGroupId,
        voiceGroupId: voiceChat.voiceChatMemoryGroupId,
        language: uiLanguage,
      })
    );
  }

  function handleNewChatSession() {
    archiveActiveConversation();
    currentArchiveBaselineRef.current = null;
    chat.onNewSession();
    voiceChat.onResetSession();
    setActiveTab("chat");
  }

  function handleHistorySelect(id: string) {
    const target = conversationHistory.find((item) => item.id === id);
    if (!target) {
      return;
    }
    const sameAsCurrent =
      target.chatGroupId === chat.chatMemoryGroupId &&
      target.voiceGroupId === voiceChat.voiceChatMemoryGroupId &&
      areMessageListsEqual(target.chatMessages, chat.chatMessages) &&
      areMessageListsEqual(target.voiceMessages, voiceChat.voiceChatMessages);
    if (!sameAsCurrent) {
      archiveActiveConversation();
    }
    currentArchiveBaselineRef.current = target;
    setActiveTab("chat");
    chat.replaceSession(target.chatMessages, target.chatGroupId);
    voiceChat.replaceSession(target.voiceMessages, target.voiceGroupId);
  }

  function handleClearConversationHistory() {
    setConversationHistory([]);
    saveConversationHistory([]);
  }

  function handleDeleteConversationHistoryItem(id: string) {
    setConversationHistory((prev) => {
      const next = prev.filter((item) => item.id !== id);
      saveConversationHistory(next);
      return next;
    });
  }

  return (
    <I18nProvider language={uiLanguage}>
      <main className={isDesktopEmbedded ? "vsApp desktopEmbedded" : "vsApp"}>
        <AppSidebar
          activeTab={activeTab}
          chatHistoryItems={conversationHistory.map((item) => ({
            id: item.id,
            content: item.content,
          }))}
          onTabChange={setActiveTab}
          onNewChatSession={handleNewChatSession}
          onHistorySelect={handleHistorySelect}
          onClearHistory={handleClearConversationHistory}
          onDeleteHistoryItem={handleDeleteConversationHistoryItem}
        />

        <section className="vsMainScrollArea">
          <div className="vsContentMaxContainer">
            <div className="vsWorkspaceViewport">
              <div className={workspaceClassName}>
                {activeTab === "chat" ? (
                  <ChatPage
                    chat={chat}
                    voiceChat={voiceChat}
                    errorRuntimeContext={errorRuntimeContext}
                  />
                ) : null}

                {shouldShowVoiceCenter ? (
                  <VoiceCenterPage
                    initialSubTab={resolveVoiceCenterTab(activeTab)}
                    tts={tts}
                    design={voiceManagement.design}
                    clone={voiceManagement.clone}
                    errorRuntimeContext={errorRuntimeContext}
                  />
                ) : null}

                {activeTab === "translate" ? (
                  <TranslatePage translate={translate} errorRuntimeContext={errorRuntimeContext} />
                ) : null}

                {activeTab === "audio_overview" ? (
                  <AudioOverviewPage audioOverview={audioOverview} errorRuntimeContext={errorRuntimeContext} />
                ) : null}

                {activeTab === "settings" ? <SettingsPage settings={settings} /> : null}
              </div>
            </div>
          </div>
        </section>
      </main>
    </I18nProvider>
  );
}
