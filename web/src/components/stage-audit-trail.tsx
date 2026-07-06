import type { StageCard } from "../api/types";
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
  const providerName =
    readString(stage.evidence_payload, "provider_name") || readString(stage.input_payload, "provider_name");
  const providerModel =
    readString(stage.evidence_payload, "provider_model") || readString(stage.input_payload, "provider_model");
  const providerRoute = providerName ? (providerModel ? `${providerName} / ${providerModel}` : providerName) : "";
  const rawResponse = readString(stage.output_payload, "raw_response");

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
          <Badge tone={rawResponse ? "teal" : "gray"}>
            {rawResponse ? t("stageAuditRawResponseSaved") : t("stageAuditRawResponseMissing")}
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
          <dd className="mt-1 font-semibold text-slate-900">{fieldCount(stage.output_payload)}</dd>
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
          {rawResponse ? (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t("stageAuditRawResponse")}
              </p>
              <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-xs leading-5 text-slate-100">
                {rawResponse}
              </pre>
            </div>
          ) : null}
          <JsonPayloadBlock label={t("stageInputPayload")} payload={stage.input_payload} />
          <JsonPayloadBlock label={t("stageOutputPayload")} payload={stage.output_payload} />
          <JsonPayloadBlock label={t("stageEvidencePayload")} payload={stage.evidence_payload} />
          <p className="text-xs text-slate-500">
            {t("stageConfidence")}: {labelFromEnum(stage.confidence)}
          </p>
        </div>
      </details>
    </div>
  );
}
