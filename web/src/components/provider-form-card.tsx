import type { FormEvent } from "react";
import type { ProviderKind, ProviderScope, User } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import type { ProviderFormState } from "../lib/provider-form";
import { Button } from "./button";
import { Card, CardHeading } from "./card";
import { Input, Select } from "./input";

const providerKinds: readonly ProviderKind[] = ["openai_compatible", "anthropic", "custom"];

type ProviderFormCardProps = {
  readonly currentUser: User | null;
  readonly formState: ProviderFormState;
  readonly isEditing: boolean;
  readonly onCancelEdit: () => void;
  readonly onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  readonly onUpdate: (formState: ProviderFormState) => void;
  readonly submitError: string | null;
  readonly submitting: boolean;
};

export function ProviderFormCard({
  currentUser,
  formState,
  isEditing,
  onCancelEdit,
  onSubmit,
  onUpdate,
  submitError,
  submitting,
}: ProviderFormCardProps) {
  const { t } = useI18n();

  function updateField<Key extends keyof ProviderFormState>(key: Key, value: ProviderFormState[Key]) {
    onUpdate({ ...formState, [key]: value });
  }

  return (
    <Card>
      <CardHeading
        action={
          isEditing ? (
            <Button onClick={onCancelEdit} size="sm" variant="secondary">
              {t("providerCancelEdit")}
            </Button>
          ) : null
        }
        description={isEditing ? t("providerEditDescription") : t("providerAddDescription")}
        title={isEditing ? t("providerEditTitle") : t("providerAddTitle")}
      />
      <form className="mt-6 space-y-4" onSubmit={onSubmit}>
        <Input
          label={t("providerName")}
          onChange={(event) => updateField("name", event.target.value)}
          placeholder="GPT-4o Lab Shared"
          required
          value={formState.name}
        />
        <Select
          label={t("providerKind")}
          onChange={(event) => updateField("kind", event.target.value as ProviderKind)}
          value={formState.kind}
        >
          {providerKinds.map((kind) => (
            <option key={kind} value={kind}>
              {labelFromEnum(kind)}
            </option>
          ))}
        </Select>
        <Input
          label={t("providerBaseUrl")}
          onChange={(event) => updateField("baseUrl", event.target.value)}
          required
          type="url"
          value={formState.baseUrl}
        />
        <Input
          label={t("providerDefaultModel")}
          onChange={(event) => updateField("defaultModel", event.target.value)}
          placeholder="gpt-4o"
          required
          value={formState.defaultModel}
        />
        <Input
          label={t("providerApiKey")}
          onChange={(event) => updateField("apiKey", event.target.value)}
          placeholder={isEditing ? t("providerKeepKeyPlaceholder") : "sk-..."}
          required={!isEditing}
          type="password"
          value={formState.apiKey}
        />
        {isEditing ? (
          <label className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
            <input
              checked={formState.isActive}
              className="h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
              onChange={(event) => updateField("isActive", event.target.checked)}
              type="checkbox"
            />
            <span className="text-sm font-medium text-slate-700">{t("providerEnabled")}</span>
          </label>
        ) : null}
        <Select
          disabled={isEditing}
          hint={
            isEditing
              ? t("providerScopeLockedHint")
              : currentUser?.role === "admin"
                ? t("providerScopeSharedHint")
                : t("providerScopePersonalHint")
          }
          label={t("providerScope")}
          onChange={(event) => updateField("scope", event.target.value as ProviderScope)}
          value={formState.scope}
        >
          <option value="personal">{t("scopePersonal")}</option>
          <option disabled={currentUser?.role !== "admin"} value="shared">
            {t("scopeShared")}
          </option>
        </Select>
        {submitError ? <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{submitError}</p> : null}
        <Button className="w-full" loading={submitting} type="submit">
          {isEditing ? t("providerUpdate") : t("providerSave")}
        </Button>
      </form>
    </Card>
  );
}
