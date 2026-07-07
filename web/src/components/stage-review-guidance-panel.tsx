import { useEffect, useState } from "react";
import { getErrorMessage } from "../api/client";
import { getStageReviewGuidance, type StageReviewGuidance } from "../api/stage-review-guidance";
import type { StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import { Badge } from "./badge";

function GuidanceList({ emptyLabel, items }: { readonly emptyLabel: string; readonly items: readonly string[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">{emptyLabel}</p>;
  }

  return (
    <ul className="space-y-1 text-sm text-slate-600">
      {items.map((item) => (
        <li className="flex gap-2" key={item}>
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function guidanceTone(guidance: StageReviewGuidance) {
  if (guidance.approval_state === "approved") {
    return "green";
  }
  if (guidance.approval_state === "rejected") {
    return "red";
  }
  if (guidance.can_approve) {
    return "teal";
  }
  return "amber";
}

export function StageReviewGuidancePanel({ stage }: { readonly stage: StageCard }) {
  const { t } = useI18n();
  const [guidance, setGuidance] = useState<StageReviewGuidance | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setLoadError(null);

    void getStageReviewGuidance(stage.id)
      .then((nextGuidance) => {
        if (active) {
          setGuidance(nextGuidance);
        }
      })
      .catch((error) => {
        if (!active) {
          return;
        }
        if (error instanceof Error) {
          setGuidance(null);
          setLoadError(getErrorMessage(error));
          return;
        }
        throw error;
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [stage.id, stage.updated_at]);

  return (
    <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-900">{t("stageReviewGuidanceTitle")}</p>
          <p className="mt-1 text-sm text-slate-600">{t("stageReviewGuidanceDescription")}</p>
        </div>
        {guidance ? (
          <div className="flex flex-wrap gap-2 sm:justify-end">
            <Badge tone={guidanceTone(guidance)}>{labelFromEnum(guidance.approval_state)}</Badge>
            <Badge tone="gray">
              {t("stageConfidence")}: {labelFromEnum(guidance.confidence)}
            </Badge>
          </div>
        ) : null}
      </div>

      {loading ? <p className="mt-3 text-sm text-slate-500">{t("stageReviewGuidanceLoading")}</p> : null}
      {loadError ? (
        <p className="mt-3 rounded-md border border-rose-200 bg-white px-3 py-2 text-sm text-rose-700">
          {t("stageReviewGuidanceLoadFailed")}: {loadError}
        </p>
      ) : null}

      {guidance ? (
        <div className="mt-4 grid gap-3 lg:grid-cols-3">
          <div className="rounded-md border border-slate-200 bg-white px-3 py-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t("stageReviewGuidanceChecklist")}
            </p>
            <div className="mt-2">
              <GuidanceList emptyLabel={t("notAvailable")} items={guidance.checklist} />
            </div>
          </div>
          <div className="rounded-md border border-slate-200 bg-white px-3 py-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t("stageReviewGuidanceEvidence")}
            </p>
            <div className="mt-2">
              <GuidanceList
                emptyLabel={t("stageReviewGuidanceNoEvidence")}
                items={guidance.evidence_summary}
              />
            </div>
          </div>
          <div className="rounded-md border border-slate-200 bg-white px-3 py-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t("stageReviewGuidanceWarnings")}
            </p>
            <div className="mt-2">
              <GuidanceList emptyLabel={t("stageReviewGuidanceNoWarnings")} items={guidance.warnings} />
            </div>
          </div>
        </div>
      ) : null}

      {guidance?.blocking_reason ? (
        <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {t("stageReviewGuidanceBlockingReason")}: {guidance.blocking_reason}
        </p>
      ) : null}
    </div>
  );
}
