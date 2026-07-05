import type { Provider, ProviderKind, ProviderScope, User } from "../api/types";

export type ProviderFormState = {
  readonly apiKey: string;
  readonly baseUrl: string;
  readonly defaultModel: string;
  readonly isActive: boolean;
  readonly kind: ProviderKind;
  readonly name: string;
  readonly scope: ProviderScope;
};

export const initialProviderFormState: ProviderFormState = {
  apiKey: "",
  baseUrl: "https://api.openai.com/v1",
  defaultModel: "",
  isActive: true,
  kind: "openai_compatible",
  name: "",
  scope: "personal",
};

export function providerToFormState(provider: Provider): ProviderFormState {
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

export function canManageProvider(provider: Provider, currentUser: User | null) {
  if (!currentUser) {
    return false;
  }
  return currentUser.role === "admin" || provider.owner_user_id === currentUser.id;
}
