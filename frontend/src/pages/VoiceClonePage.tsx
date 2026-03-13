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
  return (
    <section className="vsTtsWorkspace">
      <form className="vsTtsLayout" onSubmit={clone.onSubmit} style={{ margin: 0 }}>
        {/* ── Left Pane: Clone Input ── */}
        <div className="vsTtsPrimary" style={{ flex: 1, borderRight: "1px solid var(--line)" }}>
          <header className="vsTtsPrimaryHeader">
            <h2 className="vsTtsPrimaryTitle">{t("音色克隆工作室 (Voice Clone)", "Voice Clone Studio")}</h2>
            <div className="vsTtsPrimaryStats">
              <span>{t("通过上传音频样板复刻特定人声", "Recreate a specific voice from an uploaded audio sample")}</span>
            </div>
          </header>

          <div className="vsTtsEditorWrap" style={{ display: "flex", flexDirection: "column", gap: "24px", padding: "24px", overflowY: "auto" }}>
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
                  {t("💡 建议：上传 5-30 秒清晰、无背景噪音的单人说话音频，效果最佳。", "💡 Tip: upload a clear 5-30 second single-speaker clip with minimal background noise for best results.")}
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

            <div style={{ marginTop: "auto", padding: "16px", background: "#f8fafc", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
              <p className="vsFieldHint">
                <strong>{t("温馨提示：", "Reminder:")}</strong> {t("克隆音色仅供个人研究与创作使用。请确保您拥有该声音样本的使用授权，尊重他人的声音版权与隐私。", "Voice cloning is for personal research and creative work only. Make sure you have permission to use the source voice sample and respect voice rights and privacy.")}
              </p>
            </div>
          </div>

          <div className="vsTtsEditorFooter" style={{ marginTop: "16px" }}>
            <button
              type="button"
              className="vsBtnSecondary"
              onClick={() => void clone.onRefresh()}
              disabled={clone.cloneListBusy || clone.cloneBusy}
            >
              {clone.cloneListBusy ? t("刷新中...", "Refreshing...") : t("刷新音色库", "Refresh voice library")}
            </button>
            <button
              type="submit"
              className="vsBtnPrimary"
              disabled={clone.cloneBusy || !clone.cloneAudioFile}
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

        {/* ── Right Pane: Voice Catalog ── */}
        <div className="vsTtsSecondary" style={{ width: "380px", flexShrink: 0 }}>

          <div className="vsCardSection">
            <h3 className="vsCardSubTitle">{t("任务状态", "Task status")}</h3>

            <ErrorNotice
              message={clone.cloneError}
              scope="voice_clone"
              context={{ ...errorRuntimeContext, preferred_name: clone.cloneName }}
            />
            {clone.cloneInfo ? <p className="vsSettingsNotice ok" style={{ marginBottom: 16 }}>{clone.cloneInfo}</p> : null}

            {!clone.cloneError && !clone.cloneInfo && !clone.cloneBusy && (
              <div className="vsTtsEmptyResult" style={{ padding: "32px 16px" }}>
                <div className="vsEmptyIcon">🧬</div>
                <div className="vsEmptyTitle">{t("等待启动", "Waiting to start")}</div>
                <div className="vsEmptyDesc">{t("上传音频样板后点击“开始克隆”", "Upload a sample, then click Start voice cloning")}</div>
              </div>
            )}

            {clone.cloneBusy && (
              <div className="vsTtsEmptyResult" style={{ padding: "32px 16px", borderColor: "var(--brand)" }}>
                <div className="spinner-mini" style={{ width: "32px", height: "32px", marginBottom: "12px" }}></div>
                <div className="vsEmptyTitle" style={{ color: "var(--brand)" }}>{t("处理中", "Processing")}</div>
                <div className="vsEmptyDesc">{t("正在通过大模型提取声纹特征，请稍候", "Extracting voiceprint features with the model. Please wait.")}</div>
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
