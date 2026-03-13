import ErrorNotice from "../components/ErrorNotice";
import { PROVIDERS } from "../appConfig";
import type { UseTranslateResult } from "../hooks/useTranslate";
import { useI18n } from "../i18n";
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
  const { t } = useI18n();
  const sourceCount = countChars(translate.translateInput);
  const resultCount = countChars(translate.translateResult);

  return (
    <section className="vsTranslatePage">
      <form className="vsTranslateShell" onSubmit={translate.onSubmit}>
        <div className="vsTranslateTopbar">
          <div className="vsTranslateToolbar">
            <label className="vsTranslateField">
              <span>{t("供应商", "Provider")}</span>
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

            <label className="vsTranslateField" style={{ minWidth: 200 }}>
              <span>{t("模型", "Model")}</span>
              <input
                value={translate.translateModel}
                onChange={(e) => translate.onModelChange(e.target.value)}
                placeholder={t("默认模型", "Default model")}
              />
            </label>

            <label className="vsTranslateField">
              <span>{t("源语言", "Source")}</span>
              <input
                value={translate.sourceLanguage}
                onChange={(e) => translate.onSourceLanguageChange(e.target.value)}
                placeholder={t("自动检测", "Auto Detect")}
              />
            </label>

            <button
              type="button"
              className="vsTranslateSwapBtn"
              onClick={translate.onSwapLanguages}
              aria-label={t("交换语言方向", "Swap languages")}
              title={t("交换语言方向", "Swap languages")}
            >
              ⇄
            </button>

            <label className="vsTranslateField">
              <span>{t("目标语言", "Target")}</span>
              <input
                value={translate.targetLanguage}
                onChange={(e) => translate.onTargetLanguageChange(e.target.value)}
                placeholder={t("目标语言", "Target language")}
              />
            </label>
          </div>

          <div className="vsTranslateTopbarActions">
            <button
              type="submit"
              className="vsTranslateSubmitBtn"
              disabled={translate.translateBusy}
            >
              {translate.translateBusy ? t("翻译中...", "Translating...") : t("开始翻译", "Translate")}
            </button>
          </div>
        </div>

        <div className="vsTranslateEditorGrid">
          <section className="vsTranslatePane source">
            <div className="vsTranslatePaneHead">
              <div>
                <strong>{t("原文", "Source")}</strong>
              </div>
              <div className="vsTranslatePaneActions">
                <button
                  type="button"
                  className="ghost"
                  onClick={() => void translate.onPasteInput()}
                >
                  {t("粘贴", "Paste")}
                </button>
                <button
                  type="button"
                  className="ghost"
                  onClick={() => void translate.onCopySource()}
                  disabled={!sourceCount}
                >
                  {t("复制", "Copy")}
                </button>
              </div>
            </div>

            <textarea
              className="vsTranslateTextarea"
              value={translate.translateInput}
              onChange={(e) => translate.onInputChange(e.target.value)}
              placeholder={t("在这里输入要翻译的内容...", "Enter the text to translate here...")}
            />

            <div className="vsTranslatePaneFooter">
              <span className="muted">{t(`${sourceCount} 字`, `${sourceCount} chars`)}</span>
              <div className="inlineActions">
                <button
                  type="button"
                  className="ghost"
                  onClick={translate.onClearAll}
                  disabled={!sourceCount && !resultCount}
                >
                  {t("清空", "Clear")}
                </button>
              </div>
            </div>
          </section>

          <section className="vsTranslatePane result">
            <div className="vsTranslatePaneHead">
              <div>
                <strong>{t("译文", "Translation")}</strong>
              </div>
              <div className="vsTranslatePaneActions">
                <button
                  type="button"
                  className="ghost"
                  onClick={() => void translate.onCopyResult()}
                  disabled={!resultCount}
                >
                  {t("复制", "Copy")}
                </button>
              </div>
            </div>

            {resultCount ? (
              <pre className="vsTranslateResult">{translate.translateResult}</pre>
            ) : (
              <div className="vsTranslatePlaceholder">
                <p>{t("译文将显示在这里", "Translation will appear here")}</p>
              </div>
            )}

            <div className="vsTranslatePaneFooter">
              <span className="muted">{t(`${resultCount} 字`, `${resultCount} chars`)}</span>
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
