import { useState } from "react";
import {
  DEFAULT_TEXT,
  type ActiveTab
} from "./appConfig";
import AppSidebar from "./components/AppSidebar";
import useChat from "./hooks/useChat";
import useAudioOverview from "./hooks/useAudioOverview";
import useSettings from "./hooks/useSettings";
import useTts from "./hooks/useTts";
import useTranslate from "./hooks/useTranslate";
import useVoiceManagement from "./hooks/useVoiceManagement";
import AudioOverviewPage from "./pages/AudioOverviewPage";
import ChatPage from "./pages/ChatPage";
import SettingsPage from "./pages/SettingsPage";
import TtsPage from "./pages/TtsPage";
import TranslatePage from "./pages/TranslatePage";
import VoiceClonePage from "./pages/VoiceClonePage";
import VoiceDesignPage from "./pages/VoiceDesignPage";
import { formatErrorMessage } from "./utils/errorFormatting";

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("chat");
  const tts = useTts({ defaultText: DEFAULT_TEXT, formatErrorMessage });
  const chat = useChat({ formatErrorMessage });
  const audioOverview = useAudioOverview({ voices: tts.voices, formatErrorMessage });
  const settings = useSettings({ formatErrorMessage });
  const voiceManagement = useVoiceManagement({ formatErrorMessage });
  const { errorRuntimeContext } = settings;

  const translate = useTranslate({ formatErrorMessage });

  function handleNewChatSession() {
    chat.onNewSession();
    setActiveTab("chat");
  }

  function handleHistorySelect(content: string) {
    setActiveTab("chat");
    chat.onSelectHistory(content);
  }

  return (
    <main className="vsApp">
      <AppSidebar
        activeTab={activeTab}
        chatHistoryItems={chat.chatHistoryItems}
        onTabChange={setActiveTab}
        onNewChatSession={handleNewChatSession}
        onHistorySelect={handleHistorySelect}
      />

      <section className="legacyMain">
        {activeTab === "chat" ? (
          <ChatPage chat={chat} errorRuntimeContext={errorRuntimeContext} />
        ) : null}

        {activeTab === "tts" ? (
          <TtsPage tts={tts} errorRuntimeContext={errorRuntimeContext} />
        ) : null}

        {activeTab === "translate" ? (
          <TranslatePage translate={translate} errorRuntimeContext={errorRuntimeContext} />
        ) : null}

        {activeTab === "voice_design" ? (
          <VoiceDesignPage
            design={voiceManagement.design}
            errorRuntimeContext={errorRuntimeContext}
          />
        ) : null}

        {activeTab === "voice_clone" ? (
          <VoiceClonePage
            clone={voiceManagement.clone}
            errorRuntimeContext={errorRuntimeContext}
          />
        ) : null}

        {activeTab === "audio_overview" ? (
          <AudioOverviewPage audioOverview={audioOverview} errorRuntimeContext={errorRuntimeContext} />
        ) : null}

        {activeTab === "settings" ? <SettingsPage settings={settings} /> : null}
      </section>
    </main>
  );
}
