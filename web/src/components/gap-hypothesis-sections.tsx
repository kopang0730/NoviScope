import type { ReactNode } from "react";
import { useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import { confidenceTone } from "../lib/gap-hypothesis-tones";
import type { IdeaGeneratorView, IdeaItem } from "../lib/gap-hypothesis-view";
import { Badge } from "./badge";
import { Button } from "./button";
import { SourceStageList } from "./source-stage-list";

function SupportingPaperList({ items }: { readonly items: readonly string[] }) {
  const { t } = useI18n();

  if (items.length === 0) {
    return <p className="text-sm text-slate-500">{t("notAvailable")}</p>;
  }

  return (
    <ul className="space-y-1 text-sm text-slate-600">
      {items.map((item) => (
        <li className="flex gap-2" key={item}>
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-300" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function IdeaField({
  children,
  title,
}: {
  readonly children: ReactNode;
  readonly title: string;
}) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
      <div className="mt-1">{children}</div>
    </div>
  );
}

export function GapSummarySection({ view }: { readonly view: IdeaGeneratorView }) {
  const { t } = useI18n();
  const alreadySelected = view.selectionStatus === "selected_for_experiment_design";

  return (
    <div className="grid gap-3 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t("ideaGeneratorSummary")}
        </p>
        <p className="mt-2 text-sm text-slate-700">{view.summary || t("noSummaryYet")}</p>
      </div>
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t("ideaSelectionGate")}
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          <Badge tone={confidenceTone(view.confidence)}>
            {t("stageConfidence")}: {labelFromEnum(view.confidence)}
          </Badge>
          <Badge tone={alreadySelected ? "green" : "amber"}>
            {t("selectionStatus")}: {labelFromEnum(view.selectionStatus)}
          </Badge>
        </div>
        {Object.keys(view.sourceStageIds).length > 0 ? (
          <div className="mt-3">
            <p className="font-semibold uppercase tracking-wide text-slate-500">
              {t("sourceStages")}
            </p>
            <div className="mt-2">
              <SourceStageList sourceStageIds={view.sourceStageIds} />
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function IdeaCardList({
  alreadySelected,
  ideas,
  onSelectIdea,
  pendingIdeaId,
  selectedIdeaIds,
}: {
  readonly alreadySelected: boolean;
  readonly ideas: readonly IdeaItem[];
  readonly onSelectIdea: (idea: IdeaItem) => void;
  readonly pendingIdeaId: string | null;
  readonly selectedIdeaIds: ReadonlySet<string>;
}) {
  const { t } = useI18n();

  if (ideas.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
        {t("noIdeasFound")}
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {ideas.map((idea) => (
        <IdeaCard
          alreadySelected={alreadySelected}
          idea={idea}
          isSelected={selectedIdeaIds.has(idea.ideaId)}
          key={idea.ideaId || idea.ideaTitle}
          onSelectIdea={onSelectIdea}
          pendingIdeaId={pendingIdeaId}
        />
      ))}
    </div>
  );
}

function IdeaCard({
  alreadySelected,
  idea,
  isSelected,
  onSelectIdea,
  pendingIdeaId,
}: {
  readonly alreadySelected: boolean;
  readonly idea: IdeaItem;
  readonly isSelected: boolean;
  readonly onSelectIdea: (idea: IdeaItem) => void;
  readonly pendingIdeaId: string | null;
}) {
  const { t } = useI18n();
  const buttonDisabled = alreadySelected || isSelected;
  const buttonText = isSelected ? t("ideaAlreadySelected") : t("selectIdeaUnavailable");

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-base font-semibold text-slate-900">
              {idea.ideaTitle || t("notAvailable")}
            </h4>
            {isSelected ? <Badge tone="green">{t("selectedIdeaBadge")}</Badge> : null}
          </div>
          <p className="mt-2 text-sm text-slate-600">
            {idea.coreHypothesis || t("notAvailable")}
          </p>
        </div>
        <Button
          disabled={buttonDisabled}
          loading={pendingIdeaId === idea.ideaId}
          onClick={() => onSelectIdea(idea)}
          size="sm"
        >
          {buttonDisabled ? buttonText : t("selectIdeaForExperiment")}
        </Button>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <IdeaField title={t("basedOnPapers")}>
          <SupportingPaperList items={idea.basedOnWhichPapers} />
        </IdeaField>
        <IdeaField title={t("expectedImprovement")}>
          <p className="text-sm text-slate-600">
            {idea.expectedImprovement || t("notAvailable")}
          </p>
        </IdeaField>
        <IdeaField title={t("requiredData")}>
          <p className="text-sm text-slate-600">{idea.requiredData || t("notAvailable")}</p>
        </IdeaField>
        <IdeaField title={t("requiredBaseline")}>
          <p className="text-sm text-slate-600">
            {idea.requiredBaseline || t("notAvailable")}
          </p>
        </IdeaField>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Badge tone={confidenceTone(idea.experimentFeasibility)}>
          {t("experimentFeasibility")}: {labelFromEnum(idea.experimentFeasibility)}
        </Badge>
        <Badge tone={confidenceTone(idea.noveltyRisk)}>
          {t("noveltyRisk")}: {labelFromEnum(idea.noveltyRisk)}
        </Badge>
        <Badge tone={confidenceTone(idea.applicationValue)}>
          {t("applicationValue")}: {labelFromEnum(idea.applicationValue)}
        </Badge>
        <Badge tone={confidenceTone(idea.confidence)}>
          {t("stageConfidence")}: {labelFromEnum(idea.confidence)}
        </Badge>
      </div>
    </section>
  );
}
