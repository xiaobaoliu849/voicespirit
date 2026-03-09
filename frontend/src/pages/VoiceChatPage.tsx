import ErrorNotice from "../components/ErrorNotice";
import type { UseVoiceChatResult } from "../hooks/useVoiceChat";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  voiceChat: UseVoiceChatResult;
  errorRuntimeContext: ErrorRuntimeContext;
};

export default function VoiceChatPage({ voiceChat, errorRuntimeContext }: Props) {
  return (
    <section className="vsTtsWorkspace">
      <div className="vsTtsLayout">
        <div className="vsTtsPrimary">
          <header className="vsTtsPrimaryHeader">
            <div>
              <h2 className="vsTtsPrimaryTitle">语音聊天工作台</h2>
              <p className="vsFieldHint">
                现在直接走后端代理的 Google native realtime，会持续收音、实时出字并即时回音。
              </p>
            </div>
            <div className="vsTtsPrimaryStats">
              <span>{voiceChat.voiceChatConnected ? "实时会话中" : "待机"}</span>
            </div>
          </header>

          <div className="vsCardSection" style={{ display: "grid", gap: 16 }}>
            <div className="vsField">
              <label className="vsFieldLabel">当前模型供应商</label>
              <select
                className="vsSelect"
                value={voiceChat.voiceChatProvider}
                onChange={(e) => voiceChat.onProviderChange(e.target.value)}
                disabled={voiceChat.voiceChatBusy}
              >
                {voiceChat.voiceChatProviderOptions.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>

            <div className="vsField">
              <label className="vsFieldLabel">当前模型</label>
              <input
                className="vsInput"
                list="voice-chat-model-options"
                value={voiceChat.voiceChatModel}
                onChange={(e) => voiceChat.onModelChange(e.target.value)}
                disabled={voiceChat.voiceChatBusy}
              />
              <datalist id="voice-chat-model-options">
                {voiceChat.voiceChatModelOptions.map((item) => (
                  <option key={item} value={item} />
                ))}
              </datalist>
            </div>

            <div className="vsField">
              <label className="vsFieldLabel">Google 实时音色</label>
              <select
                className="vsSelect"
                value={voiceChat.voiceChatVoice}
                onChange={(e) => voiceChat.onVoiceChange(e.target.value)}
                disabled={voiceChat.voiceChatBusy || voiceChat.voiceChatConnected}
              >
                {voiceChat.voiceChatVoiceOptions.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>

            <div
              style={{
                display: "grid",
                placeItems: "center",
                gap: 12,
                minHeight: 220,
                borderRadius: 24,
                border: "1px solid var(--border-color)",
                background: "var(--surface-color)",
              }}
            >
              <button
                type="button"
                className={voiceChat.voiceChatRecording ? "vsBtnPrimary" : "vsBtnSecondary"}
                onClick={() => void voiceChat.onToggleRecording()}
                disabled={!voiceChat.voiceChatSupported || voiceChat.voiceChatBusy}
                style={{
                  width: 160,
                  height: 160,
                  borderRadius: "50%",
                  fontSize: 20,
                }}
              >
                {voiceChat.voiceChatRecording ? "结束会话" : "开始实时聊天"}
              </button>
              <div className="vsEmptyDesc">{voiceChat.voiceChatStatus}</div>
            </div>

            <ErrorNotice
              message={voiceChat.voiceChatError}
              scope="voice-chat"
              context={{
                ...errorRuntimeContext,
                provider: voiceChat.voiceChatProvider,
                model: voiceChat.voiceChatModel,
                voice: voiceChat.voiceChatVoice,
              }}
            />
          </div>
        </div>

        <div className="vsTtsSecondary">
          <div className="vsCardSection">
            <h3 className="vsCardSubTitle">实时会话说明</h3>
            <p className="vsFieldHint">
              当前先恢复 Google native realtime。
              连接后会持续监听麦克风，用户讲话会实时转成文字，模型语音和文字会同步回传。
            </p>
          </div>

          <div className="vsCardSection border-top">
            <h3 className="vsCardSubTitle">本轮语音内容</h3>
            <div className="vsField">
              <label className="vsFieldLabel">识别结果</label>
              <textarea className="vsTextarea" rows={4} value={voiceChat.voiceChatTranscript} readOnly />
            </div>
            <div className="vsField" style={{ marginTop: 12 }}>
              <label className="vsFieldLabel">助手回复</label>
              <textarea className="vsTextarea" rows={5} value={voiceChat.voiceChatReply} readOnly />
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 12 }}>
              <button type="button" className="vsBtnSecondary" onClick={voiceChat.onResetSession}>
                清空本轮
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
