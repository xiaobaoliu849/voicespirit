import { useState } from "react";
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
  const [isCatalogOpen, setIsCatalogOpen] = useState(true);

  return (
    <section className="vsTtsWorkspace">
      <form className="vsTtsLayout" onSubmit={design.onSubmit} style={{ margin: 0, display: "flex", height: "100%" }}>
        {/* ── Left Pane: Design Input ── */}
        <div className="vsTtsPrimary" style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
          <header className="vsTtsPrimaryHeader" style={{ padding: "12px 24px", minHeight: "56px" }}>
            <span style={{ fontSize: "14px", fontWeight: "600", color: "var(--text)" }}>
              {t("通过自然语言描述创造专属音色", "Create a custom voice from a natural-language description")}
            </span>
          </header>

          <div className="vsTtsEditorWrap">
            <div className="vsTtsEditorCard custom-scrollbar" style={{ padding: "24px", overflowY: "auto", gap: "20px" }}>
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

              {/* Design feedback & preview player inline */}
              {design.designPreviewAudio && (
                <div style={{ marginTop: "24px", padding: "16px", background: "rgba(255, 251, 245, 0.9)", border: "1px solid var(--brand-soft)", borderRadius: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--brand)" }}>
                    {t(`✨ 音色设计成功！这是新音色《${design.designName}》的试听：`, `✨ Voice design succeeded. Preview for "${design.designName}":`)}
                  </div>
                  <audio controls src={design.designPreviewAudio} className="vsAudioElement" style={{ width: "100%", height: "36px" }} />
                </div>
              )}
            </div>
          </div>

          <div className="vsTtsEditorFooter" style={{ marginTop: "auto", display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 24px" }}>
            <button
              type="button"
              className="vsBtnSecondary"
              onClick={() => void design.onRefresh()}
              disabled={design.designListBusy || design.designBusy}
              style={{ height: "36px" }}
            >
              {design.designListBusy ? t("刷新中...", "Refreshing...") : t("刷新音色库", "Refresh voice library")}
            </button>
            
            <div style={{ display: "flex", gap: "10px" }}>
              <button
                type="button"
                className="vsBtnSecondary"
                onClick={() => setIsCatalogOpen(!isCatalogOpen)}
                style={{ height: "36px", borderStyle: "dashed" }}
              >
                {isCatalogOpen ? t("隐藏音色库", "Hide Library") : t("显示音色库", "Show Library")}
              </button>
              <button
                type="submit"
                className="vsBtnPrimary"
                disabled={design.designBusy}
                style={{ height: "36px", minWidth: "120px" }}
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
        </div>

        {/* ── Right Pane: Voice Catalog & Results (Collapsible) ── */}
        <div 
          className={`vsTtsSecondary vsCollapsibleSidebar ${isCatalogOpen ? "open" : "collapsed"}`} 
          style={{ 
            width: isCatalogOpen ? "340px" : "0px", 
            padding: isCatalogOpen ? "24px" : "0px", 
            borderLeft: isCatalogOpen ? "1px solid var(--line)" : "none",
            flexShrink: 0,
            overflowY: "auto"
          }}
        >
          <div className="vsCardSection">
            <h3 className="vsCardSubTitle">{t("任务状态及反馈", "Task status & feedback")}</h3>

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
