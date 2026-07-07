import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { getErrorMessage } from "../api/client";
import { updateStage } from "../api/quests";
import type { StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { Badge } from "./badge";
import { Button } from "./button";
import { Select, TextArea } from "./input";

const demandReviewVerdicts = ["unverified", "plausible", "verified", "rejected"] as const;

type DemandReviewVerdict = (typeof demandReviewVerdicts)[number];

type FormState = {
  readonly notes: string;
  readonly sourcesText: string;
  readonly verdict: DemandReviewVerdict;
};

function readString(payload: Readonly<Record<string, unknown>>, key: string) {
  const value = payload[key];
  return typeof value === "string" ? value : "";
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function readStringArray(payload: Readonly<Record<string, unknown>>, key: string) {
  const value = payload[key];
  return Array.isArray(value) ? value.filter(isString) : [];
}

function parseDemandReviewVerdict(value: string): DemandReviewVerdict {
  switch (value) {
    case "plausible":
      return "plausible";
    case "verified":
      return "verified";
    case "rejected":
      return "rejected";
    case "unverified":
      return "unverified";
    default:
      return "unverified";
  }
}

function buildFormState(stage: StageCard): FormState {
  return {
    notes: readString(stage.evidence_payload, "human_demand_review_notes"),
    sourcesText: readStringArray(stage.evidence_payload, "human_demand_sources").join("\n"),
    verdict: parseDemandReviewVerdict(readString(stage.evidence_payload, "human_demand_verdict")),
  };
}

function splitSources(value: string) {
  return value
    .split(/\r?\n/)
    .map((source) => source.trim())
    .filter((source) => source.length > 0);
}

function verdictRequiresSources(verdict: DemandReviewVerdict) {
  switch (verdict) {
    case "plausible":
    case "verified":
      return true;
    case "rejected":
    case "unverified":
      return false;
  }
}

function verdictLabel(verdict: DemandReviewVerdict, t: ReturnType<typeof useI18n>["t"]) {
  switch (verdict) {
    case "plausible":
      return t("demandSourceVerdictPlausible");
    case "verified":
      return t("demandSourceVerdictVerified");
    case "rejected":
      return t("demandSourceVerdictRejected");
    case "unverified":
      return t("demandSourceVerdictUnverified");
  }
}

export function DemandSourceReviewForm({ onStageChange, stage }: {
  readonly onStageChange?: (stage: StageCard) => void;
  readonly stage: StageCard;
}) {
  const { t } = useI18n();
  const [formState, setFormState] = useState<FormState>(() => buildFormState(stage));
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const savedSources = readStringArray(stage.evidence_payload, "human_demand_sources");
  const savedNotes = readString(stage.evidence_payload, "human_demand_review_notes");
  const savedVerdict = parseDemandReviewVerdict(readString(stage.evidence_payload, "human_demand_verdict"));

  useEffect(() => {
    setFormState(buildFormState(stage));
    setSaveError(null);
  }, [stage.evidence_payload, stage.id]);

  useEffect(() => {
    setSaved(false);
  }, [stage.id]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!onStageChange) {
      return;
    }

    setSaving(true);
    setSaveError(null);
    setSaved(false);

    const sources = splitSources(formState.sourcesText);
    if (verdictRequiresSources(formState.verdict) && sources.length === 0) {
      setSaveError(t("demandSourceRequiredForPositiveVerdict"));
      setSaving(false);
      return;
    }

    try {
      const updatedStage = await updateStage(stage.id, {
        evidence_payload: {
          ...stage.evidence_payload,
          human_demand_review_notes: formState.notes.trim(),
          human_demand_reviewed_at: new Date().toISOString(),
          human_demand_sources: sources,
          human_demand_verdict: formState.verdict,
        },
      });
      onStageChange(updatedStage);
      setSaved(true);
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
    <section className="mt-3 rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-900">{t("demandSourceReviewTitle")}</p>
          <p className="mt-1 text-sm leading-6 text-slate-600">{t("demandSourceReviewDescription")}</p>
        </div>
        <Badge tone={savedVerdict === "verified" ? "green" : savedVerdict === "rejected" ? "red" : "amber"}>
          {verdictLabel(savedVerdict, t)}
        </Badge>
      </div>

      <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t("demandSourceRecordedEvidence")}
        </p>
        {savedSources.length > 0 ? (
          <ul className="mt-2 space-y-1 text-sm text-slate-600">
            {savedSources.map((source) => (
              <li className="break-words" key={source}>
                {source}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-slate-500">{t("demandSourceNoSources")}</p>
        )}
        {savedNotes ? <p className="mt-2 text-sm leading-6 text-slate-600">{savedNotes}</p> : null}
      </div>

      <form className="mt-4 space-y-4" onSubmit={(event) => void handleSubmit(event)}>
        <Select
          label={t("demandSourceVerdict")}
          onChange={(event) =>
            setFormState((current) => ({
              ...current,
              verdict: parseDemandReviewVerdict(event.target.value),
            }))
          }
          value={formState.verdict}
        >
          {demandReviewVerdicts.map((verdict) => (
            <option key={verdict} value={verdict}>
              {verdictLabel(verdict, t)}
            </option>
          ))}
        </Select>
        <TextArea
          hint={t("demandSourceListHint")}
          label={t("demandSourceList")}
          onChange={(event) => setFormState((current) => ({ ...current, sourcesText: event.target.value }))}
          placeholder={t("demandSourceListPlaceholder")}
          rows={4}
          value={formState.sourcesText}
        />
        <TextArea
          hint={t("demandSourceNotesHint")}
          label={t("demandSourceNotes")}
          onChange={(event) => setFormState((current) => ({ ...current, notes: event.target.value }))}
          placeholder={t("demandSourceNotesPlaceholder")}
          rows={4}
          value={formState.notes}
        />

        {!onStageChange ? (
          <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            {t("demandSourceReviewUnavailable")}
          </p>
        ) : null}
        {saveError ? (
          <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {saveError}
          </p>
        ) : null}
        {saved ? (
          <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            {t("demandSourceReviewSaved")}
          </p>
        ) : null}
        <Button disabled={!onStageChange} loading={saving} type="submit">
          {t("demandSourceReviewSave")}
        </Button>
      </form>
    </section>
  );
}
