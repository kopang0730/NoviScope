import type { Language } from "../i18n/i18n-context";
import { useI18n } from "../i18n/i18n-context";

const languages: Language[] = ["zh", "en"];

export function LanguageToggle() {
  const { language, setLanguage, t } = useI18n();

  return (
    <div aria-label={t("languageLabel")} className="inline-flex rounded-lg border border-slate-300 bg-white p-1">
      {languages.map((item) => {
        const isActive = item === language;
        return (
          <button
            aria-pressed={isActive}
            className={[
              "h-11 min-w-16 rounded-md px-3 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500",
              isActive ? "bg-teal-600 text-white" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
            ].join(" ")}
            key={item}
            onClick={() => setLanguage(item)}
            type="button"
          >
            {item === "zh" ? t("languageChinese") : t("languageEnglish")}
          </button>
        );
      })}
    </div>
  );
}
