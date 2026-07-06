import { describe, expect, it } from "vitest";

import type { StageCard } from "../api/types";
import { translations } from "../i18n/translations";
import { buildStageDetails } from "./research-canvas-data";
import { paperMeetingWriterAgentId } from "./stages";

function buildPaperWriterStage(outputPayload: Record<string, unknown>): StageCard {
  return {
    agent_id: paperMeetingWriterAgentId,
    confidence: "medium",
    created_at: "2026-07-06T00:00:00Z",
    evidence_payload: {
      artifact_count: 4,
      download_format: "markdown",
    },
    human_approved: null,
    id: "stage_paper",
    input_payload: {},
    output_payload: outputPayload,
    quest_id: "quest_1",
    review_notes: "",
    status: "complete",
    summary: "Generated review-only paper and meeting artifacts.",
    title: "Paper & Meeting Writer",
    updated_at: "2026-07-06T00:00:00Z",
  };
}

describe("buildStageDetails", () => {
  it("surfaces paper writer claim boundaries when draft artifacts exist", () => {
    const stage = buildPaperWriterStage({
      experiment_results_not_available: ["No reviewed experiment metrics are available."],
      human_review_required: ["Confirm every citation before submission."],
      model_generated_hypotheses: ["Temporal smoothing may improve action labels."],
      verified_facts: ["A coach feedback scenario was recorded upstream."],
    });

    const details = buildStageDetails(stage, (key) => translations.en[key]);

    expect(details).toEqual([
      {
        label: "Verified facts",
        value: "A coach feedback scenario was recorded upstream.",
      },
      {
        label: "Model-generated hypotheses",
        value: "Temporal smoothing may improve action labels.",
      },
      {
        label: "Experiment results not available",
        value: "No reviewed experiment metrics are available.",
      },
      {
        label: "Human review required",
        value: "Confirm every citation before submission.",
      },
    ]);
  });
});
