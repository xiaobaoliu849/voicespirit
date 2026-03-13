import { useEffect, useState } from "react";
import { useI18n } from "../i18n";
import TtsPage from "./TtsPage";
import VoiceDesignPage from "./VoiceDesignPage";
import VoiceClonePage from "./VoiceClonePage";
import { TranscriptionPage } from "./TranscriptionPage";
import type { ErrorRuntimeContext } from "../types/ui";
import type { UseTtsResult } from "../hooks/useTts";
import type { VoiceCloneController, VoiceDesignController } from "../hooks/useVoiceManagement";

export type VoiceCenterSubTab = "tts" | "design" | "clone" | "transcribe";

type Props = {
  initialSubTab?: VoiceCenterSubTab;
  tts: UseTtsResult;
  design: VoiceDesignController;
  clone: VoiceCloneController;
  errorRuntimeContext: ErrorRuntimeContext;
};

export default function VoiceCenterPage({
  initialSubTab = "tts",
  tts,
  design,
  clone,
  errorRuntimeContext
}: Props) {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<VoiceCenterSubTab>(initialSubTab);

  useEffect(() => {
    setActiveTab(initialSubTab);
  }, [initialSubTab]);

  const tabs = [
    { id: "tts" as const, label: t("文本到音频", "Text to Audio") },
    { id: "design" as const, label: t("设计音色", "Voice Design") },
    { id: "clone" as const, label: t("音色克隆", "Voice Clone") },
    { id: "transcribe" as const, label: t("一键转写", "Transcribe") },
  ];

  return (
    <div className="vsVoiceCenter">
      <div className="vsVoiceCenterNav">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`vsVoiceSubTab ${isActive ? "active" : ""}`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      <div className="vsVoiceCenterContent">
        <div className="vsVoiceCenterScroll">
          {activeTab === "tts" && (
             <div className="vsVoiceSubContent"><TtsPage tts={tts} errorRuntimeContext={errorRuntimeContext} /></div>
          )}
          {activeTab === "design" && (
             <div className="vsVoiceSubContent"><VoiceDesignPage design={design} errorRuntimeContext={errorRuntimeContext} /></div>
          )}
          {activeTab === "clone" && (
             <div className="vsVoiceSubContent"><VoiceClonePage clone={clone} errorRuntimeContext={errorRuntimeContext} /></div>
          )}
          {activeTab === "transcribe" && (
             <div className="vsVoiceSubContent"><TranscriptionPage /></div>
          )}
        </div>
      </div>
    </div>
  );
}
