import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getErrorMessage } from "../api/client";
import { selectStageIdeas } from "../api/quests";
import type { StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { buildIdeaGeneratorView, type IdeaItem } from "../lib/gap-hypothesis-view";
import { useAsyncSelectionGuard } from "../lib/use-async-selection-guard";
import { buttonClassName } from "./button";
import { GapSummarySection, IdeaCardList } from "./gap-hypothesis-sections";
import { GapTable } from "./gap-table";

export function GapHypothesisOutput({
  experimentPlannerStage,
  onStageChange,
  stage,
}: {
  readonly experimentPlannerStage?: StageCard | null;
  readonly onStageChange?: (stage: StageCard) => void;
  readonly stage: StageCard;
}) {
  const { t } = useI18n();
  const [currentStage, setCurrentStage] = useState(stage);
  const [pendingIdeaId, setPendingIdeaId] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const isCurrentStage = useAsyncSelectionGuard(stage.id);

  useEffect(() => {
    setCurrentStage(stage);
    setPendingIdeaId(null);
    setSubmitError(null);
  }, [stage]);

  const ideaGenerator = useMemo(() => buildIdeaGeneratorView(currentStage), [currentStage]);

  if (!ideaGenerator) {
    return null;
  }

  const selectedIdeaIds = new Set(ideaGenerator.selectedIdeaIds);
  const alreadySelected = ideaGenerator.selectionStatus === "selected_for_experiment_design";

  async function handleSelectIdea(idea: IdeaItem) {
    const view = buildIdeaGeneratorView(currentStage);
    if (!view) {
      return;
    }

    setPendingIdeaId(idea.ideaId);
    setSubmitError(null);
    setSuccessMessage(null);

    const nextSelectedIdeaIds = selectedIdeaIds.has(idea.ideaId)
      ? [...view.selectedIdeaIds]
      : [...view.selectedIdeaIds, idea.ideaId];
    const reviewNotes = [
      currentStage.review_notes,
      t("ideaSelectionReviewPrefix"),
      idea.ideaTitle || idea.ideaId,
      t("ideaSelectionReviewSuffix"),
    ]
      .filter(Boolean)
      .join(" ");

    try {
      const updatedStage = await selectStageIdeas(currentStage.id, {
        review_notes: reviewNotes,
        selected_idea_ids: nextSelectedIdeaIds,
      });
      if (!isCurrentStage()) {
        return;
      }
      setCurrentStage(updatedStage);
      onStageChange?.(updatedStage);
      setSuccessMessage(t("ideaSelectionSaved"));
    } catch (error) {
      if (!isCurrentStage()) {
        return;
      }
      if (error instanceof Error) {
        setSubmitError(getErrorMessage(error));
      } else {
        throw error;
      }
    } finally {
      if (isCurrentStage()) {
        setPendingIdeaId(null);
      }
    }
  }

  return (
    <div className="space-y-5">
      <GapSummarySection view={ideaGenerator} />

      <section className="space-y-3">
        <div>
          <h3 className="text-base font-semibold text-slate-900">{t("gapListTitle")}</h3>
          <p className="mt-1 text-sm text-slate-500">{t("gapListDescription")}</p>
        </div>
        <GapTable gaps={ideaGenerator.gaps} />
      </section>

      <section className="space-y-3">
        <div>
          <h3 className="text-base font-semibold text-slate-900">{t("ideaListTitle")}</h3>
          <p className="mt-1 text-sm text-slate-500">{t("ideaListDescription")}</p>
        </div>
        <IdeaCardList
          alreadySelected={alreadySelected}
          ideas={ideaGenerator.ideas}
          onSelectIdea={(idea) => void handleSelectIdea(idea)}
          pendingIdeaId={pendingIdeaId}
          selectedIdeaIds={selectedIdeaIds}
        />
      </section>

      {alreadySelected ? (
        <section className="flex flex-col gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-emerald-900">{t("ideaSelectionNextStepTitle")}</p>
            <p className="mt-1 text-sm leading-6 text-emerald-800">{t("ideaSelectionNextStepDescription")}</p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <Link
              className={buttonClassName({ size: "sm", variant: "secondary" })}
              to={
                experimentPlannerStage
                  ? `/stages/${experimentPlannerStage.id}?quest=${currentStage.quest_id}`
                  : `/?quest=${currentStage.quest_id}`
              }
            >
              {experimentPlannerStage ? t("ideaSelectionOpenExperimentPlanner") : t("ideaSelectionOpenWorkflow")}
            </Link>
            <Link className={buttonClassName({ size: "sm", variant: "secondary" })} to={`/canvas?quest=${currentStage.quest_id}`}>
              {t("openFullCanvas")}
            </Link>
          </div>
        </section>
      ) : null}

      {submitError ? (
        <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {submitError}
        </p>
      ) : null}
      {successMessage ? (
        <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
          {successMessage}
        </p>
      ) : null}
    </div>
  );
}
