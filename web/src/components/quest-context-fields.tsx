import { useState } from "react";
import { Button } from "./button";
import { TextArea } from "./input";
import { useI18n } from "../i18n/i18n-context";
import { hasAdditionalQuestContext, type QuestContextField, type QuestIntakeState } from "../lib/quest-intake";

type QuestContextFieldsProps = {
  readonly formState: QuestIntakeState;
  readonly onFieldChange: (field: QuestContextField, value: string) => void;
};

export function QuestContextFields({ formState, onFieldChange }: QuestContextFieldsProps) {
  const { t } = useI18n();
  const [expanded, setExpanded] = useState(false);
  const isOpen = expanded || hasAdditionalQuestContext(formState);

  if (!isOpen) {
    return (
      <Button onClick={() => setExpanded(true)} type="button" variant="secondary">
        {t("questAddResearchContext")}
      </Button>
    );
  }

  return (
    <div className="space-y-6 border-t border-slate-200 pt-5">
      <section aria-labelledby="quest-reality-heading" className="space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-900" id="quest-reality-heading">
            {t("questRealitySection")}
          </h3>
          <p className="mt-1 text-sm text-slate-600">{t("questRealitySectionDescription")}</p>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <TextArea
            hint={t("questScenarioHint")}
            label={t("questScenario")}
            onChange={(event) => onFieldChange("scenario", event.target.value)}
            placeholder={t("questScenarioPlaceholder")}
            rows={4}
            value={formState.scenario}
          />
          <TextArea
            hint={t("questDemandEvidenceSourcesHint")}
            label={t("questDemandEvidenceSources")}
            onChange={(event) => onFieldChange("demandEvidenceSources", event.target.value)}
            placeholder={t("questDemandEvidenceSourcesPlaceholder")}
            rows={4}
            value={formState.demandEvidenceSources}
          />
          <TextArea
            hint={t("questTargetUserHint")}
            label={t("questTargetUser")}
            onChange={(event) => onFieldChange("targetUser", event.target.value)}
            placeholder={t("questTargetUserPlaceholder")}
            rows={4}
            value={formState.targetUser}
          />
          <TextArea
            label={t("questTarget")}
            onChange={(event) => onFieldChange("target", event.target.value)}
            placeholder={t("questTargetPlaceholder")}
            rows={4}
            value={formState.target}
          />
          <TextArea
            label={t("questPainPoint")}
            onChange={(event) => onFieldChange("painPoint", event.target.value)}
            placeholder={t("questPainPointPlaceholder")}
            rows={4}
            value={formState.painPoint}
          />
          <TextArea
            hint={t("questKnownWorkHint")}
            label={t("questKnownWork")}
            onChange={(event) => onFieldChange("knownWork", event.target.value)}
            placeholder={t("questKnownWorkPlaceholder")}
            rows={4}
            value={formState.knownWork}
          />
        </div>
      </section>

      <section aria-labelledby="quest-experiment-heading" className="space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-900" id="quest-experiment-heading">
            {t("questExperimentSection")}
          </h3>
          <p className="mt-1 text-sm text-slate-600">{t("questExperimentSectionDescription")}</p>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <TextArea
            hint={t("questDataAssetsHint")}
            label={t("questDataAssets")}
            onChange={(event) => onFieldChange("dataAssets", event.target.value)}
            placeholder={t("questDataAssetsPlaceholder")}
            rows={4}
            value={formState.dataAssets}
          />
          <TextArea
            label={t("questMetric")}
            onChange={(event) => onFieldChange("metric", event.target.value)}
            placeholder={t("questMetricPlaceholder")}
            rows={4}
            value={formState.metric}
          />
          <TextArea
            label={t("questExpectedOutput")}
            onChange={(event) => onFieldChange("expectedOutput", event.target.value)}
            placeholder={t("questExpectedOutputPlaceholder")}
            rows={4}
            value={formState.expectedOutput}
          />
        </div>
      </section>
    </div>
  );
}
