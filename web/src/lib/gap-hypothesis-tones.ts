import type { StageConfidence } from "../api/types";
import type { BadgeTone } from "../components/badge";
import type { GapEvidenceType } from "./gap-hypothesis-view";

export function confidenceTone(value: StageConfidence): BadgeTone {
  if (value === "high") {
    return "green";
  }
  if (value === "medium") {
    return "amber";
  }
  if (value === "low") {
    return "red";
  }
  return "gray";
}

export function evidenceTone(value: GapEvidenceType): BadgeTone {
  if (value === "paper_limitations") {
    return "blue";
  }
  if (value === "human_context") {
    return "teal";
  }
  return "gray";
}
