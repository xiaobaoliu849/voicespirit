import { useState } from "react";
import type { AudioAgentSource } from "../../api";
import { useI18n } from "../../i18n";

type Props = {
  sources: AudioAgentSource[];
};

const SOURCE_TYPE_LABELS: Record<string, { zh: string; en: string }> = {
  evermem: { zh: "长期记忆", en: "Memory" },
  manual_text: { zh: "手动资料", en: "Manual text" },
  manual_url: { zh: "来源 URL", en: "Source URL" },
  provider_search: { zh: "模型检索", en: "Provider search" },
  transcript: { zh: "转录文本", en: "Transcript" },
};

function SourceCard({ source }: { source: AudioAgentSource }) {
  const [expanded, setExpanded] = useState(false);
  const { t, language } = useI18n();
  const typeLabel = SOURCE_TYPE_LABELS[source.source_type];
  const label = typeLabel
    ? language === "zh-CN" ? typeLabel.zh : typeLabel.en
    : source.source_type;

  const hasContent = source.content && source.content.trim().length > 0;
  const displayText = expanded ? source.content : source.snippet;

  return (
    <div className="vsAgentSourceCard">
      <div className="vsAgentSourceCardHeader">
        <span className="vsAgentSourceTypeBadge">{label}</span>
        {source.title ? (
          <span className="vsAgentSourceTitle">{source.title}</span>
        ) : null}
        {source.score > 0 ? (
          <span className="vsAgentSourceScore">{Math.round(source.score * 100)}%</span>
        ) : null}
      </div>
      {displayText ? (
        <p className="vsAgentSourceSnippet">
          {displayText}
        </p>
      ) : source.uri ? (
        <p className="vsAgentSourceUri">{source.uri}</p>
      ) : null}
      {hasContent && source.content !== source.snippet ? (
        <button
          className="vsAgentSourceToggle"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded
            ? t("收起", "Collapse")
            : t("展开详情", "Show details")}
        </button>
      ) : null}
    </div>
  );
}

export default function AgentSourcesPanel({ sources }: Props) {
  const { t } = useI18n();

  if (sources.length === 0) {
    return null;
  }

  return (
    <div className="vsAgentSourcesPanel">
      <h4 className="vsAgentSourcesTitle">
        {t(`参考资料 (${sources.length})`, `Sources (${sources.length})`)}
      </h4>
      <div className="vsAgentSourceList">
        {sources.map((source) => (
          <SourceCard key={source.id} source={source} />
        ))}
      </div>
    </div>
  );
}
