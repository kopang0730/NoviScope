import type { FormEvent } from "react";
import { useCallback, useEffect, useState } from "react";
import { createProvider, getProviders, updateProvider } from "../api/providers";
import { getErrorMessage } from "../api/client";
import type { Provider, ProviderKind, ProviderScope } from "../api/types";
import { useAuth } from "../auth/auth-context";
import { Badge } from "../components/badge";
import { Button } from "../components/button";
import { Card, CardHeading } from "../components/card";
import { Input, Select } from "../components/input";
import { MobileStack, Table, TableCell, TableHead } from "../components/table";
import { formatDateTime, labelFromEnum } from "../lib/format";

const providerKinds: ProviderKind[] = ["openai_compatible", "anthropic", "custom"];

type FormState = {
  apiKey: string;
  baseUrl: string;
  defaultModel: string;
  isActive: boolean;
  kind: ProviderKind;
  name: string;
  scope: ProviderScope;
};

const initialFormState: FormState = {
  apiKey: "",
  baseUrl: "https://api.openai.com/v1",
  defaultModel: "",
  isActive: true,
  kind: "openai_compatible",
  name: "",
  scope: "personal",
};

function scopeBadgeTone(scope: ProviderScope) {
  return scope === "shared" ? "teal" : "blue";
}

function providerToFormState(provider: Provider): FormState {
  return {
    apiKey: "",
    baseUrl: provider.base_url,
    defaultModel: provider.default_model,
    isActive: provider.is_active,
    kind: provider.kind,
    name: provider.name,
    scope: provider.scope,
  };
}

export function ProviderSettingsPage() {
  const { currentUser } = useAuth();
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingError, setLoadingError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formState, setFormState] = useState<FormState>(initialFormState);
  const [editingProviderId, setEditingProviderId] = useState<string | null>(null);

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

  function canEditProvider(provider: Provider) {
    if (!currentUser) {
      return false;
    }
    return currentUser.role === "admin" || provider.owner_user_id === currentUser.id;
  }

  function startEditingProvider(provider: Provider) {
    setSubmitError(null);
    setEditingProviderId(provider.id);
    setFormState(providerToFormState(provider));
  }

  function resetForm() {
    setSubmitError(null);
    setEditingProviderId(null);
    setFormState(initialFormState);
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
          ...initialFormState,
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

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
      <Card>
        <CardHeading
          description="List the providers visible to the current user. Shared providers are admin-managed."
          title="Providers"
        />
        {!currentUser ? (
          <p className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
            Sign in to load provider data. The table and form still render so the UI can be reviewed without API data.
          </p>
        ) : null}
        {loadingError ? <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{loadingError}</p> : null}
        {loading ? <p className="mt-4 text-sm text-slate-500">Loading providers...</p> : null}
        {!loading && providers.length === 0 ? (
          <p className="mt-4 rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
            No providers available yet.
          </p>
        ) : null}
        {providers.length > 0 ? (
          <>
            <Table className="mt-4">
              <thead>
                <tr>
                  <TableHead>Name</TableHead>
                  <TableHead>Kind</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Scope</TableHead>
                  <TableHead>Updated</TableHead>
                  <TableHead>Actions</TableHead>
                </tr>
              </thead>
              <tbody>
                {providers.map((provider) => (
                  <tr key={provider.id}>
                    <TableCell>
                      <div className="font-medium text-slate-900">{provider.name}</div>
                      <div className="mt-1 text-xs text-slate-500">{provider.base_url}</div>
                    </TableCell>
                    <TableCell>{labelFromEnum(provider.kind)}</TableCell>
                    <TableCell>{provider.default_model}</TableCell>
                    <TableCell>
                      <Badge tone={scopeBadgeTone(provider.scope)}>{labelFromEnum(provider.scope)}</Badge>
                    </TableCell>
                    <TableCell>{formatDateTime(provider.updated_at)}</TableCell>
                    <TableCell>
                      {canEditProvider(provider) ? (
                        <Button
                          aria-label={`Edit ${provider.name}`}
                          onClick={() => startEditingProvider(provider)}
                          size="sm"
                          variant="secondary"
                        >
                          Edit
                        </Button>
                      ) : (
                        <span className="text-sm text-slate-400">View only</span>
                      )}
                    </TableCell>
                  </tr>
                ))}
              </tbody>
            </Table>
            <MobileStack>
              {providers.map((provider) => (
                <div className="rounded-lg border border-slate-200 bg-white p-4" key={provider.id}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium text-slate-900">{provider.name}</p>
                      <p className="mt-1 text-sm text-slate-500">{provider.default_model}</p>
                    </div>
                    <Badge tone={scopeBadgeTone(provider.scope)}>{labelFromEnum(provider.scope)}</Badge>
                  </div>
                  <p className="mt-3 text-sm text-slate-600">{provider.base_url}</p>
                  <p className="mt-2 text-xs text-slate-500">Updated {formatDateTime(provider.updated_at)}</p>
                  {canEditProvider(provider) ? (
                    <Button
                      className="mt-4 w-full"
                      onClick={() => startEditingProvider(provider)}
                      size="sm"
                      variant="secondary"
                    >
                      Edit
                    </Button>
                  ) : null}
                </div>
              ))}
            </MobileStack>
          </>
        ) : null}
      </Card>

      <Card>
        <CardHeading
          description={
            isEditing
              ? "Update provider metadata. Leave API key blank to keep the stored key."
              : "Create a new provider using the current backend contract."
          }
          title={isEditing ? "Edit Provider" : "Add Provider"}
        />
        <form className="mt-6 space-y-4" onSubmit={(event) => void handleSubmit(event)}>
          <Input
            label="Name"
            onChange={(event) => setFormState((current) => ({ ...current, name: event.target.value }))}
            placeholder="GPT-4o Lab Shared"
            required
            value={formState.name}
          />
          <Select
            label="Provider Kind"
            onChange={(event) => setFormState((current) => ({ ...current, kind: event.target.value as ProviderKind }))}
            value={formState.kind}
          >
            {providerKinds.map((kind) => (
              <option key={kind} value={kind}>
                {labelFromEnum(kind)}
              </option>
            ))}
          </Select>
          <Input
            label="Base URL"
            onChange={(event) => setFormState((current) => ({ ...current, baseUrl: event.target.value }))}
            required
            type="url"
            value={formState.baseUrl}
          />
          <Input
            label="Default Model"
            onChange={(event) => setFormState((current) => ({ ...current, defaultModel: event.target.value }))}
            placeholder="gpt-4o"
            required
            value={formState.defaultModel}
          />
          <Input
            label="API Key"
            onChange={(event) => setFormState((current) => ({ ...current, apiKey: event.target.value }))}
            placeholder={isEditing ? "Leave blank to keep existing key" : "sk-..."}
            required={!isEditing}
            type="password"
            value={formState.apiKey}
          />
          {isEditing ? (
            <label className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
              <input
                checked={formState.isActive}
                className="h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                onChange={(event) => setFormState((current) => ({ ...current, isActive: event.target.checked }))}
                type="checkbox"
              />
              <span className="text-sm font-medium text-slate-700">Provider enabled</span>
            </label>
          ) : null}
          <Select
            disabled={isEditing}
            hint={
              isEditing
                ? "Scope cannot be changed after creation in the current backend contract."
                : currentUser?.role === "admin"
                  ? "Admins may create personal or shared providers."
                  : "Members can create personal providers only."
            }
            label="Scope"
            onChange={(event) => setFormState((current) => ({ ...current, scope: event.target.value as ProviderScope }))}
            value={formState.scope}
          >
            <option value="personal">Personal</option>
            <option disabled={currentUser?.role !== "admin"} value="shared">
              Shared
            </option>
          </Select>
          {submitError ? <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{submitError}</p> : null}
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button className="w-full" loading={submitting} type="submit">
              {isEditing ? "Save Changes" : "Save Provider"}
            </Button>
            {isEditing ? (
              <Button className="w-full" disabled={submitting} onClick={resetForm} type="button" variant="secondary">
                Cancel Edit
              </Button>
            ) : null}
          </div>
        </form>
      </Card>
    </div>
  );
}
