import type { ChatMessage } from "../api";

let messageCounter = 0;

/** Generate a stable, unique id for a chat message. */
export function createMessageId(): string {
  messageCounter += 1;
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `msg-${crypto.randomUUID()}`;
  }
  return `msg-${Date.now().toString(36)}-${messageCounter.toString(36)}-${Math.random()
    .toString(36)
    .slice(2, 8)}`;
}

/**
 * Ensure every message has a stable id. Messages that already carry one keep
 * it (so ids survive a localStorage archive round-trip); any without one get a
 * freshly generated id. Returns the same array when nothing needs assigning.
 */
export function ensureMessageIds(messages: ChatMessage[]): ChatMessage[] {
  let changed = false;
  const next = messages.map((msg) => {
    if (msg.id) {
      return msg;
    }
    changed = true;
    return { ...msg, id: createMessageId() };
  });
  return changed ? next : messages;
}
