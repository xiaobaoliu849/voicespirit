import ErrorNotice from "../components/ErrorNotice";
import VoiceCatalog from "../components/VoiceCatalog";
import type { VoiceDesignController } from "../hooks/useVoiceManagement";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  design: VoiceDesignController;
  errorRuntimeContext: ErrorRuntimeContext;
};

export default function VoiceDesignPage({ design, errorRuntimeContext }: Props) {
  return (
    <section className="legacyPanel">
      <form className="form" onSubmit={design.onSubmit}>
        <div className="row">
          <label>
            音色名称
            <input
              value={design.designName}
              onChange={(e) => design.onNameChange(e.target.value)}
              placeholder="例如：voice_design_demo"
            />
          </label>
          <label>
            语言
            <input
              value={design.designLanguage}
              onChange={(e) => design.onLanguageChange(e.target.value)}
              placeholder="例如：zh / en"
            />
          </label>
        </div>

        <label>
          音色描述
          <textarea
            rows={4}
            value={design.designPrompt}
            onChange={(e) => design.onPromptChange(e.target.value)}
            placeholder="描述音色的年龄、语气、场景和说话风格"
          />
        </label>

        <label>
          试听文本
          <textarea
            rows={3}
            value={design.designPreviewText}
            onChange={(e) => design.onPreviewTextChange(e.target.value)}
            placeholder="输入一段用于试听的示例文本"
          />
        </label>

        <div className="inlineActions">
          <button type="submit" disabled={design.designBusy}>
            {design.designBusy ? "创建中..." : "创建设计音色"}
          </button>
          <button
            type="button"
            className="ghost"
            onClick={() => void design.onRefresh()}
            disabled={design.designListBusy || design.designBusy}
          >
            {design.designListBusy ? "加载中..." : "刷新列表"}
          </button>
        </div>

        <ErrorNotice
          message={design.designError}
          scope="voice_design"
          context={{
            ...errorRuntimeContext,
            preferred_name: design.designName,
            language: design.designLanguage
          }}
        />
        {design.designInfo ? <p className="ok">{design.designInfo}</p> : null}

        {design.designPreviewAudio ? (
          <div className="audioWrap">
            <p>试听音频</p>
            <audio controls src={design.designPreviewAudio} />
          </div>
        ) : null}

        <VoiceCatalog
          title="设计音色列表"
          voices={design.designVoices}
          busy={design.designBusy}
          listBusy={design.designListBusy}
          emptyText="暂无音色。"
          onDeleteVoice={design.onDeleteVoice}
        />
      </form>
    </section>
  );
}
