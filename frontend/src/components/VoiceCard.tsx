import React, { useMemo } from "react";
import type { CustomVoice } from "../api";
import { useI18n } from "../i18n";

type Props = {
  item: CustomVoice;
  onDelete: (e: React.MouseEvent) => void;
};

/* Deterministic gradient palette based on string hash */
const COVER_GRADIENTS = [
  ["#f43f5e", "#fb7185", "#fda4af"], // rose
  ["#8b5cf6", "#a78bfa", "#c4b5fd"], // violet
  ["#3b82f6", "#60a5fa", "#93c5fd"], // blue
  ["#10b981", "#34d399", "#6ee7b7"], // emerald
  ["#f59e0b", "#fbbf24", "#fcd34d"], // amber
  ["#0ea5e9", "#38bdf8", "#7dd3fc"], // sky
];

function hashStr(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

function DiamondPattern({ color }: { color: string }) {
  return (
    <svg className="vsTranscribeCardWave" viewBox="0 0 100 100" preserveAspectRatio="none">
      <polygon points="50,0 100,50 50,100 0,50" fill={color} opacity="0.15" />
      <polygon points="10,20 30,40 10,60 -10,40" fill={color} opacity="0.2" />
      <polygon points="90,60 110,80 90,100 70,80" fill={color} opacity="0.2" />
    </svg>
  );
}

export const VoiceCard: React.FC<Props> = ({ item, onDelete }) => {
  const { t } = useI18n();
  const hash = useMemo(() => hashStr(item.voice), [item.voice]);
  const palette = COVER_GRADIENTS[hash % COVER_GRADIENTS.length];
  const isDesign = item.type === "voice_design";

  return (
    <div className="vsTranscribeCard completed">
      {/* Cover */}
      <div className="vsTranscribeCardCover">
        <div
          className="vsTranscribeCardCoverBg"
          style={{
            background: `linear-gradient(135deg, ${palette[0]}, ${palette[1]} 60%, ${palette[2]})`,
          }}
        />
        <DiamondPattern color="rgba(255,255,255,0.8)" />
        <span className="vsTranscribeCardFormatBadge">
          {isDesign ? "Design" : "Clone"}
        </span>
      </div>

      {/* Meta */}
      <div className="vsTranscribeCardMeta">
        <div className="vsTranscribeCardMetaTop">
          <span className="vsTranscribeCardTime">
            {item.target_model}
          </span>
        </div>
        <h4 className="vsTranscribeCardTitle" title={item.voice}>
          {item.voice}
        </h4>
        <p className="vsTranscribeCardPreview">
          {isDesign
            ? t("基于自然语言生成的专属音色", "Custom voice generated from description")
            : t("基于样本音频克隆的复刻音色", "Voice cloned from audio sample")}
        </p>
      </div>

      {/* Footer */}
      <div className="vsTranscribeCardFooter">
        <span />
        <button
          className="vsTranscribeCardDeleteBtn"
          onClick={onDelete}
          title={t("删除音色", "Delete voice")}
        >
          {t("删除", "Delete")}
        </button>
      </div>
    </div>
  );
};
