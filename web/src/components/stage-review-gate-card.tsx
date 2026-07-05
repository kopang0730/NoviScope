import { useEffect, useState } from "react";
import { getErrorMessage } from "../api/client";
import { updateStage } from "../api/quests";
import type { StageCard } from "../api/types";
import { useI18n, type TranslationKey } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import { stageTone } from "../lib/status-tones";
import { Badge, type BadgeTone } from "./badge";
import { Button } from "./button";
import { Card, CardHeading } from "./card";
import { TextArea } from "./input";

type ReviewDecision = "approved" | "pending" | "rejected";

function reviewDecision(stage: StageCard): ReviewDecision {
  if (stage.human_approved === true) {
    return "approved";
  }
  if (stage.human_approved === false) {
    return "rejected";
  }
  return "pending";
}

function reviewTone(decision: ReviewDecision): BadgeTone {
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

export function StageReviewGateCard({
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
  const [reopening, setReopening] = useState(false);
  const [successKey, setSuccessKey] = useState<TranslationKey | null>(null);
  const decision = reviewDecision(stage);
  const canRecordReview = stage.status === "complete";
  const canReopenForRerun = canRecordReview && stage.human_approved === false;

  useEffect(() => {
    setNotes(stage.review_notes);
    setPendingDecision(null);
    setReviewError(null);
    setReopening(false);
  }, [stage.id, stage.review_notes, stage.human_approved]);

  useEffect(() => {
    setSuccessKey(null);
  }, [stage.id]);

  async function submitReview(nextDecision: ReviewDecision) {
    if (!canRecordReview) {
      return;
    }

    setPendingDecision(nextDecision);
    setReviewError(null);
    setSuccessKey(null);

    try {
      const updatedStage = await updateStage(stage.id, {
        human_approved: approvalValue(nextDecision),
        review_notes: notes.trim(),
      });
      onStageChange(updatedStage);
      setSuccessKey("stageReviewSaved");
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

  async function reopenForRerun() {
    if (!canReopenForRerun) {
      return;
    }

    setReopening(true);
    setReviewError(null);
    setSuccessKey(null);

    try {
      const updatedStage = await updateStage(stage.id, { status: "blocked" });
      onStageChange(updatedStage);
      setSuccessKey("stageReviewReopened");
    } catch (error) {
      if (error instanceof Error) {
        setReviewError(getErrorMessage(error));
        return;
      }
      throw error;
    } finally {
      setReopening(false);
    }
  }

  return (
    <Card>
      <CardHeading description={t("stageReviewGateDescription")} title={t("stageReviewGateTitle")} />
      <div className="mt-4 grid gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 lg:grid-cols-[minmax(0,1fr)_auto]">
        <div>
          <p className="text-sm font-medium text-slate-900">{t("stageReviewDecision")}</p>
          <p className="mt-1 text-sm text-slate-600">
            {decision === "approved"
              ? t("stageReviewApprovedDescription")
              : decision === "rejected"
                ? t("stageReviewRejectedDescription")
                : t("stageReviewPendingDescription")}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 lg:justify-end">
          <Badge tone={stageTone(stage.status)}>{labelFromEnum(stage.status)}</Badge>
          <Badge tone={reviewTone(decision)}>
            {decision === "approved"
              ? t("stageReviewApproved")
              : decision === "rejected"
                ? t("stageReviewRejected")
                : t("stageReviewPending")}
          </Badge>
        </div>
      </div>

      <div className="mt-4">
        <TextArea
          hint={t("stageReviewNotesHint")}
          label={t("reviewNotes")}
          onChange={(event) => setNotes(event.target.value)}
          placeholder={t("stageReviewNotesPlaceholder")}
          rows={4}
          value={notes}
        />
      </div>

      {!canRecordReview ? (
        <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {t("stageReviewActionUnavailable")}
        </p>
      ) : null}
      {canReopenForRerun ? (
        <p className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
          {t("stageReviewReopenDescription")}
        </p>
      ) : null}
      {reviewError ? (
        <p className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {reviewError}
        </p>
      ) : null}
      {successKey ? (
        <p className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
          {t(successKey)}
        </p>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          disabled={!canRecordReview}
          loading={pendingDecision === "approved"}
          onClick={() => void submitReview("approved")}
          size="sm"
        >
          {t("stageReviewApproveAction")}
        </Button>
        <Button
          disabled={!canRecordReview}
          loading={pendingDecision === "rejected"}
          onClick={() => void submitReview("rejected")}
          size="sm"
          variant="secondary"
        >
          {t("stageReviewRejectAction")}
        </Button>
        <Button
          disabled={!canRecordReview}
          loading={pendingDecision === "pending"}
          onClick={() => void submitReview("pending")}
          size="sm"
          variant="ghost"
        >
          {t("stageReviewResetAction")}
        </Button>
        {canReopenForRerun ? (
          <Button loading={reopening} onClick={() => void reopenForRerun()} size="sm" variant="secondary">
            {t("stageReviewReopenAction")}
          </Button>
        ) : null}
      </div>
    </Card>
  );
}
