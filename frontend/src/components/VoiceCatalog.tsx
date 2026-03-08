import type { CustomVoice } from "../api";

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
              删除
            </button>
          </div>
        ))}
        {!voices.length ? <p className="vsInlineEmptyState muted">{emptyText}</p> : null}
      </div>
    </div>
  );
}
