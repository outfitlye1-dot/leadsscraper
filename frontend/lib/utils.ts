import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | null | undefined) {
  if (!date) return "—";
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return "—";
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}

export function capitalize(str: string) {
  return str.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Turn FastAPI `detail` (string | object | array) into a display string. */
export function formatApiDetail(detail: unknown): string {
  if (detail == null) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          const entry = item as { msg: unknown; loc?: unknown[] };
          const path = Array.isArray(entry.loc)
            ? entry.loc.filter((p) => p !== "body").join(".")
            : "";
          const msg = String(entry.msg);
          return path ? `${path}: ${msg}` : msg;
        }
        return JSON.stringify(item);
      })
      .join("; ");
  }
  if (typeof detail === "object" && detail !== null && "msg" in detail) {
    return String((detail as { msg: unknown }).msg);
  }
  return String(detail);
}

export function formatApiError(err: unknown, fallback = "Something went wrong"): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data
    ?.detail;
  const formatted = formatApiDetail(detail);
  if (formatted) return formatted;
  if (typeof err === "object" && err && "message" in err) {
    const msg = String((err as { message: unknown }).message || "");
    if (/^network error$/i.test(msg)) {
      return "Cannot reach the API (Network Error). Check Railway is online, or restart the backend and try again.";
    }
    if (msg && !/^request failed with status code/i.test(msg)) {
      return msg;
    }
  }
  return fallback;
}
