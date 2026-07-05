import { Fragment } from "react";
import { Link } from "react-router-dom";
import type { Quest, StageCard, StageStatus } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { formatDateTime, labelFromEnum } from "../lib/format";
import { canRunStage } from "../lib/stages";
import { stageTone } from "../lib/status-tones";
import { Badge } from "./badge";
import { Button, buttonClassName } from "./button";

type CanvasDetail = {
  readonly label: string;
  readonly value: string;
};

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

function statusBorderClassName(status: StageStatus) {
  if (status === "complete") {
    return "border-emerald-300";
  }
  if (status === "blocked") {
    return "border-rose-300";
  }
  if (status === "running") {
    return "border-amber-300";
  }
  return "border-slate-300";
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

  if (blockingDetail) {
    details.push({ label: t("canvasBlocked"), value: blockingDetail });
  }

  return details.slice(0, 4);
}

export function ResearchCanvas({
  onRunStage,
  runningStageId,
  selectedQuest,
  stages,
}: {
  readonly onRunStage: (stageId: string) => void;
  readonly runningStageId: string | null;
  readonly selectedQuest: Quest;
  readonly stages: readonly StageCard[];
}) {
  const { t } = useI18n();

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="flex flex-col gap-2 px-1 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-900">{t("researchCanvasTitle")}</p>
          <p className="mt-1 text-sm text-slate-500">{t("researchCanvasDescription")}</p>
        </div>
        <Badge tone="gray">
          {t("updated")} {formatDateTime(selectedQuest.updated_at)}
        </Badge>
      </div>

      <div className="mt-4 rounded-lg border border-slate-200 bg-white p-3">
        <div className="space-y-2">
          {stages.map((stage, index) => {
            const details = buildStageDetails(stage, t);
            return (
              <Fragment key={stage.id}>
                <div
                  className={[
                    "rounded-lg border bg-white p-4 shadow-sm",
                    statusBorderClassName(stage.status),
                  ].join(" ")}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        {index + 1}. {stage.agent_id}
                      </p>
                      <h3 className="mt-1 line-clamp-2 text-sm font-semibold text-slate-900">{stage.title}</h3>
                    </div>
                    <Badge tone={stageTone(stage.status)}>{labelFromEnum(stage.status)}</Badge>
                  </div>

                  <p className="mt-3 line-clamp-3 text-sm text-slate-600">
                    {stage.summary || t("noSummaryYet")}
                  </p>

                  <div className="mt-4 grid gap-2">
                    {details.length > 0 ? (
                      details.map((detail) => (
                        <div className="rounded-md bg-slate-50 px-3 py-2" key={`${detail.label}-${detail.value}`}>
                          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                            {detail.label}
                          </p>
                          <p className="mt-1 line-clamp-2 text-xs text-slate-700">{detail.value}</p>
                        </div>
                      ))
                    ) : (
                      <p className="rounded-md border border-dashed border-slate-200 px-3 py-2 text-xs text-slate-500">
                        {t("canvasWaitingForOutput")}
                      </p>
                    )}
                  </div>

                  <div className="mt-4 flex items-center gap-2">
                    {canRunStage(stage) ? (
                      <Button loading={runningStageId === stage.id} onClick={() => onRunStage(stage.id)} size="sm">
                        {t("runStage")}
                      </Button>
                    ) : null}
                    <Link
                      className={buttonClassName({ size: "sm", variant: "secondary" })}
                      to={`/stages/${stage.id}?quest=${selectedQuest.id}`}
                    >
                      {t("open")}
                    </Link>
                  </div>
                </div>

                {index < stages.length - 1 ? (
                  <div className="flex h-8 items-center justify-center" aria-hidden="true">
                    <div className="h-full w-px bg-slate-300" />
                    <span className="-ml-[5px] mt-5 text-slate-400">v</span>
                  </div>
                ) : null}
              </Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
}
