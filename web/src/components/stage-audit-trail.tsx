import { useEffect, useState } from "react";
import { getErrorMessage } from "../api/client";
import { getStageDisplayOutput } from "../api/quests";
import type { StageCard } from "../api/types";
import type { StageDisplayOutputResponse } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import { Badge } from "./badge";

function fieldCount(payload: Readonly<Record<string, unknown>>) {
  return Object.keys(payload).length;
}

function readString(payload: Readonly<Record<string, unknown>>, key: string) {
  const value = payload[key];
  return typeof value === "string" ? value.trim() : "";
}

function JsonPayloadBlock({
  label,
  payload,
}: {
  readonly label: string;
  readonly payload: Readonly<Record<string, unknown>>;
}) {
  const { t } = useI18n();
  const count = fieldCount(payload);

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      {count === 0 ? (
        <p className="mt-2 rounded-lg border border-dashed border-slate-300 px-3 py-2 text-sm text-slate-500">
          {t("notAvailable")}
        </p>
      ) : (
        <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-xs leading-5 text-slate-100">
          {JSON.stringify(payload, null, 2)}
        </pre>
      )}
    </div>
  );
}

export function StageAuditTrail({ stage }: { readonly stage: StageCard }) {
  const { t } = useI18n();
  const [displayOutput, setDisplayOutput] = useState<StageDisplayOutputResponse | null>(null);
  const [displayOutputError, setDisplayOutputError] = useState<string | null>(null);
  const [displayOutputLoading, setDisplayOutputLoading] = useState(false);
  const providerName =
    readString(stage.evidence_payload, "provider_name") || readString(stage.input_payload, "provider_name");
  const providerModel =
    readString(stage.evidence_payload, "provider_model") || readString(stage.input_payload, "provider_model");
  const providerRoute = providerName ? (providerModel ? `${providerName} / ${providerModel}` : providerName) : "";
  const rawResponseAvailable = displayOutput?.raw_response_available ?? false;
  const hiddenFields = displayOutput?.hidden_fields ?? [];
  const displayPayload = displayOutput?.display_payload ?? {};

  useEffect(() => {
    let active = true;
    setDisplayOutputLoading(true);
    setDisplayOutputError(null);

    void getStageDisplayOutput(stage.id)
      .then((output) => {
        if (!active) {
          return;
        }
        setDisplayOutput(output);
      })
      .catch((error) => {
        if (!active) {
          return;
        }
        if (error instanceof Error) {
          setDisplayOutputError(getErrorMessage(error));
          return;
        }
        throw error;
      })
      .finally(() => {
        if (active) {
          setDisplayOutputLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [stage.id]);

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-900">{t("stageAuditTitle")}</p>
          <p className="mt-1 text-sm text-slate-600">{t("stageAuditDescription")}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge tone={providerRoute ? "blue" : "gray"}>
            {t("stageAuditProviderModel")}: {providerRoute || t("stageAuditNoProvider")}
          </Badge>
          <Badge tone={rawResponseAvailable ? "teal" : "gray"}>
            {displayOutputLoading
              ? t("stageAuditDisplayLoading")
              : rawResponseAvailable
                ? t("stageAuditRawResponseSaved")
                : t("stageAuditRawResponseMissing")}
          </Badge>
          <Badge tone={hiddenFields.length > 0 ? "amber" : "gray"}>
            {t("stageAuditHiddenFields")}: {hiddenFields.length}
          </Badge>
        </div>
      </div>

      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
          <dt className="text-xs font-medium text-slate-500">{t("stageInputPayload")}</dt>
          <dd className="mt-1 font-semibold text-slate-900">{fieldCount(stage.input_payload)}</dd>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
          <dt className="text-xs font-medium text-slate-500">{t("stageOutputPayload")}</dt>
          <dd className="mt-1 font-semibold text-slate-900">{fieldCount(displayPayload)}</dd>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
          <dt className="text-xs font-medium text-slate-500">{t("stageEvidencePayload")}</dt>
          <dd className="mt-1 font-semibold text-slate-900">{fieldCount(stage.evidence_payload)}</dd>
        </div>
      </dl>

      <details className="mt-4 rounded-lg border border-slate-200 bg-white">
        <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-slate-800">
          {t("stageAuditOpenPayloads")}
        </summary>
        <div className="space-y-4 border-t border-slate-200 p-4">
          <p className="text-sm text-slate-600">{t("stageAuditPayloadCaveat")}</p>
          {displayOutputError ? (
            <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              {t("stageAuditDisplayLoadFailed")}: {displayOutputError}
            </p>
          ) : null}
          {hiddenFields.length > 0 ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
              <p className="text-sm font-medium text-amber-900">{t("stageAuditHiddenFields")}</p>
              <ul className="mt-2 space-y-1 text-xs text-amber-800">
                {hiddenFields.map((field) => (
                  <li key={field}>{field}</li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500">
              {t("stageAuditNoHiddenFields")}
            </p>
          )}
          <JsonPayloadBlock label={t("stageInputPayload")} payload={stage.input_payload} />
          <JsonPayloadBlock label={t("stageAuditSanitizedOutputPayload")} payload={displayPayload} />
          <JsonPayloadBlock label={t("stageEvidencePayload")} payload={stage.evidence_payload} />
          <p className="text-xs text-slate-500">
            {t("stageConfidence")}: {labelFromEnum(stage.confidence)}
          </p>
        </div>
      </details>
    </div>
  );
}
