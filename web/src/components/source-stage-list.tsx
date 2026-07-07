import { useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";

export function SourceStageList({ sourceStageIds }: { readonly sourceStageIds: Readonly<Record<string, string>> }) {
  const { t } = useI18n();
  const entries = Object.entries(sourceStageIds);

  if (entries.length === 0) {
    return <p className="text-sm text-slate-500">{t("notAvailable")}</p>;
  }

  return (
    <ul className="space-y-1 text-sm text-slate-600">
      {entries.map(([key, value]) => {
        const sourceStageId = value.trim();

        return (
          <li className="flex flex-wrap gap-x-2 gap-y-1" key={key}>
            <span className="font-medium text-slate-700">{labelFromEnum(key)}:</span>
            <span className={sourceStageId ? "break-all" : "text-slate-500"}>
              {sourceStageId || t("notAvailable")}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
