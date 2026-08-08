import { isAxiosError } from "axios";

export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    const status = error.response?.status;
    if (!error.response) {
      return "Cannot reach the API. On Vercel set NEXT_PUBLIC_API_URL to your Railway /api URL, then redeploy.";
    }
    if (status === 404) {
      return "API not found (404). Set NEXT_PUBLIC_API_URL=https://leadsscraper-production.up.railway.app/api on Vercel and redeploy.";
    }
    if (status === 409) {
      const detail = error.response?.data?.detail;
      if (typeof detail === "string" && detail) return detail;
      return "Email already registered — try logging in instead.";
    }
    if (status === 500) {
      const detail = error.response?.data?.detail;
      if (typeof detail === "string" && detail) return detail;
      return "Server error — backend may be busy. Stop the scraper and try again.";
    }
    if (status === 503) {
      const detail = error.response?.data?.detail;
      if (typeof detail === "string" && detail) return detail;
      return "Server is busy (scraper running). Please try again in a few seconds.";
    }
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item?.msg ?? String(item)).join(", ");
    }
  }
  return fallback;
}
