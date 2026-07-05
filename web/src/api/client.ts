export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

type RequestOptions = Omit<RequestInit, "body" | "credentials"> & {
  body?: unknown;
};

function extractMessage(payload: unknown, fallback: string) {
  if (typeof payload === "string" && payload.trim()) {
    return payload;
  }

  if (payload && typeof payload === "object") {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  }

  return fallback;
}

function buildFallbackMessage(path: string, status: number, payload: unknown) {
  const hasPayload =
    payload !== null &&
    payload !== undefined &&
    !(typeof payload === "string" && payload.trim().length === 0);

  if (status >= 500 && !hasPayload) {
    return `NoviScope API is unavailable right now for ${path}. If the backend is not running, start it and refresh.`;
  }

  return `Request failed with status ${status}.`;
}

export function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unexpected error";
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, headers, method, ...rest } = options;
  const requestHeaders = new Headers(headers);

  if (body !== undefined && !requestHeaders.has("Content-Type")) {
    requestHeaders.set("Content-Type", "application/json");
  }

  if (!requestHeaders.has("Accept")) {
    requestHeaders.set("Accept", "application/json");
  }

  let response: Response;

  try {
    response = await fetch(path, {
      ...rest,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "include",
      headers: requestHeaders,
      method: method ?? (body === undefined ? "GET" : "POST"),
    });
  } catch {
    throw new Error("Unable to reach the NoviScope API. Check whether the backend is running.");
  }

  const contentType = response.headers.get("content-type") ?? "";
  const payload =
    response.status === 204
      ? null
      : contentType.includes("application/json")
        ? await response.json().catch(() => null)
        : await response.text().catch(() => null);

  if (!response.ok) {
    throw new ApiError(extractMessage(payload, buildFallbackMessage(path, response.status, payload)), response.status, payload);
  }

  return payload as T;
}
