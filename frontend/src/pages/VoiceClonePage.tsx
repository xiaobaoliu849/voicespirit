import ErrorNotice from "../components/ErrorNotice";
import VoiceCatalog from "../components/VoiceCatalog";
import type { VoiceCloneController } from "../hooks/useVoiceManagement";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  clone: VoiceCloneController;
  errorRuntimeContext: ErrorRuntimeContext;
};

export default function VoiceClonePage({ clone, errorRuntimeContext }: Props) {
  return (
    <section className="legacyPanel">
      <form className="form" onSubmit={clone.onSubmit}>
        <label>
          音色名称
          <input
            value={clone.cloneName}
            onChange={(e) => clone.onNameChange(e.target.value)}
            placeholder="例如：voice_clone_demo"
          />
        </label>

        <label>
          音频文件
          <input
            type="file"
            accept="audio/*"
            onChange={(e) => clone.onAudioFileChange(e.target.files?.[0] || null)}
          />
        </label>
        {clone.cloneAudioFile ? <p className="muted">已选择：{clone.cloneAudioFile.name}</p> : null}

        <div className="inlineActions">
          <button type="submit" disabled={clone.cloneBusy}>
            {clone.cloneBusy ? "创建中..." : "创建克隆音色"}
          </button>
          <button
            type="button"
            className="ghost"
            onClick={() => void clone.onRefresh()}
            disabled={clone.cloneListBusy || clone.cloneBusy}
          >
            {clone.cloneListBusy ? "加载中..." : "刷新列表"}
          </button>
        </div>

        <ErrorNotice
          message={clone.cloneError}
          scope="voice_clone"
          context={{ ...errorRuntimeContext, preferred_name: clone.cloneName }}
        />
        {clone.cloneInfo ? <p className="ok">{clone.cloneInfo}</p> : null}

        <VoiceCatalog
          title="克隆音色列表"
          voices={clone.cloneVoices}
          busy={clone.cloneBusy}
          listBusy={clone.cloneListBusy}
          emptyText="暂无音色。"
          onDeleteVoice={clone.onDeleteVoice}
        />
      </form>
    </section>
  );
}
