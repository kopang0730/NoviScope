import type { StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { buildDemandValidationView } from "../lib/demand-validation-view";
import { localizedResearchLabel } from "../lib/research-labels";
import { Badge } from "./badge";

function bulletToneClassName(tone: "amber" | "rose" | "teal") {
  switch (tone) {
    case "amber":
      return "bg-amber-500";
    case "rose":
      return "bg-rose-500";
    case "teal":
      return "bg-teal-500";
  }
}

function BulletList({
  emptyLabel,
  items,
  tone = "teal",
}: {
  readonly emptyLabel: string;
  readonly items: readonly string[];
  readonly tone?: "amber" | "rose" | "teal";
}) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">{emptyLabel}</p>;
  }

  return (
    <ul className="space-y-1 text-sm text-slate-600">
      {items.map((item) => (
        <li className="flex gap-2" key={item}>
          <span className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${bulletToneClassName(tone)}`} />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function DecisionSignal({ label, value }: { readonly label: string; readonly value: string }) {
  return (
    <div className="border-l-2 border-slate-200 pl-3">
      <dt className="text-xs font-semibold text-slate-500">{label}</dt>
      <dd className="mt-1 text-sm font-semibold text-slate-900">{value}</dd>
    </div>
  );
}

export function DemandValidationOverview({ stage }: { readonly stage: StageCard }) {
  const { t } = useI18n();
  const view = buildDemandValidationView(stage);

  if (!view) {
    return null;
  }

  const hasHumanReviewedSources = view.sourceVerification === "human_reviewed_sources";

  return (
    <section aria-label={t("demandDecisionBrief")} className="mt-5 border-t border-slate-200 pt-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold text-slate-500">{t("demandDecisionBrief")}</p>
          <p className="mt-1 text-sm text-slate-600">{t("demandDecisionBriefDescription")}</p>
        </div>
        <Badge tone={hasHumanReviewedSources ? "green" : "amber"}>
          {t("sourceVerification")}: {localizedResearchLabel(view.sourceVerification || "unknown", t)}
        </Badge>
      </div>

      <dl className="mt-4 grid gap-4 sm:grid-cols-2">
        <DecisionSignal
          label={t("demandAssessment")}
          value={localizedResearchLabel(view.assessment || "unclear", t)}
        />
        <DecisionSignal
          label={t("goNoGoRecommendation")}
          value={localizedResearchLabel(view.goNoGoRecommendation || "needs_more_evidence", t)}
        />
      </dl>

      <div className="mt-5 grid border-y border-slate-200 lg:grid-cols-2">
        <section className="py-4 lg:border-r lg:border-slate-200 lg:pr-6">
          <h4 className="text-sm font-semibold text-slate-900">{t("researchContext")}</h4>
          <dl className="mt-3 space-y-3">
            <div>
              <dt className="text-xs font-semibold text-slate-500">{t("realWorldScenario")}</dt>
              <dd className="mt-1 text-sm leading-6 text-slate-700">
                {view.realWorldScenario || t("notAvailable")}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold text-slate-500">{t("targetUserOrCustomer")}</dt>
              <dd className="mt-1 text-sm leading-6 text-slate-700">
                {view.targetUserOrCustomer || t("notAvailable")}
              </dd>
            </div>
          </dl>
        </section>

        <section className="border-t border-slate-200 py-4 lg:border-t-0 lg:pl-6">
          <h4 className="text-sm font-semibold text-slate-900">{t("evidenceStatus")}</h4>
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-xs font-semibold text-emerald-700">{t("evidenceForDemand")}</p>
              <div className="mt-2">
                <BulletList emptyLabel={t("notAvailable")} items={view.evidenceForDemand} />
              </div>
            </div>
            <div>
              <p className="text-xs font-semibold text-amber-700">{t("missingEvidence")}</p>
              <div className="mt-2">
                <BulletList emptyLabel={t("notAvailable")} items={view.missingEvidence} tone="amber" />
              </div>
            </div>
          </div>
        </section>
      </div>

      {view.risks.length > 0 ? (
        <div className="mt-4">
          <p className="text-xs font-semibold text-rose-700">{t("risks")}</p>
          <div className="mt-2">
            <BulletList emptyLabel={t("notAvailable")} items={view.risks} tone="rose" />
          </div>
        </div>
      ) : null}

      <div className="mt-4 border-l-2 border-teal-500 bg-teal-50 px-4 py-3">
        <p className="text-xs font-semibold text-teal-700">{t("nextStep")}</p>
        <p className="mt-1 text-sm leading-6 text-teal-950">{view.nextStep || t("notAvailable")}</p>
      </div>
    </section>
  );
}
