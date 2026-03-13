import type { CustomVoice } from "../api";
import { useI18n } from "../i18n";

type Props = {
  title: string;
  voices: CustomVoice[];
  busy: boolean;
  listBusy: boolean;
  emptyText: string;
  onDeleteVoice: (voiceName: string) => void | Promise<void>;
};

export default function VoiceCatalog({
  title,
  voices,
  busy,
  listBusy,
  emptyText,
  onDeleteVoice
}: Props) {
  const { t } = useI18n();
  return (
    <div className="resultBox">
      <p>
        {title}（{voices.length}）
      </p>
      <div className="voiceList">
        {voices.map((item) => (
          <div key={item.voice} className="voiceItem">
            <div>
              <strong>{item.voice}</strong>
              <p>{item.target_model}</p>
            </div>
            <button
              type="button"
              className="danger"
              onClick={() => void onDeleteVoice(item.voice)}
              disabled={busy || listBusy}
            >
              {t("删除", "Delete")}
            </button>
          </div>
        ))}
        {!voices.length ? <p className="vsInlineEmptyState muted">{emptyText}</p> : null}
      </div>
    </div>
  );
}
