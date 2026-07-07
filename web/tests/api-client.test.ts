import { afterEach, describe, expect, it } from "bun:test";
import { ApiConnectionError, ApiResponseParseError, apiRequest } from "../src/api/client";

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
});

function installFetch(handler: typeof fetch): void {
  globalThis.fetch = handler;
}

describe("apiRequest", () => {
  it("throws a typed connection error with the original cause when fetch fails", async () => {
    // Given: the browser cannot reach the backend API.
    const cause = new TypeError("fetch failed");
    installFetch(async () => {
      throw cause;
    });

    // When: a request is made through the shared API client.
    const request = apiRequest<unknown>("/api/auth/me");

    // Then: callers receive a typed error without losing the underlying cause.
    await expect(request).rejects.toBeInstanceOf(ApiConnectionError);
    try {
      await request;
    } catch (error) {
      if (!(error instanceof ApiConnectionError)) {
        throw error;
      }
      expect(error.cause).toBe(cause);
    }
  });

  it("throws a typed parse error when a successful JSON response is malformed", async () => {
    // Given: the API returns a successful response with invalid JSON.
    installFetch(
      async () => new Response("{", { headers: { "content-type": "application/json" }, status: 200 }),
    );

    // When: a request expects the shared client to decode the response.
    const request = apiRequest<unknown>("/api/quests");

    // Then: the malformed payload is surfaced instead of silently becoming null.
    await expect(request).rejects.toBeInstanceOf(ApiResponseParseError);
    try {
      await request;
    } catch (error) {
      if (!(error instanceof ApiResponseParseError)) {
        throw error;
      }
      expect(error.path).toBe("/api/quests");
      expect(error.status).toBe(200);
    }
  });
});
