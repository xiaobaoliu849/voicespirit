import { afterEach, describe, expect, it, vi } from "vitest";

import { streamChatCompletion } from "./api";

function createStreamResponse(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

describe("chat stream parsing", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("preserves leading spaces inside streamed delta chunks", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      createStreamResponse([
        'event: delta\ndata: {"content":"Hello"}\n\n',
        'event: delta\ndata: {"content":" there"}\n\n',
        'event: done\ndata: {"memories_retrieved":1,"memory_saved":true}\n\n',
      ])
    );
    vi.stubGlobal("fetch", fetchMock);

    let output = "";
    let meta: { memoriesRetrieved: number; memorySaved: boolean } | undefined;
    await streamChatCompletion(
      {
        provider: "DashScope",
        model: "qwen-plus",
        messages: [{ role: "user", content: "hello" }],
      },
      {
        onDelta: (chunk) => {
          output += chunk;
        },
        onDone: (result) => {
          meta = result;
        },
      }
    );

    expect(output).toBe("Hello there");
    expect(meta).toEqual({ memoriesRetrieved: 1, memorySaved: true });
  });
});
