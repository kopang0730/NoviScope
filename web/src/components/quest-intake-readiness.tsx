import type { TranslationKey } from "../i18n/i18n-context";
import { useI18n } from "../i18n/i18n-context";
import type { QuestIntakeState } from "../lib/quest-intake";
import { Badge, type BadgeTone } from "./badge";

type IntakeField = {
  readonly key: keyof QuestIntakeState;
  readonly labelKey: TranslationKey;
};

type ReadinessSection = {
  readonly descriptionKey: TranslationKey;
  readonly fields: readonly IntakeField[];
  readonly titleKey: TranslationKey;
};

const readinessSections = [
  {
    descriptionKey: "questReadinessDemandDescription",
    fields: [
      { key: "scenario", labelKey: "questScenario" },
      { key: "demandEvidenceSources", labelKey: "questDemandEvidenceSources" },
      { key: "targetUser", labelKey: "questTargetUser" },
    ],
    titleKey: "questReadinessDemandTitle",
  },
  {
    descriptionKey: "questReadinessScopeDescription",
    fields: [
      { key: "direction", labelKey: "questDirection" },
      { key: "target", labelKey: "questTarget" },
      { key: "painPoint", labelKey: "questPainPoint" },
    ],
    titleKey: "questReadinessScopeTitle",
  },
  {
    descriptionKey: "questReadinessPriorWorkDescription",
    fields: [{ key: "knownWork", labelKey: "questKnownWork" }],
    titleKey: "questReadinessPriorWorkTitle",
  },
  {
    descriptionKey: "questReadinessExperimentDescription",
    fields: [
      { key: "dataAssets", labelKey: "questDataAssets" },
      { key: "metric", labelKey: "questMetric" },
      { key: "expectedOutput", labelKey: "questExpectedOutput" },
    ],
    titleKey: "questReadinessExperimentTitle",
  },
] as const satisfies readonly ReadinessSection[];

function hasValue(value: string) {
  return value.trim().length > 0;
}

function missingFields(section: ReadinessSection, formState: QuestIntakeState) {
  return section.fields.filter((field) => !hasValue(formState[field.key]));
}

function sectionTone(isCovered: boolean): BadgeTone {
  return isCovered ? "green" : "amber";
}

export function QuestIntakeReadiness({ formState }: { readonly formState: QuestIntakeState }) {
  const { t } = useI18n();
  const coveredCount = readinessSections.filter((section) => missingFields(section, formState).length === 0).length;
  const isReadyForFirstPass = coveredCount >= 3 && hasValue(formState.scenario) && hasValue(formState.demandEvidenceSources);

  return (
    <section className="mt-5 rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">{t("questReadinessTitle")}</h3>
          <p className="mt-1 text-sm leading-6 text-slate-600">{t("questReadinessDescription")}</p>
        </div>
        <Badge tone={isReadyForFirstPass ? "green" : "amber"}>
          {isReadyForFirstPass ? t("questReadinessReady") : t("questReadinessNeedsContext")}
        </Badge>
      </div>

      <p className="mt-3 text-xs font-medium text-slate-500">
        {coveredCount}/{readinessSections.length} {t("questReadinessSectionsCovered")}
      </p>

      <div className="mt-3 grid gap-2">
        {readinessSections.map((section) => {
          const missing = missingFields(section, formState);
          const isCovered = missing.length === 0;

          return (
            <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2" key={section.titleKey}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs font-semibold text-slate-900">{t(section.titleKey)}</p>
                <Badge tone={sectionTone(isCovered)}>
                  {isCovered ? t("questReadinessCovered") : t("questReadinessMissing")}
                </Badge>
              </div>
              <p className="mt-1 text-xs leading-5 text-slate-600">{t(section.descriptionKey)}</p>
              {!isCovered ? (
                <p className="mt-2 text-xs leading-5 text-amber-800">
                  {t("questReadinessMissingFields")}: {missing.map((field) => t(field.labelKey)).join(", ")}
                </p>
              ) : null}
            </div>
          );
        })}
      </div>

      <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">
        {t("questReadinessHumanGateNote")}
      </p>
    </section>
  );
}
