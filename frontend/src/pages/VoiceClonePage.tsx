import ErrorNotice from "../components/ErrorNotice";
import VoiceCatalog from "../components/VoiceCatalog";
import type { VoiceCloneController } from "../hooks/useVoiceManagement";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  clone: VoiceCloneController;
  errorRuntimeContext: ErrorRuntimeContext;
};

export default function VoiceClonePage({ clone, errorRuntimeContext }: Props) {
  return (
    <section className="vsTtsWorkspace">
      <form className="vsTtsLayout" onSubmit={clone.onSubmit} style={{ margin: 0 }}>
        {/* ── Left Pane: Clone Input ── */}
        <div className="vsTtsPrimary" style={{ flex: 1, borderRight: "1px solid var(--line)" }}>
          <header className="vsTtsPrimaryHeader">
            <h2 className="vsTtsPrimaryTitle">音色克隆工作室 (Voice Clone)</h2>
            <div className="vsTtsPrimaryStats">
              <span>通过上传音频样板复刻特定人声</span>
            </div>
          </header>

          <div className="vsTtsEditorWrap" style={{ display: "flex", flexDirection: "column", gap: "24px", padding: "24px", overflowY: "auto" }}>
            <label className="vsField">
              <span className="vsFieldLabel">新音色命名</span>
              <input
                className="vsInput"
                value={clone.cloneName}
                onChange={(e) => clone.onNameChange(e.target.value)}
                placeholder="例如：my_cloned_voice_v1"
                required
              />
              <span className="vsFieldHint">请使用字母、数字或下划线，方便在模型调用时识别。</span>
            </label>

            <div className="vsCardSection" style={{ background: "var(--surface)", padding: "24px", borderRadius: "8px", border: "1px dashed var(--brand)", textAlign: "center", cursor: "pointer" }}>
              <label className="vsField">
                <span className="vsFieldLabel" style={{ fontSize: "15px", marginBottom: "8px" }}>🎙️ 上传音频样板 (Audio Sample)</span>
                <input
                  type="file"
                  accept="audio/*"
                  className="vsInput"
                  style={{ display: "block", margin: "0 auto 12px", width: "100%", maxWidth: "300px" }}
                  onChange={(e) => clone.onAudioFileChange(e.target.files?.[0] || null)}
                  required
                />
                <span className="vsFieldHint" style={{ marginTop: "12px", color: "var(--brand-dark)" }}>
                  💡 建议：上传 5-30 秒清晰、无背景噪音的单人说话音频，效果最佳。
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
                <strong>温馨提示：</strong> 克隆音色仅供个人研究与创作使用。请确保您拥有该声音样本的使用授权，尊重他人的声音版权与隐私。
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
              {clone.cloneListBusy ? "刷新中..." : "刷新音色库"}
            </button>
            <button
              type="submit"
              className="vsBtnPrimary"
              disabled={clone.cloneBusy || !clone.cloneAudioFile}
            >
              {clone.cloneBusy ? (
                <>
                  <span className="spinner-mini"></span>
                  正在上传并训练…
                </>
              ) : (
                "开始克隆音色"
              )}
            </button>
          </div>
        </div>

        {/* ── Right Pane: Voice Catalog ── */}
        <div className="vsTtsSecondary" style={{ width: "380px", flexShrink: 0 }}>

          <div className="vsCardSection">
            <h3 className="vsCardSubTitle">任务状态</h3>

            <ErrorNotice
              message={clone.cloneError}
              scope="voice_clone"
              context={{ ...errorRuntimeContext, preferred_name: clone.cloneName }}
            />
            {clone.cloneInfo ? <p className="vsSettingsNotice ok" style={{ marginBottom: 16 }}>{clone.cloneInfo}</p> : null}

            {!clone.cloneError && !clone.cloneInfo && !clone.cloneBusy && (
              <div className="vsTtsEmptyResult" style={{ padding: "32px 16px" }}>
                <div className="vsEmptyIcon">🧬</div>
                <div className="vsEmptyTitle">等待启动</div>
                <div className="vsEmptyDesc">上传音频样板后点击“开始克隆”</div>
              </div>
            )}

            {clone.cloneBusy && (
              <div className="vsTtsEmptyResult" style={{ padding: "32px 16px", borderColor: "var(--brand)" }}>
                <div className="spinner-mini" style={{ width: "32px", height: "32px", marginBottom: "12px" }}></div>
                <div className="vsEmptyTitle" style={{ color: "var(--brand)" }}>处理中</div>
                <div className="vsEmptyDesc">正在通过大模型提取声纹特征，请稍候</div>
              </div>
            )}
          </div>

          <div className="vsCardSection border-top">
            <VoiceCatalog
              title="已克隆音色库"
              voices={clone.cloneVoices}
              busy={clone.cloneBusy}
              listBusy={clone.cloneListBusy}
              emptyText="暂无克隆成功的音色。"
              onDeleteVoice={clone.onDeleteVoice}
            />
          </div>
        </div>
      </form>
    </section>
  );
}
