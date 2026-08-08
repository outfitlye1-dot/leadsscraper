"use client";

import { useEffect } from "react";
import api from "@/lib/api";
import type { BackgroundScrapeStatusResponse } from "@/lib/types";
import { useAuthStore } from "@/store/authStore";
import { useScraperJobStore } from "@/store/scraperJobStore";

const HEARTBEAT_MS = 60_000;

/** Keeps silent background scraper alive — paused while a scrape job is active. */
export function BackgroundScraperHeartbeat() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const jobBusy = useScraperJobStore(
    (s) => Boolean(s.jobId) && (s.jobStatus === "loading" || s.isSubmitting)
  );

  useEffect(() => {
    if (!isAuthenticated || jobBusy) return;

    let cancelled = false;

    const ping = async () => {
      if (cancelled || document.visibilityState === "hidden") return;
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
  }, [isAuthenticated, jobBusy]);

  return null;
}
