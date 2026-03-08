import type { UseAudioOverviewResult } from "../../hooks/useAudioOverview";

type Props = {
  audioOverview: UseAudioOverviewResult;
};

export default function PodcastSynthBar({ audioOverview }: Props) {
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
            {audioOverview.synthBarAdvancedOpen ? "收起参数" : "⚙️ 更多参数"}
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
            {audioOverview.audioOverviewSynthBusy ? "合成中..." : "🎙️ 合成"}
          </button>
        </div>
      </div>
      {audioOverview.synthBarAdvancedOpen ? (
        <div className="vsSynthBarAdvanced">
          <div className="rowOverview">
            <label>
              语速
              <input
                value={audioOverview.audioOverviewRate}
                onChange={(e) => audioOverview.onRateChange(e.target.value)}
                placeholder="+0%"
              />
            </label>
            <label>
              停顿间隔（毫秒）
              <input
                type="number"
                min={0}
                max={3000}
                value={audioOverview.audioOverviewGapMs}
                onChange={(e) => audioOverview.onGapMsChange(e.target.value)}
              />
            </label>
            <label>
              拼接策略
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
