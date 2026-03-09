import type { UseAudioOverviewResult } from "../../hooks/useAudioOverview";

type Props = {
  audioOverview: UseAudioOverviewResult;
};

export default function PodcastScriptEditor({ audioOverview }: Props) {
  if (!audioOverview.audioOverviewScriptLines.length) {
    return null;
  }

  return (
    <div className="vsPodcastStepCard">
      <div className="vsPodcastStepHeader">
        <div className="vsPodcastStepTitle">
          <span className="vsStepNum">2</span>
          <h3>编辑播客脚本</h3>
        </div>
        <div className="vsPodcastToolbar">
          <button
            type="button"
            className="ghost vsPodcastIconAction"
            title="保存脚本"
            aria-label="保存脚本"
            onClick={() => void audioOverview.onSaveScript()}
            disabled={
              audioOverview.audioOverviewSaving ||
              audioOverview.audioOverviewBusy ||
              audioOverview.audioOverviewSynthBusy
            }
          >
            💾
          </button>
          <button
            type="button"
            className="ghost vsPodcastIconAction"
            title="复制脚本"
            aria-label="复制脚本"
            onClick={() => void audioOverview.onCopyScript()}
          >
            ⧉
          </button>
          <button
            type="button"
            className="ghost vsPodcastIconAction"
            title="导出脚本"
            aria-label="导出脚本"
            onClick={audioOverview.onExportScript}
          >
            ⤓
          </button>
        </div>
      </div>
      <div className="vsPodcastStepContent">
        <div className="scriptLineBox">
          {audioOverview.audioOverviewScriptLines.map((line, index) => (
            <div
              key={`line-${index}`}
              className={`vsScriptBubble ${line.role === "B" ? "roleB" : "roleA"}`}
            >
              <div className="vsScriptBubbleMeta">
                <select
                  className="vsRoleSelect"
                  value={line.role}
                  onChange={(e) => audioOverview.onLineRoleChange(index, e.target.value)}
                >
                  <option value="A">主播 A</option>
                  <option value="B">主播 B</option>
                </select>
                <button
                  type="button"
                  className="vsRemoveLineBtn"
                  title="删除这条台词"
                  onClick={() => audioOverview.onRemoveLine(index)}
                >
                  ×
                </button>
              </div>
              <textarea
                className="vsScriptBubbleInput"
                rows={3}
                value={line.text}
                onChange={(e) => audioOverview.onLineTextChange(index, e.target.value)}
                placeholder="输入这一句台词内容"
              />
            </div>
          ))}
        </div>
        <div className="vsAddLineCenter">
          <button type="button" className="vsAddLineBtn" onClick={audioOverview.onAddLine}>
            <span className="vsBtnGlyph">+</span>
            添加台词
          </button>
        </div>
      </div>
    </div>
  );
}
