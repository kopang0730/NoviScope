import { describe, expect, it } from "vitest";
import type { StageCard } from "../api/types";
import { buildQuestReviewPacket } from "./quest-review-export";
import { buildStageReviewPacketMarkdown } from "./stage-review-packet";

const translate = (key: string) => key;

function reviewableStage(): StageCard {
  return {
    agent_id: "demand_validator",
    confidence: "medium",
    created_at: "2026-07-07T00:00:00.000Z",
    evidence_payload: {
      api_key: "sk-review-secret",
      sources: ["Coach interview"],
    },
    human_approved: true,
    id: "stage-1",
    input_payload: {
      nested: [{ token: "private-review-token", visible: "visible-input" }],
    },
    output_payload: {
      demand_assessment: "plausible",
      raw_response: "raw provider response should stay hidden",
      trace: {
        secret: "nested secret should stay hidden",
        visible: "visible-output",
      },
    },
    quest_id: "quest-1",
    review_notes: "Human reviewed demand evidence.",
    status: "complete",
    summary: "Demand has a real scenario.",
    title: "Demand validation",
    updated_at: "2026-07-07T00:00:00.000Z",
  };
}

describe("review packet payload sanitization", () => {
  it("omits secret-like fields from single-stage review packet markdown", () => {
    // Given: a saved stage contains raw provider output and secret-like payload keys.
    const stage = reviewableStage();

    // When: the browser builds the single-stage review packet.
    const markdown = buildStageReviewPacketMarkdown(stage, translate);

    // Then: the packet stays auditable without leaking hidden values.
    expect(markdown).toContain("input_payload.nested[0].token");
    expect(markdown).toContain("output_payload.raw_response");
    expect(markdown).toContain("output_payload.trace.secret");
    expect(markdown).toContain("evidence_payload.api_key");
    expect(markdown).toContain("visible-input");
    expect(markdown).toContain("visible-output");
    expect(markdown).not.toContain("private-review-token");
    expect(markdown).not.toContain("raw provider response should stay hidden");
    expect(markdown).not.toContain("nested secret should stay hidden");
    expect(markdown).not.toContain("sk-review-secret");
  });

  it("omits secret-like fields from quest review packet markdown", () => {
    // Given: a quest packet is assembled from stages with saved sensitive payload fields.
    const stage = reviewableStage();

    // When: the browser builds the quest-level review packet.
    const packet = buildQuestReviewPacket(
      {
        created_at: "2026-07-07T00:00:00.000Z",
        id: "quest-1",
        initial_direction: "Use computer vision for badminton trajectory recognition.",
        owner_user_id: "user-1",
        status: "draft",
        title: "Badminton trajectory recognition",
        updated_at: "2026-07-07T00:00:00.000Z",
      },
      [stage],
    );

    // Then: hidden paths are listed while hidden values are omitted.
    expect(packet.content).toContain("Hidden payload fields");
    expect(packet.content).toContain("input_payload.nested[0].token");
    expect(packet.content).toContain("output_payload.raw_response");
    expect(packet.content).toContain("evidence_payload.api_key");
    expect(packet.content).toContain("visible-input");
    expect(packet.content).toContain("visible-output");
    expect(packet.content).not.toContain("private-review-token");
    expect(packet.content).not.toContain("raw provider response should stay hidden");
    expect(packet.content).not.toContain("sk-review-secret");
  });
});
