import { ApiRequestError } from "../api";

export type FormatErrorMessage = (error: unknown, fallback: string) => string;

export const formatErrorMessage: FormatErrorMessage = (error, fallback) => {
  if (!(error instanceof Error)) {
    return fallback;
  }
  let message = error.message || fallback;
  if (error instanceof ApiRequestError) {
    const requestId = error.detail?.meta?.request_id;
    if (typeof requestId === "string" && requestId.trim() && !message.includes("request_id:")) {
      message = `${message} (request_id: ${requestId.trim()})`;
    }
  }
  return message;
};
