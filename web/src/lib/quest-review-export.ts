import type { Quest, StageCard } from "../api/types";
import { labelFromEnum } from "./format";
import { buildPaperMeetingWriterView } from "./paper-meeting-view";
import { parseIntakeBrief, summarizeProgress } from "./quest-overview";
import { paperMeetingWriterAgentId } from "./stages";

function slugify(value: string) {
  const slug = value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "quest";
}

function jsonBlock(value: Record<string, unknown>) {
  if (Object.keys(value).length === 0) {
    return "_No saved payload._";
  }

  return `\`\`\`json\n${JSON.stringify(value, null, 2)}\n\`\`\``;
}

function reviewState(stage: StageCard) {
  if (stage.human_approved === true) {
    return "Approved";
  }
  if (stage.human_approved === false) {
    return "Rejected";
  }
  return "Pending review";
}

function appendLine(lines: string[], label: string, value: string) {
  lines.push(`- **${label}:** ${value.trim() || "Not available"}`);
}

function formatTimestamp(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toISOString();
}

export function buildQuestReviewPacket(quest: Quest, stages: readonly StageCard[]) {
  const intake = parseIntakeBrief(quest.initial_direction);
  const progress = summarizeProgress(stages);
  const lines: string[] = [];

  lines.push(`# NoviScope Quest Review Packet: ${quest.title}`);
  lines.push("");
  lines.push("> Review-only export. This packet serializes saved NoviScope workflow state and does not claim unfinished experiments are complete.");
  lines.push("");
  lines.push("## Safety And Traceability Notes");
  lines.push("");
  lines.push("- Model-generated hypotheses and draft writing must remain under human review until explicitly approved.");
  lines.push("- Experiment plans are not experiment results. Missing data, code, or environment details should remain blocking evidence.");
  lines.push("- Citations and paper metadata are only as reliable as the recorded source payloads; verify primary papers before formal submission.");
  lines.push("- JSON payloads below are included for auditability and should be treated as the source of the summarized claims.");
  lines.push("");

  lines.push("## Quest Metadata");
  lines.push("");
  appendLine(lines, "Quest ID", quest.id);
  appendLine(lines, "Status", labelFromEnum(quest.status));
  appendLine(lines, "Created", formatTimestamp(quest.created_at));
  appendLine(lines, "Updated", formatTimestamp(quest.updated_at));
  appendLine(lines, "Stage progress", `${progress.complete}/${progress.total} complete, ${progress.running} running, ${progress.blocked} blocked, ${progress.pending} pending`);
  lines.push("");

  lines.push("## Research Intake");
  lines.push("");
  appendLine(lines, "Research direction", intake.direction || quest.initial_direction);
  appendLine(lines, "Real-world scenario / demand source", intake.scenario);
  appendLine(lines, "Demand evidence sources to verify", intake.demandEvidenceSources);
  appendLine(lines, "Target user or customer", intake.targetUser);
  appendLine(lines, "Input and desired output", intake.target);
  appendLine(lines, "Current pain point or suspected gap", intake.painPoint);
  appendLine(lines, "Known papers / methods / baselines", intake.knownWork);
  appendLine(lines, "Known baseline or reproduction target", intake.knownBaseline);
  appendLine(lines, "Data, code, or resources", intake.dataAssets);
  appendLine(lines, "Evaluation metric or success signal", intake.metric);
  appendLine(lines, "Expected research output", intake.expectedOutput);
  appendLine(lines, "Preferred output language", intake.outputLanguage);
  lines.push("");

  lines.push("## Workflow Trace");
  for (const [index, stage] of stages.entries()) {
    lines.push("");
    lines.push(`### ${index + 1}. ${stage.title}`);
    lines.push("");
    appendLine(lines, "Stage ID", stage.id);
    appendLine(lines, "Agent ID", stage.agent_id);
    appendLine(lines, "Status", labelFromEnum(stage.status));
    appendLine(lines, "Confidence", labelFromEnum(stage.confidence));
    appendLine(lines, "Human review", reviewState(stage));
    appendLine(lines, "Updated", formatTimestamp(stage.updated_at));
    appendLine(lines, "Summary", stage.summary);
    appendLine(lines, "Review notes", stage.review_notes);
    lines.push("");
    lines.push("#### Output Payload");
    lines.push("");
    lines.push(jsonBlock(stage.output_payload));
    lines.push("");
    lines.push("#### Evidence Payload");
    lines.push("");
    lines.push(jsonBlock(stage.evidence_payload));
  }

  const paperStage = stages.find((stage) => stage.agent_id === paperMeetingWriterAgentId);
  const paperView = paperStage ? buildPaperMeetingWriterView(paperStage) : null;
  lines.push("");
  lines.push("## Paper And Meeting Draft Artifacts");
  lines.push("");
  if (!paperView) {
    lines.push("_No paper or meeting draft artifacts have been generated yet._");
  } else {
    appendLine(lines, "Writer confidence", labelFromEnum(paperView.confidence));
    appendLine(lines, "Writer summary", paperView.summary);
    lines.push("");
    lines.push("### Verified Facts");
    lines.push("");
    lines.push(paperView.verifiedFacts.length ? paperView.verifiedFacts.map((item) => `- ${item}`).join("\n") : "_Not available._");
    lines.push("");
    lines.push("### Model-Generated Hypotheses");
    lines.push("");
    lines.push(paperView.modelGeneratedHypotheses.length ? paperView.modelGeneratedHypotheses.map((item) => `- ${item}`).join("\n") : "_Not available._");
    lines.push("");
    lines.push("### Experiment Results Not Available");
    lines.push("");
    lines.push(paperView.experimentResultsNotAvailable.length ? paperView.experimentResultsNotAvailable.map((item) => `- ${item}`).join("\n") : "_Not available._");
    lines.push("");
    lines.push("### Human Review Required");
    lines.push("");
    lines.push(paperView.humanReviewRequired.length ? paperView.humanReviewRequired.map((item) => `- ${item}`).join("\n") : "_Not available._");

    for (const artifact of paperView.artifacts) {
      lines.push("");
      lines.push(`### Artifact: ${artifact.filename}`);
      lines.push("");
      lines.push(artifact.content.trim() || "_No saved content._");
    }
  }

  lines.push("");
  lines.push("---");
  lines.push("");
  lines.push("Generated by NoviScope from saved workflow state.");

  return {
    content: `${lines.join("\n")}\n`,
    filename: `${slugify(quest.title)}-review-packet.md`,
  };
}
