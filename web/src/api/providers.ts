import { apiRequest } from "./client";
import type { Provider, ProviderKind, ProviderScope } from "./types";

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
