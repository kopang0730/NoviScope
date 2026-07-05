import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getQuest, getQuestStages, getQuests } from "../api/quests";
import { getErrorMessage } from "../api/client";
import type { Quest, QuestStatus, StageCard, StageStatus } from "../api/types";
import { useAuth } from "../auth/auth-context";
import { Badge } from "../components/badge";
import { buttonClassName } from "../components/button";
import { Card, CardHeading } from "../components/card";
import { Input, Select } from "../components/input";
import { MobileStack, Table, TableCell, TableHead } from "../components/table";
import { useI18n } from "../i18n/i18n-context";
import { formatDateTime, labelFromEnum } from "../lib/format";

function questTone(status: QuestStatus) {
  if (status === "complete") {
    return "green";
  }

  if (status === "full_experiment" || status === "lightweight_experiment" || status === "demand_review") {
    return "amber";
  }

  if (status === "idea_selection") {
    return "teal";
  }

  return "blue";
}

function stageTone(status: StageStatus) {
  if (status === "complete") {
    return "green";
  }

  if (status === "running") {
    return "amber";
  }

  if (status === "blocked") {
    return "red";
  }

  return "gray";
}

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
  return normalized.length > 180 ? `${normalized.slice(0, 180)}...` : normalized;
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
      setQuestsError(getErrorMessage(error));
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
        setDetailError(getErrorMessage(error));
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
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(360px,0.8fr)]">
      <Card>
        <CardHeading
          action={
            <Link className={buttonClassName({ variant: "primary" })} to="/quests/new">
              {t("navNewQuest")}
            </Link>
          }
          description={t("questListDescription")}
          title={t("navQuests")}
        />

        <div className="mt-6 grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px]">
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
          <>
            <Table className="mt-4">
              <thead>
                <tr>
                  <TableHead>{t("tableTitle")}</TableHead>
                  <TableHead>{t("tableDirection")}</TableHead>
                  <TableHead>{t("tableStatus")}</TableHead>
                  <TableHead>{t("updated")}</TableHead>
                </tr>
              </thead>
              <tbody>
                {filteredQuests.map((quest) => {
                  const isSelected = quest.id === selectedQuestId;

                  return (
                    <tr
                      className={isSelected ? "bg-teal-50" : "cursor-pointer hover:bg-slate-50"}
                      key={quest.id}
                      onClick={() => setSearchParams({ quest: quest.id })}
                    >
                      <TableCell>
                        <div className="font-medium text-slate-900">{quest.title}</div>
                      </TableCell>
                      <TableCell className="max-w-[280px] text-sm text-slate-600">{directionSummary(quest.initial_direction)}</TableCell>
                      <TableCell>
                        <Badge tone={questTone(quest.status)}>{labelFromEnum(quest.status)}</Badge>
                      </TableCell>
                      <TableCell>{formatDateTime(quest.updated_at)}</TableCell>
                    </tr>
                  );
                })}
              </tbody>
            </Table>

            <MobileStack>
              {filteredQuests.map((quest) => {
                const isSelected = quest.id === selectedQuestId;

                return (
                  <button
                    className={[
                      "w-full rounded-lg border px-4 py-4 text-left shadow-sm transition",
                      isSelected ? "border-teal-300 bg-teal-50" : "border-slate-200 bg-white",
                    ].join(" ")}
                    key={quest.id}
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
                );
              })}
            </MobileStack>
          </>
        ) : null}
      </Card>

      <Card>
        <CardHeading description={t("workflowDescription")} title={t("workflowTitle")} />
        {!selectedQuestId ? <p className="mt-4 text-sm text-slate-500">{t("selectQuestForStages")}</p> : null}
        {detailError ? <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{detailError}</p> : null}
        {detailLoading ? <p className="mt-4 text-sm text-slate-500">{t("loadingQuestDetail")}</p> : null}
        {selectedQuest ? (
          <div className="mt-6 space-y-5">
            <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-base font-semibold text-slate-900">{selectedQuest.title}</h3>
                  <p className="mt-2 whitespace-pre-wrap text-sm text-slate-600">{selectedQuest.initial_direction}</p>
                </div>
                <Badge tone={questTone(selectedQuest.status)}>{labelFromEnum(selectedQuest.status)}</Badge>
              </div>
              <div className="grid gap-2 text-xs text-slate-500 sm:grid-cols-2">
                <p>
                  {t("created")} {formatDateTime(selectedQuest.created_at)}
                </p>
                <p>
                  {t("updated")} {formatDateTime(selectedQuest.updated_at)}
                </p>
              </div>
            </div>

            {stages.length === 0 ? (
              <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
                {t("noStagesFound")}
              </p>
            ) : (
              <div className="space-y-3">
                {stages.map((stage, index) => (
                  <div className="rounded-lg border border-slate-200 p-4" key={stage.id}>
                    <div className="flex items-start gap-3">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-teal-200 bg-teal-50 text-sm font-semibold text-teal-700">
                        {index + 1}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <p className="font-medium text-slate-900">{stage.title}</p>
                            <p className="mt-1 text-sm text-slate-500">{stage.agent_id}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge tone={stageTone(stage.status)}>{labelFromEnum(stage.status)}</Badge>
                            <Link className={buttonClassName({ size: "sm", variant: "secondary" })} to={`/stages/${stage.id}?quest=${selectedQuest.id}`}>
                              {t("open")}
                            </Link>
                          </div>
                        </div>
                        <p className="mt-3 text-sm text-slate-600">{stage.summary || t("noSummaryYet")}</p>
                        {stage.review_notes ? (
                          <p className="mt-2 text-xs text-slate-500">
                            {t("reviewNotes")}: {stage.review_notes}
                          </p>
                        ) : null}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : null}
      </Card>
    </div>
  );
}
