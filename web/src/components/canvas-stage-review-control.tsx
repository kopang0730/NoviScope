import { useEffect, useState } from "react";
import { getErrorMessage } from "../api/client";
import { updateStage } from "../api/quests";
import type { StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import { stageTone } from "../lib/status-tones";
import { Badge, type BadgeTone } from "./badge";
import { Button } from "./button";
import { TextArea } from "./input";

type ReviewDecision = "approved" | "pending" | "rejected";

function currentDecision(stage: StageCard): ReviewDecision {
  if (stage.human_approved === true) {
    return "approved";
  }
  if (stage.human_approved === false) {
    return "rejected";
  }
  return "pending";
}

function decisionTone(decision: ReviewDecision): BadgeTone {
  if (decision === "approved") {
    return "green";
  }
  if (decision === "rejected") {
    return "red";
  }
  return "amber";
}

function approvalValue(decision: ReviewDecision) {
  if (decision === "approved") {
    return true;
  }
  if (decision === "rejected") {
    return false;
  }
  return null;
}

export function CanvasStageReviewControl({
  onStageChange,
  stage,
}: {
  readonly onStageChange: (stage: StageCard) => void;
  readonly stage: StageCard;
}) {
  const { t } = useI18n();
  const [notes, setNotes] = useState(stage.review_notes);
  const [pendingDecision, setPendingDecision] = useState<ReviewDecision | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [reviewSaved, setReviewSaved] = useState(false);
  const decision = currentDecision(stage);
  const canRecordReview = stage.status === "complete";
  const isSubmitting = pendingDecision !== null;

  useEffect(() => {
    setNotes(stage.review_notes);
    setPendingDecision(null);
    setReviewError(null);
  }, [stage.id, stage.review_notes, stage.human_approved]);

  useEffect(() => {
    setReviewSaved(false);
  }, [stage.id]);

  async function submitReview(nextDecision: ReviewDecision) {
    if (!canRecordReview || isSubmitting) {
      return;
    }

    setPendingDecision(nextDecision);
    setReviewError(null);
    setReviewSaved(false);

    try {
      const updatedStage = await updateStage(stage.id, {
        human_approved: approvalValue(nextDecision),
        review_notes: notes.trim(),
      });
      onStageChange(updatedStage);
      setReviewSaved(true);
    } catch (error) {
      if (error instanceof Error) {
        setReviewError(getErrorMessage(error));
        return;
      }
      throw error;
    } finally {
      setPendingDecision(null);
    }
  }

  return (
    <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 px-3 py-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-semibold text-slate-900">{t("stageReviewGateTitle")}</p>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            {decision === "approved"
              ? t("stageReviewApprovedDescription")
              : decision === "rejected"
                ? t("stageReviewRejectedDescription")
                : t("stageReviewPendingDescription")}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 sm:justify-end">
          <Badge tone={stageTone(stage.status)}>{labelFromEnum(stage.status)}</Badge>
          <Badge tone={decisionTone(decision)}>
            {decision === "approved"
              ? t("stageReviewApproved")
              : decision === "rejected"
                ? t("stageReviewRejected")
                : t("stageReviewPending")}
          </Badge>
        </div>
      </div>

      <div className="mt-3">
        <TextArea
          hint={t("stageReviewNotesHint")}
          label={t("reviewNotes")}
          onChange={(event) => {
            setNotes(event.target.value);
            setReviewSaved(false);
          }}
          placeholder={t("stageReviewNotesPlaceholder")}
          rows={3}
          value={notes}
        />
      </div>

      {!canRecordReview ? (
        <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">
          {t("stageReviewActionUnavailable")}
        </p>
      ) : null}
      {reviewError ? (
        <p className="mt-3 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-xs leading-5 text-rose-700">
          {reviewError}
        </p>
      ) : null}
      {reviewSaved ? (
        <p className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs leading-5 text-emerald-700">
          {t("stageReviewSaved")}
        </p>
      ) : null}

      <div className="mt-3 flex flex-wrap gap-2">
        <Button
          disabled={!canRecordReview || isSubmitting}
          loading={pendingDecision === "approved"}
          onClick={() => void submitReview("approved")}
          size="sm"
          type="button"
        >
          {t("stageReviewApproveAction")}
        </Button>
        <Button
          disabled={!canRecordReview || isSubmitting}
          loading={pendingDecision === "rejected"}
          onClick={() => void submitReview("rejected")}
          size="sm"
          type="button"
          variant="secondary"
        >
          {t("stageReviewRejectAction")}
        </Button>
        <Button
          disabled={!canRecordReview || isSubmitting}
          loading={pendingDecision === "pending"}
          onClick={() => void submitReview("pending")}
          size="sm"
          type="button"
          variant="ghost"
        >
          {t("stageReviewResetAction")}
        </Button>
      </div>
    </div>
  );
}
