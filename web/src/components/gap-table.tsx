import { useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import { confidenceTone, evidenceTone } from "../lib/gap-hypothesis-tones";
import type { GapItem } from "../lib/gap-hypothesis-view";
import { Badge } from "./badge";

function SupportingPaperList({ items }: { readonly items: readonly string[] }) {
  const { t } = useI18n();

  if (items.length === 0) {
    return <p className="text-sm text-slate-500">{t("notAvailable")}</p>;
  }

  return (
    <ul className="space-y-1 text-sm text-slate-600">
      {items.map((item) => (
        <li className="flex gap-2" key={item}>
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-300" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function MobileGapCard({ gap }: { readonly gap: GapItem }) {
  const { t } = useI18n();

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <div>
        <h4 className="font-medium text-slate-900">{gap.gapTitle || t("notAvailable")}</h4>
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t("severity")}
          </p>
          <div className="mt-1.5">
            <Badge tone={confidenceTone(gap.severity)}>{labelFromEnum(gap.severity)}</Badge>
          </div>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t("evidenceType")}
          </p>
          <div className="mt-1.5">
            <Badge tone={evidenceTone(gap.evidenceType)}>
              {labelFromEnum(gap.evidenceType)}
            </Badge>
          </div>
        </div>
      </div>
      <p className="mt-3 text-sm text-slate-600">{gap.description || t("notAvailable")}</p>
      <div className="mt-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t("supportingPapers")}
        </p>
        <div className="mt-2">
          <SupportingPaperList items={gap.supportingPapers} />
        </div>
      </div>
    </section>
  );
}

export function GapTable({ gaps }: { readonly gaps: readonly GapItem[] }) {
  const { t } = useI18n();

  if (gaps.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
        {t("noGapsFound")}
      </p>
    );
  }

  return (
    <>
      <div className="space-y-3 md:hidden">
        {gaps.map((gap) => (
          <MobileGapCard gap={gap} key={`${gap.gapTitle}-${gap.description}`} />
        ))}
      </div>
      <div className="hidden overflow-hidden rounded-lg border border-slate-200 md:block">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">{t("gapTitle")}</th>
              <th className="px-4 py-3">{t("description")}</th>
              <th className="px-4 py-3">{t("severity")}</th>
              <th className="px-4 py-3">{t("evidenceType")}</th>
              <th className="px-4 py-3">{t("supportingPapers")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white align-top">
            {gaps.map((gap) => (
              <tr key={`${gap.gapTitle}-${gap.description}`}>
                <td className="px-4 py-3 font-medium text-slate-900">
                  {gap.gapTitle || t("notAvailable")}
                </td>
                <td className="max-w-xl px-4 py-3 text-slate-600">
                  {gap.description || t("notAvailable")}
                </td>
                <td className="px-4 py-3">
                  <Badge tone={confidenceTone(gap.severity)}>
                    {labelFromEnum(gap.severity)}
                  </Badge>
                </td>
                <td className="px-4 py-3">
                  <Badge tone={evidenceTone(gap.evidenceType)}>
                    {labelFromEnum(gap.evidenceType)}
                  </Badge>
                </td>
                <td className="min-w-56 px-4 py-3">
                  <SupportingPaperList items={gap.supportingPapers} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
