import type { UseAudioOverviewResult } from "../../hooks/useAudioOverview";
import { useI18n } from "../../i18n";

type Props = {
  audioOverview: UseAudioOverviewResult;
};

export default function PodcastSynthBar({ audioOverview }: Props) {
  const { t } = useI18n();
  if (!audioOverview.audioOverviewScriptLines.length) {
    return null;
  }

  return (
    <div className="vsSynthBar">
      <div className="vsSynthBarMain">
        <div className="vsSynthVoices">
          <label className="vsSynthVoiceSelect">
            <span className="roleIndicator roleA">A</span>
            <select
              value={audioOverview.audioOverviewVoiceA}
              onChange={(e) => audioOverview.onVoiceAChange(e.target.value)}
              disabled={!audioOverview.audioOverviewVoiceOptions.length}
            >
              {audioOverview.audioOverviewVoiceOptions.map((item) => (
                <option key={`a-${item.name}`} value={item.name}>
                  {item.short_name || item.name}
                </option>
              ))}
            </select>
          </label>
          <label className="vsSynthVoiceSelect">
            <span className="roleIndicator roleB">B</span>
            <select
              value={audioOverview.audioOverviewVoiceB}
              onChange={(e) => audioOverview.onVoiceBChange(e.target.value)}
              disabled={!audioOverview.audioOverviewVoiceOptions.length}
            >
              {audioOverview.audioOverviewVoiceOptions.map((item) => (
                <option key={`b-${item.name}`} value={item.name}>
                  {item.short_name || item.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="vsSynthBarActions">
          <button
            type="button"
            className="vsPodcastAdvancedToggle"
            onClick={audioOverview.onToggleSynthAdvanced}
          >
            {audioOverview.synthBarAdvancedOpen ? t("收起参数", "Hide parameters") : t("⚙️ 更多参数", "⚙️ More parameters")}
          </button>
          <button
            type="button"
            className="vsSynthesizeTriggerBtn"
            onClick={() => void audioOverview.onSynthesize()}
            disabled={
              audioOverview.audioOverviewSynthBusy ||
              audioOverview.audioOverviewBusy ||
              audioOverview.audioOverviewSaving ||
              audioOverview.audioOverviewScriptLines.length < 2
            }
          >
            {audioOverview.audioOverviewSynthBusy ? t("合成中...", "Synthesizing...") : t("🎙️ 合成", "🎙️ Synthesize")}
          </button>
        </div>
      </div>
      {audioOverview.synthBarAdvancedOpen ? (
        <div className="vsSynthBarAdvanced">
          <div className="rowOverview">
            <label>
              {t("语速", "Rate")}
              <input
                value={audioOverview.audioOverviewRate}
                onChange={(e) => audioOverview.onRateChange(e.target.value)}
                placeholder="+0%"
              />
            </label>
            <label>
              {t("停顿间隔（毫秒）", "Pause gap (ms)")}
              <input
                type="number"
                min={0}
                max={3000}
                value={audioOverview.audioOverviewGapMs}
                onChange={(e) => audioOverview.onGapMsChange(e.target.value)}
              />
            </label>
            <label>
              {t("拼接策略", "Merge strategy")}
              <select
                value={audioOverview.audioOverviewMergeStrategy}
                onChange={(e) =>
                  audioOverview.onMergeStrategyChange(
                    e.target.value as UseAudioOverviewResult["audioOverviewMergeStrategy"]
                  )
                }
              >
                <option value="auto">auto</option>
                <option value="pydub">pydub</option>
                <option value="ffmpeg">ffmpeg</option>
                <option value="concat">concat</option>
              </select>
            </label>
          </div>
        </div>
      ) : null}
    </div>
  );
}
