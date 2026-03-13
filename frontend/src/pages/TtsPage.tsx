import ErrorNotice from "../components/ErrorNotice";
import type { UseTtsResult } from "../hooks/useTts";
import { useI18n } from "../i18n";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  tts: UseTtsResult;
  errorRuntimeContext: ErrorRuntimeContext;
};

export default function TtsPage({ tts, errorRuntimeContext }: Props) {
  const { t } = useI18n();
  function handleDownload() {
    if (!tts.audioUrl) return;
    const a = document.createElement("a");
    a.href = tts.audioUrl;
    a.download = "voicespirit_tts.mp3";
    a.click();
  }

  const modeTitleMap = {
    text: t("文本转语音工作台", "Text-to-speech workspace"),
    dialogue: t("对话转语音工作台", "Dialogue-to-speech workspace"),
    pdf: t("PDF 转语音工作台", "PDF-to-speech workspace"),
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
                  {t("文本转语音", "Text to speech")}
                </button>
                <button type="button" className={tts.ttsMode === "dialogue" ? "vsBtnPrimary" : "vsBtnSecondary"} onClick={() => tts.onTtsModeChange("dialogue")}>
                  {t("对话转语音", "Dialogue to speech")}
                </button>
                <button type="button" className={tts.ttsMode === "pdf" ? "vsBtnPrimary" : "vsBtnSecondary"} onClick={() => tts.onTtsModeChange("pdf")}>
                  {t("PDF 转语音", "PDF to speech")}
                </button>
              </div>
              <h2 className="vsTtsPrimaryTitle">{modeTitleMap[tts.ttsMode]}</h2>
            </div>
            <div className="vsTtsPrimaryStats">
              <span>{t(`${activeLength} 字`, `${activeLength} chars`)}</span>
            </div>
          </header>

          <div className="vsTtsEditorWrap">
            {tts.ttsMode === "text" ? (
              <textarea
                className="vsTtsEditor custom-scrollbar"
                value={tts.text}
                onChange={(e) => tts.onTextChange(e.target.value)}
                placeholder={t("输入要合成朗读的正文内容、旁白或单人对白结构…", "Enter narration, body text, or a single-speaker script to synthesize...")}
              />
            ) : null}
            {tts.ttsMode === "dialogue" ? (
              <textarea
                className="vsTtsEditor custom-scrollbar"
                value={tts.dialogueText}
                onChange={(e) => tts.onDialogueTextChange(e.target.value)}
                placeholder={t("A: 你好，欢迎来到今天的节目。\nB: 今天我们来聊聊 VoiceSpirit 的语音工作流。", "A: Hello, welcome to today's show.\nB: Today we're talking about VoiceSpirit's speech workflow.")}
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
                  placeholder={t("这里放 PDF 提取后的可朗读正文。当前版本先手动整理文本，后续再接自动提取。", "Paste the readable body text extracted from the PDF here. Manual cleanup for now; auto extraction can follow later.")}
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
              {t("清空舞台", "Clear workspace")}
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
                    {t("生成中…", "Generating...")}
                  </>
                ) : (
                  t("生成音频", "Generate audio")
                )}
              </button>
            </div>
          </div>
        </div>

        {/* ── Right Pane: Config & Output ── */}
        <div className="vsTtsSecondary">
          <div className="vsCardSection">
            <h3 className="vsCardSubTitle">{t("声音引擎配置", "Speech engine settings")}</h3>

            <div className="vsField">
              <label className="vsFieldLabel">{t("TTS 引擎", "TTS engine")}</label>
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
              <label className="vsFieldLabel">{t("首选音色", "Preferred voice")}</label>
              <div className="vsSelectWrapper">
                <select
                  className="vsSelect"
                  value={tts.voice}
                  onChange={(e) => tts.onVoiceChange(e.target.value)}
                  disabled={tts.loadingVoices || tts.voiceOptions.length === 0}
                >
                  <option value="" disabled>{t("-- 请选择音色 --", "-- Select a voice --")}</option>
                  {tts.voiceOptions.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
                {tts.loadingVoices && <div className="vsSelectLoading">{t("加载中…", "Loading...")}</div>}
              </div>
            </div>

            <div className="vsField" style={{ marginTop: 12 }}>
              <label className="vsFieldLabel">{t("全局语速微调", "Global rate adjustment")}</label>
              <div className="vsRateControl">
                <input
                  type="text"
                  className="vsInput"
                  value={tts.rate}
                  onChange={(e) => tts.onRateChange(e.target.value)}
                  placeholder={t("例如: +0%, -10%, +25%", "For example: +0%, -10%, +25%")}
                />
                <button
                  type="button"
                  className="vsBtnGhost"
                  onClick={() => tts.onRateChange("+0%")}
                  title={t("恢复默认语速", "Reset default rate")}
                >
                  Reset
                </button>
              </div>
            </div>
          </div>

          <div className="vsCardSection border-top">
            <h3 className="vsCardSubTitle">{t("合成结果及监视器", "Synthesis output and monitor")}</h3>

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
                  {t("📥 导出 MP3 音频", "📥 Export MP3 audio")}
                </button>
              </div>
            ) : (
              <div className="vsTtsEmptyResult">
                <div className="vsEmptyIcon">🎧</div>
                <div className="vsEmptyTitle">{t("暂无成果", "No output yet")}</div>
                <div className="vsEmptyDesc">{t("左侧完成内容输入，点击“生成”以试听音轨", "Enter content on the left, then click Generate to preview the track")}</div>
              </div>
            )}
          </div>
        </div>
      </form>
    </section>
  );
}
