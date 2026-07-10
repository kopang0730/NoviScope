import { useEffect, useMemo, useState } from "react";
import type { UpdateAgentAssignmentPayload } from "../api/agent-assignments";
import { getErrorMessage } from "../api/client";
import type { AgentAssignment, Provider, User, WorkflowAgentCapability } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import {
  buildAssignmentRows,
  buildAssignmentUpdates,
  type AgentAssignmentDraft,
  type AgentAssignmentRow,
} from "../lib/provider-settings-view";
import { Badge } from "./badge";
import { Button } from "./button";
import { Card, CardHeading } from "./card";
import { fieldClassName } from "./input";

type AgentAssignmentMatrixProps = {
  readonly assignments: readonly AgentAssignment[];
  readonly capabilities: readonly WorkflowAgentCapability[];
  readonly currentUser: User | null;
  readonly error: string | null;
  readonly loading: boolean;
  readonly onReload: () => Promise<void>;
  readonly onUpdate: (agentId: string, payload: UpdateAgentAssignmentPayload) => Promise<AgentAssignment>;
  readonly providers: readonly Provider[];
};

function buildDrafts(rows: readonly AgentAssignmentRow[]): Readonly<Record<string, AgentAssignmentDraft>> {
  const drafts: Record<string, AgentAssignmentDraft> = {};
  for (const row of rows) {
    drafts[row.agentId] = { modelName: row.modelName, providerId: row.providerId };
  }
  return drafts;
}

function providerLabel(provider: Provider): string {
  return provider.name;
}

function failedRoleLabels(rows: readonly AgentAssignmentRow[], updates: ReturnType<typeof buildAssignmentUpdates>, results: readonly PromiseSettledResult<AgentAssignment>[]): readonly string[] {
  const labels: string[] = [];
  results.forEach((result, index) => {
    if (result.status !== "rejected") {
      return;
    }
    const update = updates[index];
    const row = update ? rows.find((candidate) => candidate.agentId === update.agentId) : null;
    if (update) {
      labels.push(`${row?.displayName ?? update.agentId} (${update.agentId})`);
    }
  });
  return labels;
}

export function AgentAssignmentMatrix({ assignments, capabilities, currentUser, error, loading, onReload, onUpdate, providers }: AgentAssignmentMatrixProps) {
  const { t } = useI18n();
  const rows = useMemo(() => buildAssignmentRows(assignments, capabilities), [assignments, capabilities]);
  const sharedProviders = useMemo(() => providers.filter((provider) => provider.scope === "shared"), [providers]);
  const [drafts, setDrafts] = useState<Readonly<Record<string, AgentAssignmentDraft>>>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const canEdit = currentUser?.role === "admin";
  const updates = useMemo(() => buildAssignmentUpdates(rows, drafts), [drafts, rows]);

  useEffect(() => {
    setDrafts(buildDrafts(rows));
  }, [rows]);

  function updateDraft(agentId: string, update: Partial<AgentAssignmentDraft>) {
    setDrafts((current) => {
      const existing = current[agentId] ?? { modelName: "", providerId: "" };
      return { ...current, [agentId]: { ...existing, ...update } };
    });
    setSaveError(null);
    setSaveMessage(null);
  }

  async function saveAssignments(): Promise<void> {
    setSaving(true);
    setSaveError(null);
    setSaveMessage(null);

    const results = await Promise.allSettled(updates.map((update) => onUpdate(update.agentId, update.payload)));
    const failedRoles = failedRoleLabels(rows, updates, results);
    let reloadError: string | null = null;
    try {
      await onReload();
    } catch (error) {
      if (error instanceof Error) {
        reloadError = getErrorMessage(error);
      } else {
        throw error;
      }
    }

    if (failedRoles.length > 0) {
      setSaveError(
        `${t("agentAssignmentPartialFailure")} ${failedRoles.join(", ")}.${
          reloadError ? ` ${t("agentAssignmentReloadFailed")}: ${reloadError}` : ""
        }`,
      );
    } else if (reloadError) {
      setSaveError(`${t("agentAssignmentReloadFailed")}: ${reloadError}`);
    } else {
      setSaveMessage(t("agentAssignmentSaved"));
    }
    setSaving(false);
  }

  return (
    <Card>
      <CardHeading
        action={
          canEdit ? (
            <Button className="min-h-11" disabled={updates.length === 0} loading={saving} onClick={() => void saveAssignments()}>
              {t("agentAssignmentSaveAll")}
            </Button>
          ) : null
        }
        description={t("agentAssignmentDescription")}
        title={t("agentAssignmentTitle")}
      />
      {!canEdit ? (
        <p className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">{t("agentAssignmentAdminOnly")}</p>
      ) : null}
      {canEdit && sharedProviders.length === 0 ? (
        <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">{t("agentAssignmentNoSharedProviders")}</p>
      ) : null}
      {error ? (
        <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">{error}</p>
      ) : null}
      {saveError ? (
        <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">{saveError}</p>
      ) : null}
      {saveMessage ? (
        <p className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800" role="status">{saveMessage}</p>
      ) : null}
      {loading ? <p className="mt-4 text-sm text-slate-500">{t("loadingProviderData")}</p> : null}

      <div className="mt-5 overflow-hidden rounded-lg border border-slate-200">
        <table aria-label={t("agentAssignmentTitle")} className="w-full text-left text-sm">
          <thead className="hidden bg-slate-50 text-xs font-medium uppercase text-slate-500 xl:table-header-group">
            <tr>
              <th className="px-4 py-3">{t("agentAssignmentRole")}</th>
              <th className="px-4 py-3">{t("agentAssignmentCapability")}</th>
              <th className="px-4 py-3">{t("agentAssignmentProvider")}</th>
              <th className="px-4 py-3">{t("agentAssignmentModel")}</th>
              <th className="px-4 py-3">{t("agentAssignmentConnection")}</th>
            </tr>
          </thead>
          <tbody className="block divide-y divide-slate-200 xl:table-row-group">
            {rows.map((row) => {
              const draft = drafts[row.agentId] ?? { modelName: "", providerId: "" };
              const selectedProvider = sharedProviders.find((provider) => provider.id === draft.providerId);
              const controlDisabled = !canEdit || !row.editable;
              return (
                <tr className="grid gap-3 p-4 sm:grid-cols-2 xl:table-row xl:p-0" key={row.agentId}>
                  <td className="block min-w-0 pb-3 align-top xl:table-cell xl:px-4 xl:py-4">
                    <p className="font-medium text-slate-900">{row.displayName}</p>
                    <p className="mt-1 text-xs text-slate-500">{row.agentId}</p>
                  </td>
                  <td className="block min-w-0 pb-3 align-top xl:table-cell xl:px-4 xl:py-4">
                    <span className="mb-1 block text-xs font-medium text-slate-500 xl:hidden">{t("agentAssignmentCapability")}</span>
                    {row.status === "planned" ? (
                      <Badge tone="amber">{t("agentAssignmentPlanned")}</Badge>
                    ) : row.providerRequirement === "server_managed" ? (
                      <Badge tone="blue">{t("agentAssignmentServerManaged")}</Badge>
                    ) : (
                      <Badge tone="green">{t("agentAssignmentImplemented")}</Badge>
                    )}
                    <p className="mt-2 max-w-xs text-xs text-slate-500">{row.statusDetail}</p>
                  </td>
                  <td className="block min-w-0 pb-3 align-top xl:table-cell xl:min-w-[210px] xl:px-4 xl:py-4">
                    <label className="block">
                      <span className="mb-1 block text-xs font-medium text-slate-500 xl:sr-only">{t("agentAssignmentProvider")}</span>
                      <select
                        aria-label={`${row.displayName} ${t("agentAssignmentProvider")}`}
                        className={`${fieldClassName} min-h-11`}
                        disabled={controlDisabled}
                        onChange={(event) => updateDraft(row.agentId, { providerId: event.target.value })}
                        value={draft.providerId}
                      >
                        <option value="">
                          {row.status === "planned"
                            ? t("agentAssignmentNotImplemented")
                            : row.providerRequirement === "server_managed"
                              ? t("agentAssignmentServerManaged")
                              : t("agentAssignmentAuto")}
                        </option>
                        {row.editable
                          ? sharedProviders.map((provider) => (
                              <option key={provider.id} value={provider.id}>{providerLabel(provider)}</option>
                            ))
                          : null}
                      </select>
                    </label>
                  </td>
                  <td className="block min-w-0 pb-3 align-top xl:table-cell xl:min-w-[190px] xl:px-4 xl:py-4">
                    <label className="block">
                      <span className="mb-1 block text-xs font-medium text-slate-500 xl:sr-only">{t("agentAssignmentModel")}</span>
                      <input
                        aria-label={`${row.displayName} ${t("agentAssignmentModel")}`}
                        className={`${fieldClassName} min-h-11`}
                        disabled={controlDisabled || !draft.providerId}
                        onChange={(event) => updateDraft(row.agentId, { modelName: event.target.value })}
                        placeholder={selectedProvider?.default_model ?? t("agentAssignmentModelPlaceholder")}
                        value={draft.modelName}
                      />
                    </label>
                  </td>
                  <td className="block min-w-0 align-top xl:table-cell xl:px-4 xl:py-4">
                    <span className="mb-1 block text-xs font-medium text-slate-500 xl:hidden">{t("agentAssignmentConnection")}</span>
                    {row.status === "planned" ? (
                      <span className="text-sm text-slate-500">{t("agentAssignmentNotImplemented")}</span>
                    ) : row.providerRequirement === "server_managed" ? (
                      <span className="text-sm text-slate-600">{t("agentAssignmentServerManaged")}</span>
                    ) : (
                      <>
                        <Badge tone={row.providerIsActive === false ? "gray" : "teal"}>
                          {row.providerName ?? t("agentAssignmentAuto")}
                        </Badge>
                        {row.effectiveModel ? (
                          <p className="mt-2 text-xs text-slate-600">{row.effectiveModel}</p>
                        ) : null}
                      </>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
