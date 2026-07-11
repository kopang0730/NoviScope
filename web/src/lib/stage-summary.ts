import type { StageCard } from "../api/types";

function readSummary(value: unknown) {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return "";
  }

  const summary = Reflect.get(value, "summary");
  return typeof summary === "string" ? summary.trim() : "";
}

function readSerializedSummary(value: string) {
  const trimmed = value.trim();
  if (!trimmed.startsWith("{") || !trimmed.endsWith("}")) {
    return "";
  }

  try {
    return readSummary(JSON.parse(trimmed));
  } catch (error) {
    if (!(error instanceof SyntaxError)) {
      throw error;
    }
    return "";
  }
}

function looksLikeSerializedPayload(value: string) {
  const trimmed = value.trimStart();
  return trimmed.startsWith("{")
    || trimmed.startsWith("[")
    || trimmed.startsWith("```json");
}

export function getReadableStageSummary(stage: StageCard) {
  const serializedSummary = readSerializedSummary(stage.summary);
  if (serializedSummary) {
    return serializedSummary;
  }
  if (looksLikeSerializedPayload(stage.summary)) {
    return "";
  }
  return stage.summary.trim() || readSummary(stage.output_payload);
}
