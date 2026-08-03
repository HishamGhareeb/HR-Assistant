import { describe, expect, it, vi, afterEach } from "vitest";
import { api, ApiError } from "./client";

function mockFetchOnce(status: number, body: unknown, ok = status >= 200 && status < 300) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok,
      status,
      statusText: "status",
      json: async () => body,
    }),
  );
}

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("attaches the bearer token and JSON content-type when a body is present", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ answer: "ok", suggestions: [], blocked: false, request_id: "req-1" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await api.askQuestion("token-123", { question: "hi" });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers["Authorization"]).toBe("Bearer token-123");
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(init.body)).toEqual({ question: "hi" });
  });

  it("serializes search params, skipping undefined values", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);

    await api.listFeedback("token-123", { helpful: false, escalatedOnly: undefined });

    const [url] = fetchMock.mock.calls[0];
    expect(url).toBe("/v1/hr/feedback?helpful=false");
  });

  it("throws ApiError with the response's detail on failure", async () => {
    mockFetchOnce(403, { detail: "Not authorized to review answer feedback" });

    await expect(api.listFeedback("token-123")).rejects.toMatchObject({
      status: 403,
      detail: "Not authorized to review answer feedback",
    });
  });

  it("falls back to statusText when the error body isn't JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: "Not Found",
        json: async () => {
          throw new Error("not json");
        },
      }),
    );

    try {
      await api.getQualitySummary("token-123");
      expect.unreachable();
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(404);
      expect((err as ApiError).detail).toBe("Not Found");
    }
  });

  it("mints a dev token without requiring a bearer token", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ access_token: "abc", token_type: "bearer", expires_in: 3600 }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await api.mintDevToken({ tenant_id: "acme", user_id: "sarah" });

    expect(result.access_token).toBe("abc");
    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers["Authorization"]).toBeUndefined();
  });
});
