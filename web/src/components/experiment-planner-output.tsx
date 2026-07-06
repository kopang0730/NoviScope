import type { FormEvent, ReactNode } from "react";
import { useEffect, useState } from "react";
import { getErrorMessage } from "../api/client";
import { updateStage } from "../api/quests";
import type { StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import {
  buildExperimentPlannerView,
  readExperimentPlannerSetup,
} from "../lib/experiment-planner-view";
import { Badge } from "./badge";
import { Button } from "./button";
import { Input, TextArea } from "./input";
import { SourceStageList } from "./source-stage-list";

function BulletList({ emptyLabel, items }: { readonly emptyLabel: string; readonly items: readonly string[] }) {
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

function DetailBlock({
  children,
  title,
}: {
  readonly children: ReactNode;
  readonly title: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
      <div className="mt-2">{children}</div>
    </div>
  );
}

export function ExperimentSetupForm({
  onStageChange,
  stage,
}: {
  readonly onStageChange?: (stage: StageCard) => void;
  readonly stage: StageCard;
}) {
  const { t } = useI18n();
  const setup = readExperimentPlannerSetup(stage);
  const [codeRepository, setCodeRepository] = useState(setup.codeRepository);
  const [dataPath, setDataPath] = useState(setup.dataPath);
  const [environmentNotes, setEnvironmentNotes] = useState(setup.environmentNotes);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    const nextSetup = readExperimentPlannerSetup(stage);
    setCodeRepository(nextSetup.codeRepository);
    setDataPath(nextSetup.dataPath);
    setEnvironmentNotes(nextSetup.environmentNotes);
    setSaveError(null);
  }, [stage]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setSaveError(null);
    setSuccessMessage(null);

    try {
      const updatedStage = await updateStage(stage.id, {
        input_payload: {
          ...stage.input_payload,
          code_repository: codeRepository.trim(),
          data_path: dataPath.trim(),
          environment_notes: environmentNotes.trim(),
        },
      });
      onStageChange?.(updatedStage);
      setSuccessMessage(t("experimentSetupSaved"));
    } catch (error) {
      if (error instanceof Error) {
        setSaveError(getErrorMessage(error));
        return;
      }
      throw error;
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="rounded-lg border border-teal-100 bg-teal-50 p-4" onSubmit={(event) => void handleSubmit(event)}>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-teal-950">{t("experimentSetupTitle")}</p>
          <p className="mt-1 text-sm text-teal-800">{t("experimentSetupDescription")}</p>
        </div>
        <Button disabled={!onStageChange} loading={saving} size="sm" type="submit">
          {t("experimentSetupSave")}
        </Button>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Input
          hint={t("experimentDataPathHint")}
          label={t("experimentDataPath")}
          onChange={(event) => setDataPath(event.target.value)}
          placeholder="/data/project/train"
          value={dataPath}
        />
        <Input
          hint={t("experimentCodeRepositoryHint")}
          label={t("experimentCodeRepository")}
          onChange={(event) => setCodeRepository(event.target.value)}
          placeholder="https://github.com/group/baseline"
          value={codeRepository}
        />
      </div>
      <div className="mt-4">
        <TextArea
          hint={t("experimentEnvironmentNotesHint")}
          label={t("experimentEnvironmentNotes")}
          onChange={(event) => setEnvironmentNotes(event.target.value)}
          rows={3}
          value={environmentNotes}
        />
      </div>
      {saveError ? <p className="mt-3 rounded-lg border border-rose-200 bg-white px-3 py-2 text-sm text-rose-700">{saveError}</p> : null}
      {successMessage ? <p className="mt-3 rounded-lg border border-emerald-200 bg-white px-3 py-2 text-sm text-emerald-700">{successMessage}</p> : null}
    </form>
  );
}

export function ExperimentPlannerOutput({
  onStageChange,
  stage,
}: {
  readonly onStageChange?: (stage: StageCard) => void;
  readonly stage: StageCard;
}) {
  const { t } = useI18n();
  const view = buildExperimentPlannerView(stage);

  return (
    <div className="space-y-4">
      <ExperimentSetupForm onStageChange={onStageChange} stage={stage} />

      {!view ? (
        <p className="rounded-lg border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">
          {t("noExperimentPlanFound")}
        </p>
      ) : (
        <>
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="amber">{t("planOnlyNotice")}</Badge>
              <Badge tone="teal">
                {t("stageConfidence")}: {labelFromEnum(view.confidence)}
              </Badge>
              <Badge tone="blue">
                {t("dataAvailabilityStatus")}: {labelFromEnum(view.dataAvailabilityStatus || "unknown")}
              </Badge>
            </div>
            <p className="mt-3 text-sm text-amber-900">{view.summary}</p>
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
            <DetailBlock title={t("datasetsNeeded")}>
              <BulletList emptyLabel={t("notAvailable")} items={view.datasetsNeeded} />
            </DetailBlock>
            <DetailBlock title={t("baselinesToReproduce")}>
              <BulletList emptyLabel={t("notAvailable")} items={view.baselinesToReproduce} />
            </DetailBlock>
            <DetailBlock title={t("metrics")}>
              <BulletList emptyLabel={t("notAvailable")} items={view.metrics} />
            </DetailBlock>
            <DetailBlock title={t("ablationVariables")}>
              <BulletList emptyLabel={t("notAvailable")} items={view.ablationVariables} />
            </DetailBlock>
            <DetailBlock title={t("expectedTables")}>
              <BulletList emptyLabel={t("notAvailable")} items={view.expectedTables} />
            </DetailBlock>
            <DetailBlock title={t("expectedFigures")}>
              <BulletList emptyLabel={t("notAvailable")} items={view.expectedFigures} />
            </DetailBlock>
            <DetailBlock title={t("computeRequirements")}>
              <p className="text-sm text-slate-600">{view.computeRequirements || t("notAvailable")}</p>
            </DetailBlock>
            <DetailBlock title={t("failureRisks")}>
              <BulletList emptyLabel={t("notAvailable")} items={view.failureRisks} />
            </DetailBlock>
            <DetailBlock title={t("sourceStages")}>
              <SourceStageList sourceStageIds={view.sourceStageIds} />
            </DetailBlock>
          </div>

          <DetailBlock title={t("firstRunnableScriptPlan")}>
            <ol className="space-y-2 text-sm text-slate-600">
              {view.firstRunnableScriptPlan.length > 0 ? (
                view.firstRunnableScriptPlan.map((step, index) => (
                  <li className="flex gap-3" key={step}>
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-teal-100 text-xs font-semibold text-teal-700">
                      {index + 1}
                    </span>
                    <span>{step}</span>
                  </li>
                ))
              ) : (
                <li>{t("notAvailable")}</li>
              )}
            </ol>
          </DetailBlock>

          {view.warnings.length > 0 ? (
            <DetailBlock title={t("warnings")}>
              <BulletList emptyLabel={t("notAvailable")} items={view.warnings} />
            </DetailBlock>
          ) : null}
        </>
      )}
    </div>
  );
}
