export function readRedirectPath(state: unknown) {
  if (typeof state !== "object" || state === null || !("from" in state)) {
    return "/";
  }

  const { from } = state;
  return typeof from === "string" && from.startsWith("/") && !from.startsWith("//") ? from : "/";
}
