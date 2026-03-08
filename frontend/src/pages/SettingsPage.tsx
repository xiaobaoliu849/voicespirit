import ErrorNotice from "../components/ErrorNotice";
import type { UseSettingsResult } from "../hooks/useSettings";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  settings: UseSettingsResult;
  errorRuntimeContext?: ErrorRuntimeContext;
};

export default function SettingsPage({ settings }: Props) {
  return (
    <section className="legacyPanel">
      <div className="runtimeActions">
        <button type="button" className="ghost" onClick={settings.onToggleRuntimeOpen}>
          {settings.backendRuntimeOpen ? "隐藏运行时信息" : "显示运行时信息"}
        </button>
        <button
          type="button"
          className="ghost"
          onClick={() => void settings.onCopyBackendRuntime()}
        >
          {settings.runtimeCopyStatus === "ok" ? "已复制运行时信息" : "复制运行时信息"}
        </button>
      </div>
      {settings.runtimeCopyStatus === "fail" ? (
        <p className="runtimeCopyStatus">复制失败，请手动复制运行时信息。</p>
      ) : null}
      {settings.backendRuntimeOpen ? (
        <pre className="runtimeDetails">{settings.backendRuntimeRaw}</pre>
      ) : null}
      <form className="form" onSubmit={settings.onSubmit}>
        <div className="inlineActions">
          <button
            type="submit"
            disabled={settings.settingsSaving || settings.settingsBusy}
          >
            {settings.settingsSaving ? "保存中..." : "保存供应商设置"}
          </button>
          <button
            type="button"
            className="ghost"
            onClick={() => void settings.onReload()}
            disabled={settings.settingsBusy || settings.settingsSaving}
          >
            {settings.settingsBusy ? "加载中..." : "重新加载设置"}
          </button>
        </div>

        <ErrorNotice
          message={settings.settingsError}
          scope="settings"
          context={{
            ...settings.errorRuntimeContext,
            provider: settings.settingsProvider,
            default_model: settings.settingsDefaultModel
          }}
        />
        {settings.settingsInfo ? <p className="ok">{settings.settingsInfo}</p> : null}
        {settings.settingsConfigPath ? (
          <p className="muted">配置文件：{settings.settingsConfigPath}</p>
        ) : null}

        <div className="rowWide">
          <label>
            供应商
            <select
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
          <label>
            API URL
            <input
              value={settings.settingsApiUrl}
              onChange={(e) => settings.onApiUrlChange(e.target.value)}
              placeholder="留空则使用默认地址"
            />
          </label>
        </div>

        <label>
          API Key
          <input
            type="password"
            value={settings.settingsApiKey}
            onChange={(e) => settings.onApiKeyChange(e.target.value)}
            placeholder="输入供应商 API Key"
          />
        </label>

        <label>
          默认模型
          <input
            value={settings.settingsDefaultModel}
            onChange={(e) => settings.onDefaultModelChange(e.target.value)}
            placeholder="例如：qwen-plus / deepseek-chat"
          />
        </label>

        <label>
          可用模型（每行一个）
          <textarea
            rows={6}
            value={settings.settingsAvailableModelsText}
            onChange={(e) => settings.onAvailableModelsChange(e.target.value)}
            placeholder={"model-a\nmodel-b\nmodel-c"}
          />
        </label>

        <hr style={{ margin: "24px 0", borderColor: "var(--border-color)", borderStyle: "solid", borderWidth: "1px 0 0 0" }} />

        <h3 style={{ marginBottom: 16 }}>EverMem 长期记忆 (Beta)</h3>

        <label style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
          <input
            type="checkbox"
            checked={settings.evermemEnabled}
            onChange={(e) => settings.onEvermemEnabledChange(e.target.checked)}
            style={{ width: "auto" }}
          />
          开启 EverMemOS 长期记忆
        </label>

        {settings.evermemEnabled && (
          <div className="rowWide" style={{ marginTop: 16 }}>
            <label>
              EverMem API URL
              <input
                value={settings.evermemUrl}
                onChange={(e) => settings.onEvermemUrlChange(e.target.value)}
                placeholder="例如：https://api.evermind.ai"
              />
            </label>
            <label>
              EverMem API Key
              <input
                type="password"
                value={settings.evermemKey}
                onChange={(e) => settings.onEvermemKeyChange(e.target.value)}
                placeholder="输入 EverMemOS 密钥"
              />
            </label>
          </div>
        )}
      </form>
    </section>
  );
}
