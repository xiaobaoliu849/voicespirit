import { useEffect, useRef, useState } from "react";
import type { UseVoiceChatResult } from "../hooks/useVoiceChat";

type Translator = (zh: string, en: string) => string;

type Props = {
  voiceChat: UseVoiceChatResult;
  t: Translator;
  disabled?: boolean;
  onOpenSettings?: () => void;
};

function modelHint(model: string, t: Translator): string {
  const normalized = model.toLowerCase();
  if (normalized.includes("live-translate") || normalized.includes("livetranslate")) {
    return t("实时翻译", "Live translate");
  }
  if (normalized.includes("qwen-audio")) {
    return t("Qwen-Audio 原生实时", "Qwen-Audio native");
  }
  if (normalized.includes("omni")) {
    return t("全模态实时", "Omni realtime");
  }
  return t("实时语音", "Realtime");
}

export default function VoiceCallSettingsPopover({ voiceChat, t, disabled = false, onOpenSettings }: Props) {
  const [open, setOpen] = useState(false);
  const [openUpward, setOpenUpward] = useState(true);
  const [panelMaxHeight, setPanelMaxHeight] = useState(420);
  // "" follows the active provider; "__none" means the user collapsed everything.
  const [expandedOverride, setExpandedOverride] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);
  const expandedProvider = expandedOverride === "__none"
    ? ""
    : expandedOverride || voiceChat.voiceChatProvider;

  function handleModelSelect(provider: string, model: string) {
    if (provider !== voiceChat.voiceChatProvider) {
      voiceChat.onProviderChange(provider);
    }
    voiceChat.onModelChange(model);
  }

  // Measure the free space around the summary button before opening: the
  // panel is absolutely positioned and would otherwise grow past the app
  // container (overflow: hidden) and get its top content clipped.
  function handleToggle() {
    if (!open && rootRef.current) {
      const rect = rootRef.current.getBoundingClientRect();
      const margin = 16;
      const spaceAbove = rect.top - margin;
      const spaceBelow = window.innerHeight - rect.bottom - margin;
      const upward = spaceAbove >= spaceBelow;
      setOpenUpward(upward);
      setPanelMaxHeight(Math.max(160, Math.min(420, upward ? spaceAbove : spaceBelow)));
    }
    setOpen((prev) => !prev);
  }

  // Close on outside click / Escape, mirroring the AppSidebar dropdown.
  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div className="vsVoiceSettings" ref={rootRef}>
      <button
        type="button"
        className="vsVoiceSettingsSummary"
        onClick={handleToggle}
        disabled={disabled}
        aria-haspopup="dialog"
        aria-expanded={open}
        title={t("通话设置", "Call settings")}
      >
        <span className="vsVoiceSettingsSummaryText">
          {voiceChat.voiceChatModel} · {voiceChat.voiceChatVoiceLabel}
        </span>
        <svg
          className="vsVoiceSettingsSummaryChevron"
          width="10"
          height="6"
          viewBox="0 0 10 6"
          fill="none"
          aria-hidden="true"
        >
          <path d="M1 1L5 5L9 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open ? (
        <div
          className={`vsVoiceSettingsPanel${openUpward ? "" : " below"}`}
          style={{ maxHeight: `${panelMaxHeight}px` }}
          role="dialog"
          aria-label={t("通话设置", "Call settings")}
        >
          <div className="vsVoiceSettingsSection">
            <div className="vsVoiceSettingsSectionTitle">{t("模型", "Model")}</div>
            <div className="vsVoiceSettingsList">
              {voiceChat.voiceChatRealtimeChoicesByProvider.map((group) => {
                const isCurrent = group.provider === voiceChat.voiceChatProvider;
                const isExpanded = group.provider === expandedProvider;
                return (
                  <div key={group.provider}>
                    <button
                      type="button"
                      className={`vsVoiceSettingsRow vsVoiceSettingsProviderRow${isCurrent ? " selected" : ""}`}
                      aria-expanded={isExpanded}
                      onClick={() =>
                        setExpandedOverride(isExpanded ? "__none" : group.provider)
                      }
                    >
                      <span className="vsVoiceSettingsProviderCheck" aria-hidden="true">
                        {isCurrent ? "✓" : ""}
                      </span>
                      <span className="vsVoiceSettingsRowLabel">{group.provider}</span>
                      <span className={`vsVoiceSettingsProviderChevron${isExpanded ? " expanded" : ""}`} aria-hidden="true">›</span>
                    </button>
                    {isExpanded ? (
                      <div className="vsVoiceSettingsModelList">
                        {group.models.map((model) => (
                          <button
                            key={model}
                            type="button"
                            className={`vsVoiceSettingsRow${isCurrent && model === voiceChat.voiceChatModel ? " selected" : ""}`}
                            aria-current={isCurrent && model === voiceChat.voiceChatModel ? "true" : undefined}
                            onClick={() => handleModelSelect(group.provider, model)}
                          >
                            <span className="vsVoiceSettingsRowLabel">{model}</span>
                            <span className="vsVoiceSettingsRowHint">{modelHint(model, t)}</span>
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="vsVoiceSettingsSection">
            <div className="vsVoiceSettingsSectionTitle">{t("音色", "Voice")}</div>
            <div className="vsVoiceSettingsList">
              {voiceChat.voiceChatVoiceOptions.map((item) => (
                <button
                  key={item.value}
                  type="button"
                  className={`vsVoiceSettingsRow${item.value === voiceChat.voiceChatVoice ? " selected" : ""}`}
                  aria-current={item.value === voiceChat.voiceChatVoice ? "true" : undefined}
                  onClick={() => {
                    voiceChat.onVoiceChange(item.value);
                    setOpen(false);
                  }}
                >
                  <span className="vsVoiceSettingsRowLabel">{item.label}</span>
                  {item.description ? (
                    <span className="vsVoiceSettingsRowHint">{item.description}</span>
                  ) : null}
                </button>
              ))}
            </div>
          </div>

          {voiceChat.voiceChatLiveTranslate ? (
            <div className="vsVoiceSettingsSection">
              <div className="vsVoiceSettingsSectionTitle">{t("翻译", "Translation")}</div>
              <div className="vsVoiceSettingsList vsVoiceSettingsLanguageList">
                {voiceChat.voiceChatTargetLanguageOptions.map((item) => (
                  <button
                    key={item.value}
                    type="button"
                    className={`vsVoiceSettingsRow${item.value === voiceChat.voiceChatTargetLanguageCode ? " selected" : ""}`}
                    aria-current={item.value === voiceChat.voiceChatTargetLanguageCode ? "true" : undefined}
                    onClick={() => {
                      voiceChat.onTargetLanguageCodeChange(item.value);
                      setOpen(false);
                    }}
                  >
                    <span className="vsVoiceSettingsRowLabel">{item.label}</span>
                  </button>
                ))}
              </div>
              <label
                className="vsVoiceSettingsEcho"
                title={t("输入已经是目标语言时也朗读出来", "Echo speech that is already in the target language")}
              >
                <input
                  type="checkbox"
                  checked={voiceChat.voiceChatEchoTargetLanguage}
                  onChange={(e) => voiceChat.onEchoTargetLanguageChange(e.target.checked)}
                />
                <span>{t("同语回放", "Echo")}</span>
              </label>
            </div>
          ) : null}

          {onOpenSettings ? (
            <div className="vsVoiceSettingsFooter">
              <button
                type="button"
                className="vsVoiceSettingsRow vsVoiceSettingsManageRow"
                onClick={() => {
                  setOpen(false);
                  onOpenSettings();
                }}
              >
                <span className="vsVoiceSettingsRowLabel">{t("管理模型", "Manage models")}</span>
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
