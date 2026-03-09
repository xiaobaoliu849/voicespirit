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
  const [translateInfo, setTranslateInfo] = useState("");

  function normalizeLanguage(value: string) {
    return value.trim().toLowerCase();
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const sourceText = translateInput.trim();
    if (!sourceText) {
      setTranslateError("请输入要翻译的内容。");
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
      setTranslateError(formatErrorMessage(err, "翻译请求失败。"));
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
    const nextSource = targetLanguage.trim() || "英文";
    const nextTarget = normalizedSource && normalizedSource !== "auto" ? sourceLanguage.trim() : "中文";

    setSourceLanguage(nextSource);
    setTargetLanguage(nextTarget);

    if (previousResult.trim()) {
      setTranslateInput(previousResult);
      setTranslateResult(previousInput);
    }

    setTranslateInfo("已交换语言方向。");
  }

  async function copyText(value: string, successMessage: string) {
    const text = value.trim();
    if (!text) {
      setTranslateError("当前没有可复制的内容。");
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
      setTranslateError(formatErrorMessage(err, "复制失败。"));
    }
  }

  async function onCopySource() {
    await copyText(translateInput, "已复制原文。");
  }

  async function onCopyResult() {
    await copyText(translateResult, "已复制译文。");
  }

  async function onPasteInput() {
    try {
      if (!navigator.clipboard?.readText) {
        throw new Error("clipboard api unavailable");
      }
      const text = await navigator.clipboard.readText();
      if (!text.trim()) {
        setTranslateError("剪贴板里没有可粘贴的文本。");
        return;
      }
      setTranslateInput(text);
      setTranslateError("");
      setTranslateInfo("已粘贴到原文输入区。");
    } catch (err) {
      setTranslateError(formatErrorMessage(err, "粘贴失败。"));
    }
  }

  function onClearAll() {
    setTranslateInput("");
    setTranslateResult("");
    setTranslateError("");
    setTranslateInfo("已清空翻译工作台。");
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
