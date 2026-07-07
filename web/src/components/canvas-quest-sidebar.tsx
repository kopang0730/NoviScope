import { Link } from "react-router-dom";
import type { Quest, User } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { formatDateTime, labelFromEnum } from "../lib/format";
import { questTone } from "../lib/status-tones";
import { Badge } from "./badge";
import { buttonClassName } from "./button";
import { Card, CardHeading } from "./card";
import { Input } from "./input";

function directionSummary(value: string) {
  const normalized = value.replace(/\s+/g, " ").trim();
  return normalized.length > 150 ? `${normalized.slice(0, 150)}...` : normalized;
}

export function CanvasQuestSidebar({
  authReady,
  currentUser,
  filteredQuests,
  loading,
  loadingError,
  onQueryChange,
  onSelectQuest,
  query,
  questCount,
  selectedQuestId,
}: {
  readonly authReady: boolean;
  readonly currentUser: User | null;
  readonly filteredQuests: readonly Quest[];
  readonly loading: boolean;
  readonly loadingError: string | null;
  readonly onQueryChange: (query: string) => void;
  readonly onSelectQuest: (questId: string) => void;
  readonly query: string;
  readonly questCount: number;
  readonly selectedQuestId: string | null;
}) {
  const { t } = useI18n();

  return (
    <Card className="h-fit xl:sticky xl:top-4">
      <CardHeading
        action={
          <Link className={buttonClassName({ size: "sm", variant: "primary" })} to="/quests/new">
            {t("navNewQuest")}
          </Link>
        }
        description={t("canvasWorkspaceDescription")}
        title={t("navCanvas")}
      />

      <div className="mt-5">
        <Input
          label={t("questSearch")}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder={t("questSearchPlaceholder")}
          value={query}
        />
      </div>

      {!currentUser && authReady ? (
        <p className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
          {t("questSignInPrompt")}
        </p>
      ) : null}
      {loadingError ? <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{loadingError}</p> : null}
      {loading ? <p className="mt-4 text-sm text-slate-500">{t("loadingQuests")}</p> : null}
      {!loading && filteredQuests.length === 0 ? (
        <p className="mt-4 rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
          {questCount === 0 ? t("noQuestsAvailable") : t("noQuestsMatch")}
        </p>
      ) : null}

      {filteredQuests.length > 0 ? (
        <div className="mt-4 space-y-2">
          {filteredQuests.map((quest) => {
            const isSelected = quest.id === selectedQuestId;
            return (
              <button
                className={[
                  "w-full rounded-lg border px-4 py-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2",
                  isSelected ? "border-teal-300 bg-teal-50 shadow-sm" : "border-slate-200 bg-white hover:bg-slate-50",
                ].join(" ")}
                key={quest.id}
                onClick={() => onSelectQuest(quest.id)}
                type="button"
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-medium text-slate-900">{quest.title}</p>
                  <Badge tone={questTone(quest.status)}>{labelFromEnum(quest.status)}</Badge>
                </div>
                <p className="mt-2 line-clamp-3 text-xs text-slate-600">{directionSummary(quest.initial_direction)}</p>
                <p className="mt-2 text-xs text-slate-500">
                  {t("updated")} {formatDateTime(quest.updated_at)}
                </p>
              </button>
            );
          })}
        </div>
      ) : null}
    </Card>
  );
}
