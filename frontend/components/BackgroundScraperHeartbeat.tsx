"use client";

import { useEffect } from "react";
import api from "@/lib/api";
import type { BackgroundScrapeStatusResponse } from "@/lib/types";
import { useAuthStore } from "@/store/authStore";

const HEARTBEAT_MS = 20_000;

/** Keeps background scraper running automatically while the user is logged in. */
export function BackgroundScraperHeartbeat() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  useEffect(() => {
    if (!isAuthenticated) return;

    let cancelled = false;

    const ping = async () => {
      try {
        await api.post<BackgroundScrapeStatusResponse>("/scraper/background/heartbeat");
      } catch {
        /* ignore — user may be offline briefly */
      }
    };

    const onVisible = () => {
      if (!cancelled && document.visibilityState === "visible") {
        void ping();
      }
    };

    void ping();
    const id = window.setInterval(() => {
      if (!cancelled) void ping();
    }, HEARTBEAT_MS);
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      cancelled = true;
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [isAuthenticated]);

  return null;
}
