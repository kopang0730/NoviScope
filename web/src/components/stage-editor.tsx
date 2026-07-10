import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { updateStage } from "../api/quests";
import { getErrorMessage } from "../api/client";
import type { StageCard, StageStatus } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { labelFromEnum, stringifyJson } from "../lib/format";
import { useAsyncSelectionGuard } from "../lib/use-async-selection-guard";
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
  const { t } = useI18n();
  const [formState, setFormState] = useState<FormState>(() => buildFormState(stage));
  const [showPayloads, setShowPayloads] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [stageSaved, setStageSaved] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const isCurrentStage = useAsyncSelectionGuard(stage.id);

  useEffect(() => {
    setFormState(buildFormState(stage));
    setShowPayloads(false);
    setSubmitError(null);
  }, [stage]);

  useEffect(() => {
    setStageSaved(false);
  }, [stage.id]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    setStageSaved(false);

    try {
      const humanApproved =
        formState.humanApproved === "pending_review" ? null : formState.humanApproved === "approved";
      const updatedStage = await updateStage(stage.id, {
        evidence_payload: parseJsonRecord(formState.evidencePayload),
        human_approved: humanApproved,
        input_payload: parseJsonRecord(formState.inputPayload),
        output_payload: parseJsonRecord(formState.outputPayload),
        review_notes: formState.reviewNotes,
        status: formState.status,
        summary: formState.summary,
      });

      if (!isCurrentStage()) {
        return;
      }
      onStageChange(updatedStage);
      setStageSaved(true);
    } catch (error) {
      if (isCurrentStage()) {
        setSubmitError(getErrorMessage(error));
      }
    } finally {
      if (isCurrentStage()) {
        setSubmitting(false);
      }
    }
  }

  return (
    <Card>
      <CardHeading description={t("stageEditorDescription")} title={t("stageEditorTitle")} />
      <form className="mt-6 space-y-4" onSubmit={(event) => void handleSubmit(event)}>
        <div className="grid gap-4 lg:grid-cols-2">
          <Select
            label={t("stageStatus")}
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
                ? t("stageReviewPendingHint")
                : t("stageReviewDecisionHint")
            }
            label={t("stageHumanApproval")}
            onChange={(event) =>
              setFormState((current) => ({
                ...current,
                humanApproved: parseHumanApprovalValue(event.target.value),
              }))
            }
            value={formState.humanApproved}
          >
            <option value="pending_review">{t("stageReviewPending")}</option>
            <option value="approved">{t("stageReviewApproved")}</option>
            <option value="rejected">{t("stageReviewRejected")}</option>
          </Select>
        </div>
        <TextArea
          label={t("stageSummary")}
          onChange={(event) => setFormState((current) => ({ ...current, summary: event.target.value }))}
          rows={5}
          value={formState.summary}
        />
        <TextArea
          label={t("reviewNotes")}
          onChange={(event) => setFormState((current) => ({ ...current, reviewNotes: event.target.value }))}
          rows={4}
          value={formState.reviewNotes}
        />
        <div>
          <Button onClick={() => setShowPayloads((current) => !current)} size="sm" type="button" variant="secondary">
            {showPayloads ? t("stageHideAdvancedPayloads") : t("stageShowAdvancedPayloads")}
          </Button>
          {showPayloads ? (
            <div className="mt-4 grid gap-4 xl:grid-cols-3">
              <TextArea
                label={t("stageInputPayload")}
                onChange={(event) => setFormState((current) => ({ ...current, inputPayload: event.target.value }))}
                rows={10}
                value={formState.inputPayload}
              />
              <TextArea
                label={t("stageOutputPayload")}
                onChange={(event) => setFormState((current) => ({ ...current, outputPayload: event.target.value }))}
                rows={10}
                value={formState.outputPayload}
              />
              <TextArea
                label={t("stageEvidencePayload")}
                onChange={(event) => setFormState((current) => ({ ...current, evidencePayload: event.target.value }))}
                rows={10}
                value={formState.evidencePayload}
              />
            </div>
          ) : null}
        </div>
        {submitError ? <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{submitError}</p> : null}
        {stageSaved ? (
          <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            {t("stageUpdatedSuccessfully")}
          </p>
        ) : null}
        <Button loading={submitting} type="submit">
          {t("stageSave")}
        </Button>
      </form>
    </Card>
  );
}
