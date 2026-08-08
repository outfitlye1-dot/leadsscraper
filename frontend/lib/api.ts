import axios from "axios";
import { getToken } from "./auth";
import { getApiBaseUrl } from "./apiBase";
import { useAuthStore } from "@/store/authStore";

const API_URL = getApiBaseUrl();

let authRedirectInProgress = false;

function handleUnauthorized(requestUrl: string) {
  const isAuthRequest =
    requestUrl.includes("/auth/login") ||
    requestUrl.includes("/auth/register") ||
    requestUrl.includes("/auth/otp/");

  if (isAuthRequest || authRedirectInProgress || typeof window === "undefined") return;

  authRedirectInProgress = true;
  useAuthStore.getState().logout();

  const onAuthPage =
    window.location.pathname.startsWith("/login") ||
    window.location.pathname.startsWith("/register");

  if (!onAuthPage) {
    window.dispatchEvent(new Event("auth:session-expired"));
  }

  window.setTimeout(() => {
    authRedirectInProgress = false;
  }, 1000);
}

export const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (config.data instanceof FormData) {
    delete config.headers["Content-Type"];
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const requestUrl = error.config?.url || "";

    // Background keepalive must never force logout — backend restarts briefly return 401/500
    const isBackgroundKeepalive =
      requestUrl.includes("/scraper/background/heartbeat") ||
      requestUrl.includes("/scraper/background/stop") ||
      requestUrl.includes("/scraper/background/status");

    if (status === 401 && !isBackgroundKeepalive) {
      handleUnauthorized(requestUrl);
    }

    return Promise.reject(error);
  }
);

export default api;

export { API_URL as API_BASE_URL };
