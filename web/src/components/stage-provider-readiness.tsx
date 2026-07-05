import { useMemo } from "react";
import { Link } from "react-router-dom";
import type { StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import type { ProviderReadinessData } from "../lib/provider-readiness-data";
import {
  getStageProviderReadiness,
  isModelBackedStage,
  type ProviderReadiness,
  type ProviderReadinessStatus,
} from "../lib/provider-readiness";
import {
  providerReadinessLabelKey,
  providerReadinessReasonKey,
  providerReadinessSourceKey,
} from "../lib/provider-readiness-text";
import { Badge, type BadgeTone } from "./badge";
import { buttonClassName } from "./button";
import { Card, CardHeading } from "./card";

function readinessTone(status: ProviderReadinessStatus): BadgeTone {
  if (status === "blocked") {
    return "amber";
  }
  if (status === "server_managed") {
    return "blue";
  }
  if (status === "ready") {
    return "green";
  }
  return "gray";
}

function ProviderReadinessDetails({ readiness }: { readonly readiness: ProviderReadiness }) {
  const { t } = useI18n();
  return (
    <div className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
      <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t("providerReadinessProvider")}
        </p>
        <p className="mt-1 font-medium text-slate-900">
          {readiness.providerName || t("notAvailable")}
        </p>
      </div>
      <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t("providerReadinessModel")}
        </p>
        <p className="mt-1 font-medium text-slate-900">
          {readiness.modelName || t("notAvailable")}
        </p>
      </div>
      <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t("providerReadinessSource")}
        </p>
        <p className="mt-1 font-medium text-slate-900">
          {t(providerReadinessSourceKey(readiness.source))}
        </p>
      </div>
      <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t("providerReadinessRequiredKind")}
        </p>
        <p className="mt-1 font-medium text-slate-900">
          {readiness.providerKind
            ? labelFromEnum(readiness.providerKind)
            : t("providerReadinessRequiredModelKind")}
        </p>
      </div>
    </div>
  );
}

export function StageProviderReadinessCard({
  readinessData,
  stage,
}: {
  readonly readinessData: ProviderReadinessData;
  readonly stage: StageCard;
}) {
  const { t } = useI18n();
  const { assignments, error, loaded, loading, providers } = readinessData;
  const readiness = useMemo(
    () => getStageProviderReadiness(stage, providers, assignments),
    [assignments, providers, stage],
  );

  return (
    <Card>
      <CardHeading
        description={t("providerReadinessDescription")}
        title={t("providerReadinessTitle")}
      />
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Badge tone={readinessTone(readiness.status)}>
          {t(providerReadinessLabelKey(readiness.status))}
        </Badge>
        {readiness.providerKind ? (
          <Badge tone="gray">{labelFromEnum(readiness.providerKind)}</Badge>
        ) : null}
      </div>
      {loading || !loaded ? (
        <p className="mt-4 text-sm text-slate-500">{t("providerReadinessLoading")}</p>
      ) : null}
      {error ? (
        <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </p>
      ) : null}
      <p className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
        {t(providerReadinessReasonKey(readiness.reason))}
      </p>
      <div className="mt-4">
        <ProviderReadinessDetails readiness={readiness} />
      </div>
      {readiness.status === "blocked" ? (
        <div className="mt-4 flex flex-col gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 sm:flex-row sm:items-center sm:justify-between">
          <p>{t("providerReadinessConfigurePrompt")}</p>
          <Link className={buttonClassName({ size: "sm", variant: "secondary" })} to="/providers">
            {t("navProviders")}
          </Link>
        </div>
      ) : null}
    </Card>
  );
}

export function WorkflowProviderReadinessNotice({
  readinessData,
  stages,
}: {
  readonly readinessData: ProviderReadinessData;
  readonly stages: readonly StageCard[];
}) {
  const { t } = useI18n();
  const { assignments, error, loaded, loading, providers } = readinessData;
  const modelBackedStages = useMemo(() => stages.filter(isModelBackedStage), [stages]);
  const readinessByStage = useMemo(
    () =>
      modelBackedStages.map((stage) => ({
        readiness: getStageProviderReadiness(stage, providers, assignments),
        stage,
      })),
    [assignments, modelBackedStages, providers],
  );
  const blockedReadiness = readinessByStage.filter(
    ({ readiness }) => readiness.status === "blocked",
  );
  const firstReady = readinessByStage.find(({ readiness }) => readiness.status === "ready");

  if (modelBackedStages.length === 0) {
    return null;
  }

  if (loading || !loaded) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
        {t("providerReadinessLoading")}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
        {error}
      </div>
    );
  }

  if (blockedReadiness.length > 0) {
    return (
      <div className="flex flex-col gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="font-medium">{t("providerReadinessWorkflowBlockedTitle")}</p>
          <p className="mt-1">
            {t("providerReadinessWorkflowBlockedDescription")}{" "}
            {blockedReadiness.map(({ stage }) => stage.title).join(", ")}
          </p>
        </div>
        <Link className={buttonClassName({ size: "sm", variant: "secondary" })} to="/providers">
          {t("navProviders")}
        </Link>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="font-medium">{t("providerReadinessWorkflowReadyTitle")}</p>
          <p className="mt-1">
            {firstReady
              ? `${firstReady.readiness.providerName} / ${firstReady.readiness.modelName}`
              : t("providerReadinessReasonNotRequired")}
          </p>
        </div>
        <Badge tone="green">{t("providerReadinessReady")}</Badge>
      </div>
    </div>
  );
}
