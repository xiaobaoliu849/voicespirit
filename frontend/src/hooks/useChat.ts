import { FormEvent, KeyboardEvent, useMemo, useState } from "react";
import { streamChatCompletion, type ChatMessage } from "../api";
import type { FormatErrorMessage } from "../utils/errorFormatting";

type Options = {
  formatErrorMessage: FormatErrorMessage;
};

export default function useChat({ formatErrorMessage }: Options) {
  const [chatProvider, setChatProvider] = useState("Google");
  const [chatModel, setChatModel] = useState("");
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatBusy, setChatBusy] = useState(false);
  const [chatError, setChatError] = useState("");

  const chatHistoryItems = useMemo(() => {
    const items: Array<{ id: string; content: string }> = [];
    chatMessages.forEach((msg, idx) => {
      if (msg.role !== "user") {
        return;
      }
      const clean = msg.content.trim();
      if (!clean) {
        return;
      }
      const short = clean.length > 26 ? `${clean.slice(0, 26)}...` : clean;
      items.push({
        id: `${idx}-${msg.role}`,
        content: short
      });
    });
    return items.slice(-40).reverse();
  }, [chatMessages]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const userText = chatInput.trim();
    if (!userText) {
      return;
    }
    setChatError("");
    setChatBusy(true);

    const nextHistory: ChatMessage[] = [
      ...chatMessages,
      { role: "user", content: userText }
    ];
    setChatMessages([...nextHistory, { role: "assistant", content: "" }]);
    setChatInput("");

    try {
      let streamedReply = "";
      await streamChatCompletion(
        {
          provider: chatProvider,
          model: chatModel.trim() || undefined,
          messages: nextHistory,
          temperature: 0.7,
          max_tokens: 1024
        },
        {
          onDelta: (chunk) => {
            streamedReply += chunk;
            setChatMessages((prev) => {
              if (!prev.length) {
                return prev;
              }
              const next = [...prev];
              const lastIdx = next.length - 1;
              const last = next[lastIdx];
              if (last.role !== "assistant") {
                return prev;
              }
              next[lastIdx] = { ...last, content: streamedReply };
              return next;
            });
          },
          onDone: (meta) => {
            if (meta?.memoriesRetrieved || meta?.memorySaved) {
              setChatMessages((prev) => {
                const next = [...prev];
                const lastIdx = next.length - 1;
                const prevIdx = lastIdx - 1;

                if (meta.memorySaved && prevIdx >= 0 && next[prevIdx].role === "user") {
                  next[prevIdx] = { ...next[prevIdx], memorySaved: true };
                }
                if (meta.memoriesRetrieved && lastIdx >= 0 && next[lastIdx].role === "assistant") {
                  next[lastIdx] = { ...next[lastIdx], memoriesUsed: meta.memoriesRetrieved };
                }
                return next;
              });
            }
          }
        }
      );
    } catch (err) {
      setChatMessages((prev) => {
        if (!prev.length) {
          return prev;
        }
        const last = prev[prev.length - 1];
        if (last.role === "assistant" && !last.content.trim()) {
          return prev.slice(0, -1);
        }
        return prev;
      });
      setChatError(formatErrorMessage(err, "聊天请求失败。"));
    } finally {
      setChatBusy(false);
    }
  }

  function onNewSession() {
    setChatMessages([]);
    setChatInput("");
    setChatError("");
  }

  function onComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!chatBusy && chatInput.trim()) {
        event.currentTarget.form?.requestSubmit();
      }
    }
  }

  return {
    chatProvider,
    chatModel,
    chatInput,
    chatMessages,
    chatBusy,
    chatError,
    chatHistoryItems,
    onSubmit,
    onProviderChange: setChatProvider,
    onModelChange: setChatModel,
    onInputChange: setChatInput,
    onQuickAction: setChatInput,
    onComposerKeyDown,
    onNewSession,
    onSelectHistory: setChatInput
  };
}

export type UseChatResult = ReturnType<typeof useChat>;
