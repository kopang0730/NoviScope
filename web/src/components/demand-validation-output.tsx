import type { ReactNode } from "react";
import type { StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import { demandValidatorAgentId } from "../lib/stages";
import { Badge } from "./badge";
import { DemandSourceReviewForm } from "./demand-source-review-form";

type DemandValidationView = {
  readonly assessment: string;
  readonly confidence: string;
  readonly evidenceForDemand: readonly string[];
  readonly goNoGoRecommendation: string;
  readonly missingEvidence: readonly string[];
  readonly nextStep: string;
  readonly realWorldScenario: string;
  readonly risks: readonly string[];
  readonly sourcePolicy: string;
  readonly suggestedHumanChecklist: readonly string[];
  readonly targetUserOrCustomer: string;
};

function readString(payload: Readonly<Record<string, unknown>>, key: string) {
  const value = payload[key];
  return typeof value === "string" ? value : "";
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function readStringArray(payload: Readonly<Record<string, unknown>>, key: string) {
  const value = payload[key];
  return Array.isArray(value) ? value.filter(isString) : [];
}

function buildDemandValidationView(stage: StageCard): DemandValidationView | null {
  if (stage.agent_id !== demandValidatorAgentId || stage.status !== "complete") {
    return null;
  }

  return {
    assessment: readString(stage.output_payload, "demand_assessment"),
    confidence: stage.confidence,
    evidenceForDemand: readStringArray(stage.output_payload, "evidence_for_demand"),
    goNoGoRecommendation: readString(stage.output_payload, "go_or_no_go_recommendation"),
    missingEvidence: readStringArray(stage.output_payload, "missing_evidence"),
    nextStep: readString(stage.output_payload, "next_step"),
    realWorldScenario: readString(stage.output_payload, "real_world_scenario"),
    risks: readStringArray(stage.output_payload, "risks"),
    sourcePolicy: readString(stage.evidence_payload, "source_policy"),
    suggestedHumanChecklist: readStringArray(stage.output_payload, "suggested_human_checklist"),
    targetUserOrCustomer: readString(stage.output_payload, "target_user_or_customer"),
  };
}

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
            {labelFromEnum(demandValidation.assessment || "unclear")}
          </p>
        </DetailBlock>
        <DetailBlock title={t("stageConfidence")}>
          <p className="text-base font-semibold text-slate-900">
            {labelFromEnum(demandValidation.confidence)}
          </p>
        </DetailBlock>
        <DetailBlock title={t("goNoGoRecommendation")}>
          <p className="text-base font-semibold text-slate-900">
            {labelFromEnum(demandValidation.goNoGoRecommendation || "needs_more_evidence")}
          </p>
        </DetailBlock>
      </div>

      <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="amber">{t("sourcePolicy")}</Badge>
          <Badge tone="gray">{labelFromEnum(demandValidation.sourcePolicy || "unknown")}</Badge>
        </div>
        <p className="mt-2 text-sm text-amber-900">
          {demandValidation.sourcePolicy === "model_only_no_external_source_verification"
            ? t("sourcePolicyModelOnlyDescription")
            : t("sourcePolicyReviewDescription")}
        </p>
        {demandValidation.sourcePolicy === "model_only_no_external_source_verification" ? (
          <div className="mt-3 rounded-md border border-amber-200 bg-white/70 px-3 py-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">
              {t("confidenceGuardrail")}
            </p>
            <p className="mt-1 text-sm text-amber-900">{t("confidenceGuardrailModelOnly")}</p>
          </div>
        ) : null}
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
