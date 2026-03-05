import { describe, expect, it } from "vitest";
import { buildErrorHints, parseErrorCode, parseRequestId } from "./error_hints";

describe("error_hints", () => {
  it("parses error code from prefixed message", () => {
    expect(parseErrorCode("AUTH_TOKEN_INVALID: Invalid Bearer token.")).toBe(
      "AUTH_TOKEN_INVALID"
    );
  });

  it("parses request_id from metadata suffix", () => {
    expect(parseRequestId("x failed (request_id: req_123-abc)")).toBe("req_123-abc");
  });

  it("returns exact error hints for known code", () => {
    expect(buildErrorHints("AUTH_TOKEN_MISSING: Missing Bearer token.")).toEqual([
      "Set token in client env (VITE_API_TOKEN) and retry.",
      "Ensure request includes Authorization: Bearer <token>."
    ]);
  });

  it("returns prefix error hints for grouped code", () => {
    expect(buildErrorHints("CHAT_PROVIDER_ERROR_TIMEOUT: upstream timeout")).toEqual([
      "Check provider API key / endpoint / model.",
      "Retry after confirming outbound network from backend."
    ]);
  });

  it("returns no hints when no code is available", () => {
    expect(buildErrorHints("unexpected failure")).toEqual([]);
  });
});
