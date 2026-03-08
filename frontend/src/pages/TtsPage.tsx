import ErrorNotice from "../components/ErrorNotice";
import type { UseTtsResult } from "../hooks/useTts";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  tts: UseTtsResult;
  errorRuntimeContext: ErrorRuntimeContext;
};

export default function TtsPage({ tts, errorRuntimeContext }: Props) {
  return (
    <section className="legacyPanel">
      <form className="form" onSubmit={tts.onSubmit}>
        <label>
          待合成文本
          <textarea
            rows={6}
            value={tts.text}
            onChange={(e) => tts.onTextChange(e.target.value)}
            placeholder="输入要朗读的正文、旁白或对话内容"
          />
        </label>
        <div className="row">
          <label>
            音色
            <select
              value={tts.voice}
              onChange={(e) => tts.onVoiceChange(e.target.value)}
              disabled={tts.loadingVoices || tts.voiceOptions.length === 0}
            >
              {tts.voiceOptions.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            语速
            <input
              value={tts.rate}
              onChange={(e) => tts.onRateChange(e.target.value)}
              placeholder="例如：+0% / -10%"
            />
          </label>
        </div>
        <button type="submit" disabled={tts.generating}>
          {tts.generating ? "生成中..." : "生成语音"}
        </button>
        <ErrorNotice
          message={tts.ttsError}
          scope="tts"
          context={{ ...errorRuntimeContext, voice: tts.voice, rate: tts.rate }}
        />
        {tts.audioUrl ? (
          <div className="audioWrap">
            <p>预览音频</p>
            <audio controls src={tts.audioUrl} />
          </div>
        ) : null}
      </form>
    </section>
  );
}
