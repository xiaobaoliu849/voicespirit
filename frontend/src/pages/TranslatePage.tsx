import ErrorNotice from "../components/ErrorNotice";
import { PROVIDERS } from "../appConfig";
import type { UseTranslateResult } from "../hooks/useTranslate";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  translate: UseTranslateResult;
  errorRuntimeContext: ErrorRuntimeContext;
};

function countChars(value: string) {
  return value.trim().length;
}

export default function TranslatePage({
  translate,
  errorRuntimeContext
}: Props) {
  const sourceCount = countChars(translate.translateInput);
  const resultCount = countChars(translate.translateResult);

  return (
    <section className="vsTranslatePage">
      <form className="vsTranslateShell" onSubmit={translate.onSubmit}>
        <div className="vsTranslateTopbar">
          <div className="vsTranslateToolbar">
            <label className="vsTranslateField">
              <span>供应商</span>
              <select
                value={translate.translateProvider}
                onChange={(e) => translate.onProviderChange(e.target.value)}
              >
                {PROVIDERS.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>

            <label className="vsTranslateField" style={{ minWidth: 320 }}>
              <span>模型</span>
              <input
                value={translate.translateModel}
                onChange={(e) => translate.onModelChange(e.target.value)}
                placeholder="留空则使用默认模型"
              />
            </label>

            <label className="vsTranslateField">
              <span>源语言</span>
              <input
                value={translate.sourceLanguage}
                onChange={(e) => translate.onSourceLanguageChange(e.target.value)}
                placeholder="Auto Detect / 中文 / 日文"
              />
            </label>

            <button
              type="button"
              className="vsTranslateSwapBtn"
              onClick={translate.onSwapLanguages}
              aria-label="交换语言方向"
              title="交换语言方向"
            >
              ⇄
            </button>

            <label className="vsTranslateField">
              <span>目标语言</span>
              <input
                value={translate.targetLanguage}
                onChange={(e) => translate.onTargetLanguageChange(e.target.value)}
                placeholder="英文 / 中文 / 法文"
              />
            </label>
          </div>

          <div className="vsTranslateTopbarActions">
            <div className="vsTranslateConfigHint">
              <span>当前任务</span>
              <strong>{translate.translateBusy ? "翻译中..." : "文本翻译工作台"}</strong>
            </div>
            <button
              type="submit"
              className="vsTranslateSubmitBtn"
              disabled={translate.translateBusy}
            >
              {translate.translateBusy ? "翻译中..." : "开始翻译"}
            </button>
          </div>
        </div>

        <div className="vsTranslateEditorGrid">
          <section className="vsTranslatePane source">
            <div className="vsTranslatePaneHead">
              <div>
                <strong>原文输入区</strong>
                <div>支持直接粘贴段落、术语或说明文本</div>
              </div>
              <div className="vsTranslatePaneActions">
                <button
                  type="button"
                  className="ghost"
                  onClick={() => void translate.onPasteInput()}
                >
                  粘贴
                </button>
                <button
                  type="button"
                  className="ghost"
                  onClick={() => void translate.onCopySource()}
                  disabled={!sourceCount}
                >
                  复制原文
                </button>
              </div>
            </div>

            <textarea
              className="vsTranslateTextarea"
              value={translate.translateInput}
              onChange={(e) => translate.onInputChange(e.target.value)}
              placeholder="在这里输入要翻译的内容。适合邮件、文档、字幕片段和术语列表。"
            />

            <div className="vsTranslatePaneFooter">
              <span className="muted">原文 {sourceCount} 字</span>
              <div className="inlineActions">
                <button
                  type="button"
                  className="ghost"
                  onClick={translate.onClearAll}
                  disabled={!sourceCount && !resultCount}
                >
                  清空
                </button>
              </div>
            </div>
          </section>

          <section className="vsTranslatePane result">
            <div className="vsTranslatePaneHead">
              <div>
                <strong>翻译结果</strong>
                <div>结果会保留排版并支持直接复制复用</div>
              </div>
              <div className="vsTranslatePaneActions">
                <button
                  type="button"
                  className="ghost"
                  onClick={() => void translate.onCopyResult()}
                  disabled={!resultCount}
                >
                  复制译文
                </button>
              </div>
            </div>

            {resultCount ? (
              <pre className="vsTranslateResult">{translate.translateResult}</pre>
            ) : (
              <div className="vsTranslatePlaceholder">
                <strong>译文会显示在这里</strong>
                <p>输入原文后点击“开始翻译”，右侧会展示完整结果，方便直接复制或继续润色。</p>
              </div>
            )}

            <div className="vsTranslatePaneFooter">
              <span className="muted">译文 {resultCount} 字</span>
              <span className="muted">{translate.translateInfo || "适合桌面端双栏阅读和对照。"}</span>
            </div>
          </section>
        </div>

        <ErrorNotice
          message={translate.translateError}
          scope="translate"
          context={{
            ...errorRuntimeContext,
            provider: translate.translateProvider,
            model: translate.translateModel,
            source_language: translate.sourceLanguage,
            target_language: translate.targetLanguage
          }}
        />
      </form>
    </section>
  );
}
