import { useMemo, useState } from "react";
import type { StageCard } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import { literatureScoutAgentId } from "../lib/stages";
import { Badge } from "./badge";
import { Input, Select } from "./input";
import { PaperDetail, type LiteraturePaper } from "./literature-paper-detail";

type ReliabilityLevel = "top_conference_or_journal" | "peer_reviewed" | "arxiv_preprint" | "unknown";
type SortMode = "score_desc" | "year_desc" | "venue_asc";

type LiteratureScoutView = {
  readonly papers: readonly LiteraturePaper[];
  readonly scoreBasis: string;
  readonly searchQuery: string;
  readonly source: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readString(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return typeof value === "string" ? value : "";
}

function readNumber(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function readStringArray(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function readReliabilityLevel(value: string): ReliabilityLevel {
  switch (value) {
    case "top_conference_or_journal":
      return "top_conference_or_journal";
    case "peer_reviewed":
      return "peer_reviewed";
    case "arxiv_preprint":
      return "arxiv_preprint";
    default:
      return "unknown";
  }
}

function parseReliabilityFilter(value: string): ReliabilityLevel | "all" {
  return value === "all" ? "all" : readReliabilityLevel(value);
}

function parseSortMode(value: string): SortMode {
  if (value === "year_desc" || value === "venue_asc") {
    return value;
  }
  return "score_desc";
}

function readPaper(value: unknown): LiteraturePaper | null {
  if (!isRecord(value)) {
    return null;
  }

  return {
    abstractSummary: readString(value, "abstract_summary"),
    authors: readStringArray(value, "authors"),
    doi: readString(value, "doi"),
    limitations: readStringArray(value, "limitations"),
    openalexId: readString(value, "openalex_id"),
    publicationType: readString(value, "publication_type"),
    recencyBucket: readString(value, "recency_bucket"),
    relevanceScore: readNumber(value, "relevance_score") ?? 0,
    reliabilityLevel: readReliabilityLevel(readString(value, "reliability_level")),
    sourceQualitySignals: readStringArray(value, "source_quality_signals"),
    sourceType: readString(value, "source_type"),
    title: readString(value, "title"),
    url: readString(value, "url"),
    venue: readString(value, "venue"),
    whyRelevant: readString(value, "why_relevant"),
    year: readNumber(value, "year"),
  };
}

function buildLiteratureScoutView(stage: StageCard): LiteratureScoutView | null {
  if (stage.agent_id !== literatureScoutAgentId || stage.status !== "complete") {
    return null;
  }

  const paperValues = stage.output_payload.papers;
  return {
    papers: Array.isArray(paperValues) ? paperValues.map(readPaper).filter((paper): paper is LiteraturePaper => paper !== null) : [],
    scoreBasis: readString(stage.output_payload, "score_basis"),
    searchQuery: readString(stage.output_payload, "search_query"),
    source: readString(stage.output_payload, "source"),
  };
}

function reliabilityTone(reliability: ReliabilityLevel) {
  if (reliability === "top_conference_or_journal") {
    return "green";
  }
  if (reliability === "peer_reviewed") {
    return "blue";
  }
  if (reliability === "arxiv_preprint") {
    return "amber";
  }
  return "gray";
}

function filterAndSortPapers(
  papers: readonly LiteraturePaper[],
  query: string,
  reliability: ReliabilityLevel | "all",
  sortMode: SortMode,
) {
  const normalizedQuery = query.trim().toLowerCase();
  const filtered = papers.filter((paper) => {
    const matchesReliability = reliability === "all" || paper.reliabilityLevel === reliability;
    const haystack = [paper.title, paper.venue, paper.authors.join(" "), paper.whyRelevant].join(" ").toLowerCase();
    return matchesReliability && (!normalizedQuery || haystack.includes(normalizedQuery));
  });

  return [...filtered].sort((left, right) => {
    if (sortMode === "year_desc") {
      return (right.year ?? 0) - (left.year ?? 0);
    }
    if (sortMode === "venue_asc") {
      return left.venue.localeCompare(right.venue);
    }
    return right.relevanceScore - left.relevanceScore;
  });
}

export function LiteratureScoutOutput({ stage }: { readonly stage: StageCard }) {
  const { t } = useI18n();
  const literatureScout = buildLiteratureScoutView(stage);
  const [query, setQuery] = useState("");
  const [reliability, setReliability] = useState<ReliabilityLevel | "all">("all");
  const [sortMode, setSortMode] = useState<SortMode>("score_desc");

  const visiblePapers = useMemo(
    () => filterAndSortPapers(literatureScout?.papers ?? [], query, reliability, sortMode),
    [literatureScout?.papers, query, reliability, sortMode],
  );

  if (!literatureScout) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 lg:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("source")}</p>
          <p className="mt-2 text-sm font-medium text-slate-900">{literatureScout.source || t("notAvailable")}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 lg:col-span-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("searchQuery")}</p>
          <p className="mt-2 text-sm text-slate-700">{literatureScout.searchQuery || t("notAvailable")}</p>
          {literatureScout.scoreBasis ? (
            <p className="mt-2 text-xs text-slate-500">
              {t("scoreBasis")}: {literatureScout.scoreBasis}
            </p>
          ) : null}
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <Input label={t("paperSearch")} onChange={(event) => setQuery(event.target.value)} value={query} />
        <Select label={t("reliability")} onChange={(event) => setReliability(parseReliabilityFilter(event.target.value))} value={reliability}>
          <option value="all">{t("allReliability")}</option>
          <option value="top_conference_or_journal">{labelFromEnum("top_conference_or_journal")}</option>
          <option value="peer_reviewed">{labelFromEnum("peer_reviewed")}</option>
          <option value="arxiv_preprint">{labelFromEnum("arxiv_preprint")}</option>
          <option value="unknown">{labelFromEnum("unknown")}</option>
        </Select>
        <Select label={t("sortBy")} onChange={(event) => setSortMode(parseSortMode(event.target.value))} value={sortMode}>
          <option value="score_desc">{t("sortScore")}</option>
          <option value="year_desc">{t("sortYear")}</option>
          <option value="venue_asc">{t("sortVenue")}</option>
        </Select>
      </div>

      {visiblePapers.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">{t("noPapersFound")}</p>
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">{t("tableTitle")}</th>
                <th className="px-4 py-3">{t("year")}</th>
                <th className="px-4 py-3">{t("venue")}</th>
                <th className="px-4 py-3">{t("reliability")}</th>
                <th className="px-4 py-3">{t("relevanceScore")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {visiblePapers.map((paper) => (
                <tr key={paper.openalexId || paper.title}>
                  <td className="max-w-xl px-4 py-3">
                    <p className="font-medium text-slate-900">{paper.title || t("notAvailable")}</p>
                    <p className="mt-1 text-xs text-slate-500">{paper.authors.join(", ") || t("notAvailable")}</p>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{paper.year ?? t("notAvailable")}</td>
                  <td className="px-4 py-3 text-slate-600">{paper.venue || t("notAvailable")}</td>
                  <td className="px-4 py-3">
                    <Badge tone={reliabilityTone(paper.reliabilityLevel)}>{labelFromEnum(paper.reliabilityLevel)}</Badge>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{paper.relevanceScore.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="space-y-2">
        {visiblePapers.map((paper) => (
          <PaperDetail key={`${paper.openalexId || paper.title}-detail`} paper={paper} />
        ))}
      </div>
    </div>
  );
}
