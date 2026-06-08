import { useState } from "react";
import EvermindBadge from "../components/EvermindBadge";
import ErrorNotice from "../components/ErrorNotice";
import type { UseSettingsResult } from "../hooks/useSettings";
import { useI18n } from "../i18n";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  settings: UseSettingsResult;
  errorRuntimeContext?: ErrorRuntimeContext;
  onClose?: () => void;
};

type SettingCategory = "general" | "provider" | "transcription" | "memory" | "desktop";

const providerDisplayNames: Record<string, string> = {
  DashScope: "阿里云 DashScope",
  DeepSeek: "DeepSeek 深度求索",
  Google: "Google Gemini",
  Groq: "Groq 极速 API",
  OpenRouter: "OpenRouter 聚合",
  SiliconFlow: "硅基流动 SiliconFlow",
  Xiaomi: "小米 mimo"
};

const providerIcons: Record<string, string> = {
  DashScope: "☁️",
  DeepSeek: "🔍",
  Google: "✦",
  Groq: "⚡",
  OpenRouter: "🔀",
  SiliconFlow: "🌊",
  Xiaomi: "📱"
};


export default function SettingsPage({ settings, errorRuntimeContext, onClose }: Props) {
  const { t } = useI18n();
  const [activeCategory, setActiveCategory] = useState<SettingCategory>("provider");
  const [modelSearch, setModelSearch] = useState("");
  const [showRawModels, setShowRawModels] = useState(false);
  const [providerSearch, setProviderSearch] = useState("");
  const [showApiKey, setShowApiKey] = useState(false);

  // Keep the overall form wrapper but conditionally render the body based on nav.
  return (
    <div className="vsSettingsLayout">
      {/* ── Left Navigation ── */}
      <nav className="vsSettingsNav">
        <h2 className="vsSettingsNavTitle">{t("偏好设置", "Preferences")}</h2>
        <ul className="vsSettingsNavList">
          <li>
            <button
              type="button"
              className={`vsSettingsNavItem ${activeCategory === "general" ? "active" : ""}`}
              onClick={() => setActiveCategory("general")}
            >
              <div className="vsSettingsNavIcon">🌐</div>
              <div className="vsSettingsNavItemTitle">{t("通用", "General")}</div>
            </button>
          </li>
          <li>
            <button
              type="button"
              className={`vsSettingsNavItem ${activeCategory === "provider" ? "active" : ""}`}
              onClick={() => setActiveCategory("provider")}
            >
              <div className="vsSettingsNavIcon">⚡</div>
              <div className="vsSettingsNavItemTitle">{t("AI 供应商", "AI Providers")}</div>
            </button>
          </li>
          <li>
            <button
              type="button"
              className={`vsSettingsNavItem ${activeCategory === "memory" ? "active" : ""}`}
              onClick={() => setActiveCategory("memory")}
            >
              <div className="vsSettingsNavIcon">🧠</div>
              <div className="vsSettingsNavItemTitle">{t("记忆中心", "Memory")}</div>
            </button>
          </li>
          <li>
            <button
              type="button"
              className={`vsSettingsNavItem ${activeCategory === "transcription" ? "active" : ""}`}
              onClick={() => setActiveCategory("transcription")}
            >
              <div className="vsSettingsNavIcon">🎙️</div>
              <div className="vsSettingsNavItemTitle">{t("文件转写", "Transcription")}</div>
            </button>
          </li>
          <li>
            <button
              type="button"
              className={`vsSettingsNavItem ${activeCategory === "desktop" ? "active" : ""}`}
              onClick={() => setActiveCategory("desktop")}
            >
              <div className="vsSettingsNavIcon">💻</div>
              <div className="vsSettingsNavItemTitle">{t("系统与运行时", "System & Runtime")}</div>
            </button>
          </li>
        </ul>
      </nav>

      {/* ── Right Content Area ── */}
      <section className={`vsSettingsContent custom-scrollbar ${activeCategory === "provider" ? "provider-tab" : ""}`}>
        <form className="vsSettingsForm" onSubmit={settings.onSubmit}>
          <header className="vsSettingsHeader">
            <div className="vsSettingsHeadInfo">
              <h1 className="vsSettingsTitle">
                {activeCategory === "general" && t("通用偏好", "General Preferences")}
                {activeCategory === "provider" && t("AI 供应商参数", "AI Provider Settings")}
                {activeCategory === "memory" && t("EverMem 长期记忆中心", "EverMem Memory Center")}
                {activeCategory === "transcription" && t("文件转写与上传配置", "Transcription & Upload Settings")}
                {activeCategory === "desktop" && t("系统与运行时状态", "System & Runtime Status")}
              </h1>
            </div>
          </header>

          <ErrorNotice
            message={settings.settingsError}
            scope="settings"
            context={{
              ...errorRuntimeContext,
              provider: settings.settingsProvider,
              default_model: settings.settingsDefaultModel
            }}
          />
          {settings.settingsInfo ? <div className="vsSettingsNotice ok">{settings.settingsInfo}</div> : null}

          {activeCategory === "general" && (
            <div className="vsSettingsCard">
              <div className="vsCardSection">
                <h3 className="vsCardSubTitle">{t("界面与语言", "Interface and Language")}</h3>
                <div className="vsFormRow">
                  <label className="vsField">
                    <span className="vsFieldLabel">{t("界面语言", "Display Language")}</span>
                    <select
                      className="vsSelect"
                      value={settings.displayLanguage}
                      onChange={(e) => settings.onDisplayLanguageChange(e.target.value)}
                      disabled={settings.settingsBusy || settings.settingsSaving}
                    >
                      <option value="zh-CN">{t("中文", "Chinese")}</option>
                      <option value="en-US">English</option>
                    </select>
                    <span className="vsFieldHint">{t("切换后当前前端界面会立即刷新文案；保存后会写入全局配置。", "Switching updates the current frontend labels immediately; saving persists it to global config.")}</span>
                  </label>
                </div>
              </div>

              <div className="vsCardSection border-top">
                <h3 className="vsCardSubTitle">{t("配置与同步", "Config and Sync")}</h3>
                {settings.settingsConfigPath ? (
                  <div className="vsSystemPath">
                    <span className="vsFieldLabel">{t("当前配置文件", "Current config file")}</span>
                    <code className="vsCodeBlock">{settings.settingsConfigPath}</code>
                  </div>
                ) : null}
              </div>
            </div>
          )}

          {/* ── Category: Provider ── */}
          {activeCategory === "provider" && (
            <div className="vsProviderSettingsGrid">
              {/* Middle Column: Providers List */}
              <div className="vsProviderListColumn">
                <div className="vsProviderSearchBar">
                  <span className="vsProviderSearchIcon">🔍</span>
                  <input
                    type="text"
                    value={providerSearch}
                    onChange={(e) => setProviderSearch(e.target.value)}
                    placeholder={t("搜索供应商...", "Search providers...")}
                  />
                </div>
                <div className="vsProviderSelectGroup">
                  {settings.providerOptions
                    .filter(name => {
                      if (!providerSearch.trim()) return true;
                      const q = providerSearch.toLowerCase();
                      return name.toLowerCase().includes(q) || (providerDisplayNames[name] || "").toLowerCase().includes(q);
                    })
                    .map((providerName) => {
                    const isActive = settings.settingsProvider === providerName;
                    const hasKey = !!settings.providerModelCatalog[providerName]?.defaultModel || 
                      (settings.providerModelCatalog[providerName]?.availableModels && settings.providerModelCatalog[providerName].availableModels.length > 0);
                    
                    return (
                      <button
                        key={providerName}
                        type="button"
                        className={`vsProviderSelectorItem ${isActive ? "active" : ""}`}
                        onClick={() => settings.onProviderChange(providerName)}
                      >
                        <div className="vsProviderSelectorMeta">
                          <span className="vsProviderItemIcon">{providerIcons[providerName] || "🔗"}</span>
                          <span className="vsProviderNameText">{providerDisplayNames[providerName] || providerName}</span>
                        </div>
                        <span className={`vsActiveDot ${hasKey ? "" : "inactive"}`} title={hasKey ? t("已配置", "Configured") : t("未配置", "Not configured")} />
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Right Column: Config Details (fills ALL remaining space) */}
              <div className="vsProviderConfigColumn">
                <div className="vsProviderConfigHeader">
                  <div className="vsProviderConfigTitleRow">
                    <h2 className="vsProviderConfigTitle">{providerDisplayNames[settings.settingsProvider] || settings.settingsProvider}</h2>
                    {settings.settingsApiKey
                      ? <span className="vsProviderStatusBadge active">{t("活跃", "Active")}</span>
                      : <span className="vsProviderStatusBadge">{t("未激活", "Inactive")}</span>}
                  </div>
                </div>

                <div className="vsProviderConfigFields">
                  <label className="vsField">
                    <span className="vsFieldLabel">API Key</span>
                    <div className="vsPasswordFieldWrap">
                      <input
                        className="vsInput"
                        type={showApiKey ? "text" : "password"}
                        value={settings.settingsApiKey}
                        onChange={(e) => settings.onApiKeyChange(e.target.value)}
                        placeholder={t("输入供应商 API Key", "Enter your API key")}
                      />
                      <button
                        type="button"
                        className="vsPasswordToggleBtn"
                        onClick={() => setShowApiKey(v => !v)}
                        title={showApiKey ? t("隐藏", "Hide") : t("显示", "Show")}
                      >
                        {showApiKey ? "🙈" : "👁"}
                      </button>
                    </div>
                  </label>

                  <label className="vsField">
                    <span className="vsFieldLabel">Base URL ({t("可选", "Optional")})</span>
                    <input
                      className="vsInput"
                      value={settings.settingsApiUrl}
                      onChange={(e) => settings.onApiUrlChange(e.target.value)}
                      placeholder={t("留空则使用默认地址", "Leave empty to use the default URL")}
                    />
                    <span className="vsFieldHint">{t("留空则使用该供应商的默认 API 端点", "Leave empty to use the default API endpoint for this provider")}</span>
                  </label>

                  <label className="vsField">
                    <span className="vsFieldLabel">{t("默认主模型", "Default Model")}</span>
                    <select
                      className="vsSelect"
                      value={settings.settingsDefaultModel}
                      onChange={(e) => settings.onDefaultModelChange(e.target.value)}
                      disabled={settings.settingsBusy || settings.settingsSaving}
                    >
                      <option value="">{t("-- 请选择 --", "-- Select --")}</option>
                      {settings.settingsAvailableModels.map((modelId) => (
                        <option key={modelId} value={modelId}>
                          {modelId}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                {/* Model Management Section */}
                <div className="vsProviderModelSection">
                  <div className="vsModelManagerHeader">
                    <h3 className="vsCardSubTitle" style={{ margin: 0 }}>
                      {t(`模型 (${settings.settingsAvailableModels.length})`, `Models (${settings.settingsAvailableModels.length})`)}
                    </h3>
                    <div className="vsModelManagerActions">
                      <input
                        className="vsInput vsSearchInput"
                        value={modelSearch}
                        onChange={(e) => setModelSearch(e.target.value)}
                        placeholder={t("搜索模型...", "Search models...")}
                        style={{ width: 180 }}
                      />
                      <button
                        type="button"
                        className="vsBtnSecondary vsBtnSmall"
                        onClick={() => void settings.onFetchModels()}
                        disabled={settings.settingsFetchingModels || settings.settingsBusy}
                      >
                        {settings.settingsFetchingModels ? t("获取中...", "Fetching...") : t("获取", "Fetch")}
                      </button>
                    </div>
                  </div>

                  {settings.settingsAvailableModels.length === 0 ? (
                    <div className="vsEmptyModels">
                      <p>
                        {settings.settingsApiKey
                          ? t("暂无模型，点击「获取」拉取列表。", "No models yet. Click Fetch to pull the list.")
                          : t("请先填入 API Key，再点击「获取」。", "Fill API Key first, then click Fetch.")}
                      </p>
                    </div>
                  ) : (
                    <div className="vsModelsList custom-scrollbar">
                      {settings.settingsAvailableModels
                        .filter(m => m.toLowerCase().includes(modelSearch.toLowerCase()))
                        .map((modelId) => {
                          const isEnabled = settings.settingsEnabledModels.includes(modelId);
                          const isDefault = settings.settingsDefaultModel === modelId;
                          return (
                            <label key={modelId} className="vsModelRow">
                              <span className="vsModelRowName" title={modelId}>{modelId}</span>
                              {isDefault && <span className="vsDefaultBadge">{t("默认", "Default")}</span>}
                              <input
                                type="checkbox"
                                className="vsSwitch vsSwitchSmall"
                                checked={isEnabled}
                                onChange={() => settings.onToggleModelEnabled(modelId)}
                              />
                            </label>
                          );
                        })}
                    </div>
                  )}

                  <button
                    type="button"
                    className="vsRawModelsToggle"
                    onClick={() => setShowRawModels(v => !v)}
                  >
                    {showRawModels
                      ? t("▾ 收起手动编辑", "▾ Hide raw editor")
                      : t("▸ 手动编辑可用模型（高级）", "▸ Edit raw models (advanced)")}
                  </button>
                  {showRawModels && (
                    <div style={{ marginTop: 8 }}>
                      <textarea
                        className="vsTextarea"
                        rows={4}
                        value={settings.settingsAvailableModelsText}
                        onChange={(e) => settings.onAvailableModelsChange(e.target.value)}
                        placeholder={"model-a\nmodel-b"}
                      />
                    </div>
                  )}
                </div>

                {settings.settingsProvider === "Xiaomi" && (
                  <div className="vsProviderModelSection">
                    <h3 className="vsCardSubTitle">{t("小米语音合成配置 (Xiaomi TTS Settings)", "Xiaomi TTS Settings")}</h3>
                    <div className="vsProviderConfigFields">
                      <label className="vsField">
                        <span className="vsFieldLabel">Xiaomi API Key</span>
                        <input
                          className="vsInput"
                          type="password"
                          value={settings.xiaomiApiKey}
                          onChange={(e) => settings.onXiaomiApiKeyChange(e.target.value)}
                          placeholder={t("输入小米 API Key (tp-xxxxx 或 sk-xxxxx)", "Enter Xiaomi API Key (tp-xxxxx or sk-xxxxx)")}
                        />
                      </label>
                      <label className="vsField">
                        <span className="vsFieldLabel">Xiaomi API Base URL</span>
                        <input
                          className="vsInput"
                          value={settings.xiaomiApiUrl}
                          onChange={(e) => settings.onXiaomiApiUrlChange(e.target.value)}
                          placeholder="https://api.xiaomimimo.com"
                        />
                      </label>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── Category: Memory ── */}
          {activeCategory === "memory" && (
            <div className="vsSettingsCard">
              <div className="vsMemoryHero">
                <EvermindBadge variant="light" className="vsMemoryHeroBadge" />
                <div className="vsMemoryHeroCopy">
                  <strong>{t("VoiceSpirit × EverMind", "VoiceSpirit × EverMind")}</strong>
                  <p>
                    {t(
                      "把品牌放在记忆中心最合适，因为这里是用户真正配置、理解并启用 EverMem 的地方；侧边栏则保留一个运行时状态入口。",
                      "The memory center is the right home for the brand because this is where users actually configure, understand, and enable EverMem; the sidebar keeps a smaller runtime status touchpoint.",
                    )}
                  </p>
                </div>
              </div>
              <div className="vsCardSection">
                <label className="vsToggleLabel">
                  <div className="vsToggleInfo">
                    <span className="vsToggleTitle">{t("启用长期记忆支持", "Enable Long-Term Memory")}</span>
                    <span className="vsToggleDesc">{t("激活与 EverMemOS 的连接通讯。", "Enable the connection to EverMemOS.")}</span>
                  </div>
                  <input
                    type="checkbox"
                    className="vsSwitch"
                    checked={settings.evermemEnabled}
                    onChange={(e) => settings.onEvermemEnabledChange(e.target.checked)}
                  />
                </label>
                {settings.evermemEnabled && (
                  <label className="vsToggleLabel warning-tint">
                    <div className="vsToggleInfo">
                      <span className="vsToggleTitle">{t("启用「临时会话」模式", "Enable Temporary Session Mode")}</span>
                      <span className="vsToggleDesc">{t("开启后，应用本次运行期间将不检索云端记忆，也不写入任何新记忆记录。", "When enabled, this app run will not read from cloud memory or write new memory records.")}</span>
                    </div>
                    <input
                      type="checkbox"
                      className="vsSwitch"
                      checked={settings.evermemTempSession}
                      onChange={(e) => settings.onEvermemTempSessionChange(e.target.checked)}
                    />
                  </label>
                )}
              </div>

              {settings.evermemEnabled && (
                <>
                  <div className="vsCardSection border-top">
                    <div className="vsFormRow">
                      <label className="vsField">
                        <span className="vsFieldLabel">API URL</span>
                        <input
                          className="vsInput"
                          value={settings.evermemApiUrl}
                          onChange={(e) => settings.onEvermemApiUrlChange(e.target.value)}
                          placeholder="https://api.evermind.ai"
                        />
                      </label>
                      <label className="vsField">
                        <span className="vsFieldLabel">API Key</span>
                        <input
                          className="vsInput"
                          type="password"
                          value={settings.evermemApiKey}
                          onChange={(e) => settings.onEvermemApiKeyChange(e.target.value)}
                          placeholder={t("EverMemOS 访问密钥", "EverMemOS access key")}
                        />
                      </label>
                    </div>
                    <label className="vsField">
                      <span className="vsFieldLabel">{t("Scope ID (留空为默认)", "Scope ID (leave empty for default)")}</span>
                      <input
                        className="vsInput"
                        value={settings.evermemScopeId}
                        onChange={(e) => settings.onEvermemScopeIdChange(e.target.value)}
                        placeholder={t("指定云端分区作用域", "Specify the cloud memory scope")}
                      />
                    </label>
                  </div>

                  <div className="vsCardSection border-top vsMemoryScenes">
                    <h3 className="vsCardSubTitle">{t("场景生效控制", "Scene Controls")}</h3>
                    <p className="vsFieldHint" style={{ marginBottom: 12 }}>{t("请根据需要勾选以下场景，授权 AI 主动参与学习。", "Enable the scenes where the AI is allowed to learn proactively.")}</p>

                    <div className="vsCheckGrid">
                      <label className="vsCheckItem">
                        <input
                          type="checkbox"
                          checked={settings.evermemRememberChat}
                          onChange={(e) => settings.onEvermemRememberChatChange(e.target.checked)}
                        />
                        <span>{t("AI 对话助手", "AI Chat Assistant")}</span>
                      </label>
                      <label className="vsCheckItem">
                        <input
                          type="checkbox"
                          checked={settings.evermemRememberVoiceChat}
                          onChange={(e) => settings.onEvermemRememberVoiceChatChange(e.target.checked)}
                        />
                        <span>{t("实时语音对话", "Realtime Voice Chat")}</span>
                      </label>
                      <label className="vsCheckItem">
                        <input
                          type="checkbox"
                          checked={settings.evermemRememberRecordings}
                          onChange={(e) => settings.onEvermemRememberRecordingsChange(e.target.checked)}
                        />
                        <span>{t("录音提炼分析任务", "Recording analysis tasks")}</span>
                      </label>
                      <label className="vsCheckItem">
                        <input
                          type="checkbox"
                          checked={settings.evermemStoreTranscript}
                          onChange={(e) => settings.onEvermemStoreTranscriptChange(e.target.checked)}
                        />
                        <span>{t("全量转写归档存储", "Archive full transcripts")}</span>
                      </label>
                      <label className="vsCheckItem">
                        <input
                          type="checkbox"
                          checked={settings.evermemRememberPodcast}
                          onChange={(e) => settings.onEvermemRememberPodcastChange(e.target.checked)}
                        />
                        <span>{t("双人播客台本生成", "Two-speaker podcast scripts")}</span>
                      </label>
                      <label className="vsCheckItem">
                        <input
                          type="checkbox"
                          checked={settings.evermemRememberTts}
                          onChange={(e) => settings.onEvermemRememberTtsChange(e.target.checked)}
                        />
                        <span>{t("纯文本朗读", "Plain text narration")}</span>
                      </label>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* ── Category: Transcription ── */}
          {activeCategory === "transcription" && (
            <div className="vsSettingsCard">
              <div className="vsFormRow">
                <label className="vsField">
                  <span className="vsFieldLabel">{t("文件上传模式", "Upload Mode")}</span>
                  <select
                    data-testid="transcription-upload-mode"
                    className="vsSelect"
                    value={settings.transcriptionUploadMode}
                    onChange={(e) => settings.onTranscriptionUploadModeChange(e.target.value)}
                  >
                    <option value="static">{t("本地静态发布 (Static)", "Local static hosting")}</option>
                    <option value="s3">{t("S3 兼容对象存储 (S3 API)", "S3-compatible object storage")}</option>
                    <option value="disabled">{t("禁用公网分发 (Disabled)", "Disable public distribution")}</option>
                  </select>
                  <span className="vsFieldHint">{t("控制生成的录音/视频文稿文件如何暂存于存储中供后端模型拉取及分享使用。", "Controls how generated recording/video transcript files are staged for backend model access and sharing.")}</span>
                </label>
                <label className="vsField">
                  <span className="vsFieldLabel">{t("分发基础域名 (Public Base URL)", "Public Base URL")}</span>
                  <input
                    className="vsInput"
                    value={settings.transcriptionPublicBaseUrl}
                    onChange={(e) => settings.onTranscriptionPublicBaseUrlChange(e.target.value)}
                    placeholder="https://files.example.com"
                  />
                  <span className="vsFieldHint">{t("文件上传结束后生成的访问根锚点。", "Root URL used to access uploaded files.")}</span>
                </label>
              </div>

              {settings.transcriptionUploadMode === "s3" && (
                <div className="vsCardSection border-top">
                  <h3 className="vsCardSubTitle">{t("S3 Bucket 连接参数", "S3 Bucket Connection")}</h3>
                  <div className="vsFormRow">
                    <label className="vsField">
                      <span className="vsFieldLabel">Bucket Name</span>
                      <input
                        className="vsInput"
                        value={settings.transcriptionS3Bucket}
                        onChange={(e) => settings.onTranscriptionS3BucketChange(e.target.value)}
                        placeholder={t("例如: voicespirit-assets", "For example: voicespirit-assets")}
                      />
                    </label>
                    <label className="vsField">
                      <span className="vsFieldLabel">{t("Region (区域代码)", "Region")}</span>
                      <input
                        className="vsInput"
                        value={settings.transcriptionS3Region}
                        onChange={(e) => settings.onTranscriptionS3RegionChange(e.target.value)}
                        placeholder={t("例如: us-east-1", "For example: us-east-1")}
                      />
                    </label>
                  </div>

                  <div className="vsFormRow">
                    <label className="vsField">
                      <span className="vsFieldLabel">{t("自定义 Endpoint URL", "Custom Endpoint URL")}</span>
                      <input
                        className="vsInput"
                        value={settings.transcriptionS3EndpointUrl}
                        onChange={(e) => settings.onTranscriptionS3EndpointUrlChange(e.target.value)}
                        placeholder={t("例如: https://s3.example.com", "For example: https://s3.example.com")}
                      />
                    </label>
                    <label className="vsField">
                      <span className="vsFieldLabel">{t("存储前缀 (Key Prefix)", "Key Prefix")}</span>
                      <input
                        className="vsInput"
                        value={settings.transcriptionS3KeyPrefix}
                        onChange={(e) => settings.onTranscriptionS3KeyPrefixChange(e.target.value)}
                        placeholder={t("例如: voice-jobs/", "For example: voice-jobs/")}
                      />
                    </label>
                  </div>

                  <div className="vsFormRow">
                    <label className="vsField">
                      <span className="vsFieldLabel">{t("访问凭证 ID (Access Key)", "Access Key ID")}</span>
                      <input
                        className="vsInput"
                        type="password"
                        value={settings.transcriptionS3AccessKeyId}
                        onChange={(e) => settings.onTranscriptionS3AccessKeyIdChange(e.target.value)}
                        placeholder={t("输入 Access Key ID", "Enter Access Key ID")}
                      />
                    </label>
                    <label className="vsField">
                      <span className="vsFieldLabel">{t("访问私钥 (Secret Key)", "Secret Access Key")}</span>
                      <input
                        className="vsInput"
                        type="password"
                        value={settings.transcriptionS3SecretAccessKey}
                        onChange={(e) => settings.onTranscriptionS3SecretAccessKeyChange(e.target.value)}
                        placeholder={t("输入 Secret Access Key", "Enter Secret Access Key")}
                      />
                    </label>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── Category: Desktop / System ── */}
          {activeCategory === "desktop" && (
            <div className="vsSettingsCard vsDesktopSection">
              <div className="vsCardSection">
                <h3 className="vsCardSubTitle">{t("诊断与底层信息", "Diagnostics & Runtime Details")}</h3>
                <div className="vsFormRow">
                  <label className="vsField">
                    <span className="vsFieldLabel">{t("后端阶段", "Backend Phase")}</span>
                    <input
                      className="vsInput"
                      value={settings.desktopSection.backendPhase || t("未上报", "Unknown")}
                      readOnly
                    />
                  </label>
                  <label className="vsField">
                    <span className="vsFieldLabel">{t("运行状态", "Backend Status")}</span>
                    <input
                      className="vsInput"
                      value={settings.desktopSection.backendStatus || t("未知", "Unknown")}
                      readOnly
                    />
                  </label>
                </div>
                <div className="vsFormRow">
                  <label className="vsField">
                    <span className="vsFieldLabel">{t("鉴权模式", "Auth Mode")}</span>
                    <input
                      className="vsInput"
                      value={settings.desktopSection.backendAuthMode || t("未启用", "Disabled")}
                      readOnly
                    />
                  </label>
                  <label className="vsField">
                    <span className="vsFieldLabel">{t("版本号", "Version")}</span>
                    <input
                      className="vsInput"
                      value={settings.desktopSection.backendVersion || t("未上报", "Unknown")}
                      readOnly
                    />
                  </label>
                </div>
                <div className="vsSettingsNotice">
                  {t(
                    "当前桌面壳已具备单实例、原生菜单和窗口状态保存。托盘、全局快捷键、置顶等原生能力先保存配置，后续再接壳层。",
                    "The desktop shell already supports single-instance mode, native menus, and window state persistence. Tray, global shortcuts, and always-on-top are stored now and can be wired into the shell later."
                  )}
                </div>
                <div className="vsSystemActions">
                  <button type="button" className="vsBtnGhost" onClick={settings.onToggleRuntimeOpen}>
                    {settings.backendRuntimeOpen
                      ? t("隐藏系统运行时日志", "Hide runtime log")
                      : t("显示系统运行时日志", "Show runtime log")}
                  </button>
                  <button
                    type="button"
                    className="vsBtnGhost"
                    onClick={() => void settings.onCopyBackendRuntime()}
                  >
                    {settings.runtimeCopyStatus === "ok"
                      ? t("已复制到剪贴板！", "Copied to clipboard!")
                      : t("复制运行时信息", "Copy runtime info")}
                  </button>
                </div>
                {settings.runtimeCopyStatus === "fail" && (
                  <p className="vsSettingsNotice warning">{t("复制失败，请尝试选取下方文本后手动复制。", "Copy failed. Try selecting the text below and copying it manually.")}</p>
                )}
                {settings.backendRuntimeOpen && (
                  <pre className="runtimeDetails">{settings.backendRuntimeRaw}</pre>
                )}

                {settings.settingsConfigPath && (
                  <div className="vsSystemPath">
                    <span className="vsFieldLabel">{t("全局配置文件宿主路径:", "Config File Path:")}</span>
                    <code className="vsCodeBlock">{settings.settingsConfigPath}</code>
                  </div>
                )}

                <div className="vsCardSection border-top">
                  <h3 className="vsCardSubTitle">{t("最近一次桌面预检", "Latest Desktop Preflight")}</h3>
                  <div className={`vsSettingsNotice ${settings.desktopSection.preflight.ok === false ? "warning" : "ok"}`}>
                    {!settings.desktopSection.preflight.available && t("尚未生成桌面预检结果。可在桌面菜单中运行预检。", "No desktop preflight result has been generated yet. Run the preflight from the desktop menu.")}
                    {settings.desktopSection.preflight.available && settings.desktopSection.preflight.ok === true &&
                      t(
                        `桌面预检通过。时间：${settings.desktopSection.preflight.timestamp || "未知"}。`,
                        `Desktop preflight passed. Time: ${settings.desktopSection.preflight.timestamp || "Unknown"}.`
                      )}
                    {settings.desktopSection.preflight.available && settings.desktopSection.preflight.ok === false &&
                      t(
                        `桌面预检存在 ${settings.desktopSection.preflight.failed_count} 个问题。时间：${settings.desktopSection.preflight.timestamp || "未知"}。`,
                        `Desktop preflight found ${settings.desktopSection.preflight.failed_count} issues. Time: ${settings.desktopSection.preflight.timestamp || "Unknown"}.`
                      )}
                  </div>

                  {settings.desktopSection.preflight.failed_checks.length ? (
                    <div className="vsSystemPath">
                      <span className="vsFieldLabel">{t("失败项摘要", "Failed Checks")}</span>
                      <code className="vsCodeBlock">
                        {settings.desktopSection.preflight.failed_checks
                          .map((item) => `${item.name}: ${item.detail}`)
                          .join("\n")}
                      </code>
                    </div>
                  ) : null}

                  {settings.desktopSection.latestError.available ? (
                    <div className="vsSystemPath">
                      <span className="vsFieldLabel">{t("最近一次启动错误", "Latest Launch Error")}</span>
                      <code className="vsCodeBlock">
                        {`${settings.desktopSection.latestError.error_type || "Error"}\n${settings.desktopSection.latestError.message || t("未知错误", "Unknown error")}\n${settings.desktopSection.latestError.timestamp || ""}`.trim()}
                      </code>
                    </div>
                  ) : null}

                  {settings.desktopSection.latestError.available &&
                  settings.desktopSection.latestError.recovery_hints.length ? (
                    <div className="vsSettingsNotice warning">
                      <strong>{t("恢复建议", "Recovery Suggestions")}</strong>
                      <ul style={{ margin: "8px 0 0 18px" }}>
                        {settings.desktopSection.latestError.recovery_hints.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  {settings.desktopSection.diagnosticsDir ? (
                    <div className="vsSystemPath">
                      <span className="vsFieldLabel">{t("诊断目录", "Diagnostics Directory")}</span>
                      <code className="vsCodeBlock">{settings.desktopSection.diagnosticsDir}</code>
                    </div>
                  ) : null}
                </div>
              </div>

              <div className="vsCardSection border-top">
                <h3 className="vsCardSubTitle">{t("桌面偏好", "Desktop Preferences")}</h3>
                <label className="vsToggleLabel">
                  <div className="vsToggleInfo">
                    <span className="vsToggleTitle">{t("记住窗口位置", "Remember Window Position")}</span>
                    <span className="vsToggleDesc">{t("将桌面窗口位置和尺寸写入配置，用于下次启动恢复。", "Save the desktop window position and size for the next launch.")}</span>
                  </div>
                  <input
                    type="checkbox"
                    className="vsSwitch"
                    checked={settings.desktopRememberWindowPosition}
                    onChange={(e) => settings.onDesktopRememberWindowPositionChange(e.target.checked)}
                  />
                </label>

                <label className="vsToggleLabel">
                  <div className="vsToggleInfo">
                    <span className="vsToggleTitle">{t("窗口始终置顶", "Always On Top")}</span>
                    <span className="vsToggleDesc">{t("保存桌面置顶偏好，待原生壳层接线后可直接生效。", "Save the always-on-top preference for the native desktop shell.")}</span>
                  </div>
                  <input
                    type="checkbox"
                    className="vsSwitch"
                    checked={settings.desktopAlwaysOnTop}
                    onChange={(e) => settings.onDesktopAlwaysOnTopChange(e.target.checked)}
                  />
                </label>

                <label className="vsToggleLabel">
                  <div className="vsToggleInfo">
                    <span className="vsToggleTitle">{t("显示托盘图标", "Show Tray Icon")}</span>
                    <span className="vsToggleDesc">{t("保留桌面托盘偏好，后续桌面壳补齐托盘能力时直接复用。", "Persist the tray preference so the native shell can reuse it later.")}</span>
                  </div>
                  <input
                    type="checkbox"
                    className="vsSwitch"
                    checked={settings.desktopShowTrayIcon}
                    onChange={(e) => settings.onDesktopShowTrayIconChange(e.target.checked)}
                  />
                </label>

                <label className="vsField" style={{ marginTop: 20 }}>
                  <span className="vsFieldLabel">{t("唤醒快捷键", "Wake Shortcut")}</span>
                  <input
                    className="vsInput"
                    value={settings.desktopWakeShortcut}
                    onChange={(e) => settings.onDesktopWakeShortcutChange(e.target.value)}
                    placeholder={t("例如：Alt+Shift+S", "For example: Alt+Shift+S")}
                  />
                  <span className="vsFieldHint">{t("当前先保存到全局配置，供后续原生全局快捷键接线使用。", "Saved into the global config for future native global shortcut support.")}</span>
                </label>
              </div>
            </div>
          )}

          {activeCategory === "desktop" && (
            <div className="vsSettingsCard">
              <div className="vsCardSection">
                <h3 className="vsCardSubTitle">{t("开源推荐：VibeVoice TTS", "Open Source Pick: VibeVoice TTS")}</h3>
                <p className="vsFieldHint" style={{ marginTop: 4 }}>
                  {t(
                    "微软 2025 年开源的 VibeVoice（MIT 协议）支持几秒参考音频即可克隆声音，最长 90 分钟连续合成，可精确控制时间轴与情感。适合本地部署、无 API 成本的场景。",
                    "Microsoft's open-source VibeVoice (MIT, 2025) clones voices from a few seconds of reference audio, synthesizes up to 90 minutes of continuous speech with precise timeline and emotion control. Great for on-prem, zero-API-cost deployments."
                  )}
                </p>
                <ul style={{ margin: "12px 0 12px 20px", padding: 0, color: "var(--text)", fontSize: "13px", lineHeight: 1.7 }}>
                  <li>{t("声音克隆：仅需 3–10 秒参考音频", "Voice cloning: 3–10s reference audio")}</li>
                  <li>{t("长音频：支持 90 分钟连续合成", "Long-form: up to 90-minute continuous synthesis")}</li>
                  <li>{t("多说话人：同一段文本可切换音色", "Multi-speaker: switch timbres within one text")}</li>
                </ul>
                <div className="vsSystemActions">
                  <a
                    className="vsBtnGhost vsBtnSmall"
                    href="https://github.com/microsoft/VibeVoice"
                    target="_blank"
                    rel="noreferrer"
                    style={{ textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 6 }}
                  >
                    {t("访问 GitHub 仓库 ↗", "Visit GitHub repo ↗")}
                  </a>
                  <a
                    className="vsBtnGhost vsBtnSmall"
                    href="https://microsoft.github.io/VibeVoice/"
                    target="_blank"
                    rel="noreferrer"
                    style={{ textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 6 }}
                  >
                    {t("官方项目页 ↗", "Project page ↗")}
                  </a>
                </div>
              </div>
            </div>
          )}

          {/* Dynamic Action Footer matching Alma */}
          <footer className="vsSettingsFormFooter">
            <div className="vsSettingsFooterStatus">
              {settings.settingsSaving ? (
                <span className="status-saving">
                  <span className="spinner-mini"></span> {t("正在保存更改...", "Saving changes...")}
                </span>
              ) : settings.settingsBusy ? (
                <span className="status-loading">{t("正在加载配置...", "Loading settings...")}</span>
              ) : settings.settingsInfo ? (
                <span className="status-saved ok">✓ {settings.settingsInfo}</span>
              ) : (
                <span className="status-ready">{t("所有更改已保存", "All changes saved")}</span>
              )}
            </div>
            <div className="vsSettingsFooterActions">
              <button
                type="button"
                className="vsBtnGhost vsFooterReloadBtn"
                onClick={() => void settings.onReload()}
                disabled={settings.settingsBusy || settings.settingsSaving}
                style={{ marginRight: 8, fontSize: "12px" }}
              >
                {t("重新加载", "Reload")}
              </button>
              {onClose && (
                <button
                  type="button"
                  className="vsBtnSecondary vsFooterCloseBtn"
                  onClick={onClose}
                  disabled={settings.settingsSaving || settings.settingsBusy}
                >
                  {t("关闭", "Close")}
                </button>
              )}
              <button
                type="submit"
                className="vsBtnPrimary vsFooterSaveBtn"
                disabled={settings.settingsSaving || settings.settingsBusy}
              >
                {settings.settingsSaving ? t("保存中...", "Saving...") : t("保存", "Save")}
              </button>
            </div>
          </footer>

        </form>
      </section>
    </div>
  );
}
