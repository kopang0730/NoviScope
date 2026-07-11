import { apiRequest } from "./client";
import type { Provider, ProviderApiMode, ProviderKind, ProviderScope } from "./types";

type ProvidersResponse = {
  providers: Provider[];
};

export type CreateProviderPayload = {
  name: string;
  kind: ProviderKind;
  base_url: string;
  default_model: string;
  api_key: string;
  scope: ProviderScope;
  api_mode: ProviderApiMode;
};

export type UpdateProviderPayload = {
  name?: string;
  kind?: ProviderKind;
  base_url?: string;
  default_model?: string;
  api_key?: string;
  is_active?: boolean;
  api_mode?: ProviderApiMode;
};

export type ProviderConnectionTestResult = {
  ok: boolean;
  provider_id: string;
  model: string;
  message: string;
};

export async function getProviders() {
  const response = await apiRequest<ProvidersResponse>("/api/providers");
  return response.providers;
}

export function createProvider(payload: CreateProviderPayload) {
  return apiRequest<Provider>("/api/providers", {
    body: payload,
    method: "POST",
  });
}

export function updateProvider(providerId: string, payload: UpdateProviderPayload) {
  return apiRequest<Provider>(`/api/providers/${providerId}`, {
    body: payload,
    method: "PATCH",
  });
}

export function testProviderConnection(providerId: string) {
  return apiRequest<ProviderConnectionTestResult>(`/api/providers/${providerId}/test`, {
    method: "POST",
  });
}
