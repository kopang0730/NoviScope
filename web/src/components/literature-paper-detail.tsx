import { useI18n } from "../i18n/i18n-context";

export type LiteraturePaper = {
  readonly abstractSummary: string;
  readonly arxivId: string;
  readonly authors: readonly string[];
  readonly doi: string;
  readonly limitations: readonly string[];
  readonly openalexId: string;
  readonly publicationType: string;
  readonly recencyBucket: string;
  readonly relevanceScore: number;
  readonly reliabilityLevel: "top_conference_or_journal" | "peer_reviewed" | "arxiv_preprint" | "unknown";
  readonly sourceQualitySignals: readonly string[];
  readonly sourceType: string;
  readonly title: string;
  readonly url: string;
  readonly venue: string;
  readonly whyRelevant: string;
  readonly year: number | null;
};

function DetailField({
  children,
  label,
}: {
  readonly children: string;
  readonly label: string;
}) {
  return (
    <p>
      <span className="font-medium text-slate-700">{label}:</span> {children}
    </p>
  );
}

function DetailList({
  emptyLabel,
  items,
}: {
  readonly emptyLabel: string;
  readonly items: readonly string[];
}) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">{emptyLabel}</p>;
  }

  return (
    <ul className="space-y-1">
      {items.map((item) => (
        <li className="flex gap-2" key={item}>
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export function PaperDetail({ paper }: { readonly paper: LiteraturePaper }) {
  const { t } = useI18n();

  return (
    <details className="rounded-lg border border-slate-200 bg-white p-3">
      <summary className="cursor-pointer text-sm font-medium text-slate-800">
        {paper.title || t("notAvailable")}
      </summary>
      <div className="mt-3 grid gap-3 text-sm text-slate-600 lg:grid-cols-2">
        <DetailField label={t("abstractSummary")}>
          {paper.abstractSummary || t("notAvailable")}
        </DetailField>
        <DetailField label={t("whyRelevant")}>
          {paper.whyRelevant || t("notAvailable")}
        </DetailField>
        <DetailField label={t("limitations")}>
          {paper.limitations.length > 0 ? paper.limitations.join("; ") : t("notAvailable")}
        </DetailField>
        <div>
          <p className="font-medium text-slate-700">{t("sourceQualitySignals")}:</p>
          <div className="mt-1">
            <DetailList emptyLabel={t("notAvailable")} items={paper.sourceQualitySignals} />
          </div>
        </div>
        <p>
          <span className="font-medium text-slate-700">{t("publicationType")}:</span>{" "}
          {paper.publicationType || t("notAvailable")}
          <br />
          <span className="font-medium text-slate-700">{t("sourceType")}:</span>{" "}
          {paper.sourceType || t("notAvailable")}
          <br />
          <span className="font-medium text-slate-700">{t("recencyBucket")}:</span>{" "}
          {paper.recencyBucket || t("notAvailable")}
        </p>
        <p>
          <span className="font-medium text-slate-700">DOI:</span> {paper.doi || t("notAvailable")}
          <br />
          <span className="font-medium text-slate-700">arXiv ID:</span>{" "}
          {paper.arxivId || t("notAvailable")}
          <br />
          <span className="font-medium text-slate-700">{t("openalexId")}:</span>{" "}
          {paper.openalexId || t("notAvailable")}
        </p>
      </div>
      {paper.url ? (
        <a
          className="mt-3 inline-flex text-sm font-medium text-teal-700 hover:text-teal-800"
          href={paper.url}
          rel="noreferrer"
          target="_blank"
        >
          {t("viewPaper")}
        </a>
      ) : null}
    </details>
  );
}
