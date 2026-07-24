import { useEffect, useRef, useState } from "react";
import type { UseVoiceChatResult } from "../hooks/useVoiceChat";
import {
  DASHSCOPE_PROVIDER,
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
  const [flyoutToLeft, setFlyoutToLeft] = useState(false);
  const [panelMaxHeight, setPanelMaxHeight] = useState(480);
  const [activeTab, setActiveTab] = useState<"model" | "voice" | "translation">("model");
  const [expandedOverride, setExpandedOverride] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);
  const expandedProvider = expandedOverride === "__none"
    ? ""
    : expandedOverride || voiceChat.voiceChatProvider;

  const isDashScopeLiveTranslate =
    voiceChat.voiceChatProvider === DASHSCOPE_PROVIDER && voiceChat.voiceChatLiveTranslate;

  function handleModelSelect(provider: string, model: string) {
    if (provider !== voiceChat.voiceChatProvider) {
      voiceChat.onProviderChange(provider);
    }
    voiceChat.onModelChange(model);
  }

  function handleToggle() {
    if (!open && rootRef.current) {
      const rect = rootRef.current.getBoundingClientRect();
      const margin = 16;
      const spaceAbove = rect.top - margin;
      const spaceBelow = window.innerHeight - rect.bottom - margin;
      const upward = spaceAbove >= spaceBelow;
      setOpenUpward(upward);
      setFlyoutToLeft(rect.left + 540 > window.innerWidth);
      setPanelMaxHeight(Math.max(200, Math.min(520, upward ? spaceAbove : spaceBelow)));
    }
    setOpen((prev) => !prev);
  }

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

  // Voice Clone label fix: when voice clone is enabled, prioritize showing Voice Clone label
  const activeVoiceLabel = voiceChat.voiceChatEnableVoiceClone
    ? t("声音复刻 (本人音色)", "Voice Clone (Your Voice)")
    : voiceChat.voiceChatVoiceLabel;

  const summaryText = voiceChat.voiceChatLiveTranslate
    ? `${voiceChat.voiceChatModel} · ${
        voiceChat.voiceChatEnableVoiceClone
          ? t("声音复刻 (本人)", "Voice Clone")
          : formatTranslationSummary(
              voiceChat.voiceChatTranslationMode,
              voiceChat.voiceChatSourceLanguageCode,
              voiceChat.voiceChatTargetLanguageCode
            )
      }`
    : `${voiceChat.voiceChatModel} · ${activeVoiceLabel}`;

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
          {/* Zcode-style Cascading Tab Navigation Header */}
          <div className="vsCascadingTabBar">
            <button
              type="button"
              className={`vsCascadingTabItem${activeTab === "model" ? " active" : ""}`}
              onClick={() => setActiveTab("model")}
            >
              🤖 {t("模型", "Model")}
            </button>
            <button
              type="button"
              className={`vsCascadingTabItem${activeTab === "voice" ? " active" : ""}`}
              onClick={() => setActiveTab("voice")}
            >
              🎙️ {t("音色", "Voice")}
            </button>
            {voiceChat.voiceChatLiveTranslate ? (
              <button
                type="button"
                className={`vsCascadingTabItem${activeTab === "translation" ? " active" : ""}`}
                onClick={() => setActiveTab("translation")}
              >
                🌐 {t("同传与复刻", "Translate & Clone")}
              </button>
            ) : null}
          </div>

          {/* TAB 1: MODEL SELECTION - Zcode Horizontal Flyout Submenu */}
          {activeTab === "model" ? (
            <div className="vsVoiceSettingsSection">
              <div className="vsVoiceSettingsList">
                {voiceChat.voiceChatRealtimeChoicesByProvider.map((group) => {
                  const isCurrent = group.provider === voiceChat.voiceChatProvider;
                  const isExpanded = group.provider === expandedProvider;
                  return (
                    <div
                      key={group.provider}
                      className="vsVoiceSettingsProviderGroup"
                      onMouseEnter={() => setExpandedOverride(group.provider)}
                    >
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
                        <div className={`vsVoiceSettingsModelListFlyout${flyoutToLeft ? " flyLeft" : ""}`}>
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
          ) : null}

          {/* TAB 2: VOICE SELECTION */}
          {activeTab === "voice" ? (
            <div className="vsVoiceSettingsSection">
              {voiceChat.voiceChatEnableVoiceClone ? (
                <div className="vsVoiceCloneActiveBadge" style={{ padding: "8px 12px", marginBottom: 8, background: "rgba(96, 165, 250, 0.12)", border: "1px solid rgba(96, 165, 250, 0.3)", borderRadius: 8, fontSize: 12, color: "#60a5fa" }}>
                  ✨ {t("声音复刻已激活：将使用您本人的声音朗读外语", "Voice Clone active: Speaking in your own voice")}
                </div>
              ) : null}
              <div className="vsVoiceSettingsList" style={{ maxHeight: 280, overflowY: "auto" }}>
                {voiceChat.voiceChatVoiceOptions.map((item) => (
                  <button
                    key={item.value}
                    type="button"
                    className={`vsVoiceSettingsRow${!voiceChat.voiceChatEnableVoiceClone && item.value === voiceChat.voiceChatVoice ? " selected" : ""}`}
                    onClick={() => {
                      if (voiceChat.voiceChatEnableVoiceClone) {
                        voiceChat.onVoiceCloneToggle?.(false);
                      }
                      voiceChat.onVoiceChange(item.value);
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
          ) : null}

          {/* TAB 3: TRANSLATION & VOICE CLONE */}
          {activeTab === "translation" && voiceChat.voiceChatLiveTranslate ? (
            <div className="vsVoiceSettingsSection vsVoiceTranslationCard">
              {isDashScopeLiveTranslate ? (
                <div className="vsTranslationModeSegment" style={{ justifyContent: "center", padding: "6px 12px", fontSize: 12, opacity: 0.9 }}>
                  <span>{t("单向同传 (源语言 → 目标语言)", "Unidirectional (Source → Target)")}</span>
                </div>
              ) : (
                <div className="vsTranslationModeSegment">
                  <button
                    type="button"
                    className={voiceChat.voiceChatTranslationMode === "bidirectional" ? "active" : ""}
                    onClick={() => voiceChat.onTranslationModeChange("bidirectional")}
                  >
                    {t("双向互翻 ⇄", "Bidirectional ⇄")}
                  </button>
                  <button
                    type="button"
                    className={voiceChat.voiceChatTranslationMode === "unidirectional" ? "active" : ""}
                    onClick={() => voiceChat.onTranslationModeChange("unidirectional")}
                  >
                    {t("单向翻译 →", "Single Direction →")}
                  </button>
                </div>
              )}

              {/* Preset Language Pair Pills */}
              <div className="vsPresetPairSection">
                <div className="vsPresetSubTitle">{t("常用语对", "Preset pairs")}</div>
                <div className="vsPresetPillsGroup">
                  {PRESET_LANGUAGE_PAIRS.map((pair) => {
                    const active =
                      voiceChat.voiceChatSourceLanguageCode === pair.source &&
                      voiceChat.voiceChatTargetLanguageCode === pair.target;
                    return (
                      <button
                        key={`${pair.source}-${pair.target}`}
                        type="button"
                        className={`vsPresetPillBtn${active ? " active" : ""}`}
                        onClick={() => voiceChat.onPresetLanguagePairSelect(pair.source, pair.target)}
                      >
                        {pair.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Language Selector Box */}
              <div className="vsLanguageSelectorBox">
                <div className="vsLanguageSelectGroup">
                  <label className="vsLanguageSelectLabel">
                    {!isDashScopeLiveTranslate && voiceChat.voiceChatTranslationMode === "bidirectional"
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
                  title={t("一键颠倒语言", "Swap languages")}
                  onClick={voiceChat.onSwapLanguages}
                >
                  ⇄
                </button>

                <div className="vsLanguageSelectGroup">
                  <label className="vsLanguageSelectLabel">
                    {!isDashScopeLiveTranslate && voiceChat.voiceChatTranslationMode === "bidirectional"
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

              {/* DashScope Voice Clone Controls */}
              {isDashScopeLiveTranslate ? (
                <div style={{ marginTop: 12, paddingTop: 10, borderTop: "1px solid rgba(255, 255, 255, 0.08)" }}>
                  <label
                    className="vsVoiceSettingsEcho"
                    title={t("自动提取您的发言声纹，并使用您本人的音色朗读外语", "Extract your voiceprint and speak target languages in your own voice")}
                    style={{ marginBottom: voiceChat.voiceChatEnableVoiceClone ? 8 : 0 }}
                  >
                    <input
                      type="checkbox"
                      checked={voiceChat.voiceChatEnableVoiceClone || false}
                      onChange={(e) => voiceChat.onVoiceCloneToggle?.(e.target.checked)}
                    />
                    <span style={{ fontWeight: 600, color: "#60a5fa" }}>
                      {t("声音复刻 (用本人音色朗读)", "Voice Clone (Speak in your own voice)")}
                    </span>
                  </label>

                  {voiceChat.voiceChatEnableVoiceClone ? (
                    <div className="vsPresetPillsGroup" style={{ marginTop: 6 }}>
                      <button
                        type="button"
                        className={`vsPresetPillBtn ${voiceChat.voiceChatVoiceCloneFrequency === "once" ? "active" : ""}`}
                        onClick={() => voiceChat.onVoiceCloneFrequencyChange?.("once")}
                        title={t("服务端录入首句声纹并在会话内持续使用", "Clone voice from first utterance and reuse")}
                      >
                        {t("单人实时复刻", "Single Speaker (Once)")}
                      </button>
                      <button
                        type="button"
                        className={`vsPresetPillBtn ${voiceChat.voiceChatVoiceCloneFrequency === "always" ? "active" : ""}`}
                        onClick={() => voiceChat.onVoiceCloneFrequencyChange?.("always")}
                        title={t("每次发声均动态捕获声纹特征，适合多人对话", "Dynamically capture voice per utterance")}
                      >
                        {t("动态实时复刻", "Multi Speaker (Always)")}
                      </button>
                    </div>
                  ) : null}
                </div>
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
