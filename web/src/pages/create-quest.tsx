import type { FormEvent } from "react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createQuest } from "../api/quests";
import { getErrorMessage } from "../api/client";
import { useAuth } from "../auth/auth-context";
import { Button } from "../components/button";
import { Card, CardHeading } from "../components/card";
import { Input, Select, TextArea } from "../components/input";
import { QuestIntakeReadiness } from "../components/quest-intake-readiness";
import { useI18n } from "../i18n/i18n-context";
import {
  buildInitialDirection,
  emptyIntake,
  isOutputLanguage,
  questIntakeExamples,
  type QuestIntakeState,
} from "../lib/quest-intake";

export function CreateQuestPage() {
  const navigate = useNavigate();
  const { currentUser } = useAuth();
  const { language, t } = useI18n();
  const [formState, setFormState] = useState<QuestIntakeState>(emptyIntake);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const preview = useMemo(() => buildInitialDirection(formState, language), [formState, language]);

  function updateField<Key extends keyof QuestIntakeState>(key: Key, value: QuestIntakeState[Key]) {
    setFormState((current) => ({ ...current, [key]: value }));
  }

  function updateOutputLanguage(value: string) {
    if (isOutputLanguage(value)) {
      updateField("outputLanguage", value);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const quest = await createQuest({
        initial_direction: preview,
        title: formState.title,
      });
      navigate(`/?quest=${quest.id}`, { replace: true });
    } catch (submitError) {
      if (submitError instanceof Error) {
        setError(getErrorMessage(submitError));
      } else {
        throw submitError;
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
      <Card>
        <CardHeading description={t("questFormDescription")} title={t("navNewQuest")} />
        {!currentUser ? (
          <p className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
            {t("signInFirstQuest")}
          </p>
        ) : null}

        <div className="mt-5 flex flex-wrap gap-2">
          <Button onClick={() => setFormState(questIntakeExamples[language].erasure)} size="sm" type="button" variant="secondary">
            {t("questExampleErasure")}
          </Button>
          <Button onClick={() => setFormState(questIntakeExamples[language].badminton)} size="sm" type="button" variant="secondary">
            {t("questExampleBadminton")}
          </Button>
        </div>

        <QuestIntakeReadiness formState={formState} />

        <form className="mt-6 space-y-6" onSubmit={(event) => void handleSubmit(event)}>
          <section className="grid gap-4 lg:grid-cols-2">
            <Input
              label={t("questTitle")}
              onChange={(event) => updateField("title", event.target.value)}
              placeholder={t("questTitlePlaceholder")}
              required
              value={formState.title}
            />
            <Select
              label={t("questOutputLanguage")}
              onChange={(event) => updateOutputLanguage(event.target.value)}
              value={formState.outputLanguage}
            >
              <option value="both">{t("questOutputLanguageBoth")}</option>
              <option value="zh">{t("questOutputLanguageZh")}</option>
              <option value="en">{t("questOutputLanguageEn")}</option>
            </Select>
            <TextArea
              hint={t("questDirectionHint")}
              label={t("questDirection")}
              onChange={(event) => updateField("direction", event.target.value)}
              placeholder={t("questDirectionPlaceholder")}
              required
              rows={5}
              value={formState.direction}
            />
          </section>

          <section className="space-y-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">{t("questRealitySection")}</h3>
              <p className="mt-1 text-sm text-slate-600">{t("questRealitySectionDescription")}</p>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <TextArea
                hint={t("questScenarioHint")}
                label={t("questScenario")}
                onChange={(event) => updateField("scenario", event.target.value)}
                placeholder={t("questScenarioPlaceholder")}
                rows={4}
                value={formState.scenario}
              />
              <TextArea
                hint={t("questDemandEvidenceSourcesHint")}
                label={t("questDemandEvidenceSources")}
                onChange={(event) => updateField("demandEvidenceSources", event.target.value)}
                placeholder={t("questDemandEvidenceSourcesPlaceholder")}
                rows={4}
                value={formState.demandEvidenceSources}
              />
              <TextArea
                hint={t("questTargetUserHint")}
                label={t("questTargetUser")}
                onChange={(event) => updateField("targetUser", event.target.value)}
                placeholder={t("questTargetUserPlaceholder")}
                rows={4}
                value={formState.targetUser}
              />
              <TextArea
                label={t("questTarget")}
                onChange={(event) => updateField("target", event.target.value)}
                placeholder={t("questTargetPlaceholder")}
                rows={4}
                value={formState.target}
              />
              <TextArea
                label={t("questPainPoint")}
                onChange={(event) => updateField("painPoint", event.target.value)}
                placeholder={t("questPainPointPlaceholder")}
                rows={4}
                value={formState.painPoint}
              />
              <TextArea
                hint={t("questKnownWorkHint")}
                label={t("questKnownWork")}
                onChange={(event) => updateField("knownWork", event.target.value)}
                placeholder={t("questKnownWorkPlaceholder")}
                rows={4}
                value={formState.knownWork}
              />
            </div>
          </section>

          <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">{t("questExperimentSection")}</h3>
              <p className="mt-1 text-sm text-slate-600">{t("questExperimentSectionDescription")}</p>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <TextArea
                hint={t("questDataAssetsHint")}
                label={t("questDataAssets")}
                onChange={(event) => updateField("dataAssets", event.target.value)}
                placeholder={t("questDataAssetsPlaceholder")}
                rows={4}
                value={formState.dataAssets}
              />
              <TextArea
                label={t("questMetric")}
                onChange={(event) => updateField("metric", event.target.value)}
                placeholder={t("questMetricPlaceholder")}
                rows={4}
                value={formState.metric}
              />
              <TextArea
                label={t("questExpectedOutput")}
                onChange={(event) => updateField("expectedOutput", event.target.value)}
                placeholder={t("questExpectedOutputPlaceholder")}
                rows={4}
                value={formState.expectedOutput}
              />
            </div>
          </section>

          {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-slate-500">{t("questSubmitHint")}</p>
            <Button loading={submitting} type="submit">
              {t("questCreate")}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardHeading description={t("questSubmitHint")} title={t("initialDirectionPreview")} />
        <pre className="mt-4 max-h-[760px] overflow-auto whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-950 p-4 text-xs leading-6 text-slate-100">
          {preview}
        </pre>
      </Card>
    </div>
  );
}
