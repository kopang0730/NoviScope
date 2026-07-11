import { useEffect, useId, useState } from "react";
import { Link } from "react-router-dom";
import type {
  Provider,
  WorkflowAgentCapability,
  WorkflowNextAction,
} from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { getActivePersonalProviders } from "../lib/personal-provider-overrides";
import { supportsWorkflowProviderOverride } from "../lib/workflow-action-provider";
import {
  buildWorkflowActionView,
  workflowActionStagePath,
} from "../lib/workflow-action-view";
import { Badge } from "./badge";
import { Button, buttonClassName } from "./button";
import { Select } from "./input";

type QuestNextActionStripProps = {
  readonly actions: readonly WorkflowNextAction[];
  readonly capabilities: readonly WorkflowAgentCapability[];
  readonly currentUserId: string | null;
  readonly onRun: (stageId: string, providerId?: string) => void;
  readonly providers: readonly Provider[];
  readonly questId: string;
  readonly runningStageId: string | null;
};

export function QuestNextActionStrip({
  actions,
  capabilities,
  currentUserId,
  onRun,
  providers,
  questId,
  runningStageId,
}: QuestNextActionStripProps) {
  const { language, t } = useI18n();
  const headingId = useId();
  const action = actions[0] ?? null;
  const [selectedProviderId, setSelectedProviderId] = useState("");

  useEffect(() => {
    setSelectedProviderId("");
  }, [action?.stage_id]);

  if (!action) {
    return (
      <section
        aria-labelledby={headingId}
        className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-4 sm:px-5"
      >
        <h2 className="text-sm font-semibold text-slate-900" id={headingId}>
          {t("canvasNextAction")}
        </h2>
        <p className="mt-2 text-sm text-slate-600">{t("workflowActionNoPending")}</p>
      </section>
    );
  }

  const view = buildWorkflowActionView(action, language);
  const stagePath = `/stages/${action.stage_id}?quest=${questId}`;
  const primaryStagePath = workflowActionStagePath(action, questId);
  const supportsProviderOverride = supportsWorkflowProviderOverride(action, capabilities);
  const overrideProviders = getActivePersonalProviders(providers, currentUserId);

  const primaryCommand = (() => {
    switch (view.command) {
      case "open_providers":
        return (
          <Link
            className={buttonClassName({ className: "min-h-11", variant: "primary" })}
            to="/providers"
          >
            {t("workflowActionConfigureProvider")}
          </Link>
        );
      case "open_stage":
        return (
          <Link
            className={buttonClassName({ className: "min-h-11", variant: "primary" })}
            to={primaryStagePath}
          >
            {action.action_type === "review_stage"
              ? t("workflowActionReviewStage")
              : t("workflowActionResolveBlocker")}
          </Link>
        );
      case "run":
        return (
          <Button
            className="min-h-11"
            disabled={view.disabled}
            loading={runningStageId === action.stage_id}
            onClick={() => onRun(action.stage_id, selectedProviderId || undefined)}
          >
            {t("workflowActionRunStage")}
          </Button>
        );
      case "wait":
        return (
          <Button className="min-h-11" disabled>
            {t("workflowActionWaitForStage")}
          </Button>
        );
    }
  })();

  return (
    <section
      aria-labelledby={headingId}
      className="sticky top-3 z-10 rounded-lg border border-teal-200 bg-white px-4 py-4 shadow-panel sm:px-5 lg:static"
      id="quest-next-action"
    >
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
            <div className="order-2 xl:order-1">
              <Select
                className="min-h-11"
                label={t("workflowActionProviderOverride")}
                onChange={(event) => setSelectedProviderId(event.target.value)}
                value={selectedProviderId}
              >
                <option value="">{t("workflowActionProviderDefault")}</option>
                {overrideProviders.map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {provider.name} · {t("workflowActionProviderPersonal")}
                  </option>
                ))}
              </Select>
            </div>
          ) : null}

          <div className="order-1 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:justify-end xl:order-2">
            {primaryCommand}
            <Link
              className={buttonClassName({ className: "min-h-11", variant: "secondary" })}
              to={`${stagePath}#evidence`}
            >
              {t("workflowActionViewDetail")}
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
