import ErrorNotice from "../components/ErrorNotice";
import { PROVIDERS } from "../appConfig";
import type { UseTranslateResult } from "../hooks/useTranslate";
import type { ErrorRuntimeContext } from "../types/ui";

type Props = {
  translate: UseTranslateResult;
  errorRuntimeContext: ErrorRuntimeContext;
};

export default function TranslatePage({
  translate,
  errorRuntimeContext
}: Props) {
  return (
    <section className="legacyPanel">
      <form className="form" onSubmit={translate.onSubmit}>
        <div className="row">
          <label>
            供应商
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
          <label>
            模型（可选）
            <input
              value={translate.translateModel}
              onChange={(e) => translate.onModelChange(e.target.value)}
              placeholder="留空则使用默认模型"
            />
          </label>
        </div>

        <div className="row3">
          <label>
            源语言
            <input
              value={translate.sourceLanguage}
              onChange={(e) => translate.onSourceLanguageChange(e.target.value)}
              placeholder="例如：auto / 中文 / 日文"
            />
          </label>
          <label>
            目标语言
            <input
              value={translate.targetLanguage}
              onChange={(e) => translate.onTargetLanguageChange(e.target.value)}
              placeholder="例如：英文 / 中文 / 法文"
            />
          </label>
        </div>

        <label>
          待翻译文本
          <textarea
            rows={5}
            value={translate.translateInput}
            onChange={(e) => translate.onInputChange(e.target.value)}
            placeholder="输入需要翻译的段落、句子或术语"
          />
        </label>
        <button type="submit" disabled={translate.translateBusy}>
          {translate.translateBusy ? "翻译中..." : "开始翻译"}
        </button>
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
        {translate.translateResult ? (
          <div className="resultBox">
            <p>翻译结果</p>
            <pre>{translate.translateResult}</pre>
          </div>
        ) : null}
      </form>
    </section>
  );
}
