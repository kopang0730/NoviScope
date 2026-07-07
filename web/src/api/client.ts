export class ApiError extends Error {
  readonly payload: unknown;
  readonly status: number;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

export class ApiConnectionError extends Error {
  readonly cause: Error;
  readonly name = "ApiConnectionError";
  readonly path: string;

  constructor(path: string, cause: Error) {
    super("Unable to reach the NoviScope API. Check whether the backend is running.");
    this.cause = cause;
    this.path = path;
  }
}

type ApiResponseParseErrorInput = {
  readonly cause: Error;
  readonly contentType: string;
  readonly path: string;
  readonly status: number;
};

export class ApiResponseParseError extends Error {
  readonly cause: Error;
  readonly contentType: string;
  readonly name = "ApiResponseParseError";
  readonly path: string;
  readonly status: number;

  constructor(input: ApiResponseParseErrorInput) {
    super(`NoviScope API returned a malformed response for ${input.path}.`);
    this.cause = input.cause;
    this.contentType = input.contentType;
    this.path = input.path;
    this.status = input.status;
  }
}

type RequestOptions = Omit<RequestInit, "body" | "credentials"> & {
  readonly body?: unknown;
};

type ParsedPayload =
  | { readonly kind: "parsed"; readonly payload: unknown }
  | { readonly error: ApiResponseParseError; readonly kind: "parse_failed" };

type ParseFailurePayload = {
  readonly content_type: string;
  readonly error_kind: "response_parse_failed";
  readonly message: string;
  readonly status: number;
};

function isRecord(payload: unknown): payload is Record<string, unknown> {
  return typeof payload === "object" && payload !== null && !Array.isArray(payload);
}

function extractMessage(payload: unknown, fallback: string): string {
  if (typeof payload === "string" && payload.trim()) {
    return payload;
  }

  if (isRecord(payload)) {
    const detail = payload.detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  }

  return fallback;
}

function buildFallbackMessage(path: string, status: number, payload: unknown): string {
  const hasPayload =
    payload !== null &&
    payload !== undefined &&
    !(typeof payload === "string" && payload.trim().length === 0);

  if (status >= 500 && !hasPayload) {
    return `NoviScope API is unavailable right now for ${path}. If the backend is not running, start it and refresh.`;
  }

  return `Request failed with status ${status}.`;
}

function buildParseFailurePayload(error: ApiResponseParseError): ParseFailurePayload {
  return {
    content_type: error.contentType,
    error_kind: "response_parse_failed",
    message: error.message,
    status: error.status,
  };
}

async function parseResponsePayload(response: Response, path: string): Promise<ParsedPayload> {
  const contentType = response.headers.get("content-type") ?? "";

  if (response.status === 204) {
    return { kind: "parsed", payload: null };
  }

  try {
    if (contentType.includes("application/json")) {
      const payload: unknown = await response.json();
      return { kind: "parsed", payload };
    }

    return { kind: "parsed", payload: await response.text() };
  } catch (error) {
    if (error instanceof Error) {
      return {
        error: new ApiResponseParseError({
          cause: error,
          contentType,
          path,
          status: response.status,
        }),
        kind: "parse_failed",
      };
    }

    throw error;
  }
}

export function getErrorMessage(error: unknown): string {
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
  } catch (error) {
    if (error instanceof Error) {
      throw new ApiConnectionError(path, error);
    }

    throw error;
  }

  const parsedPayload = await parseResponsePayload(response, path);

  if (parsedPayload.kind === "parse_failed") {
    if (response.ok) {
      throw parsedPayload.error;
    }

    const payload = buildParseFailurePayload(parsedPayload.error);
    throw new ApiError(
      extractMessage(payload, buildFallbackMessage(path, response.status, payload)),
      response.status,
      payload,
    );
  }

  const { payload } = parsedPayload;
  if (!response.ok) {
    throw new ApiError(
      extractMessage(payload, buildFallbackMessage(path, response.status, payload)),
      response.status,
      payload,
    );
  }

  return payload as T;
}
