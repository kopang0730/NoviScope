import type { StageCard } from "../api/types";
import { type TranslationKey, useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import { Badge, type BadgeTone } from "./badge";
import { Card, CardHeading } from "./card";

type ClaimSafetyState =
  | "approved"
  | "missing_evidence"
  | "missing_output"
  | "needs_review"
  | "not_complete"
  | "rejected";

function payloadFieldCount(payload: Readonly<Record<string, unknown>>) {
  return Object.keys(payload).length;
}

function claimSafetyState(stage: StageCard): ClaimSafetyState {
  if (stage.status !== "complete") {
    return "not_complete";
  }
  if (stage.human_approved === false) {
    return "rejected";
  }
  if (stage.human_approved !== true) {
    return "needs_review";
  }
  if (payloadFieldCount(stage.output_payload) === 0) {
    return "missing_output";
  }
  if (payloadFieldCount(stage.evidence_payload) === 0) {
    return "missing_evidence";
  }
  return "approved";
}

function claimSafetyTone(state: ClaimSafetyState): BadgeTone {
  switch (state) {
    case "approved":
      return "green";
    case "missing_evidence":
    case "missing_output":
    case "needs_review":
    case "not_complete":
      return "amber";
    case "rejected":
      return "red";
  }
}

const claimSafetyBadgeKeyByState = {
  approved: "stageClaimSafetyBadge_approved",
  missing_evidence: "stageClaimSafetyBadge_missing_evidence",
  missing_output: "stageClaimSafetyBadge_missing_output",
  needs_review: "stageClaimSafetyBadge_needs_review",
  not_complete: "stageClaimSafetyBadge_not_complete",
  rejected: "stageClaimSafetyBadge_rejected",
} as const satisfies Record<ClaimSafetyState, TranslationKey>;

const claimSafetyDetailKeyByState = {
  approved: "stageClaimSafetyDetail_approved",
  missing_evidence: "stageClaimSafetyDetail_missing_evidence",
  missing_output: "stageClaimSafetyDetail_missing_output",
  needs_review: "stageClaimSafetyDetail_needs_review",
  not_complete: "stageClaimSafetyDetail_not_complete",
  rejected: "stageClaimSafetyDetail_rejected",
} as const satisfies Record<ClaimSafetyState, TranslationKey>;

const claimSafetyStateKeyByState = {
  approved: "stageClaimSafetyState_approved",
  missing_evidence: "stageClaimSafetyState_missing_evidence",
  missing_output: "stageClaimSafetyState_missing_output",
  needs_review: "stageClaimSafetyState_needs_review",
  not_complete: "stageClaimSafetyState_not_complete",
  rejected: "stageClaimSafetyState_rejected",
} as const satisfies Record<ClaimSafetyState, TranslationKey>;

export function StageClaimSafetyCard({ stage }: { readonly stage: StageCard }) {
  const { t } = useI18n();
  const state = claimSafetyState(stage);
  const outputFieldCount = payloadFieldCount(stage.output_payload);
  const evidenceFieldCount = payloadFieldCount(stage.evidence_payload);

  return (
    <Card>
      <CardHeading description={t("stageClaimSafetyDescription")} title={t("stageClaimSafetyTitle")} />

      <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-900">{t(claimSafetyStateKeyByState[state])}</p>
            <p className="mt-1 text-sm leading-6 text-slate-600">{t(claimSafetyDetailKeyByState[state])}</p>
          </div>
          <Badge tone={claimSafetyTone(state)}>{t(claimSafetyBadgeKeyByState[state])}</Badge>
        </div>

        <dl className="mt-4 grid gap-2 text-xs sm:grid-cols-4">
          <div className="rounded-md bg-white px-3 py-2">
            <dt className="font-semibold uppercase tracking-wide text-slate-500">{t("stageClaimSafetyStageStatus")}</dt>
            <dd className="mt-1 font-semibold text-slate-900">{labelFromEnum(stage.status)}</dd>
          </div>
          <div className="rounded-md bg-white px-3 py-2">
            <dt className="font-semibold uppercase tracking-wide text-slate-500">{t("stageClaimSafetyHumanReview")}</dt>
            <dd className="mt-1 font-semibold text-slate-900">
              {stage.human_approved === true
                ? t("stageReviewApproved")
                : stage.human_approved === false
                  ? t("stageReviewRejected")
                  : t("stageReviewPending")}
            </dd>
          </div>
          <div className="rounded-md bg-white px-3 py-2">
            <dt className="font-semibold uppercase tracking-wide text-slate-500">{t("canvasOutputFields")}</dt>
            <dd className="mt-1 font-semibold text-slate-900">{outputFieldCount}</dd>
          </div>
          <div className="rounded-md bg-white px-3 py-2">
            <dt className="font-semibold uppercase tracking-wide text-slate-500">{t("canvasEvidenceFields")}</dt>
            <dd className="mt-1 font-semibold text-slate-900">{evidenceFieldCount}</dd>
          </div>
        </dl>
      </div>
    </Card>
  );
}
