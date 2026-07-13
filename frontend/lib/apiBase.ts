/** API base URL. Use `/api` (default) so Next.js proxies to the backend — works with ngrok. */
export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || "/api";
}

/** Origin for downloads / absolute links (no trailing /api). */
export function getApiOrigin(): string {
  const base = getApiBaseUrl();
  if (base.startsWith("/")) {
    if (typeof window !== "undefined") return window.location.origin;
    return "";
  }
  return base.replace(/\/api\/?$/, "");
}
