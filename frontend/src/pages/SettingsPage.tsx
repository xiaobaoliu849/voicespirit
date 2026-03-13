import { useState } from "react";
import ErrorNotice from "../components/ErrorNotice";
import type { UseSettingsResult } from "../hooks/useSettings";
import { useI18n } from "../i18n";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  settings: UseSettingsResult;
  errorRuntimeContext?: ErrorRuntimeContext;
};

type SettingCategory = "general" | "provider" | "transcription" | "memory" | "desktop";

export default function SettingsPage({ settings, errorRuntimeContext }: Props) {
  const { t } = useI18n();
  const [activeCategory, setActiveCategory] = useState<SettingCategory>("provider");

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
              <div>
                <div className="vsSettingsNavItemTitle">{t("通用", "General")}</div>
                <div className="vsSettingsNavItemDesc">{t("界面语言与工作区", "Language and workspace")}</div>
              </div>
            </button>
          </li>
          <li>
            <button
              type="button"
              className={`vsSettingsNavItem ${activeCategory === "provider" ? "active" : ""}`}
              onClick={() => setActiveCategory("provider")}
            >
              <div className="vsSettingsNavIcon">⚡</div>
              <div>
                <div className="vsSettingsNavItemTitle">{t("AI 供应商", "AI Providers")}</div>
                <div className="vsSettingsNavItemDesc">{t("模型服务与密钥", "Models and API keys")}</div>
              </div>
            </button>
          </li>
          <li>
            <button
              type="button"
              className={`vsSettingsNavItem ${activeCategory === "memory" ? "active" : ""}`}
              onClick={() => setActiveCategory("memory")}
            >
              <div className="vsSettingsNavIcon">🧠</div>
              <div>
                <div className="vsSettingsNavItemTitle">{t("记忆中心", "Memory")}</div>
                <div className="vsSettingsNavItemDesc">{t("EverMem 存储配置", "EverMem storage")}</div>
              </div>
            </button>
          </li>
          <li>
            <button
              type="button"
              className={`vsSettingsNavItem ${activeCategory === "transcription" ? "active" : ""}`}
              onClick={() => setActiveCategory("transcription")}
            >
              <div className="vsSettingsNavIcon">🎙️</div>
              <div>
                <div className="vsSettingsNavItemTitle">{t("文件转写", "Transcription")}</div>
                <div className="vsSettingsNavItemDesc">{t("对象存储上传配置", "Object storage upload")}</div>
              </div>
            </button>
          </li>
          <li>
            <button
              type="button"
              className={`vsSettingsNavItem ${activeCategory === "desktop" ? "active" : ""}`}
              onClick={() => setActiveCategory("desktop")}
            >
              <div className="vsSettingsNavIcon">💻</div>
              <div>
                <div className="vsSettingsNavItemTitle">{t("系统与运行时", "System & Runtime")}</div>
                <div className="vsSettingsNavItemDesc">{t("后端诊断与高级选项", "Backend diagnostics and advanced options")}</div>
              </div>
            </button>
          </li>
        </ul>
      </nav>

      {/* ── Right Content Area ── */}
      <section className="vsSettingsContent custom-scrollbar">
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
              <p className="vsSettingsDesc">
                {activeCategory === "general" && t("管理界面语言、配置载入，以及当前工作区的基础偏好。", "Manage interface language, config reload, and workspace-level preferences.")}
                {activeCategory === "provider" && t("配置语音生成、文本理解与翻译使用的基础大语言模型服务。", "Configure the base model services used for speech, chat, and translation.")}
                {activeCategory === "memory" && t("连接 EverMemOS 为您的 AI 提供跨应用的记忆能力和上下文连续性。", "Connect EverMemOS to give your AI cross-app memory and continuous context.")}
                {activeCategory === "transcription" && t("配置音频文件的上传策略及云端对象存储信息。", "Configure the upload strategy and cloud object storage details for audio files.")}
                {activeCategory === "desktop" && t("环境诊断、应用底层路径与开发者选项。", "Environment diagnostics, runtime paths, and developer options.")}
              </p>
            </div>

            <div className="vsSettingsGlobalActions">
              <button
                type="button"
                className="vsBtnSecondary"
                onClick={() => void settings.onReload()}
                disabled={settings.settingsBusy || settings.settingsSaving}
              >
                {settings.settingsBusy ? t("加载中...", "Loading...") : t("重新加载配置", "Reload settings")}
              </button>
              <button
                type="submit"
                className="vsBtnPrimary"
                disabled={settings.settingsSaving || settings.settingsBusy}
              >
                {settings.settingsSaving ? t("保存中...", "Saving...") : t("保存全部修改", "Save all changes")}
              </button>
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
                  <div className="vsSettingsFeatureCallout">
                    <strong>{t("工作区范围", "Workspace scope")}</strong>
                    <p>{t("语言属于全局偏好，不应混在 AI 供应商配置里。这里负责界面层体验，AI 模型设置单独放在下一项。", "Language is a global preference and should not live inside AI provider configuration. This section owns UI behavior, while model settings live in the next section.")}</p>
                  </div>
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
                <div className="vsSettingsFeatureCallout subtle">
                  <strong>{t("操作建议", "Recommended flow")}</strong>
                  <p>{t("先在这里确定显示语言和全局偏好，再进入 AI、转写或记忆模块做具体配置，层级会更清楚。", "Set display language and global preferences here first, then go into AI, transcription, or memory for module-specific configuration.")}</p>
                </div>
              </div>
            </div>
          )}

          {/* ── Category: Provider ── */}
          {activeCategory === "provider" && (
            <div className="vsSettingsCard">
              <div className="vsFormRow">
                <label className="vsField">
                  <span className="vsFieldLabel">{t("默认服务商", "Default Provider")}</span>
                  <select
                    className="vsSelect"
                    value={settings.settingsProvider}
                    onChange={(e) => settings.onProviderChange(e.target.value)}
                  >
                    {settings.providerOptions.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="vsField">
                  <span className="vsFieldLabel">API Base URL</span>
                  <input
                    className="vsInput"
                    value={settings.settingsApiUrl}
                    onChange={(e) => settings.onApiUrlChange(e.target.value)}
                    placeholder={t("留空则使用默认地址", "Leave empty to use the default URL")}
                  />
                  <span className="vsFieldHint">{t("用于代理后端地址等自定义 Endpoint。", "Use this for a proxy backend or a custom endpoint.")}</span>
                </label>
              </div>

              <div className="vsFormRow">
                <label className="vsField">
                  <span className="vsFieldLabel">API Key</span>
                  <input
                    className="vsInput"
                    type="password"
                    value={settings.settingsApiKey}
                    onChange={(e) => settings.onApiKeyChange(e.target.value)}
                    placeholder={t("输入供应商 API Key", "Enter the provider API key")}
                  />
                </label>

                <label className="vsField">
                  <span className="vsFieldLabel">{t("默认主模型", "Default Model")}</span>
                  <input
                    className="vsInput"
                    value={settings.settingsDefaultModel}
                    onChange={(e) => settings.onDefaultModelChange(e.target.value)}
                    placeholder={t("例如：qwen-plus / deepseek-chat", "For example: qwen-plus / deepseek-chat")}
                  />
                </label>
              </div>

              <label className="vsField">
                <span className="vsFieldLabel">{t("可用模型列表（每行一个）", "Available Models (one per line)")}</span>
                <textarea
                  className="vsTextarea"
                  rows={5}
                  value={settings.settingsAvailableModelsText}
                  onChange={(e) => settings.onAvailableModelsChange(e.target.value)}
                  placeholder={"model-a\nmodel-b\nmodel-c"}
                />
              </label>
            </div>
          )}

          {/* ── Category: Memory ── */}
          {activeCategory === "memory" && (
            <div className="vsSettingsCard">
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

        </form>
      </section>
    </div>
  );
}
