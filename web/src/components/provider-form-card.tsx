import type { FormEvent } from "react";
import type { ProviderApiMode, ProviderKind, User } from "../api/types";
import { useI18n } from "../i18n/i18n-context";
import { labelFromEnum } from "../lib/format";
import type { ProviderFormState } from "../lib/provider-form";
import type { ProviderScopeTab } from "../lib/provider-settings-view";
import { Badge } from "./badge";
import { Button } from "./button";
import { Card, CardHeading } from "./card";
import { Input, Select } from "./input";

const providerKinds: readonly ProviderKind[] = ["openai_compatible", "anthropic", "custom"];
const providerApiModes: readonly ProviderApiMode[] = [
  "auto",
  "chat_completions",
  "responses",
];

function unsupportedProviderApiMode(mode: never): never {
  throw new TypeError(`Unsupported provider API mode: ${mode}`);
}

type ProviderFormCardProps = {
  readonly currentUser: User | null;
  readonly formState: ProviderFormState;
  readonly isEditing: boolean;
  readonly onCancelEdit: () => void;
  readonly onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  readonly onUpdate: (formState: ProviderFormState) => void;
  readonly scope: ProviderScopeTab;
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
  scope,
  submitError,
  submitting,
}: ProviderFormCardProps) {
  const { t } = useI18n();

  function updateField<Key extends keyof ProviderFormState>(key: Key, value: ProviderFormState[Key]) {
    onUpdate({ ...formState, [key]: value });
  }

  function providerKindFromValue(value: string): ProviderKind {
    return providerKinds.find((kind) => kind === value) ?? "openai_compatible";
  }

  function providerApiModeFromValue(value: string): ProviderApiMode {
    return providerApiModes.find((mode) => mode === value) ?? "auto";
  }

  function providerApiModeLabel(mode: ProviderApiMode) {
    switch (mode) {
      case "auto":
        return t("providerApiModeAuto");
      case "chat_completions":
        return t("providerApiModeChatCompletions");
      case "responses":
        return t("providerApiModeResponses");
      default:
        return unsupportedProviderApiMode(mode);
    }
  }

  function updateProviderKind(kind: ProviderKind) {
    onUpdate({
      ...formState,
      apiMode: kind === "anthropic" ? "auto" : formState.apiMode,
      kind,
    });
  }

  const canCreateInScope = scope === "personal" || currentUser?.role === "admin";

  if (!isEditing && !canCreateInScope) {
    return (
      <Card>
        <CardHeading
          description={t("providerSharedCreateAdminOnly")}
          title={t("providerAddTitle")}
        />
        <p className="mt-5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-600">
          {t("providerSharedCreatePersonalPrompt")}
        </p>
      </Card>
    );
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
          onChange={(event) => updateProviderKind(providerKindFromValue(event.target.value))}
          value={formState.kind}
        >
          {providerKinds.map((kind) => (
            <option key={kind} value={kind}>
              {labelFromEnum(kind)}
            </option>
          ))}
        </Select>
        {formState.kind !== "anthropic" ? (
          <Select
            hint={t("providerApiModeHint")}
            label={t("providerApiMode")}
            onChange={(event) =>
              updateField("apiMode", providerApiModeFromValue(event.target.value))
            }
            value={formState.apiMode}
          >
            {providerApiModes.map((mode) => (
              <option key={mode} value={mode}>
                {providerApiModeLabel(mode)}
              </option>
            ))}
          </Select>
        ) : null}
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
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3">
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm font-medium text-slate-700">{t("providerScope")}</span>
            <Badge tone={formState.scope === "shared" ? "teal" : "blue"}>
              {formState.scope === "shared" ? t("scopeShared") : t("scopePersonal")}
            </Badge>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            {isEditing
              ? t("providerScopeLockedHint")
              : formState.scope === "shared"
                ? t("providerSharedDefaultsDescription")
                : t("providerPersonalOverrideDescription")}
          </p>
        </div>
        {submitError ? <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{submitError}</p> : null}
        <Button className="w-full" loading={submitting} type="submit">
          {isEditing ? t("providerUpdate") : t("providerSave")}
        </Button>
      </form>
    </Card>
  );
}
