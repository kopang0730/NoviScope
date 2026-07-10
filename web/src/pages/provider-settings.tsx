import type { FormEvent } from "react";
import { useCallback, useEffect, useState } from "react";
import {
  getAgentAssignments,
  updateAgentAssignment,
} from "../api/agent-assignments";
import {
  createProvider,
  getProviders,
  testProviderConnection,
  updateProvider,
  type ProviderConnectionTestResult,
} from "../api/providers";
import { getErrorMessage } from "../api/client";
import type { AgentAssignment, Provider, WorkflowAgentCapability } from "../api/types";
import { getWorkflowCapabilities } from "../api/workflow";
import { useAuth } from "../auth/auth-context";
import { AgentAssignmentMatrix } from "../components/agent-assignment-matrix";
import { ProviderFormCard } from "../components/provider-form-card";
import { ProviderListCard } from "../components/provider-list-card";
import { ProviderScopeTabs } from "../components/provider-scope-tabs";
import { useI18n } from "../i18n/i18n-context";
import {
  initialProviderFormState,
  providerToFormState,
  type ProviderFormState,
} from "../lib/provider-form";
import {
  filterProviders,
  type ProviderScopeTab,
} from "../lib/provider-settings-view";

export function ProviderSettingsPage() {
  const { currentUser } = useAuth();
  const { t } = useI18n();
  const [assignments, setAssignments] = useState<readonly AgentAssignment[]>([]);
  const [capabilities, setCapabilities] = useState<readonly WorkflowAgentCapability[]>([]);
  const [providers, setProviders] = useState<readonly Provider[]>([]);
  const [activeScope, setActiveScope] = useState<ProviderScopeTab>("personal");
  const [assignmentError, setAssignmentError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingError, setLoadingError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [editingProviderId, setEditingProviderId] = useState<string | null>(null);
  const [formState, setFormState] = useState<ProviderFormState>(initialProviderFormState);
  const [testingProviderId, setTestingProviderId] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, ProviderConnectionTestResult>>({});

  const isEditing = editingProviderId !== null;
  const visibleProviders = filterProviders(providers, activeScope);

  useEffect(() => {
    if (!currentUser) {
      return;
    }
    const defaultScope = currentUser.role === "admin" ? "shared" : "personal";
    setActiveScope(defaultScope);
    setFormState({ ...initialProviderFormState, scope: defaultScope });
  }, [currentUser]);

  const loadProviderData = useCallback(async () => {
    if (!currentUser) {
      setAssignments([]);
      setCapabilities([]);
      setProviders([]);
      setAssignmentError(null);
      setLoading(false);
      setLoadingError(null);
      return;
    }

    setLoading(true);
    setLoadingError(null);
    setAssignmentError(null);

    try {
      const [nextProviders, nextAssignments, nextCapabilities] = await Promise.all([
        getProviders(),
        getAgentAssignments(),
        getWorkflowCapabilities(),
      ]);
      setProviders(nextProviders);
      setAssignments(nextAssignments);
      setCapabilities(nextCapabilities);
    } catch (error) {
      const message = getErrorMessage(error);
      setAssignmentError(message);
      setLoadingError(message);
    } finally {
      setLoading(false);
    }
  }, [currentUser]);

  useEffect(() => {
    void loadProviderData();
  }, [loadProviderData]);

  const reloadAssignments = useCallback(async () => {
    try {
      const nextAssignments = await getAgentAssignments();
      setAssignments(nextAssignments);
      setAssignmentError(null);
    } catch (error) {
      setAssignmentError(getErrorMessage(error));
      throw error;
    }
  }, []);

  function resetForm() {
    setSubmitError(null);
    setEditingProviderId(null);
    setFormState({ ...initialProviderFormState, scope: activeScope });
  }

  function changeScope(scope: ProviderScopeTab) {
    setActiveScope(scope);
    setSubmitError(null);
    setEditingProviderId(null);
    setFormState({ ...initialProviderFormState, scope });
  }

  function startEditingProvider(provider: Provider) {
    setSubmitError(null);
    setEditingProviderId(provider.id);
    setFormState(providerToFormState(provider));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);
    setSubmitting(true);

    try {
      if (editingProviderId) {
        await updateProvider(editingProviderId, {
          ...(formState.apiKey.trim() ? { api_key: formState.apiKey } : {}),
          base_url: formState.baseUrl,
          default_model: formState.defaultModel,
          is_active: formState.isActive,
          kind: formState.kind,
          name: formState.name,
        });
        resetForm();
      } else {
        await createProvider({
          api_key: formState.apiKey,
          base_url: formState.baseUrl,
          default_model: formState.defaultModel,
          kind: formState.kind,
          name: formState.name,
          scope: formState.scope,
        });
        setFormState({
          ...initialProviderFormState,
          baseUrl: formState.baseUrl,
          kind: formState.kind,
          scope: activeScope,
        });
      }
      await loadProviderData();
    } catch (error) {
      setSubmitError(getErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleTestProvider(provider: Provider) {
    setTestingProviderId(provider.id);
    try {
      const result = await testProviderConnection(provider.id);
      setTestResults((current) => ({ ...current, [provider.id]: result }));
    } catch (error) {
      setTestResults((current) => ({
        ...current,
        [provider.id]: {
          message: getErrorMessage(error),
          model: provider.default_model,
          ok: false,
          provider_id: provider.id,
        },
      }));
    } finally {
      setTestingProviderId(null);
    }
  }

  return (
    <div className="grid gap-4">
      <ProviderScopeTabs
        activeScope={activeScope}
        onChange={changeScope}
        providers={providers}
      />
      <div className="grid gap-4 2xl:grid-cols-[minmax(0,1.35fr)_minmax(340px,0.65fr)]">
        <ProviderListCard
          currentUser={currentUser}
          loading={loading}
          loadingError={loadingError}
          onEdit={startEditingProvider}
          onTest={(provider) => void handleTestProvider(provider)}
          providers={visibleProviders}
          scope={activeScope}
          testResults={testResults}
          testingProviderId={testingProviderId}
        />
        <ProviderFormCard
          currentUser={currentUser}
          formState={formState}
          isEditing={isEditing}
          onCancelEdit={resetForm}
          onSubmit={(event) => void handleSubmit(event)}
          onUpdate={setFormState}
          scope={activeScope}
          submitError={submitError}
          submitting={submitting}
        />
      </div>
      {activeScope === "shared" ? (
        <AgentAssignmentMatrix
          assignments={assignments}
          capabilities={capabilities}
          currentUser={currentUser}
          error={assignmentError}
          loading={loading}
          onReload={reloadAssignments}
          onUpdate={updateAgentAssignment}
          providers={providers}
        />
      ) : (
        <p className="rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">
          {t("providerPersonalOverrideDescription")}
        </p>
      )}
    </div>
  );
}
