import type { ReactNode } from "react";
import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { translations, type Language, type TranslationKey } from "./translations";

export type { Language, TranslationKey } from "./translations";

const languageStorageKey = "noviscope-language";

type I18nContextValue = {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: TranslationKey) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

function readInitialLanguage(): Language {
  if (typeof window === "undefined") {
    return "zh";
  }

  try {
    return window.localStorage.getItem(languageStorageKey) === "en" ? "en" : "zh";
  } catch {
    return "zh";
  }
}

function persistLanguagePreference(language: Language) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(languageStorageKey, language);
  } catch {
    return;
  }
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(readInitialLanguage);

  const setLanguage = (nextLanguage: Language) => {
    setLanguageState(nextLanguage);
  };

  useEffect(() => {
    persistLanguagePreference(language);
    document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  }, [language]);

  const value = useMemo<I18nContextValue>(
    () => ({
      language,
      setLanguage,
      t: (key) => translations[language][key],
    }),
    [language],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used within an I18nProvider");
  }
  return context;
}
