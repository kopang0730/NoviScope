import type { FormEvent } from "react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createQuest } from "../api/quests";
import { getErrorMessage } from "../api/client";
import { useAuth } from "../auth/auth-context";
import { Button } from "../components/button";
import { Card, CardHeading } from "../components/card";
import { Input, Select, TextArea } from "../components/input";
import { QuestContextFields } from "../components/quest-context-fields";
import { useI18n } from "../i18n/i18n-context";
import {
  buildInitialDirection,
  deriveQuestTitle,
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
        initial_direction: buildInitialDirection(formState, language),
        title: deriveQuestTitle(formState, language),
      });
      navigate(`/canvas?quest=${quest.id}`, { replace: true });
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

        <form className="mt-6 space-y-5" onSubmit={(event) => void handleSubmit(event)}>
          <section className="grid gap-4 lg:grid-cols-2">
            <TextArea
              className="lg:col-span-2"
              hint={t("questDirectionHint")}
              label={t("questDirection")}
              onChange={(event) => updateField("direction", event.target.value)}
              placeholder={t("questDirectionPlaceholder")}
              required
              rows={4}
              value={formState.direction}
            />
            <Input
              hint={t("questTitleOptionalHint")}
              label={t("questTitle")}
              maxLength={80}
              onChange={(event) => updateField("title", event.target.value)}
              placeholder={t("questTitlePlaceholder")}
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
          </section>

          <div className="flex flex-wrap gap-2">
            <Button onClick={() => setFormState(questIntakeExamples[language].erasure)} size="sm" type="button" variant="secondary">
              {t("questExampleErasure")}
            </Button>
            <Button onClick={() => setFormState(questIntakeExamples[language].badminton)} size="sm" type="button" variant="secondary">
              {t("questExampleBadminton")}
            </Button>
          </div>

          <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900" role="note">
            {t("questDemandReviewNotice")}
          </p>

          <QuestContextFields formState={formState} onFieldChange={updateField} />

          {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-slate-500">{t("questSubmitHint")}</p>
            <Button loading={submitting} type="submit">
              {t("questCreate")}
            </Button>
          </div>
        </form>
      </Card>

      <aside className="hidden h-fit min-w-0 rounded-lg border border-slate-200 bg-white p-5 shadow-panel xl:sticky xl:top-4 xl:block xl:p-6">
        <h2 className="text-lg font-semibold text-slate-900">{t("initialDirectionPreview")}</h2>
        <p className="mt-1 text-sm text-slate-500">{t("questSubmitHint")}</p>
        <pre className="mt-4 max-h-[760px] overflow-auto whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-950 p-4 text-xs leading-6 text-slate-100">
          {preview}
        </pre>
      </aside>
      <details className="rounded-lg border border-slate-200 bg-white p-5 shadow-panel xl:hidden">
        <summary className="cursor-pointer text-sm font-semibold text-slate-900">{t("initialDirectionPreview")}</summary>
        <pre className="mt-4 max-h-[420px] overflow-auto whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-950 p-4 text-xs leading-6 text-slate-100">
          {preview}
        </pre>
      </details>
    </div>
  );
}
