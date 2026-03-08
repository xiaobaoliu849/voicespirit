import { PROVIDERS } from "../../appConfig";
import type { UseAudioOverviewResult } from "../../hooks/useAudioOverview";

type Props = {
  audioOverview: UseAudioOverviewResult;
};

export default function PodcastTopicStep({ audioOverview }: Props) {
  return (
    <div className="vsPodcastStepCard">
      <div className="vsPodcastStepHeader">
        <div className="vsPodcastStepTitle">
          <span className="vsStepNum">1</span>
          <h3>确定播客主题</h3>
        </div>
      </div>
      <div className="vsPodcastStepContent">
        <label className="vsPodcastField">
          <span className="vsPodcastFieldLabel">话题</span>
          <textarea
            className="vsTopicInput"
            rows={5}
            value={audioOverview.audioOverviewTopic}
            onChange={(e) => audioOverview.onTopicChange(e.target.value)}
            placeholder="输入你想讨论的话题，例如：AI 如何改变个人学习习惯？"
          />
        </label>

        <div className="vsPodcastStepActions">
          <button
            className="vsGenerateBtn"
            type="submit"
            disabled={audioOverview.audioOverviewBusy}
          >
            {audioOverview.audioOverviewBusy ? "生成中..." : "生成脚本"}
          </button>
          <button
            type="button"
            className="vsPodcastAdvancedToggle"
            onClick={audioOverview.onToggleAdvanced}
          >
            {audioOverview.audioOverviewAdvancedOpen ? "收起高级设置" : "⚙️ 高级设置"}
          </button>
        </div>

        {audioOverview.audioOverviewAdvancedOpen ? (
          <div className="vsPodcastAdvancedPanel">
            <div className="rowOverview">
              <label>
                语言
                <select
                  value={audioOverview.audioOverviewLanguage}
                  onChange={(e) => audioOverview.onLanguageChange(e.target.value)}
                >
                  <option value="zh">中文</option>
                  <option value="en">英文</option>
                </select>
              </label>
              <label>
                LLM 供应商
                <select
                  value={audioOverview.audioOverviewProvider}
                  onChange={(e) => audioOverview.onProviderChange(e.target.value)}
                >
                  {PROVIDERS.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                模型
                <input
                  value={audioOverview.audioOverviewModel}
                  onChange={(e) => audioOverview.onModelChange(e.target.value)}
                  placeholder="留空则使用默认模型"
                />
              </label>
              <label>
                对话轮数
                <input
                  type="number"
                  min={2}
                  max={40}
                  value={audioOverview.audioOverviewTurnCount}
                  onChange={(e) => audioOverview.onTurnCountChange(e.target.value)}
                />
              </label>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
