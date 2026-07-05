import type { StageCard, StageStatus } from "../api/types";
import { canRunStage } from "./stages";

export type IntakeBrief = {
  readonly dataAssets: string;
  readonly direction: string;
  readonly expectedOutput: string;
  readonly knownWork: string;
  readonly metric: string;
  readonly outputLanguage: string;
  readonly painPoint: string;
  readonly scenario: string;
  readonly target: string;
  readonly targetUser: string;
};

export type ProgressSummary = {
  readonly blocked: number;
  readonly complete: number;
  readonly pending: number;
  readonly running: number;
  readonly total: number;
};

export type PreviewData = {
  readonly demand: {
    readonly detail: string;
    readonly status: StageStatus;
    readonly value: string;
  };
  readonly experiment: {
    readonly detail: string;
    readonly scriptStepCount: number;
    readonly status: StageStatus;
  };
  readonly idea: {
    readonly detail: string;
    readonly ideaCount: number;
    readonly selectedIdeaTitle: string;
  };
  readonly literature: {
    readonly detail: string;
    readonly paperCount: number;
  };
  readonly writing: {
    readonly artifactCount: number | null;
    readonly detail: string;
    readonly status: StageStatus;
  };
};

const blankValues = new Set(["Not provided", "未提供"]);

function readLineValue(source: string, labels: readonly string[]) {
  const lines = source.split("\n");

  for (const label of labels) {
    const prefix = `- ${label}:`;
    const line = lines.find((item) => item.trimStart().startsWith(prefix));
    const value = line ? line.trimStart().slice(prefix.length).trim() : "";
    if (value && !blankValues.has(value)) {
      return value;
    }
  }

  return "";
}

function readString(payload: Readonly<Record<string, unknown>>, key: string) {
  const value = payload[key];
  return typeof value === "string" ? value : "";
}

function readStringArray(payload: Readonly<Record<string, unknown>>, key: string) {
  const value = payload[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function readRecordArray(payload: Readonly<Record<string, unknown>>, key: string) {
  const value = payload[key];
  return Array.isArray(value)
    ? value.filter(
        (item): item is Record<string, unknown> =>
          typeof item === "object" && item !== null && !Array.isArray(item),
      )
    : [];
}

function findStage(stages: readonly StageCard[], agentId: string) {
  return stages.find((stage) => stage.agent_id === agentId);
}

function findSelectedIdeaTitle(stage: StageCard | undefined) {
  if (!stage) {
    return "";
  }

  const selectedIdeaIds = new Set(readStringArray(stage.output_payload, "selected_idea_ids"));
  const ideas = readRecordArray(stage.output_payload, "ideas");
  const selectedIdea = ideas.find((idea) => selectedIdeaIds.has(readString(idea, "idea_id")));
  return selectedIdea ? readString(selectedIdea, "idea_title") : "";
}

export function parseIntakeBrief(initialDirection: string): IntakeBrief {
  return {
    dataAssets: readLineValue(initialDirection, ["Data, code, or resources", "Data, code, or resources already available", "已有数据、代码或资源"]),
    direction: readLineValue(initialDirection, ["Research direction", "研究方向"]),
    expectedOutput: readLineValue(initialDirection, ["Expected research output", "期望科研产出"]),
    knownWork: readLineValue(initialDirection, ["Known papers / methods / baselines", "Known papers, methods, or baselines", "已知论文、方法或 baseline"]),
    metric: readLineValue(initialDirection, ["Evaluation metric or success signal", "评价指标或成功信号"]),
    outputLanguage: readLineValue(initialDirection, ["Preferred output language", "期望产出语言"]),
    painPoint: readLineValue(initialDirection, ["Current pain point or suspected gap", "当前痛点或可能 gap"]),
    scenario: readLineValue(initialDirection, ["Real-world scenario / demand source", "真实应用场景或需求来源"]),
    target: readLineValue(initialDirection, ["Input and desired output", "输入与期望输出"]),
    targetUser: readLineValue(initialDirection, ["Target user or customer", "目标用户或客户"]),
  };
}

export function summarizeProgress(stages: readonly StageCard[]): ProgressSummary {
  let blocked = 0;
  let complete = 0;
  let pending = 0;
  let running = 0;

  for (const stage of stages) {
    if (stage.status === "blocked") {
      blocked += 1;
    } else if (stage.status === "complete") {
      complete += 1;
    } else if (stage.status === "running") {
      running += 1;
    } else {
      pending += 1;
    }
  }

  return { blocked, complete, pending, running, total: stages.length };
}

export function findNextStage(stages: readonly StageCard[]) {
  return (
    stages.find((stage) => stage.status === "running") ??
    stages.find((stage) => canRunStage(stage)) ??
    stages.find((stage) => stage.status === "blocked") ??
    stages.find((stage) => stage.status === "pending") ??
    null
  );
}

export function buildPreviewData(stages: readonly StageCard[]): PreviewData {
  const demandStage = findStage(stages, "demand_validator");
  const literatureStage = findStage(stages, "literature_scout");
  const ideaStage = findStage(stages, "idea_generator");
  const experimentStage = findStage(stages, "experiment_planner");
  const paperStage = findStage(stages, "paper_meeting_writer");
  const papers = literatureStage ? readRecordArray(literatureStage.output_payload, "papers") : [];
  const ideas = ideaStage ? readRecordArray(ideaStage.output_payload, "ideas") : [];
  const scriptPlan = experimentStage ? readStringArray(experimentStage.output_payload, "first_runnable_script_plan") : [];
  const artifactCount = paperStage?.evidence_payload.artifact_count;

  return {
    demand: {
      detail: readString(demandStage?.output_payload ?? {}, "real_world_scenario") || demandStage?.summary || "",
      status: demandStage?.status ?? "pending",
      value: readString(demandStage?.output_payload ?? {}, "demand_assessment"),
    },
    experiment: {
      detail: experimentStage?.summary || "",
      scriptStepCount: scriptPlan.length,
      status: experimentStage?.status ?? "pending",
    },
    idea: {
      detail: findSelectedIdeaTitle(ideaStage) || ideaStage?.summary || "",
      ideaCount: ideas.length,
      selectedIdeaTitle: findSelectedIdeaTitle(ideaStage),
    },
    literature: {
      detail: papers[0] ? readString(papers[0], "title") : literatureStage?.summary || "",
      paperCount: papers.length,
    },
    writing: {
      artifactCount: typeof artifactCount === "number" ? artifactCount : null,
      detail: paperStage?.summary || "",
      status: paperStage?.status ?? "pending",
    },
  };
}
