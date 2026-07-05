import type { FormEvent } from "react";
import { useCallback, useEffect, useState } from "react";
import {
  createProvider,
  getProviders,
  testProviderConnection,
  updateProvider,
  type ProviderConnectionTestResult,
} from "../api/providers";
import { getErrorMessage } from "../api/client";
import type { Provider } from "../api/types";
import { useAuth } from "../auth/auth-context";
import { ProviderFormCard } from "../components/provider-form-card";
import { ProviderListCard } from "../components/provider-list-card";
import {
  initialProviderFormState,
  providerToFormState,
  type ProviderFormState,
} from "../lib/provider-form";

export function ProviderSettingsPage() {
  const { currentUser } = useAuth();
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingError, setLoadingError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [editingProviderId, setEditingProviderId] = useState<string | null>(null);
  const [formState, setFormState] = useState<ProviderFormState>(initialProviderFormState);
  const [testingProviderId, setTestingProviderId] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, ProviderConnectionTestResult>>({});

  const isEditing = editingProviderId !== null;

  const loadProviders = useCallback(async () => {
    if (!currentUser) {
      setProviders([]);
      setLoading(false);
      setLoadingError(null);
      return;
    }

    setLoading(true);
    setLoadingError(null);

    try {
      setProviders(await getProviders());
    } catch (error) {
      setLoadingError(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, [currentUser]);

  useEffect(() => {
    void loadProviders();
  }, [loadProviders]);

  function resetForm() {
    setSubmitError(null);
    setEditingProviderId(null);
    setFormState(initialProviderFormState);
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
        });
      }
      await loadProviders();
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
    <div className="grid gap-4 2xl:grid-cols-[minmax(0,1.35fr)_minmax(340px,0.65fr)]">
      <ProviderListCard
        currentUser={currentUser}
        loading={loading}
        loadingError={loadingError}
        onEdit={startEditingProvider}
        onTest={(provider) => void handleTestProvider(provider)}
        providers={providers}
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
        submitError={submitError}
        submitting={submitting}
      />
    </div>
  );
}
