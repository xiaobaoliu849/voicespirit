import ErrorNotice from "../components/ErrorNotice";
import VoiceCatalog from "../components/VoiceCatalog";
import type { VoiceDesignController } from "../hooks/useVoiceManagement";
import { useI18n } from "../i18n";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  design: VoiceDesignController;
  errorRuntimeContext: ErrorRuntimeContext;
};

export default function VoiceDesignPage({ design, errorRuntimeContext }: Props) {
  const { t } = useI18n();
  return (
    <section className="vsTtsWorkspace">
      <form className="vsTtsLayout" onSubmit={design.onSubmit} style={{ margin: 0 }}>
        {/* ── Left Pane: Design Input ── */}
        <div className="vsTtsPrimary" style={{ flex: 1, borderRight: "1px solid var(--line)" }}>
          <header className="vsTtsPrimaryHeader">
            <h2 className="vsTtsPrimaryTitle">{t("音色设计工作室 (Voice Design)", "Voice Design Studio")}</h2>
            <div className="vsTtsPrimaryStats">
              <span>{t("通过自然语言描述创造专属音色", "Create a custom voice from a natural-language description")}</span>
            </div>
          </header>

          <div className="vsTtsEditorWrap" style={{ display: "flex", flexDirection: "column", gap: "20px", padding: "24px", overflowY: "auto" }}>
            <div className="vsFormRow">
              <label className="vsField">
                <span className="vsFieldLabel">{t("音色名称", "Voice name")}</span>
                <input
                  className="vsInput"
                  value={design.designName}
                  onChange={(e) => design.onNameChange(e.target.value)}
                  placeholder={t("例如：voice_design_demo", "For example: voice_design_demo")}
                  required
                />
              </label>
              <label className="vsField">
                <span className="vsFieldLabel">{t("预设语种", "Preset language")}</span>
                <input
                  className="vsInput"
                  value={design.designLanguage}
                  onChange={(e) => design.onLanguageChange(e.target.value)}
                  placeholder="zh / en"
                  required
                />
              </label>
            </div>

            <label className="vsField">
              <span className="vsFieldLabel">{t("风格提示词 (Prompt)", "Style prompt")}</span>
              <textarea
                className="vsTextarea"
                rows={5}
                value={design.designPrompt}
                onChange={(e) => design.onPromptChange(e.target.value)}
                placeholder={t("在此详细描述音色的年龄、语气、场景和说话风格... 如：一个活泼可爱的中国南方小女孩的声音，带有童音，语速偏快。", "Describe the voice in detail here: age, tone, use case, and speaking style... For example: a lively young southern Chinese girl with a childlike tone and brisk pacing.")}
                required
              />
            </label>

            <label className="vsField" style={{ marginTop: "16px" }}>
              <span className="vsFieldLabel">{t("试听检验文本 (Preview Text)", "Preview text")}</span>
              <textarea
                className="vsTextarea"
                rows={3}
                value={design.designPreviewText}
                onChange={(e) => design.onPreviewTextChange(e.target.value)}
                placeholder={t("输入一段用于新音色试听的示例文本", "Enter a sample script to preview the new voice")}
                required
              />
            </label>
          </div>

          <div className="vsTtsEditorFooter" style={{ marginTop: "16px" }}>
            <button
              type="button"
              className="vsBtnSecondary"
              onClick={() => void design.onRefresh()}
              disabled={design.designListBusy || design.designBusy}
            >
              {design.designListBusy ? t("刷新中...", "Refreshing...") : t("刷新音色库", "Refresh voice library")}
            </button>
            <button
              type="submit"
              className="vsBtnPrimary"
              disabled={design.designBusy}
            >
              {design.designBusy ? (
                <>
                  <span className="spinner-mini"></span>
                  {t("正在设计并合成…", "Designing and synthesizing...")}
                </>
              ) : (
                t("创造全新音色", "Create a new voice")
              )}
            </button>
          </div>
        </div>

        {/* ── Right Pane: Voice Catalog & Results ── */}
        <div className="vsTtsSecondary" style={{ width: "380px", flexShrink: 0 }}>

          <div className="vsCardSection">
            <h3 className="vsCardSubTitle">{t("设计反馈与试听结果", "Design feedback and preview")}</h3>

            <ErrorNotice
              message={design.designError}
              scope="voice_design"
              context={{
                ...errorRuntimeContext,
                preferred_name: design.designName,
                language: design.designLanguage
              }}
            />
            {design.designInfo ? <p className="vsSettingsNotice ok" style={{ marginBottom: 16 }}>{design.designInfo}</p> : null}

            {design.designPreviewAudio ? (
              <div className="vsTtsAudioPlayer" style={{ marginBottom: "20px" }}>
                <div style={{ marginBottom: 12, fontSize: 13, fontWeight: 600, color: "var(--brand)" }}>
                  {t(`✨ 音色设计成功！这是新音色《${design.designName}》的试听：`, `✨ Voice design succeeded. Preview for "${design.designName}":`)}
                </div>
                <audio controls src={design.designPreviewAudio} className="vsAudioElement" />
              </div>
            ) : (
              <div className="vsTtsEmptyResult" style={{ marginBottom: "20px" }}>
                <div className="vsEmptyIcon" style={{ fontSize: 24 }}>🪄</div>
                <div className="vsEmptyTitle">{t("暂无成果", "No output yet")}</div>
              </div>
            )}
          </div>

          <div className="vsCardSection border-top">
            <VoiceCatalog
              title={t("设计音色云端库", "Designed voice library")}
              voices={design.designVoices}
              busy={design.designBusy}
              listBusy={design.designListBusy}
              emptyText={t("暂无您设计的自定义音色。", "No designed custom voices yet.")}
              onDeleteVoice={design.onDeleteVoice}
            />
          </div>
        </div>
      </form>
    </section>
  );
}
