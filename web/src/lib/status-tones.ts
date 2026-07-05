import type { QuestStatus, StageStatus } from "../api/types";
import type { BadgeTone } from "../components/badge";

export function questTone(status: QuestStatus): BadgeTone {
  if (status === "complete") {
    return "green";
  }

  if (status === "full_experiment" || status === "lightweight_experiment" || status === "demand_review") {
    return "amber";
  }

  if (status === "idea_selection") {
    return "teal";
  }

  return "blue";
}

export function stageTone(status: StageStatus): BadgeTone {
  if (status === "complete") {
    return "green";
  }

  if (status === "running") {
    return "amber";
  }

  if (status === "blocked") {
    return "red";
  }

  return "gray";
}
