import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { Quest, User } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { buttonClassName } from "./button";
import { Input, Select } from "./input";

type QuestNavigationProps = {
  readonly onSelectQuest: (questId: string) => void;
  readonly quests: readonly Quest[];
  readonly selectedQuestId: string | null;
};

export type CanvasQuestRailProps = QuestNavigationProps & {
  readonly authReady: boolean;
  readonly currentUser: User | null;
  readonly error: string | null;
  readonly loading: boolean;
  readonly onReplaceQuest: (questId: string) => void;
};

function directionSummary(value: string) {
  const normalized = value.replace(/\s+/g, " ").trim();
  return normalized.length > 150 ? `${normalized.slice(0, 150)}...` : normalized;
}

export function CanvasQuestRail({
  authReady,
  currentUser,
  error,
  loading,
  onSelectQuest,
  onReplaceQuest,
  quests,
  selectedQuestId,
}: CanvasQuestRailProps) {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [collapsed, setCollapsed] = useState(false);
  const filteredQuests = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return quests.filter(
      (quest) =>
        normalizedQuery.length === 0 ||
        quest.title.toLowerCase().includes(normalizedQuery) ||
        quest.initial_direction.toLowerCase().includes(normalizedQuery),
    );
  }, [query, quests]);

  useEffect(() => {
    const firstQuest = filteredQuests[0];
    if (
      firstQuest &&
      (!selectedQuestId || !filteredQuests.some((quest) => quest.id === selectedQuestId))
    ) {
      onReplaceQuest(firstQuest.id);
    }
  }, [filteredQuests, onReplaceQuest, selectedQuestId]);

  return (
    <aside
      className={[
        "hidden h-fit rounded-lg border border-slate-200 bg-white p-3 shadow-panel lg:sticky lg:top-4 lg:block",
        collapsed ? "w-[132px]" : "w-[280px]",
      ].join(" ")}
    >
      <div className="flex items-center justify-between gap-2">
        {!collapsed ? <h1 className="text-base font-semibold text-slate-900">{t("navCanvas")}</h1> : null}
        <button
          aria-expanded={!collapsed}
          className="min-h-11 rounded-lg border border-slate-300 px-3 text-xs font-medium text-slate-700 transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
          onClick={() => setCollapsed((current) => !current)}
          type="button"
        >
          {collapsed ? t("questRailExpand") : t("questRailCollapse")}
        </button>
      </div>

      {!collapsed ? (
        <>
          <Link
            className={buttonClassName({ className: "mt-3 min-h-11 w-full", variant: "primary" })}
            to="/quests/new"
          >
            {t("navNewQuest")}
          </Link>
          <div className="mt-4">
            <Input
              label={t("questSearch")}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t("questSearchPlaceholder")}
              value={query}
            />
          </div>

          {!currentUser && authReady ? (
            <p className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
              {t("questSignInPrompt")}
            </p>
          ) : null}
          {error ? (
            <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </p>
          ) : null}
          {loading ? <p className="mt-4 text-sm text-slate-500">{t("loadingQuests")}</p> : null}
          {!loading && filteredQuests.length === 0 ? (
            <p className="mt-4 rounded-lg border border-dashed border-slate-300 px-3 py-5 text-sm text-slate-500">
              {quests.length === 0 ? t("noQuestsAvailable") : t("noQuestsMatch")}
            </p>
          ) : null}

          {filteredQuests.length > 0 ? (
            <div className="mt-4 space-y-2">
              {filteredQuests.map((quest) => {
                const isSelected = quest.id === selectedQuestId;
                return (
                  <button
                    className={[
                      "w-full rounded-lg border px-3 py-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2",
                      isSelected
                        ? "border-teal-300 bg-teal-50"
                        : "border-slate-200 bg-white hover:bg-slate-50",
                    ].join(" ")}
                    key={quest.id}
                    onClick={() => onSelectQuest(quest.id)}
                    type="button"
                  >
                    <p className="break-words text-sm font-medium text-slate-900">{quest.title}</p>
                    <p className="mt-1 line-clamp-2 text-xs text-slate-600">
                      {directionSummary(quest.initial_direction)}
                    </p>
                  </button>
                );
              })}
            </div>
          ) : null}
        </>
      ) : null}
    </aside>
  );
}

export function CanvasQuestSelector({
  onSelectQuest,
  quests,
  selectedQuestId,
}: QuestNavigationProps) {
  const { t } = useI18n();
  return (
    <div className="lg:hidden">
      <Select
        className="min-h-11"
        disabled={quests.length === 0}
        label={t("questSelector")}
        onChange={(event) => onSelectQuest(event.target.value)}
        value={selectedQuestId ?? ""}
      >
        {quests.length === 0 ? <option value="">{t("noQuestsAvailable")}</option> : null}
        {quests.map((quest) => (
          <option key={quest.id} value={quest.id}>
            {quest.title}
          </option>
        ))}
      </Select>
    </div>
  );
}
