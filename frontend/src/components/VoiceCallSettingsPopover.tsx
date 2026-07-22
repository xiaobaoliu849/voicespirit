import { useEffect, useRef, useState } from "react";
import type { UseVoiceChatResult } from "../hooks/useVoiceChat";
import {
  PRESET_LANGUAGE_PAIRS,
  formatTranslationSummary,
} from "../hooks/useVoiceChatHelpers";

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
  const [panelMaxHeight, setPanelMaxHeight] = useState(480);
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
      setPanelMaxHeight(Math.max(200, Math.min(520, upward ? spaceAbove : spaceBelow)));
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

  const summaryText = voiceChat.voiceChatLiveTranslate
    ? `${voiceChat.voiceChatModel} · ${formatTranslationSummary(
        voiceChat.voiceChatTranslationMode,
        voiceChat.voiceChatSourceLanguageCode,
        voiceChat.voiceChatTargetLanguageCode
      )}`
    : `${voiceChat.voiceChatModel} · ${voiceChat.voiceChatVoiceLabel}`;

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
        <span className="vsVoiceSettingsSummaryText">{summaryText}</span>
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
            <div className="vsVoiceSettingsSection vsVoiceTranslationCard">
              <div className="vsVoiceSettingsSectionTitle">{t("翻译配置", "Translation Settings")}</div>
              
              {/* Translation Mode Segmented Switch */}
              <div className="vsTranslationModeSegment">
                <button
                  type="button"
                  className={`vsSegmentBtn${voiceChat.voiceChatTranslationMode === "bidirectional" ? " active" : ""}`}
                  onClick={() => voiceChat.onTranslationModeChange("bidirectional")}
                >
                  {t("双向互翻 ⇄", "Bi-directional ⇄")}
                </button>
                <button
                  type="button"
                  className={`vsSegmentBtn${voiceChat.voiceChatTranslationMode === "unidirectional" ? " active" : ""}`}
                  onClick={() => voiceChat.onTranslationModeChange("unidirectional")}
                >
                  {t("单向翻译 →", "One-way →")}
                </button>
              </div>

              {/* Quick Preset Pills */}
              <div className="vsPresetPairSection">
                <div className="vsPresetSubTitle">{t("常用语对", "Popular Pairs")}</div>
                <div className="vsPresetPillsGroup">
                  {PRESET_LANGUAGE_PAIRS.map((pair) => {
                    const isSelected =
                      voiceChat.voiceChatSourceLanguageCode === pair.source &&
                      voiceChat.voiceChatTargetLanguageCode === pair.target;
                    return (
                      <button
                        key={pair.label}
                        type="button"
                        className={`vsPresetPillBtn${isSelected ? " active" : ""}`}
                        onClick={() => voiceChat.onPresetLanguagePairSelect(pair.source, pair.target)}
                      >
                        {pair.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Language Pair Selectors & Swap Button */}
              <div className="vsLanguageSelectorBox">
                <div className="vsLanguageSelectGroup">
                  <label className="vsLanguageSelectLabel">
                    {voiceChat.voiceChatTranslationMode === "bidirectional"
                      ? t("语言 A", "Language A")
                      : t("源语言", "Source Lang")}
                  </label>
                  <select
                    className="vsLanguageSelectDropdown"
                    value={voiceChat.voiceChatSourceLanguageCode}
                    onChange={(e) => voiceChat.onSourceLanguageCodeChange(e.target.value)}
                  >
                    {voiceChat.voiceChatTargetLanguageOptions.map((opt) => (
                      <option key={`src-${opt.value}`} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  type="button"
                  className="vsVoiceSettingsSwapBtn"
                  onClick={voiceChat.onSwapLanguages}
                  title={t("一键颠倒语言", "Swap languages")}
                >
                  ⇄
                </button>

                <div className="vsLanguageSelectGroup">
                  <label className="vsLanguageSelectLabel">
                    {voiceChat.voiceChatTranslationMode === "bidirectional"
                      ? t("语言 B", "Language B")
                      : t("目标语言", "Target Lang")}
                  </label>
                  <select
                    className="vsLanguageSelectDropdown"
                    value={voiceChat.voiceChatTargetLanguageCode}
                    onChange={(e) => voiceChat.onTargetLanguageCodeChange(e.target.value)}
                  >
                    {voiceChat.voiceChatTargetLanguageOptions.map((opt) => (
                      <option key={`tgt-${opt.value}`} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Single Direction Echo Checkbox */}
              {voiceChat.voiceChatTranslationMode === "unidirectional" ? (
                <label
                  className="vsVoiceSettingsEcho"
                  title={t("输入已经是目标语言时也朗读出来", "Echo speech that is already in the target language")}
                >
                  <input
                    type="checkbox"
                    checked={voiceChat.voiceChatEchoTargetLanguage}
                    onChange={(e) => voiceChat.onEchoTargetLanguageChange(e.target.checked)}
                  />
                  <span>{t("同语回放", "Echo target language")}</span>
                </label>
              ) : null}
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
