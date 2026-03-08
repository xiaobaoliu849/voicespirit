import { FormEvent, useState } from "react";
import { translateText } from "../api";
import type { FormatErrorMessage } from "../utils/errorFormatting";

type Options = {
  formatErrorMessage: FormatErrorMessage;
};

export default function useTranslate({ formatErrorMessage }: Options) {
  const [translateProvider, setTranslateProvider] = useState("DashScope");
  const [translateModel, setTranslateModel] = useState("");
  const [sourceLanguage, setSourceLanguage] = useState("auto");
  const [targetLanguage, setTargetLanguage] = useState("英文");
  const [translateInput, setTranslateInput] = useState("这是一个翻译接口测试。");
  const [translateResult, setTranslateResult] = useState("");
  const [translateBusy, setTranslateBusy] = useState(false);
  const [translateError, setTranslateError] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const sourceText = translateInput.trim();
    if (!sourceText) {
      setTranslateError("请输入要翻译的内容。");
      return;
    }

    setTranslateError("");
    setTranslateBusy(true);
    try {
      const result = await translateText({
        text: sourceText,
        source_language: sourceLanguage.trim() || "auto",
        target_language: targetLanguage.trim(),
        provider: translateProvider,
        model: translateModel.trim() || undefined
      });
      setTranslateResult(result.translated_text);
    } catch (err) {
      setTranslateError(formatErrorMessage(err, "翻译请求失败。"));
    } finally {
      setTranslateBusy(false);
    }
  }

  return {
    translateProvider,
    translateModel,
    sourceLanguage,
    targetLanguage,
    translateInput,
    translateResult,
    translateBusy,
    translateError,
    onSubmit,
    onProviderChange: setTranslateProvider,
    onModelChange: setTranslateModel,
    onSourceLanguageChange: setSourceLanguage,
    onTargetLanguageChange: setTargetLanguage,
    onInputChange: setTranslateInput
  };
}

export type UseTranslateResult = ReturnType<typeof useTranslate>;
