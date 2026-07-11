import type { ReactNode } from "react";
import type { StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { buildDemandValidationView } from "../lib/demand-validation-view";
import { localizedResearchLabel } from "../lib/research-labels";
import { Badge } from "./badge";
import { DemandSourceReviewForm } from "./demand-source-review-form";

function BulletList({ emptyLabel, items }: { readonly emptyLabel: string; readonly items: readonly string[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">{emptyLabel}</p>;
  }

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
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
      <div className="mt-2">{children}</div>
    </div>
  );
}

export function DemandValidationOutput({
  onStageChange,
  stage,
}: {
  readonly onStageChange?: (stage: StageCard) => void;
  readonly stage: StageCard;
}) {
  const { t } = useI18n();
  const demandValidation = buildDemandValidationView(stage);

  if (!demandValidation) {
    return null;
  }

  return (
    <>
      <div className="mt-5 grid gap-3 lg:grid-cols-3">
        <DetailBlock title={t("demandAssessment")}>
          <p className="text-base font-semibold text-slate-900">
            {localizedResearchLabel(demandValidation.assessment || "unclear", t)}
          </p>
        </DetailBlock>
        <DetailBlock title={t("stageConfidence")}>
          <p className="text-base font-semibold text-slate-900">
            {localizedResearchLabel(demandValidation.confidence, t)}
          </p>
        </DetailBlock>
        <DetailBlock title={t("goNoGoRecommendation")}>
          <p className="text-base font-semibold text-slate-900">
            {localizedResearchLabel(
              demandValidation.goNoGoRecommendation || "needs_more_evidence",
              t,
            )}
          </p>
        </DetailBlock>
      </div>

      <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="amber">{t("sourcePolicy")}</Badge>
          <Badge tone="gray">
            {localizedResearchLabel(demandValidation.sourcePolicy || "unknown", t)}
          </Badge>
        </div>
        <p className="mt-2 text-sm text-amber-900">
          {demandValidation.sourcePolicy === "model_only_no_external_source_verification"
            ? t("sourcePolicyModelOnlyDescription")
            : t("sourcePolicyReviewDescription")}
        </p>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <DetailBlock title={t("realWorldScenario")}>
          <p className="text-sm text-slate-600">
            {demandValidation.realWorldScenario || t("notAvailable")}
          </p>
        </DetailBlock>
        <DetailBlock title={t("targetUserOrCustomer")}>
          <p className="text-sm text-slate-600">
            {demandValidation.targetUserOrCustomer || t("notAvailable")}
          </p>
        </DetailBlock>
        <DetailBlock title={t("evidenceForDemand")}>
          <BulletList emptyLabel={t("notAvailable")} items={demandValidation.evidenceForDemand} />
        </DetailBlock>
        <DetailBlock title={t("missingEvidence")}>
          <BulletList emptyLabel={t("notAvailable")} items={demandValidation.missingEvidence} />
        </DetailBlock>
        <DetailBlock title={t("risks")}>
          <BulletList emptyLabel={t("notAvailable")} items={demandValidation.risks} />
        </DetailBlock>
        <DetailBlock title={t("humanChecklist")}>
          <BulletList emptyLabel={t("notAvailable")} items={demandValidation.suggestedHumanChecklist} />
        </DetailBlock>
      </div>
      <div className="mt-3 rounded-lg border border-teal-200 bg-teal-50 p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">{t("nextStep")}</p>
        <p className="mt-2 text-sm text-teal-900">{demandValidation.nextStep || t("notAvailable")}</p>
      </div>
      <DemandSourceReviewForm onStageChange={onStageChange} stage={stage} />
    </>
  );
}
