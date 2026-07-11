import type { Provider } from "../api/types";

export function getActivePersonalProviders(
  providers: readonly Provider[],
  currentUserId: string | null,
): readonly Provider[] {
  return providers.filter(
    (provider) =>
      provider.is_active
      && provider.scope === "personal"
      && provider.owner_user_id === currentUserId,
  );
}
