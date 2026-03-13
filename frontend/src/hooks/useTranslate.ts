import { FormEvent, useState } from "react";
import { translateText } from "../api";
import { createInlineTranslator, type UiLanguage } from "../i18n";
import type { FormatErrorMessage } from "../utils/errorFormatting";

type Options = {
  formatErrorMessage: FormatErrorMessage;
  language?: UiLanguage;
};

export default function useTranslate({ formatErrorMessage, language = "zh-CN" }: Options) {
  const t = createInlineTranslator(language);
  const [translateProvider, setTranslateProvider] = useState("DashScope");
  const [translateModel, setTranslateModel] = useState("");
  const [sourceLanguage, setSourceLanguage] = useState("auto");
  const [targetLanguage, setTargetLanguage] = useState(t("英文", "English"));
  const [translateInput, setTranslateInput] = useState(
    t("这是一个翻译接口测试。", "This is a translation API test.")
  );
  const [translateResult, setTranslateResult] = useState("");
  const [translateBusy, setTranslateBusy] = useState(false);
  const [translateError, setTranslateError] = useState("");
  const [translateInfo, setTranslateInfo] = useState("");

  function normalizeLanguage(value: string) {
    return value.trim().toLowerCase();
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const sourceText = translateInput.trim();
    if (!sourceText) {
      setTranslateError(t("请输入要翻译的内容。", "Enter text to translate."));
      return;
    }

    setTranslateError("");
    setTranslateInfo("");
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
      setTranslateError(formatErrorMessage(err, t("翻译请求失败。", "Translation request failed.")));
    } finally {
      setTranslateBusy(false);
    }
  }

  function onInputChange(value: string) {
    setTranslateInput(value);
    if (translateError) {
      setTranslateError("");
    }
  }

  function onSwapLanguages() {
    const previousInput = translateInput;
    const previousResult = translateResult;
    const normalizedSource = normalizeLanguage(sourceLanguage);
    const nextSource = targetLanguage.trim() || t("英文", "English");
    const nextTarget = normalizedSource && normalizedSource !== "auto"
      ? sourceLanguage.trim()
      : t("中文", "Chinese");

    setSourceLanguage(nextSource);
    setTargetLanguage(nextTarget);

    if (previousResult.trim()) {
      setTranslateInput(previousResult);
      setTranslateResult(previousInput);
    }

    setTranslateInfo(t("已交换语言方向。", "Swapped the translation direction."));
  }

  async function copyText(value: string, successMessage: string) {
    const text = value.trim();
    if (!text) {
      setTranslateError(t("当前没有可复制的内容。", "There is nothing to copy yet."));
      return;
    }

    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error("clipboard api unavailable");
      }
      await navigator.clipboard.writeText(text);
      setTranslateError("");
      setTranslateInfo(successMessage);
    } catch (err) {
      setTranslateError(formatErrorMessage(err, t("复制失败。", "Copy failed.")));
    }
  }

  async function onCopySource() {
    await copyText(translateInput, t("已复制原文。", "Copied the source text."));
  }

  async function onCopyResult() {
    await copyText(translateResult, t("已复制译文。", "Copied the translation."));
  }

  async function onPasteInput() {
    try {
      if (!navigator.clipboard?.readText) {
        throw new Error("clipboard api unavailable");
      }
      const text = await navigator.clipboard.readText();
      if (!text.trim()) {
        setTranslateError(t("剪贴板里没有可粘贴的文本。", "The clipboard does not contain any text."));
        return;
      }
      setTranslateInput(text);
      setTranslateError("");
      setTranslateInfo(t("已粘贴到原文输入区。", "Pasted into the source text field."));
    } catch (err) {
      setTranslateError(formatErrorMessage(err, t("粘贴失败。", "Paste failed.")));
    }
  }

  function onClearAll() {
    setTranslateInput("");
    setTranslateResult("");
    setTranslateError("");
    setTranslateInfo(t("已清空翻译工作台。", "Cleared the translation workspace."));
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
    translateInfo,
    onSubmit,
    onProviderChange: setTranslateProvider,
    onModelChange: setTranslateModel,
    onSourceLanguageChange: setSourceLanguage,
    onTargetLanguageChange: setTargetLanguage,
    onInputChange,
    onSwapLanguages,
    onCopySource,
    onCopyResult,
    onPasteInput,
    onClearAll
  };
}

export type UseTranslateResult = ReturnType<typeof useTranslate>;
