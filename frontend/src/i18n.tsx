import { createContext, useContext, useEffect, useMemo, type ReactNode } from "react";

export type UiLanguage = "zh-CN" | "en-US";

type Translator = (zh: string, en: string) => string;

type I18nContextValue = {
  language: UiLanguage;
  isEnglish: boolean;
  t: Translator;
};

const DEFAULT_LANGUAGE: UiLanguage = "zh-CN";

export function normalizeUiLanguage(value: unknown): UiLanguage {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized) {
    return DEFAULT_LANGUAGE;
  }
  if (
    normalized === "en" ||
    normalized === "en-us" ||
    normalized === "english" ||
    normalized.startsWith("en-")
  ) {
    return "en-US";
  }
  return "zh-CN";
}

export function createInlineTranslator(language: UiLanguage): Translator {
  const normalized = normalizeUiLanguage(language);
  return (zh: string, en: string) => (normalized === "en-US" ? en : zh);
}

export function localizeText(language: UiLanguage, zh: string, en: string): string {
  return createInlineTranslator(language)(zh, en);
}

const defaultContextValue: I18nContextValue = {
  language: DEFAULT_LANGUAGE,
  isEnglish: false,
  t: (zh) => zh,
};

const I18nContext = createContext<I18nContextValue>(defaultContextValue);

export function I18nProvider({
  language,
  children,
}: {
  language: UiLanguage;
  children: ReactNode;
}) {
  const normalizedLanguage = normalizeUiLanguage(language);
  const value = useMemo<I18nContextValue>(() => {
    const isEnglish = normalizedLanguage === "en-US";
    return {
      language: normalizedLanguage,
      isEnglish,
      t: createInlineTranslator(normalizedLanguage),
    };
  }, [normalizedLanguage]);

  useEffect(() => {
    if (typeof document === "undefined") {
      return;
    }
    document.documentElement.lang = normalizedLanguage === "en-US" ? "en" : "zh-CN";
  }, [normalizedLanguage]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  return useContext(I18nContext);
}
