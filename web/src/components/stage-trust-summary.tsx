import type { ReactNode } from "react";
import type { StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { buildStageTrustSummary } from "../lib/stage-trust-summary";
import { Badge } from "./badge";
import { SourceStageList } from "./source-stage-list";

function BulletList({ items }: { readonly items: readonly string[] }) {
  return (
    <ul className="space-y-1 text-sm text-slate-600">
      {items.map((item) => (
        <li className="flex gap-2" key={item}>
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function DetailBlock({
  children,
  title,
}: {
  readonly children: ReactNode;
  readonly title: string;
}) {
  return (
    <div className="border-l-2 border-teal-200 pl-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
      <div className="mt-2">{children}</div>
    </div>
  );
}

export function StageTrustSummary({ stage }: { readonly stage: StageCard }) {
  const { t } = useI18n();
  const summary = buildStageTrustSummary(stage);
  const sourceStageCount = Object.keys(summary.sourceStageIds).length;
  const hasTrustSignal =
    summary.requiresHumanReview ||
    summary.planOnly ||
    summary.noExperimentResults ||
    summary.reviewItems.length > 0 ||
    summary.warnings.length > 0 ||
    sourceStageCount > 0;

  if (!hasTrustSignal) {
    return null;
  }

  return (
    <div className="mt-3 border-l-4 border-teal-400 bg-teal-50/60 px-4 py-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">{t("stageTrustSummaryTitle")}</h3>
          <p className="mt-1 text-xs text-slate-600">{t("stageTrustSummaryDescription")}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {summary.requiresHumanReview ? <Badge tone="amber">{t("humanReviewRequired")}</Badge> : null}
          {summary.planOnly ? <Badge tone="blue">{t("planOnlyNotice")}</Badge> : null}
          {summary.noExperimentResults ? <Badge tone="gray">{t("experimentResultsNotAvailable")}</Badge> : null}
        </div>
      </div>

      {summary.reviewItems.length > 0 || summary.warnings.length > 0 || sourceStageCount > 0 ? (
        <div className="mt-3 grid gap-3 lg:grid-cols-3">
          {summary.reviewItems.length > 0 ? (
            <DetailBlock title={t("humanReviewRequired")}>
              <BulletList items={summary.reviewItems} />
            </DetailBlock>
          ) : null}
          {summary.warnings.length > 0 ? (
            <DetailBlock title={t("warnings")}>
              <BulletList items={summary.warnings} />
            </DetailBlock>
          ) : null}
          {sourceStageCount > 0 ? (
            <DetailBlock title={t("sourceStages")}>
              <SourceStageList sourceStageIds={summary.sourceStageIds} />
            </DetailBlock>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
