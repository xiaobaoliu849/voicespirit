import { useState } from "react";
import ErrorNotice from "../components/ErrorNotice";
import type { UseSettingsResult } from "../hooks/useSettings";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  settings: UseSettingsResult;
  errorRuntimeContext?: ErrorRuntimeContext;
};

type SettingCategory = "provider" | "transcription" | "memory" | "desktop";

export default function SettingsPage({ settings, errorRuntimeContext }: Props) {
  const [activeCategory, setActiveCategory] = useState<SettingCategory>("provider");

  // Keep the overall form wrapper but conditionally render the body based on nav.
  return (
    <div className="vsSettingsLayout">
      {/* ── Left Navigation ── */}
      <nav className="vsSettingsNav">
        <h2 className="vsSettingsNavTitle">偏好设置</h2>
        <ul className="vsSettingsNavList">
          <li>
            <button
              type="button"
              className={`vsSettingsNavItem ${activeCategory === "provider" ? "active" : ""}`}
              onClick={() => setActiveCategory("provider")}
            >
              <div className="vsSettingsNavIcon">⚡</div>
              <div>
                <div className="vsSettingsNavItemTitle">AI 供应商</div>
                <div className="vsSettingsNavItemDesc">模型服务与密钥</div>
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
                <div className="vsSettingsNavItemTitle">记忆中心</div>
                <div className="vsSettingsNavItemDesc">EverMem 存储配置</div>
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
                <div className="vsSettingsNavItemTitle">文件转写</div>
                <div className="vsSettingsNavItemDesc">对象存储上传配置</div>
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
                <div className="vsSettingsNavItemTitle">系统与运行时</div>
                <div className="vsSettingsNavItemDesc">后端诊断与高级选项</div>
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
                {activeCategory === "provider" && "AI 供应商参数"}
                {activeCategory === "memory" && "EverMem 长期记忆中心"}
                {activeCategory === "transcription" && "文件转写与上传配置"}
                {activeCategory === "desktop" && "系统与运行时状态"}
              </h1>
              <p className="vsSettingsDesc">
                {activeCategory === "provider" && "配置语音生成、文本理解与翻译使用的基础大语言模型服务。"}
                {activeCategory === "memory" && "连接 EverMemOS 为您的 AI 提供跨应用的记忆能力和上下文连续性。"}
                {activeCategory === "transcription" && "配置音频文件的上传策略及云端对象存储信息。"}
                {activeCategory === "desktop" && "环境诊断、应用底层路径与开发者选项。"}
              </p>
            </div>

            <div className="vsSettingsGlobalActions">
              <button
                type="button"
                className="vsBtnSecondary"
                onClick={() => void settings.onReload()}
                disabled={settings.settingsBusy || settings.settingsSaving}
              >
                {settings.settingsBusy ? "加载中..." : "重新加载配置"}
              </button>
              <button
                type="submit"
                className="vsBtnPrimary"
                disabled={settings.settingsSaving || settings.settingsBusy}
              >
                {settings.settingsSaving ? "保存中..." : "保存全部修改"}
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

          {/* ── Category: Provider ── */}
          {activeCategory === "provider" && (
            <div className="vsSettingsCard">
              <div className="vsFormRow">
                <label className="vsField">
                  <span className="vsFieldLabel">默认服务商</span>
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
                    placeholder="留空则使用默认地址"
                  />
                  <span className="vsFieldHint">用于代理后端地址等自定义 Endpoint。</span>
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
                    placeholder="输入供应商 API Key"
                  />
                </label>

                <label className="vsField">
                  <span className="vsFieldLabel">默认主模型</span>
                  <input
                    className="vsInput"
                    value={settings.settingsDefaultModel}
                    onChange={(e) => settings.onDefaultModelChange(e.target.value)}
                    placeholder="例如：qwen-plus / deepseek-chat"
                  />
                </label>
              </div>

              <label className="vsField">
                <span className="vsFieldLabel">可用模型列表（每行一个）</span>
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
                    <span className="vsToggleTitle">启用长期记忆支持</span>
                    <span className="vsToggleDesc">激活与 EverMemOS 的连接通讯。</span>
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
                      <span className="vsToggleTitle">启用「临时会话」模式</span>
                      <span className="vsToggleDesc">开启后，应用本次运行期间将不检索云端记忆，也不写入任何新记忆记录。</span>
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
                          placeholder="EverMemOS 访问密钥"
                        />
                      </label>
                    </div>
                    <label className="vsField">
                      <span className="vsFieldLabel">Scope ID (留空为默认)</span>
                      <input
                        className="vsInput"
                        value={settings.evermemScopeId}
                        onChange={(e) => settings.onEvermemScopeIdChange(e.target.value)}
                        placeholder="指定云端分区作用域"
                      />
                    </label>
                  </div>

                  <div className="vsCardSection border-top vsMemoryScenes">
                    <h3 className="vsCardSubTitle">场景生效控制</h3>
                    <p className="vsFieldHint" style={{ marginBottom: 12 }}>请根据需要勾选以下场景，授权 AI 主动参与学习。</p>

                    <div className="vsCheckGrid">
                      <label className="vsCheckItem">
                        <input
                          type="checkbox"
                          checked={settings.evermemRememberChat}
                          onChange={(e) => settings.onEvermemRememberChatChange(e.target.checked)}
                        />
                        <span>AI 对话助手</span>
                      </label>
                      <label className="vsCheckItem">
                        <input
                          type="checkbox"
                          checked={settings.evermemRememberVoiceChat}
                          onChange={(e) => settings.onEvermemRememberVoiceChatChange(e.target.checked)}
                        />
                        <span>实时语音对话</span>
                      </label>
                      <label className="vsCheckItem">
                        <input
                          type="checkbox"
                          checked={settings.evermemRememberRecordings}
                          onChange={(e) => settings.onEvermemRememberRecordingsChange(e.target.checked)}
                        />
                        <span>录音提炼分析任务</span>
                      </label>
                      <label className="vsCheckItem">
                        <input
                          type="checkbox"
                          checked={settings.evermemStoreTranscript}
                          onChange={(e) => settings.onEvermemStoreTranscriptChange(e.target.checked)}
                        />
                        <span>全量转写归档存储</span>
                      </label>
                      <label className="vsCheckItem">
                        <input
                          type="checkbox"
                          checked={settings.evermemRememberPodcast}
                          onChange={(e) => settings.onEvermemRememberPodcastChange(e.target.checked)}
                        />
                        <span>双人播客台本生成</span>
                      </label>
                      <label className="vsCheckItem">
                        <input
                          type="checkbox"
                          checked={settings.evermemRememberTts}
                          onChange={(e) => settings.onEvermemRememberTtsChange(e.target.checked)}
                        />
                        <span>纯文本朗读</span>
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
                  <span className="vsFieldLabel">文件上传模式</span>
                  <select
                    className="vsSelect"
                    value={settings.transcriptionUploadMode}
                    onChange={(e) => settings.onTranscriptionUploadModeChange(e.target.value)}
                  >
                    <option value="static">本地静态发布 (Static)</option>
                    <option value="s3">S3 兼容对象存储 (S3 API)</option>
                    <option value="disabled">禁用公网分发 (Disabled)</option>
                  </select>
                  <span className="vsFieldHint">控制生成的录音/视频文稿文件如何暂存于存储中供后端模型拉取及分享使用。</span>
                </label>
                <label className="vsField">
                  <span className="vsFieldLabel">分发基础域名 (Public Base URL)</span>
                  <input
                    className="vsInput"
                    value={settings.transcriptionPublicBaseUrl}
                    onChange={(e) => settings.onTranscriptionPublicBaseUrlChange(e.target.value)}
                    placeholder="https://files.example.com"
                  />
                  <span className="vsFieldHint">文件上传结束后生成的访问根锚点。</span>
                </label>
              </div>

              {settings.transcriptionUploadMode === "s3" && (
                <div className="vsCardSection border-top">
                  <h3 className="vsCardSubTitle">S3 Bucket 连接参数</h3>
                  <div className="vsFormRow">
                    <label className="vsField">
                      <span className="vsFieldLabel">Bucket Name</span>
                      <input
                        className="vsInput"
                        value={settings.transcriptionS3Bucket}
                        onChange={(e) => settings.onTranscriptionS3BucketChange(e.target.value)}
                        placeholder="例如: voicespirit-assets"
                      />
                    </label>
                    <label className="vsField">
                      <span className="vsFieldLabel">Region (区域代码)</span>
                      <input
                        className="vsInput"
                        value={settings.transcriptionS3Region}
                        onChange={(e) => settings.onTranscriptionS3RegionChange(e.target.value)}
                        placeholder="例如: us-east-1"
                      />
                    </label>
                  </div>

                  <div className="vsFormRow">
                    <label className="vsField">
                      <span className="vsFieldLabel">自定义 Endpoint URL</span>
                      <input
                        className="vsInput"
                        value={settings.transcriptionS3EndpointUrl}
                        onChange={(e) => settings.onTranscriptionS3EndpointUrlChange(e.target.value)}
                        placeholder="例如: https://s3.example.com"
                      />
                    </label>
                    <label className="vsField">
                      <span className="vsFieldLabel">存储前缀 (Key Prefix)</span>
                      <input
                        className="vsInput"
                        value={settings.transcriptionS3KeyPrefix}
                        onChange={(e) => settings.onTranscriptionS3KeyPrefixChange(e.target.value)}
                        placeholder="例如: voice-jobs/"
                      />
                    </label>
                  </div>

                  <div className="vsFormRow">
                    <label className="vsField">
                      <span className="vsFieldLabel">访问凭证 ID (Access Key)</span>
                      <input
                        className="vsInput"
                        type="password"
                        value={settings.transcriptionS3AccessKeyId}
                        onChange={(e) => settings.onTranscriptionS3AccessKeyIdChange(e.target.value)}
                        placeholder="输入 Access Key ID"
                      />
                    </label>
                    <label className="vsField">
                      <span className="vsFieldLabel">访问私钥 (Secret Key)</span>
                      <input
                        className="vsInput"
                        type="password"
                        value={settings.transcriptionS3SecretAccessKey}
                        onChange={(e) => settings.onTranscriptionS3SecretAccessKeyChange(e.target.value)}
                        placeholder="输入 Secret Access Key"
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
                <h3 className="vsCardSubTitle">诊断与底层信息</h3>
                <div className="vsFormRow">
                  <label className="vsField">
                    <span className="vsFieldLabel">后端阶段</span>
                    <input
                      className="vsInput"
                      value={settings.desktopSection.backendPhase || "未上报"}
                      readOnly
                    />
                  </label>
                  <label className="vsField">
                    <span className="vsFieldLabel">运行状态</span>
                    <input
                      className="vsInput"
                      value={settings.desktopSection.backendStatus || "未知"}
                      readOnly
                    />
                  </label>
                </div>
                <div className="vsFormRow">
                  <label className="vsField">
                    <span className="vsFieldLabel">鉴权模式</span>
                    <input
                      className="vsInput"
                      value={settings.desktopSection.backendAuthMode || "未启用"}
                      readOnly
                    />
                  </label>
                  <label className="vsField">
                    <span className="vsFieldLabel">版本号</span>
                    <input
                      className="vsInput"
                      value={settings.desktopSection.backendVersion || "未上报"}
                      readOnly
                    />
                  </label>
                </div>
                <div className="vsSettingsNotice">
                  当前桌面壳已具备单实例、原生菜单和窗口状态保存。托盘、全局快捷键、置顶等原生能力先保存配置，后续再接壳层。
                </div>
                <div className="vsSystemActions">
                  <button type="button" className="vsBtnGhost" onClick={settings.onToggleRuntimeOpen}>
                    {settings.backendRuntimeOpen ? "隐藏系统运行时日志" : "显示系统运行时日志"}
                  </button>
                  <button
                    type="button"
                    className="vsBtnGhost"
                    onClick={() => void settings.onCopyBackendRuntime()}
                  >
                    {settings.runtimeCopyStatus === "ok" ? "已复制到剪贴板！" : "复制运行时信息"}
                  </button>
                </div>
                {settings.runtimeCopyStatus === "fail" && (
                  <p className="vsSettingsNotice warning">复制失败，请尝试选取下方文本后手动复制。</p>
                )}
                {settings.backendRuntimeOpen && (
                  <pre className="runtimeDetails">{settings.backendRuntimeRaw}</pre>
                )}

                {settings.settingsConfigPath && (
                  <div className="vsSystemPath">
                    <span className="vsFieldLabel">全局配置文件宿主路径:</span>
                    <code className="vsCodeBlock">{settings.settingsConfigPath}</code>
                  </div>
                )}

                <div className="vsCardSection border-top">
                  <h3 className="vsCardSubTitle">最近一次桌面预检</h3>
                  <div className={`vsSettingsNotice ${settings.desktopSection.preflight.ok === false ? "warning" : "ok"}`}>
                    {!settings.desktopSection.preflight.available && "尚未生成桌面预检结果。可在桌面菜单中运行预检。"}
                    {settings.desktopSection.preflight.available && settings.desktopSection.preflight.ok === true &&
                      `桌面预检通过。时间：${settings.desktopSection.preflight.timestamp || "未知"}。`}
                    {settings.desktopSection.preflight.available && settings.desktopSection.preflight.ok === false &&
                      `桌面预检存在 ${settings.desktopSection.preflight.failed_count} 个问题。时间：${settings.desktopSection.preflight.timestamp || "未知"}。`}
                  </div>

                  {settings.desktopSection.preflight.failed_checks.length ? (
                    <div className="vsSystemPath">
                      <span className="vsFieldLabel">失败项摘要</span>
                      <code className="vsCodeBlock">
                        {settings.desktopSection.preflight.failed_checks
                          .map((item) => `${item.name}: ${item.detail}`)
                          .join("\n")}
                      </code>
                    </div>
                  ) : null}

                  {settings.desktopSection.latestError.available ? (
                    <div className="vsSystemPath">
                      <span className="vsFieldLabel">最近一次启动错误</span>
                      <code className="vsCodeBlock">
                        {`${settings.desktopSection.latestError.error_type || "Error"}\n${settings.desktopSection.latestError.message || "未知错误"}\n${settings.desktopSection.latestError.timestamp || ""}`.trim()}
                      </code>
                    </div>
                  ) : null}

                  {settings.desktopSection.latestError.available &&
                  settings.desktopSection.latestError.recovery_hints.length ? (
                    <div className="vsSettingsNotice warning">
                      <strong>恢复建议</strong>
                      <ul style={{ margin: "8px 0 0 18px" }}>
                        {settings.desktopSection.latestError.recovery_hints.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  {settings.desktopSection.diagnosticsDir ? (
                    <div className="vsSystemPath">
                      <span className="vsFieldLabel">诊断目录</span>
                      <code className="vsCodeBlock">{settings.desktopSection.diagnosticsDir}</code>
                    </div>
                  ) : null}
                </div>
              </div>

              <div className="vsCardSection border-top">
                <h3 className="vsCardSubTitle">桌面偏好</h3>
                <label className="vsToggleLabel">
                  <div className="vsToggleInfo">
                    <span className="vsToggleTitle">记住窗口位置</span>
                    <span className="vsToggleDesc">将桌面窗口位置和尺寸写入配置，用于下次启动恢复。</span>
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
                    <span className="vsToggleTitle">窗口始终置顶</span>
                    <span className="vsToggleDesc">保存桌面置顶偏好，待原生壳层接线后可直接生效。</span>
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
                    <span className="vsToggleTitle">显示托盘图标</span>
                    <span className="vsToggleDesc">保留桌面托盘偏好，后续桌面壳补齐托盘能力时直接复用。</span>
                  </div>
                  <input
                    type="checkbox"
                    className="vsSwitch"
                    checked={settings.desktopShowTrayIcon}
                    onChange={(e) => settings.onDesktopShowTrayIconChange(e.target.checked)}
                  />
                </label>

                <label className="vsField" style={{ marginTop: 20 }}>
                  <span className="vsFieldLabel">唤醒快捷键</span>
                  <input
                    className="vsInput"
                    value={settings.desktopWakeShortcut}
                    onChange={(e) => settings.onDesktopWakeShortcutChange(e.target.value)}
                    placeholder="例如：Alt+Shift+S"
                  />
                  <span className="vsFieldHint">当前先保存到全局配置，供后续原生全局快捷键接线使用。</span>
                </label>
              </div>
            </div>
          )}

        </form>
      </section>
    </div>
  );
}
