import type { Quest, StageCard } from "../api/types";
import { useI18n, type TranslationKey } from "../i18n/i18n-context";
import { formatDateTime, labelFromEnum } from "../lib/format";
import { stageTone } from "../lib/status-tones";
import { getWorkflowStageReadiness } from "../lib/workflow-readiness";
import { Badge } from "./badge";
import { CanvasStageNode, type CanvasDetail } from "./research-canvas-stage-node";

function readString(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return typeof value === "string" ? value : "";
}

function readStringArray(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function readRecordArray(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return Array.isArray(value)
    ? value.filter(
        (item): item is Record<string, unknown> =>
          typeof item === "object" && item !== null && !Array.isArray(item),
      )
    : [];
}

function findSelectedIdeaTitle(stage: StageCard) {
  const selectedIdeaIds = new Set(readStringArray(stage.output_payload, "selected_idea_ids"));
  const ideas = readRecordArray(stage.output_payload, "ideas");
  const selectedIdea = ideas.find((idea) => selectedIdeaIds.has(readString(idea, "idea_id")));
  return selectedIdea ? readString(selectedIdea, "idea_title") : "";
}

function isHumanGateStage(stage: StageCard) {
  return stage.agent_id === "demand_validator" || stage.agent_id === "idea_generator";
}

function needsHumanReview(stage: StageCard) {
  return stage.status === "complete" && isHumanGateStage(stage) && stage.human_approved === null;
}

function findNextActionStage(stages: readonly StageCard[]) {
  return (
    stages.find((stage) => stage.status === "running")
    ?? stages.find(needsHumanReview)
    ?? stages.find((stage) => getWorkflowStageReadiness(stage, stages).canRun)
    ?? stages.find((stage) => stage.status === "blocked")
    ?? stages.find((stage) => stage.status !== "complete")
    ?? null
  );
}

function phaseKeyForAgent(agentId: string): TranslationKey {
  if (agentId === "demand_validator") {
    return "canvasPhaseDemand";
  }
  if (agentId === "literature_scout") {
    return "canvasPhaseDiscovery";
  }
  if (agentId === "idea_generator") {
    return "canvasPhaseHypothesis";
  }
  if (agentId === "experiment_planner") {
    return "canvasPhaseExperiment";
  }
  if (agentId === "paper_meeting_writer") {
    return "canvasPhaseWriting";
  }
  return "canvasPhaseWorkflow";
}

function buildStageDetails(stage: StageCard, t: ReturnType<typeof useI18n>["t"]): CanvasDetail[] {
  const details: CanvasDetail[] = [];
  const blockingDetail = readString(stage.evidence_payload, "blocking_detail");

  if (stage.agent_id === "demand_validator") {
    const scenario = readString(stage.output_payload, "real_world_scenario");
    if (scenario) {
      details.push({ label: t("canvasEvidence"), value: scenario });
    }
  }

  if (stage.agent_id === "literature_scout") {
    const papers = readRecordArray(stage.output_payload, "papers");
    details.push({ label: t("canvasPapers"), value: String(papers.length) });
    if (papers[0]) {
      details.push({ label: t("canvasEvidence"), value: readString(papers[0], "title") });
    }
  }

  if (stage.agent_id === "idea_generator") {
    const selectedIdeaTitle = findSelectedIdeaTitle(stage);
    const ideas = readRecordArray(stage.output_payload, "ideas");
    details.push({ label: t("canvasIdeaCount"), value: String(ideas.length) });
    if (selectedIdeaTitle) {
      details.push({ label: t("canvasSelectedIdea"), value: selectedIdeaTitle });
    }
  }

  if (stage.agent_id === "experiment_planner") {
    const dataStatus = readString(stage.output_payload, "data_availability_status");
    const scriptPlan = readStringArray(stage.output_payload, "first_runnable_script_plan");
    const missingInputs = readStringArray(stage.evidence_payload, "missing_inputs");
    if (dataStatus) {
      details.push({ label: t("dataAvailabilityStatus"), value: labelFromEnum(dataStatus) });
    }
    if (scriptPlan.length > 0) {
      details.push({ label: t("canvasPlanSteps"), value: String(scriptPlan.length) });
    }
    if (missingInputs.length > 0) {
      details.push({ label: t("canvasInputsNeeded"), value: missingInputs.map(labelFromEnum).join(", ") });
    }
  }

  if (stage.agent_id === "paper_meeting_writer") {
    const artifactCount = stage.evidence_payload.artifact_count;
    const downloadFormat = readString(stage.evidence_payload, "download_format");
    if (typeof artifactCount === "number") {
      details.push({ label: t("canvasArtifacts"), value: String(artifactCount) });
    }
    if (downloadFormat) {
      details.push({ label: t("canvasDownloadFormat"), value: labelFromEnum(downloadFormat) });
    }
  }

  if (blockingDetail) {
    details.push({ label: t("canvasBlocked"), value: blockingDetail });
  }

  return details.slice(0, 4);
}

export function ResearchCanvas({
  onRunStage,
  runningStageId,
  selectedQuest,
  showHeading = true,
  stages,
}: {
  readonly onRunStage: (stageId: string) => void;
  readonly runningStageId: string | null;
  readonly selectedQuest: Quest;
  readonly showHeading?: boolean;
  readonly stages: readonly StageCard[];
}) {
  const { t } = useI18n();
  const nextActionStage = findNextActionStage(stages);
  const completeCount = stages.filter((stage) => stage.status === "complete").length;
  const blockedCount = stages.filter((stage) => stage.status === "blocked").length;
  const reviewCount = stages.filter(needsHumanReview).length;
  const progressLabel = stages.length > 0 ? `${completeCount}/${stages.length}` : "0/0";

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      {showHeading ? (
        <div className="flex flex-col gap-2 px-1 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-900">{t("researchCanvasTitle")}</p>
            <p className="mt-1 text-sm text-slate-500">{t("researchCanvasDescription")}</p>
          </div>
          <Badge tone="gray">
            {t("updated")} {formatDateTime(selectedQuest.updated_at)}
          </Badge>
        </div>
      ) : null}

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("canvasProgress")}</p>
          <p className="mt-1 text-lg font-semibold text-slate-950">{progressLabel}</p>
          <p className="mt-1 text-xs text-slate-500">{t("canvasCompleteCount")}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("overviewBlockedStages")}</p>
          <p className="mt-1 text-lg font-semibold text-slate-950">{blockedCount}</p>
          <p className="mt-1 text-xs text-slate-500">{t("canvasBlockedCount")}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("stageReviewPending")}</p>
          <p className="mt-1 text-lg font-semibold text-slate-950">{reviewCount}</p>
          <p className="mt-1 text-xs text-slate-500">{t("canvasReviewCount")}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("canvasNextAction")}</p>
          {nextActionStage ? (
            <div className="mt-1 grid gap-2">
              <p className="line-clamp-2 break-words text-sm font-semibold text-slate-950">{nextActionStage.title}</p>
              <div>
                <Badge tone={stageTone(nextActionStage.status)}>{labelFromEnum(nextActionStage.status)}</Badge>
              </div>
            </div>
          ) : (
            <p className="mt-1 text-sm font-semibold text-slate-950">{t("canvasNoNextAction")}</p>
          )}
        </div>
      </div>

      <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200 bg-white p-4">
        <div className="mb-4 flex min-w-[980px] flex-col gap-2 border-b border-slate-200 pb-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-900">{t("canvasMapTitle")}</p>
            <p className="mt-1 text-sm text-slate-500">{t("canvasMapDescription")}</p>
          </div>
          <Badge tone={nextActionStage ? stageTone(nextActionStage.status) : "gray"}>
            {nextActionStage ? t("canvasNextAction") : t("canvasNoNextAction")}
          </Badge>
        </div>
        <div className="grid min-w-[980px] grid-cols-5 gap-3">
          {stages.map((stage, index) => (
            <CanvasStageNode
              details={buildStageDetails(stage, t)}
              index={index}
              isNextAction={nextActionStage?.id === stage.id}
              key={stage.id}
              onRunStage={onRunStage}
              phaseLabel={t(phaseKeyForAgent(stage.agent_id))}
              runningStageId={runningStageId}
              selectedQuest={selectedQuest}
              stage={stage}
              total={stages.length}
              workflowReadiness={getWorkflowStageReadiness(stage, stages)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
