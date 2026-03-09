import ErrorNotice from "../components/ErrorNotice";
import type { UseTtsResult } from "../hooks/useTts";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  tts: UseTtsResult;
  errorRuntimeContext: ErrorRuntimeContext;
};

export default function TtsPage({ tts, errorRuntimeContext }: Props) {
  function handleDownload() {
    if (!tts.audioUrl) return;
    const a = document.createElement("a");
    a.href = tts.audioUrl;
    a.download = "voicespirit_tts.mp3";
    a.click();
  }

  const modeTitleMap = {
    text: "文本转语音工作台",
    dialogue: "对话转语音工作台",
    pdf: "PDF 转语音工作台",
  } as const;

  const activeLength =
    tts.ttsMode === "dialogue"
      ? tts.dialogueText.length
      : tts.ttsMode === "pdf"
        ? tts.pdfText.length
        : tts.text.length;

  return (
    <section className="vsTtsWorkspace">
      <form className="vsTtsLayout" onSubmit={tts.onSubmit}>
        {/* ── Left Pane: Editor Area ── */}
        <div className="vsTtsPrimary">
          <header className="vsTtsPrimaryHeader">
            <div>
              <div className="vsModeTabs" style={{ display: "flex", gap: 8, marginBottom: 14 }}>
                <button type="button" className={tts.ttsMode === "text" ? "vsBtnPrimary" : "vsBtnSecondary"} onClick={() => tts.onTtsModeChange("text")}>
                  文本转语音
                </button>
                <button type="button" className={tts.ttsMode === "dialogue" ? "vsBtnPrimary" : "vsBtnSecondary"} onClick={() => tts.onTtsModeChange("dialogue")}>
                  对话转语音
                </button>
                <button type="button" className={tts.ttsMode === "pdf" ? "vsBtnPrimary" : "vsBtnSecondary"} onClick={() => tts.onTtsModeChange("pdf")}>
                  PDF 转语音
                </button>
              </div>
              <h2 className="vsTtsPrimaryTitle">{modeTitleMap[tts.ttsMode]}</h2>
            </div>
            <div className="vsTtsPrimaryStats">
              <span>{activeLength} 字</span>
            </div>
          </header>

          <div className="vsTtsEditorWrap">
            {tts.ttsMode === "text" ? (
              <textarea
                className="vsTtsEditor custom-scrollbar"
                value={tts.text}
                onChange={(e) => tts.onTextChange(e.target.value)}
                placeholder="输入要合成朗读的正文内容、旁白或单人对白结构…"
              />
            ) : null}
            {tts.ttsMode === "dialogue" ? (
              <textarea
                className="vsTtsEditor custom-scrollbar"
                value={tts.dialogueText}
                onChange={(e) => tts.onDialogueTextChange(e.target.value)}
                placeholder={"A: 你好，欢迎来到今天的节目。\nB: 今天我们来聊聊 VoiceSpirit 的语音工作流。"}
              />
            ) : null}
            {tts.ttsMode === "pdf" ? (
              <div style={{ display: "grid", gap: 12 }}>
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => tts.onPdfFileChange(e.target.files?.[0] || null)}
                />
                <textarea
                  className="vsTtsEditor custom-scrollbar"
                  value={tts.pdfText}
                  onChange={(e) => tts.onPdfTextChange(e.target.value)}
                  placeholder="这里放 PDF 提取后的可朗读正文。当前版本先手动整理文本，后续再接自动提取。"
                />
              </div>
            ) : null}
          </div>

          <div className="vsTtsEditorFooter">
            <button
              type="button"
              className="vsBtnSecondary"
              onClick={() => {
                if (tts.ttsMode === "dialogue") {
                  tts.onDialogueTextChange("");
                  return;
                }
                if (tts.ttsMode === "pdf") {
                  tts.onPdfTextChange("");
                  tts.onPdfFileChange(null);
                  return;
                }
                tts.onTextChange("");
              }}
              disabled={!tts.activeSourceText}
            >
              清空舞台
            </button>
            <div className="vsTtsActionGroup">
              <button
                type="submit"
                className="vsBtnPrimary"
                disabled={tts.generating || !tts.activeSourceText.trim()}
              >
                {tts.generating ? (
                  <>
                    <span className="spinner-mini"></span>
                    生成中…
                  </>
                ) : (
                  "生成音频"
                )}
              </button>
            </div>
          </div>
        </div>

        {/* ── Right Pane: Config & Output ── */}
        <div className="vsTtsSecondary">
          <div className="vsCardSection">
            <h3 className="vsCardSubTitle">声音引擎配置</h3>

            <div className="vsField">
              <label className="vsFieldLabel">TTS 引擎</label>
              <div className="vsSelectWrapper">
                <select
                  className="vsSelect"
                  value={tts.ttsEngine}
                  onChange={(e) => tts.onEngineChange(e.target.value as typeof tts.ttsEngine)}
                >
                  {tts.engineOptions.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="vsFieldHint">
                {tts.engineOptions.find((item) => item.value === tts.ttsEngine)?.hint || ""}
              </div>
            </div>

            <div className="vsField">
              <label className="vsFieldLabel">首选音色</label>
              <div className="vsSelectWrapper">
                <select
                  className="vsSelect"
                  value={tts.voice}
                  onChange={(e) => tts.onVoiceChange(e.target.value)}
                  disabled={tts.loadingVoices || tts.voiceOptions.length === 0}
                >
                  <option value="" disabled>-- 请选择音色 --</option>
                  {tts.voiceOptions.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
                {tts.loadingVoices && <div className="vsSelectLoading">加载中…</div>}
              </div>
            </div>

            <div className="vsField" style={{ marginTop: 12 }}>
              <label className="vsFieldLabel">全局语速微调</label>
              <div className="vsRateControl">
                <input
                  type="text"
                  className="vsInput"
                  value={tts.rate}
                  onChange={(e) => tts.onRateChange(e.target.value)}
                  placeholder="例如: +0%, -10%, +25%"
                />
                <button
                  type="button"
                  className="vsBtnGhost"
                  onClick={() => tts.onRateChange("+0%")}
                  title="恢复默认语速"
                >
                  Reset
                </button>
              </div>
            </div>
          </div>

          <div className="vsCardSection border-top">
            <h3 className="vsCardSubTitle">合成结果及监视器</h3>

            <ErrorNotice
              message={tts.ttsError}
              scope="tts"
              context={{ ...errorRuntimeContext, voice: tts.voice, rate: tts.rate }}
            />
            {tts.ttsInfo ? <p className="vsSettingsNotice ok" style={{ margin: "0 0 16px 0" }}>{tts.ttsInfo}</p> : null}

            {tts.audioUrl ? (
              <div className="vsTtsAudioPlayer">
                <audio controls src={tts.audioUrl} className="vsAudioElement" />
                <button
                  type="button"
                  className="vsBtnSecondary vsTtsDownloadBtn"
                  onClick={handleDownload}
                  style={{ width: "100%", marginTop: 16 }}
                >
                  📥 导出 MP3 音频
                </button>
              </div>
            ) : (
              <div className="vsTtsEmptyResult">
                <div className="vsEmptyIcon">🎧</div>
                <div className="vsEmptyTitle">暂无成果</div>
                <div className="vsEmptyDesc">左侧完成内容输入，点击“生成”以试听音轨</div>
              </div>
            )}
          </div>
        </div>
      </form>
    </section>
  );
}
