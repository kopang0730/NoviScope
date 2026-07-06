import type { StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import {
  getLocalizedStageRunGateReason,
  type StageRunGate,
} from "../lib/stage-run-gate";
import {
  demandValidatorAgentId,
  experimentPlannerAgentId,
  getStageRunAvailability,
  ideaGeneratorAgentId,
  paperMeetingWriterAgentId,
} from "../lib/stages";
import { Card, CardHeading } from "./card";
import { DemandValidationOutput } from "./demand-validation-output";
import { ExperimentPlannerOutput } from "./experiment-planner-output";
import { GapHypothesisOutput } from "./gap-hypothesis-output";
import { LiteratureScoutOutput } from "./literature-scout-output";
import { PaperMeetingOutput } from "./paper-meeting-output";
import { StageRunSummary } from "./stage-run-summary";

export function StageOutputPanel({
  onStageChange,
  stage,
  stageRunGate,
  workflowStages = [],
}: {
  readonly onStageChange?: (stage: StageCard) => void;
  readonly stage: StageCard;
  readonly stageRunGate?: StageRunGate;
  readonly workflowStages?: readonly StageCard[];
}) {
  const { t } = useI18n();
  const runStateDescription = stageRunGate
    ? getLocalizedStageRunGateReason(stageRunGate, t)
    : getStageRunAvailability(stage).reason;
  const experimentPlannerStage =
    workflowStages.find((candidate) => candidate.agent_id === experimentPlannerAgentId) ?? null;

  if (stage.agent_id === "literature_scout" && stage.status === "complete") {
    return (
      <Card>
        <CardHeading description={t("literatureScoutDescription")} title={t("literatureScoutResult")} />
        <div className="mt-5">
          <StageRunSummary stage={stage} stageRunGate={stageRunGate} />
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
          <StageRunSummary stage={stage} stageRunGate={stageRunGate} />
        </div>
        <div className="mt-5">
          <GapHypothesisOutput
            experimentPlannerStage={experimentPlannerStage}
            onStageChange={onStageChange}
            stage={stage}
          />
        </div>
      </Card>
    );
  }

  if (stage.agent_id === experimentPlannerAgentId) {
    return (
      <Card>
        <CardHeading description={t("experimentPlannerDescription")} title={t("experimentPlannerResult")} />
        <div className="mt-5">
          <StageRunSummary stage={stage} stageRunGate={stageRunGate} />
        </div>
        <div className="mt-5">
          <ExperimentPlannerOutput onStageChange={onStageChange} stage={stage} />
        </div>
      </Card>
    );
  }

  if (stage.agent_id === paperMeetingWriterAgentId) {
    return (
      <Card>
        <CardHeading description={t("paperMeetingDescription")} title={t("paperMeetingResult")} />
        <div className="mt-5">
          <StageRunSummary stage={stage} stageRunGate={stageRunGate} />
        </div>
        <div className="mt-5">
          <PaperMeetingOutput stage={stage} />
        </div>
      </Card>
    );
  }

  if (stage.agent_id !== demandValidatorAgentId || stage.status !== "complete") {
    return (
      <Card>
        <CardHeading description={runStateDescription} title={t("stageRunState")} />
        <StageRunSummary stage={stage} stageRunGate={stageRunGate} />
      </Card>
    );
  }

  return (
    <Card>
      <CardHeading description={t("demandValidationDescription")} title={t("demandValidationResult")} />
      <DemandValidationOutput onStageChange={onStageChange} stage={stage} />
    </Card>
  );
}
