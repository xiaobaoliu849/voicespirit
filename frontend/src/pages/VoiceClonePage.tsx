import { useState } from "react";
import ErrorNotice from "../components/ErrorNotice";
import VoiceCatalog from "../components/VoiceCatalog";
import type { VoiceCloneController } from "../hooks/useVoiceManagement";
import { useI18n } from "../i18n";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  clone: VoiceCloneController;
  errorRuntimeContext: ErrorRuntimeContext;
};

export default function VoiceClonePage({ clone, errorRuntimeContext }: Props) {
  const { t } = useI18n();
  const [isCatalogOpen, setIsCatalogOpen] = useState(true);

  return (
    <section className="vsTtsWorkspace">
      <form className="vsTtsLayout" onSubmit={clone.onSubmit} style={{ margin: 0, display: "flex", height: "100%" }}>
        {/* ── Left Pane: Clone Input ── */}
        <div className="vsTtsPrimary" style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
          <header className="vsTtsPrimaryHeader" style={{ padding: "12px 24px", minHeight: "56px" }}>
            <span style={{ fontSize: "14px", fontWeight: "600", color: "var(--text)" }}>
              {t("通过上传音频样板复刻特定人声", "Recreate a specific voice from an uploaded audio sample")}
            </span>
          </header>

          <div className="vsTtsEditorWrap">
            <div className="vsTtsEditorCard custom-scrollbar" style={{ padding: "24px", overflowY: "auto", gap: "24px" }}>
              <label className="vsField">
                <span className="vsFieldLabel">{t("新音色命名", "New voice name")}</span>
                <input
                  className="vsInput"
                  value={clone.cloneName}
                  onChange={(e) => clone.onNameChange(e.target.value)}
                  placeholder={t("例如：my_cloned_voice_v1", "For example: my_cloned_voice_v1")}
                  required
                />
                <span className="vsFieldHint">{t("请使用字母、数字或下划线，方便在模型调用时识别。", "Use letters, numbers, or underscores so the model can reference it reliably.")}</span>
              </label>

              <div className="vsCardSection" style={{ background: "var(--surface)", padding: "24px", borderRadius: "8px", border: "1px dashed var(--brand)", textAlign: "center", cursor: "pointer" }}>
                <label className="vsField">
                  <span className="vsFieldLabel" style={{ fontSize: "15px", marginBottom: "8px" }}>{t("🎙️ 上传音频样板 (Audio Sample)", "🎙️ Upload audio sample")}</span>
                  <input
                    type="file"
                    accept="audio/*"
                    className="vsInput"
                    style={{ display: "block", margin: "0 auto 12px", width: "100%", maxWidth: "300px" }}
                    onChange={(e) => clone.onAudioFileChange(e.target.files?.[0] || null)}
                    required
                  />
                  <span className="vsFieldHint" style={{ marginTop: "12px", color: "var(--brand-dark)" }}>
                    {t("💡 建议：上传 5-30 秒清晰、无背景噪音 of a single speaker clip, for best results.", "💡 Tip: upload a clear 5-30 second single-speaker clip with minimal background noise for best results.")}
                  </span>
                </label>

                {clone.cloneAudioFile && (
                  <div style={{ marginTop: "16px", padding: "12px", background: "#fff", borderRadius: "8px", border: "1px solid var(--line)", display: "flex", alignItems: "center", gap: "10px" }}>
                    <span style={{ fontSize: "20px" }}>📄</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: "14px", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {clone.cloneAudioFile.name}
                      </div>
                      <div style={{ fontSize: "12px", color: "var(--muted)" }}>
                        {(clone.cloneAudioFile.size / 1024 / 1024).toFixed(2)} MB
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Inline Training Status Indicators */}
              {clone.cloneBusy && (
                <div style={{ padding: "16px", background: "rgba(107, 76, 246, 0.05)", border: "1px dashed var(--brand)", borderRadius: "12px", display: "flex", alignItems: "center", gap: "12px" }}>
                  <span className="spinner-mini" style={{ width: "24px", height: "24px" }}></span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--brand)" }}>{t("音色克隆处理中", "Voice cloning in progress")}</div>
                    <div style={{ fontSize: "12px", color: "var(--muted)", marginTop: "2px" }}>{t("正在通过大模型提取声纹特征，请稍候…", "Extracting voiceprint features with the model. Please wait.")}</div>
                  </div>
                </div>
              )}

              {clone.cloneInfo && (
                <div style={{ padding: "16px", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "12px", display: "flex", alignItems: "center", gap: "12px", color: "#166534" }}>
                  <span style={{ fontSize: "18px" }}>✅</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: "13px", fontWeight: 600 }}>{t("克隆音色训练成功！", "Voice cloned successfully!")}</div>
                    <div style={{ fontSize: "12px", marginTop: "2px" }}>{clone.cloneInfo}</div>
                  </div>
                </div>
              )}

              <div style={{ marginTop: "auto", padding: "16px", background: "#f8fafc", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
                <p className="vsFieldHint">
                  <strong>{t("温馨提示：", "Reminder:")}</strong> {t("克隆音色仅供个人研究与创作使用。请确保您拥有该声音样本的使用授权，尊重他人的声音版权与隐私。", "Voice cloning is for personal research and creative work only. Make sure you have permission to use the source voice sample and respect voice rights and privacy.")}
                </p>
              </div>
            </div>
          </div>

          <div className="vsTtsEditorFooter" style={{ marginTop: "auto", display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 24px" }}>
            <button
              type="button"
              className="vsBtnSecondary"
              onClick={() => void clone.onRefresh()}
              disabled={clone.cloneListBusy || clone.cloneBusy}
              style={{ height: "36px" }}
            >
              {clone.cloneListBusy ? t("刷新中...", "Refreshing...") : t("刷新音色库", "Refresh voice library")}
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
                disabled={clone.cloneBusy || !clone.cloneAudioFile}
                style={{ height: "36px", minWidth: "120px" }}
              >
                {clone.cloneBusy ? (
                  <>
                    <span className="spinner-mini"></span>
                    {t("正在上传并训练…", "Uploading and training...")}
                  </>
                ) : (
                  t("开始克隆音色", "Start voice cloning")
                )}
              </button>
            </div>
          </div>
        </div>

        {/* ── Right Pane: Voice Catalog (Collapsible) ── */}
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
            <h3 className="vsCardSubTitle">{t("任务状态", "Task status")}</h3>

            <ErrorNotice
              message={clone.cloneError}
              scope="voice_clone"
              context={{ ...errorRuntimeContext, preferred_name: clone.cloneName }}
            />

            {!clone.cloneError && !clone.cloneInfo && !clone.cloneBusy && (
              <div className="vsTtsEmptyResult" style={{ padding: "24px 16px" }}>
                <div className="vsEmptyIcon" style={{ fontSize: "24px", marginBottom: "8px" }}>🧬</div>
                <div className="vsEmptyTitle">{t("等待启动", "Waiting to start")}</div>
                <div className="vsEmptyDesc">{t("上传音频样板后点击“开始克隆”", "Upload a sample, then click Start voice cloning")}</div>
              </div>
            )}
          </div>

          <div className="vsCardSection border-top">
            <VoiceCatalog
              title={t("已克隆音色库", "Cloned voice library")}
              voices={clone.cloneVoices}
              busy={clone.cloneBusy}
              listBusy={clone.cloneListBusy}
              emptyText={t("暂无克隆成功的音色。", "No cloned voices yet.")}
              onDeleteVoice={clone.onDeleteVoice}
            />
          </div>
        </div>
      </form>
    </section>
  );
}
