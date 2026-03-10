import ErrorNotice from "../components/ErrorNotice";
import VoiceCatalog from "../components/VoiceCatalog";
import type { VoiceDesignController } from "../hooks/useVoiceManagement";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  design: VoiceDesignController;
  errorRuntimeContext: ErrorRuntimeContext;
};

export default function VoiceDesignPage({ design, errorRuntimeContext }: Props) {
  return (
    <section className="vsTtsWorkspace">
      <form className="vsTtsLayout" onSubmit={design.onSubmit} style={{ margin: 0 }}>
        {/* ── Left Pane: Design Input ── */}
        <div className="vsTtsPrimary" style={{ flex: 1, borderRight: "1px solid var(--line)" }}>
          <header className="vsTtsPrimaryHeader">
            <h2 className="vsTtsPrimaryTitle">音色设计工作室 (Voice Design)</h2>
            <div className="vsTtsPrimaryStats">
              <span>通过自然语言描述创造专属音色</span>
            </div>
          </header>

          <div className="vsTtsEditorWrap" style={{ display: "flex", flexDirection: "column", gap: "20px", padding: "24px", overflowY: "auto" }}>
            <div className="vsFormRow">
              <label className="vsField">
                <span className="vsFieldLabel">音色名称</span>
                <input
                  className="vsInput"
                  value={design.designName}
                  onChange={(e) => design.onNameChange(e.target.value)}
                  placeholder="例如：voice_design_demo"
                  required
                />
              </label>
              <label className="vsField">
                <span className="vsFieldLabel">预设语种</span>
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
              <span className="vsFieldLabel">风格提示词 (Prompt)</span>
              <textarea
                className="vsTextarea"
                rows={5}
                value={design.designPrompt}
                onChange={(e) => design.onPromptChange(e.target.value)}
                placeholder="在此详细描述音色的年龄、语气、场景和说话风格... 如：一个活泼可爱的中国南方小女孩的声音，带有童音，语速偏快。"
                required
              />
            </label>

            <label className="vsField" style={{ marginTop: "16px" }}>
              <span className="vsFieldLabel">试听检验文本 (Preview Text)</span>
              <textarea
                className="vsTextarea"
                rows={3}
                value={design.designPreviewText}
                onChange={(e) => design.onPreviewTextChange(e.target.value)}
                placeholder="输入一段用于新音色试听的示例文本"
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
              {design.designListBusy ? "刷新中..." : "刷新音色库"}
            </button>
            <button
              type="submit"
              className="vsBtnPrimary"
              disabled={design.designBusy}
            >
              {design.designBusy ? (
                <>
                  <span className="spinner-mini"></span>
                  正在设计并合成…
                </>
              ) : (
                "创造全新音色"
              )}
            </button>
          </div>
        </div>

        {/* ── Right Pane: Voice Catalog & Results ── */}
        <div className="vsTtsSecondary" style={{ width: "380px", flexShrink: 0 }}>

          <div className="vsCardSection">
            <h3 className="vsCardSubTitle">设计反馈与试听结果</h3>

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
                  ✨ 音色设计成功！这是新音色《{design.designName}》的试听：
                </div>
                <audio controls src={design.designPreviewAudio} className="vsAudioElement" />
              </div>
            ) : (
              <div className="vsTtsEmptyResult" style={{ marginBottom: "20px" }}>
                <div className="vsEmptyIcon" style={{ fontSize: 24 }}>🪄</div>
                <div className="vsEmptyTitle">暂无成果</div>
              </div>
            )}
          </div>

          <div className="vsCardSection border-top">
            <VoiceCatalog
              title="设计音色云端库"
              voices={design.designVoices}
              busy={design.designBusy}
              listBusy={design.designListBusy}
              emptyText="暂无您设计的自定义音色。"
              onDeleteVoice={design.onDeleteVoice}
            />
          </div>
        </div>
      </form>
    </section>
  );
}
