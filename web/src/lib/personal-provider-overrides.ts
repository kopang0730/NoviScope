import type { Provider } from "../api/types";

export function getActivePersonalProviders(
  providers: readonly Provider[],
): readonly Provider[] {
  return providers.filter((provider) => provider.is_active && provider.scope === "personal");
}
