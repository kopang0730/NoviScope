import { useEffect, useId, useState } from "react";
import { Link } from "react-router-dom";
import type { StageCard } from "../api/types";
import { useI18n, type TranslationKey } from "../i18n/i18n-context";
import { formatDateTime, labelFromEnum } from "../lib/format";
import { getActivePersonalProviders } from "../lib/personal-provider-overrides";
import type { ProviderReadinessData } from "../lib/provider-readiness-data";
import { isModelBackedStage } from "../lib/provider-readiness";
import {
  buildStageDetails,
  hasStageEvidence,
  isHumanGateStage,
  isImplementedStageRole,
  isOutputCapableStage,
} from "../lib/research-canvas-data";
import { readSourceStageIds } from "../lib/source-stage-ids";
import { getStageRunGate } from "../lib/stage-run-gate";
import { stageTone } from "../lib/status-tones";
import { useAsyncSelectionGuard } from "../lib/use-async-selection-guard";
import { Badge } from "./badge";
import { Button, buttonClassName } from "./button";
import { Select } from "./input";
import { SourceStageList } from "./source-stage-list";
import { StageOutputPanel } from "./stage-output-summary";
import { StageProviderReadinessCard } from "./stage-provider-readiness";
import { StageReviewGateCard } from "./stage-review-gate-card";
import { StageRunSummary } from "./stage-run-summary";

export type StageWorkbenchTabId = "overview" | "evidence" | "run" | "review" | "artifacts";

export type StageWorkbenchTabsProps = {
  readonly currentUserId: string | null;
  readonly initialTabId?: StageWorkbenchTabId;
  readonly mode: "compact" | "full";
  readonly onRunStage: (stageId: string, providerId?: string) => void;
  readonly onStageChange?: (stage: StageCard) => void;
  readonly stage: StageCard;
  readonly stages: readonly StageCard[];
  readonly providerReadinessData: ProviderReadinessData;
  readonly runningStageId: string | null;
};

type TabDefinition = {
  readonly id: StageWorkbenchTabId;
  readonly labelKey: TranslationKey;
};

const tabDefinitions: readonly TabDefinition[] = [
  { id: "overview", labelKey: "stageWorkbenchOverview" },
  { id: "evidence", labelKey: "stageWorkbenchEvidence" },
  { id: "run", labelKey: "stageWorkbenchRun" },
  { id: "review", labelKey: "stageWorkbenchReview" },
  { id: "artifacts", labelKey: "stageWorkbenchArtifacts" },
];

function isTabAvailable(tabId: StageWorkbenchTabId, stage: StageCard) {
  switch (tabId) {
    case "overview":
      return true;
    case "evidence":
      return isImplementedStageRole(stage) || hasStageEvidence(stage);
    case "run":
      return isImplementedStageRole(stage);
    case "review":
      return isHumanGateStage(stage);
    case "artifacts":
      return isOutputCapableStage(stage);
  }
}

function AdvancedPayloads({ stage }: { readonly stage: StageCard }) {
  const { t } = useI18n();
  return (
    <details className="mt-4 rounded-lg border border-slate-200 bg-white">
      <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-slate-800">
        {t("stageWorkbenchAdvanced")}
      </summary>
      <div className="grid gap-4 border-t border-slate-200 p-4 xl:grid-cols-3">
        {[
          [t("stageInputPayload"), stage.input_payload],
          [t("stageOutputPayload"), stage.output_payload],
          [t("stageEvidencePayload"), stage.evidence_payload],
        ].map(([label, payload]) => (
          <div className="min-w-0" key={String(label)}>
            <p className="text-xs font-semibold text-slate-500">{String(label)}</p>
            <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-3 text-xs leading-5 text-slate-100">
              {JSON.stringify(payload, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    </details>
  );
}

export function StageWorkbenchTabs({
  currentUserId,
  initialTabId = "overview",
  mode,
  onRunStage,
  onStageChange,
  providerReadinessData,
  runningStageId,
  stage,
  stages,
}: StageWorkbenchTabsProps) {
  const { t } = useI18n();
  const instanceId = useId();
  const [activeTabId, setActiveTabId] = useState<StageWorkbenchTabId>(() =>
    isTabAvailable(initialTabId, stage) ? initialTabId : "overview",
  );
  const [currentStage, setCurrentStage] = useState(stage);
  const [selectedProviderId, setSelectedProviderId] = useState("");
  const isCurrentStage = useAsyncSelectionGuard(stage.id);
  const availableTabs = tabDefinitions.filter((tab) => isTabAvailable(tab.id, currentStage));
  const sourceStageIds = readSourceStageIds(currentStage.output_payload);
  const stageRunGate = getStageRunGate({
    providerReadinessData,
    stage: currentStage,
    stages,
  });
  const overrideProviders = getActivePersonalProviders(
    providerReadinessData.providers,
    currentUserId,
  );
  const selectedOverrideReady = overrideProviders.some(
    (provider) => provider.id === selectedProviderId,
  );
  const selectedOverrideCanRun =
    stageRunGate.workflowReadiness.canRun
    && providerReadinessData.loaded
    && !providerReadinessData.loading
    && !providerReadinessData.error
    && selectedOverrideReady;
  const canRun = selectedProviderId ? selectedOverrideCanRun : stageRunGate.canRun;
  const isRunning = runningStageId === currentStage.id;

  useEffect(() => {
    setCurrentStage(stage);
  }, [stage]);

  useEffect(() => {
    setActiveTabId(isTabAvailable(initialTabId, stage) ? initialTabId : "overview");
    setSelectedProviderId("");
  }, [initialTabId, stage]);

  function handleStageChange(nextStage: StageCard) {
    if (!isCurrentStage() || nextStage.id !== stage.id) {
      return;
    }
    setCurrentStage(nextStage);
    onStageChange?.(nextStage);
  }

  function renderPanel() {
    switch (activeTabId) {
      case "overview":
        return (
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <h3 className="text-base font-semibold text-slate-950">{currentStage.title}</h3>
                <p className="mt-1 break-all text-xs text-slate-500">{currentStage.agent_id}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge tone={stageTone(currentStage.status)}>{labelFromEnum(currentStage.status)}</Badge>
                <Badge tone="gray">{labelFromEnum(currentStage.confidence)}</Badge>
              </div>
            </div>
            <StageRunSummary stage={currentStage} stageRunGate={stageRunGate} />
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4">
              <p className="text-xs text-slate-500">{t("updated")} {formatDateTime(currentStage.updated_at)}</p>
              {mode === "compact" ? (
                <Link className={buttonClassName({ size: "sm", variant: "secondary" })} to={`/stages/${currentStage.id}?quest=${currentStage.quest_id}`}>
                  {t("stageWorkbenchOpenDetail")}
                </Link>
              ) : null}
            </div>
          </section>
        );
      case "evidence": {
        const details = buildStageDetails(currentStage, t);
        return (
          <section className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <p className="text-sm text-slate-600">{t("stageWorkbenchEvidenceDescription")}</p>
            {details.length > 0 ? (
              <dl className="mt-4 grid gap-3 sm:grid-cols-2">
                {details.map((detail) => (
                  <div className="rounded-lg border border-slate-200 bg-white px-3 py-2" key={`${currentStage.id}-${detail.label}`}>
                    <dt className="text-xs font-semibold text-slate-500">{detail.label}</dt>
                    <dd className="mt-1 text-sm text-slate-800">{detail.value}</dd>
                  </div>
                ))}
              </dl>
            ) : null}
            {Object.keys(sourceStageIds).length > 0 ? (
              <div className="mt-4 rounded-lg border border-slate-200 bg-white p-3">
                <SourceStageList sourceStageIds={sourceStageIds} />
              </div>
            ) : null}
            <AdvancedPayloads stage={currentStage} />
          </section>
        );
      }
      case "run":
        return (
          <div className="space-y-4">
            <StageProviderReadinessCard readinessData={providerReadinessData} stage={currentStage} />
            <section className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:flex-row sm:items-end sm:justify-between">
              {isModelBackedStage(currentStage) ? (
                <div className="w-full sm:max-w-sm">
                  <Select label={t("workflowActionProviderOverride")} onChange={(event) => setSelectedProviderId(event.target.value)} value={selectedProviderId}>
                    <option value="">{t("workflowActionProviderDefault")}</option>
                    {overrideProviders.map((provider) => <option key={provider.id} value={provider.id}>{provider.name}</option>)}
                  </Select>
                </div>
              ) : <p className="text-sm text-slate-600">{t("providerReadinessReasonServerManaged")}</p>}
              <Button
                disabled={!canRun || isRunning}
                loading={isRunning}
                onClick={() => onRunStage(currentStage.id, selectedProviderId || undefined)}
              >
                {t("stageWorkbenchRunAction")}
              </Button>
            </section>
          </div>
        );
      case "review":
        return mode === "full" ? (
          <StageReviewGateCard onStageChange={handleStageChange} stage={currentStage} />
        ) : (
          <section className="rounded-lg border border-amber-200 bg-amber-50 p-4">
            <p className="text-sm text-amber-900">{t("stageWorkbenchReviewCompact")}</p>
            <Link className={buttonClassName({ className: "mt-3", size: "sm", variant: "secondary" })} to={`/stages/${currentStage.id}?quest=${currentStage.quest_id}`}>
              {t("stageWorkbenchOpenDetail")}
            </Link>
          </section>
        );
      case "artifacts":
        return mode === "full" ? (
          <StageOutputPanel
            onStageChange={handleStageChange}
            stage={currentStage}
            stageRunGate={stageRunGate}
            workflowStages={stages}
          />
        ) : (
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <StageRunSummary stage={currentStage} stageRunGate={stageRunGate} />
            <Link
              className={buttonClassName({ className: "mt-3", size: "sm", variant: "secondary" })}
              to={`/stages/${currentStage.id}?quest=${currentStage.quest_id}`}
            >
              {t("stageWorkbenchOpenDetail")}
            </Link>
          </section>
        );
    }
  }

  return (
    <div className="min-w-0">
      <div aria-label={t("stageWorkbenchTabsLabel")} className="grid auto-cols-fr grid-flow-col gap-1 border-b border-slate-200" role="tablist">
        {availableTabs.map((tab) => (
          <button
            aria-controls={`${instanceId}-${tab.id}-panel`}
            aria-selected={activeTabId === tab.id}
            className={[
              "min-h-11 min-w-0 border-b-2 px-1 text-center text-xs font-semibold sm:px-3 sm:text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500",
              activeTabId === tab.id ? "border-teal-600 bg-teal-50 text-teal-900" : "border-transparent text-slate-600 hover:text-slate-900",
            ].join(" ")}
            id={`${instanceId}-${tab.id}-tab`}
            key={tab.id}
            onClick={() => setActiveTabId(tab.id)}
            role="tab"
            type="button"
          >
            {t(tab.labelKey)}
          </button>
        ))}
      </div>
      <div aria-labelledby={`${instanceId}-${activeTabId}-tab`} className="pt-4" id={`${instanceId}-${activeTabId}-panel`} role="tabpanel">
        {renderPanel()}
      </div>
    </div>
  );
}
