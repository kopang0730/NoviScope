import { useEffect, useMemo, useState } from "react";
import type { AgentAssignment, Provider, User } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import { Badge } from "./badge";
import { Button } from "./button";
import { Card, CardHeading } from "./card";
import { Input, Select } from "./input";

type AssignmentDraft = {
  readonly modelName: string;
  readonly providerId: string;
};

type AgentAssignmentCardProps = {
  readonly assignments: readonly AgentAssignment[];
  readonly currentUser: User | null;
  readonly error: string | null;
  readonly loading: boolean;
  readonly onSave: (agentId: string, draft: AssignmentDraft) => void;
  readonly providers: readonly Provider[];
  readonly saveError: string | null;
  readonly savingAgentId: string | null;
};

function buildDrafts(assignments: readonly AgentAssignment[]) {
  return Object.fromEntries(
    assignments.map((assignment) => [
      assignment.agent_id,
      {
        modelName: assignment.model_name ?? "",
        providerId: assignment.provider_id ?? "",
      },
    ]),
  ) as Record<string, AssignmentDraft>;
}

function providerLabel(provider: Provider) {
  return `${provider.name} (${labelFromEnum(provider.kind)} / ${provider.default_model})`;
}

export function AgentAssignmentCard({
  assignments,
  currentUser,
  error,
  loading,
  onSave,
  providers,
  saveError,
  savingAgentId,
}: AgentAssignmentCardProps) {
  const { t } = useI18n();
  const [drafts, setDrafts] = useState<Record<string, AssignmentDraft>>({});
  const canEdit = currentUser?.role === "admin";
  const sharedProviders = useMemo(
    () => providers.filter((provider) => provider.scope === "shared"),
    [providers],
  );

  useEffect(() => {
    setDrafts(buildDrafts(assignments));
  }, [assignments]);

  function updateDraft(agentId: string, update: Partial<AssignmentDraft>) {
    setDrafts((current) => ({
      ...current,
      [agentId]: { ...(current[agentId] ?? { modelName: "", providerId: "" }), ...update },
    }));
  }

  return (
    <Card>
      <CardHeading description={t("agentAssignmentDescription")} title={t("agentAssignmentTitle")} />
      {!canEdit ? (
        <p className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
          {t("agentAssignmentAdminOnly")}
        </p>
      ) : null}
      {sharedProviders.length === 0 ? (
        <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {t("agentAssignmentNoSharedProviders")}
        </p>
      ) : null}
      {error ? <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}
      {saveError ? <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{saveError}</p> : null}
      {loading ? <p className="mt-4 text-sm text-slate-500">{t("loadingProviderData")}</p> : null}
      <div className="mt-5 grid gap-3">
        {assignments.map((assignment) => {
          const draft = drafts[assignment.agent_id] ?? { modelName: "", providerId: "" };
          const selectedProvider = sharedProviders.find((provider) => provider.id === draft.providerId);
          return (
            <div className="rounded-lg border border-slate-200 bg-white p-4" key={assignment.agent_id}>
              <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="font-medium text-slate-900">{assignment.display_name}</p>
                  <p className="mt-1 text-xs text-slate-500">{assignment.agent_id}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge tone={assignment.provider_is_active === false ? "gray" : "teal"}>
                    {assignment.provider_name ?? t("agentAssignmentAuto")}
                  </Badge>
                  {assignment.effective_model ? (
                    <Badge tone="blue">{assignment.effective_model}</Badge>
                  ) : null}
                </div>
              </div>
              <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1.4fr)_minmax(180px,0.8fr)_auto] lg:items-end">
                <Select
                  disabled={!canEdit}
                  label={t("agentAssignmentProvider")}
                  onChange={(event) => updateDraft(assignment.agent_id, { providerId: event.target.value })}
                  value={draft.providerId}
                >
                  <option value="">{t("agentAssignmentAuto")}</option>
                  {sharedProviders.map((provider) => (
                    <option key={provider.id} value={provider.id}>
                      {providerLabel(provider)}
                    </option>
                  ))}
                </Select>
                <Input
                  disabled={!canEdit || !draft.providerId}
                  label={t("agentAssignmentModel")}
                  onChange={(event) => updateDraft(assignment.agent_id, { modelName: event.target.value })}
                  placeholder={selectedProvider?.default_model ?? t("agentAssignmentModelPlaceholder")}
                  value={draft.modelName}
                />
                <Button
                  disabled={!canEdit}
                  loading={savingAgentId === assignment.agent_id}
                  onClick={() => onSave(assignment.agent_id, draft)}
                  type="button"
                >
                  {t("agentAssignmentSave")}
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
