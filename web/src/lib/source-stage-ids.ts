export type SourceStageIds = Readonly<Record<string, string>>;

export function readSourceStageIds(payload: Record<string, unknown>): SourceStageIds {
  const value = payload.source_stage_ids;
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return {};
  }

  return Object.fromEntries(
    Object.entries(value).filter((entry): entry is [string, string] => {
      const [, stageId] = entry;
      return typeof stageId === "string" && stageId.trim() !== "";
    }),
  );
}
