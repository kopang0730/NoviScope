import { useEffect, useId, useState } from "react";
import type { Provider, WorkflowAgentCapability, WorkflowNextAction } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { supportsWorkflowProviderOverride } from "../lib/workflow-action-provider";
import { buildWorkflowActionView } from "../lib/workflow-action-view";
import { Badge } from "./badge";
import { Button } from "./button";
import { Card } from "./card";
import { Select } from "./input";

export type StageNextActionCardProps = {
  readonly action: WorkflowNextAction | null;
  readonly capabilities: readonly WorkflowAgentCapability[];
  readonly onNavigate: (path: string) => void;
  readonly onRun: (stageId: string, providerId?: string) => void;
  readonly providers: readonly Provider[];
  readonly questId: string;
  readonly runningStageId: string | null;
};

function unsupportedActionType(actionType: never): never {
  throw new TypeError(`Unsupported workflow action type: ${actionType}`);
}

export function StageNextActionCard({
  action,
  capabilities,
  onNavigate,
  onRun,
  providers,
  questId,
  runningStageId,
}: StageNextActionCardProps) {
  const { language, t } = useI18n();
  const headingId = useId();
  const [selectedProviderId, setSelectedProviderId] = useState("");

  useEffect(() => {
    setSelectedProviderId("");
  }, [action?.stage_id]);

  if (!action) {
    return (
      <Card aria-labelledby={headingId} className="bg-slate-50">
        <h2 className="text-sm font-semibold text-slate-900" id={headingId}>
          {t("canvasNextAction")}
        </h2>
        <p className="mt-2 text-sm text-slate-600">{t("workflowActionNoPending")}</p>
      </Card>
    );
  }

  const view = buildWorkflowActionView(action, language);
  const stagePath = `/stages/${action.stage_id}?quest=${questId}`;
  const activeProviders = providers.filter((provider) => provider.is_active);
  const supportsProviderOverride = supportsWorkflowProviderOverride(action, capabilities);

  const primaryCommand = (() => {
    switch (action.action_type) {
      case "configure_provider":
        return (
          <Button onClick={() => onNavigate("/providers")}>
            {t("workflowActionConfigureProvider")}
          </Button>
        );
      case "resolve_blocker":
        return (
          <Button onClick={() => onNavigate(stagePath)}>
            {t("workflowActionResolveBlocker")}
          </Button>
        );
      case "review_stage":
        return (
          <Button onClick={() => onNavigate(stagePath)}>
            {t("workflowActionReviewStage")}
          </Button>
        );
      case "run_stage":
        return (
          <Button
            disabled={view.disabled}
            loading={runningStageId === action.stage_id}
            onClick={() => onRun(action.stage_id, selectedProviderId || undefined)}
          >
            {t("workflowActionRunStage")}
          </Button>
        );
      case "wait_for_stage":
        return <Button disabled>{t("workflowActionWaitForStage")}</Button>;
      default:
        return unsupportedActionType(action.action_type);
    }
  })();

  return (
    <Card aria-labelledby={headingId} className="border-teal-200 bg-teal-50/50">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-sm font-semibold text-slate-900" id={headingId}>
              {t("canvasNextAction")}
            </h2>
            <Badge tone="teal">{t("workflowActionTrustSummary")}</Badge>
          </div>
          <p className="mt-2 break-words text-base font-semibold text-slate-950">{view.title}</p>
          <p className="mt-1 break-words text-sm leading-6 text-slate-600">{view.reason}</p>
          <p className="mt-2 break-words text-xs font-medium text-slate-500">{view.responsible}</p>
        </div>

        <div className="flex w-full shrink-0 flex-col gap-3 xl:w-auto xl:min-w-[280px]">
          {supportsProviderOverride ? (
            <Select
              className="min-h-11"
              label={t("workflowActionProviderOverride")}
              onChange={(event) => setSelectedProviderId(event.target.value)}
              value={selectedProviderId}
            >
              <option value="">{t("workflowActionProviderDefault")}</option>
              {activeProviders.map((provider) => (
                <option key={provider.id} value={provider.id}>
                  {provider.name} · {provider.scope === "personal"
                    ? t("workflowActionProviderPersonal")
                    : t("workflowActionProviderShared")}
                </option>
              ))}
            </Select>
          ) : null}

          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:justify-end">
            {primaryCommand}
            <Button
              onClick={() => onNavigate(`${stagePath}#evidence`)}
              variant="secondary"
            >
              {t("workflowActionViewDetail")}
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}
