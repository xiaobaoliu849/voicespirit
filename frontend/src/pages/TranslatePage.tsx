import ErrorNotice from "../components/ErrorNotice";
import { PROVIDERS } from "../appConfig";
import type { UseTranslateResult } from "../hooks/useTranslate";
import { useI18n } from "../i18n";
import type { ErrorRuntimeContext } from "../types/ui";
import { Clipboard, Copy, Trash2, Volume2 } from "lucide-react";

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
              <strong>{t("原文", "Source")}</strong>
              <div className="vsTranslatePaneActions">
                <button
                  type="button"
                  className="vsTranslateToolBtn"
                  onClick={() => void translate.onPasteInput()}
                  aria-label={t("粘贴原文", "Paste source text")}
                >
                  <Clipboard size={15} />
                  <span>{t("粘贴", "Paste")}</span>
                </button>
                <button
                  type="button"
                  className={`vsTranslateToolBtn ${translate.speakingTarget === "source" ? "active" : ""}`}
                  onClick={translate.onSpeakSource}
                  disabled={!sourceCount}
                  aria-label={t("朗读原文", "Play source text")}
                >
                  <Volume2 size={15} />
                  <span>{translate.speakingTarget === "source" ? t("停止", "Stop") : t("朗读", "Play")}</span>
                </button>
                <button
                  type="button"
                  className="vsTranslateToolBtn"
                  onClick={() => void translate.onCopySource()}
                  disabled={!sourceCount}
                  aria-label={t("复制原文", "Copy source text")}
                >
                  <Copy size={15} />
                  <span>{t("复制", "Copy")}</span>
                </button>
                <button
                  type="button"
                  className="vsTranslateToolBtn danger"
                  onClick={translate.onClearSource}
                  disabled={!sourceCount}
                  aria-label={t("清空原文", "Clear source text")}
                >
                  <Trash2 size={15} />
                  <span>{t("清空", "Clear")}</span>
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
            </div>
          </section>

          <section className="vsTranslatePane result">
            <div className="vsTranslatePaneHead">
              <strong>{t("译文", "Translation")}</strong>
              <div className="vsTranslatePaneActions">
                <button
                  type="button"
                  className={`vsTranslateToolBtn ${translate.speakingTarget === "result" ? "active" : ""}`}
                  onClick={translate.onSpeakResult}
                  disabled={!resultCount}
                  aria-label={t("朗读译文", "Play translated text")}
                >
                  <Volume2 size={15} />
                  <span>{translate.speakingTarget === "result" ? t("停止", "Stop") : t("朗读", "Play")}</span>
                </button>
                <button
                  type="button"
                  className="vsTranslateToolBtn"
                  onClick={() => void translate.onCopyResult()}
                  disabled={!resultCount}
                  aria-label={t("复制译文", "Copy translated text")}
                >
                  <Copy size={15} />
                  <span>{t("复制", "Copy")}</span>
                </button>
                <button
                  type="button"
                  className="vsTranslateToolBtn danger"
                  onClick={translate.onClearResult}
                  disabled={!resultCount}
                  aria-label={t("清空译文", "Clear translated text")}
                >
                  <Trash2 size={15} />
                  <span>{t("清空", "Clear")}</span>
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
