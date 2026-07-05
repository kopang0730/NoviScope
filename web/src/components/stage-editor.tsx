import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { updateStage } from "../api/quests";
import { getErrorMessage } from "../api/client";
import type { StageCard, StageStatus } from "../api/types";
import { labelFromEnum, stringifyJson } from "../lib/format";
import { Button } from "./button";
import { Card, CardHeading } from "./card";
import { Select, TextArea } from "./input";

const stageStatuses: readonly StageStatus[] = ["pending", "running", "blocked", "complete"];

type HumanApprovalValue = "pending_review" | "approved" | "rejected";

type FormState = {
  readonly evidencePayload: string;
  readonly humanApproved: HumanApprovalValue;
  readonly inputPayload: string;
  readonly outputPayload: string;
  readonly reviewNotes: string;
  readonly status: StageStatus;
  readonly summary: string;
};

function buildFormState(stage: StageCard): FormState {
  return {
    evidencePayload: stringifyJson(stage.evidence_payload),
    humanApproved: stage.human_approved === null ? "pending_review" : stage.human_approved ? "approved" : "rejected",
    inputPayload: stringifyJson(stage.input_payload),
    outputPayload: stringifyJson(stage.output_payload),
    reviewNotes: stage.review_notes,
    status: stage.status,
    summary: stage.summary,
  };
}

function parseStageStatus(value: string): StageStatus {
  switch (value) {
    case "pending":
      return "pending";
    case "running":
      return "running";
    case "blocked":
      return "blocked";
    case "complete":
      return "complete";
    default:
      return "pending";
  }
}

function parseHumanApprovalValue(value: string): HumanApprovalValue {
  switch (value) {
    case "approved":
      return "approved";
    case "rejected":
      return "rejected";
    default:
      return "pending_review";
  }
}

function isJsonRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseJsonRecord(value: string) {
  const parsed: unknown = JSON.parse(value);
  if (!isJsonRecord(parsed)) {
    throw new Error("Payload must be a JSON object.");
  }
  return parsed;
}

export function StageEditor({
  onStageChange,
  stage,
}: {
  readonly onStageChange: (stage: StageCard) => void;
  readonly stage: StageCard;
}) {
  const [formState, setFormState] = useState<FormState>(() => buildFormState(stage));
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setFormState(buildFormState(stage));
    setSubmitError(null);
    setSuccessMessage(null);
  }, [stage]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    setSuccessMessage(null);

    try {
      const humanApproved =
        formState.humanApproved === "pending_review" ? undefined : formState.humanApproved === "approved";
      const updatedStage = await updateStage(stage.id, {
        evidence_payload: parseJsonRecord(formState.evidencePayload),
        human_approved: humanApproved,
        input_payload: parseJsonRecord(formState.inputPayload),
        output_payload: parseJsonRecord(formState.outputPayload),
        review_notes: formState.reviewNotes,
        status: formState.status,
        summary: formState.summary,
      });

      onStageChange(updatedStage);
      setSuccessMessage("Stage updated successfully.");
    } catch (error) {
      setSubmitError(getErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeading description="Update stage status, summary, approval, and payloads." title="Edit Stage" />
      <form className="mt-6 space-y-4" onSubmit={(event) => void handleSubmit(event)}>
        <div className="grid gap-4 lg:grid-cols-2">
          <Select
            label="Status"
            onChange={(event) => setFormState((current) => ({ ...current, status: parseStageStatus(event.target.value) }))}
            value={formState.status}
          >
            {stageStatuses.map((status) => (
              <option key={status} value={status}>
                {labelFromEnum(status)}
              </option>
            ))}
          </Select>
          <Select
            hint={
              formState.humanApproved === "pending_review"
                ? "This stage has not been reviewed yet. Choose Approved or Rejected to record a decision."
                : "You can change the current decision, but the API does not support clearing it back to no decision."
            }
            label="Human Approval"
            onChange={(event) =>
              setFormState((current) => ({
                ...current,
                humanApproved: parseHumanApprovalValue(event.target.value),
              }))
            }
            value={formState.humanApproved}
          >
            {formState.humanApproved === "pending_review" ? <option value="pending_review">Not yet reviewed</option> : null}
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </Select>
        </div>
        <TextArea
          label="Summary"
          onChange={(event) => setFormState((current) => ({ ...current, summary: event.target.value }))}
          rows={5}
          value={formState.summary}
        />
        <TextArea
          label="Review Notes"
          onChange={(event) => setFormState((current) => ({ ...current, reviewNotes: event.target.value }))}
          rows={4}
          value={formState.reviewNotes}
        />
        <div className="grid gap-4 xl:grid-cols-3">
          <TextArea
            label="Input Payload"
            onChange={(event) => setFormState((current) => ({ ...current, inputPayload: event.target.value }))}
            rows={10}
            value={formState.inputPayload}
          />
          <TextArea
            label="Output Payload"
            onChange={(event) => setFormState((current) => ({ ...current, outputPayload: event.target.value }))}
            rows={10}
            value={formState.outputPayload}
          />
          <TextArea
            label="Evidence Payload"
            onChange={(event) => setFormState((current) => ({ ...current, evidencePayload: event.target.value }))}
            rows={10}
            value={formState.evidencePayload}
          />
        </div>
        {submitError ? <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{submitError}</p> : null}
        {successMessage ? <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{successMessage}</p> : null}
        <Button loading={submitting} type="submit">
          Save Stage
        </Button>
      </form>
    </Card>
  );
}
