import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getQuest, getQuestStages, getQuests } from "../api/quests";
import { getErrorMessage } from "../api/client";
import type { Quest, QuestStatus, StageCard } from "../api/types";
import { useAuth } from "../auth/auth-context";
import { Badge } from "../components/badge";
import { buttonClassName } from "../components/button";
import { Card, CardHeading } from "../components/card";
import { Input, Select } from "../components/input";
import { QuestOverviewPanel } from "../components/quest-overview-panel";
import { useI18n } from "../i18n/i18n-context";
import { formatDateTime, labelFromEnum } from "../lib/format";
import { questTone } from "../lib/status-tones";

const questStatusOptions: Array<QuestStatus | "all"> = [
  "all",
  "draft",
  "demand_review",
  "idea_selection",
  "lightweight_experiment",
  "full_experiment",
  "writing",
  "complete",
  "archived",
];

function directionSummary(value: string) {
  const normalized = value.replace(/\s+/g, " ").trim();
  return normalized.length > 110 ? `${normalized.slice(0, 110)}...` : normalized;
}

export function QuestListPage() {
  const { authReady, currentUser } = useAuth();
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const [quests, setQuests] = useState<Quest[]>([]);
  const [questsLoading, setQuestsLoading] = useState(false);
  const [questsError, setQuestsError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [selectedQuest, setSelectedQuest] = useState<Quest | null>(null);
  const [stages, setStages] = useState<StageCard[]>([]);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<QuestStatus | "all">("all");

  const selectedQuestId = searchParams.get("quest");

  const loadQuests = useCallback(async () => {
    if (!currentUser) {
      setQuests([]);
      setSelectedQuest(null);
      setStages([]);
      setQuestsError(null);
      setQuestsLoading(false);
      return;
    }

    setQuestsLoading(true);
    setQuestsError(null);

    try {
      setQuests(await getQuests());
    } catch (error) {
      if (error instanceof Error) {
        setQuestsError(getErrorMessage(error));
        return;
      }
      throw error;
    } finally {
      setQuestsLoading(false);
    }
  }, [currentUser]);

  useEffect(() => {
    void loadQuests();
  }, [loadQuests]);

  const filteredQuests = useMemo(() => {
    return quests.filter((quest) => {
      const matchesQuery =
        query.trim().length === 0 ||
        quest.title.toLowerCase().includes(query.toLowerCase()) ||
        quest.initial_direction.toLowerCase().includes(query.toLowerCase());
      const matchesStatus = statusFilter === "all" || quest.status === statusFilter;
      return matchesQuery && matchesStatus;
    });
  }, [query, quests, statusFilter]);

  useEffect(() => {
    if (!filteredQuests.length) {
      return;
    }

    if (!selectedQuestId || !filteredQuests.some((quest) => quest.id === selectedQuestId)) {
      setSearchParams({ quest: filteredQuests[0].id }, { replace: true });
    }
  }, [filteredQuests, selectedQuestId, setSearchParams]);

  useEffect(() => {
    if (!currentUser || !selectedQuestId) {
      setSelectedQuest(null);
      setStages([]);
      setDetailError(null);
      setDetailLoading(false);
      return;
    }

    let active = true;
    setDetailLoading(true);
    setDetailError(null);

    void Promise.all([getQuest(selectedQuestId), getQuestStages(selectedQuestId)])
      .then(([quest, questStages]) => {
        if (!active) {
          return;
        }
        setSelectedQuest(quest);
        setStages(questStages);
      })
      .catch((error) => {
        if (!active) {
          return;
        }
        setSelectedQuest(null);
        setStages([]);
        if (error instanceof Error) {
          setDetailError(getErrorMessage(error));
          return;
        }
        throw error;
      })
      .finally(() => {
        if (active) {
          setDetailLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [currentUser, selectedQuestId]);

  return (
    <div className="grid min-w-0 gap-4 xl:grid-cols-[260px_minmax(0,1fr)] 2xl:grid-cols-[280px_minmax(0,1fr)]">
      <Card className="h-fit xl:sticky xl:top-4">
        <CardHeading
          action={
            <Link className={buttonClassName({ variant: "primary" })} to="/quests/new">
              {t("navNewQuest")}
            </Link>
          }
          description={t("questListDescription")}
          title={t("navQuests")}
        />

        <div className="mt-6 grid gap-3">
          <Input label={t("questSearch")} onChange={(event) => setQuery(event.target.value)} placeholder={t("questSearchPlaceholder")} value={query} />
          <Select label={t("questStatus")} onChange={(event) => setStatusFilter(event.target.value as QuestStatus | "all")} value={statusFilter}>
            {questStatusOptions.map((status) => (
              <option key={status} value={status}>
                {status === "all" ? t("statusAll") : labelFromEnum(status)}
              </option>
            ))}
          </Select>
        </div>

        {!currentUser && authReady ? (
          <p className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
            {t("questSignInPrompt")}
          </p>
        ) : null}
        {questsError ? <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{questsError}</p> : null}
        {questsLoading ? <p className="mt-4 text-sm text-slate-500">{t("loadingQuests")}</p> : null}
        {!questsLoading && filteredQuests.length === 0 ? (
          <p className="mt-4 rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
            {quests.length === 0 ? t("noQuestsAvailable") : t("noQuestsMatch")}
          </p>
        ) : null}

        {filteredQuests.length > 0 ? (
          <div className="mt-4 space-y-2">
            {filteredQuests.map((quest) => {
              const isSelected = quest.id === selectedQuestId;

              return (
                <div
                  className={[
                    "rounded-lg border px-4 py-4 transition",
                    isSelected ? "border-teal-300 bg-teal-50 shadow-sm" : "border-slate-200 bg-white hover:bg-slate-50",
                  ].join(" ")}
                  key={quest.id}
                >
                  <button
                    className="w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2"
                    onClick={() => setSearchParams({ quest: quest.id })}
                    type="button"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="font-medium text-slate-900">{quest.title}</p>
                      <Badge tone={questTone(quest.status)}>{labelFromEnum(quest.status)}</Badge>
                    </div>
                    <p className="mt-2 text-sm text-slate-600">{directionSummary(quest.initial_direction)}</p>
                    <p className="mt-2 text-xs text-slate-500">
                      {t("updated")} {formatDateTime(quest.updated_at)}
                    </p>
                  </button>
                  <Link className="mt-3 inline-flex text-xs font-semibold text-teal-700 hover:text-teal-900" to={`/canvas?quest=${quest.id}`}>
                    {t("openFullCanvas")}
                  </Link>
                </div>
              );
            })}
          </div>
        ) : null}
      </Card>

      <div className="grid min-w-0 gap-4">
        <QuestOverviewPanel
          detailError={detailError}
          detailLoading={detailLoading}
          selectedQuest={selectedQuest}
          selectedQuestId={selectedQuestId}
          stages={stages}
        />
      </div>
    </div>
  );
}
