import type { StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";

export function StageAdvancedPayloads({ stage }: { readonly stage: StageCard }) {
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
