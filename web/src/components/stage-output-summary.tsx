import type { ReactNode } from "react";
import type { StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import {
  demandValidatorAgentId,
  experimentPlannerAgentId,
  getStageRunAvailability,
  ideaGeneratorAgentId,
} from "../lib/stages";
import { Badge } from "./badge";
import { Card, CardHeading } from "./card";
import { ExperimentPlannerOutput } from "./experiment-planner-output";
import { GapHypothesisOutput } from "./gap-hypothesis-output";
import { LiteratureScoutOutput } from "./literature-scout-output";

type DemandValidationView = {
  readonly assessment: string;
  readonly confidence: string;
  readonly evidenceForDemand: readonly string[];
  readonly goNoGoRecommendation: string;
  readonly missingEvidence: readonly string[];
  readonly nextStep: string;
  readonly realWorldScenario: string;
  readonly risks: readonly string[];
  readonly suggestedHumanChecklist: readonly string[];
  readonly targetUserOrCustomer: string;
};

function readString(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return typeof value === "string" ? value : "";
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function readStringArray(payload: Record<string, unknown>, key: string) {
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

export function StageRunSummary({ stage }: { readonly stage: StageCard }) {
  const { t } = useI18n();
  const availability = getStageRunAvailability(stage);
  const providerName = readString(stage.evidence_payload, "provider_name");

  return (
    <div className="mt-3 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={stage.confidence === "unknown" ? "gray" : "teal"}>
          {t("stageConfidence")}: {labelFromEnum(stage.confidence)}
        </Badge>
        {providerName ? <Badge tone="blue">{providerName}</Badge> : null}
      </div>
      <p className="text-sm text-slate-600">{stage.summary || t("noSummaryYet")}</p>
      <p className="text-xs text-slate-500">
        {availability.canRun ? t("stageRunReady") : t("stageRunUnavailable")}: {availability.reason}
      </p>
    </div>
  );
}

export function StageOutputPanel({
  onStageChange,
  stage,
}: {
  readonly onStageChange?: (stage: StageCard) => void;
  readonly stage: StageCard;
}) {
  const { t } = useI18n();
  const demandValidation = buildDemandValidationView(stage);

  if (stage.agent_id === "literature_scout" && stage.status === "complete") {
    return (
      <Card>
        <CardHeading description={t("literatureScoutDescription")} title={t("literatureScoutResult")} />
        <div className="mt-5">
          <StageRunSummary stage={stage} />
        </div>
        <div className="mt-5">
          <LiteratureScoutOutput stage={stage} />
        </div>
      </Card>
    );
  }

  if (stage.agent_id === ideaGeneratorAgentId && stage.status === "complete") {
    return (
      <Card>
        <CardHeading description={t("ideaGeneratorDescription")} title={t("ideaGeneratorResult")} />
        <div className="mt-5">
          <StageRunSummary stage={stage} />
        </div>
        <div className="mt-5">
          <GapHypothesisOutput onStageChange={onStageChange} stage={stage} />
        </div>
      </Card>
    );
  }

  if (stage.agent_id === experimentPlannerAgentId) {
    return (
      <Card>
        <CardHeading description={t("experimentPlannerDescription")} title={t("experimentPlannerResult")} />
        <div className="mt-5">
          <StageRunSummary stage={stage} />
        </div>
        <div className="mt-5">
          <ExperimentPlannerOutput onStageChange={onStageChange} stage={stage} />
        </div>
      </Card>
    );
  }

  if (!demandValidation) {
    return (
      <Card>
        <CardHeading description={getStageRunAvailability(stage).reason} title={t("stageRunState")} />
        <StageRunSummary stage={stage} />
      </Card>
    );
  }

  return (
    <Card>
      <CardHeading description={t("demandValidationDescription")} title={t("demandValidationResult")} />
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
    </Card>
  );
}
