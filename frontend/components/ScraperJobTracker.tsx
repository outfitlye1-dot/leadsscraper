"use client";

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { bindScraperQueryClient, useScraperJobStore } from "@/store/scraperJobStore";
import { useAuthStore } from "@/store/authStore";
import { ScraperJobBanner } from "@/components/ScraperJobBanner";

export function ScraperJobTracker() {
  const queryClient = useQueryClient();
  const userId = useAuthStore((s) => s.user?.id ?? null);
  const syncOwner = useScraperJobStore((s) => s.syncOwner);
  const resumePolling = useScraperJobStore((s) => s.resumePolling);
  const recoverActiveJob = useScraperJobStore((s) => s.recoverActiveJob);
  const jobId = useScraperJobStore((s) => s.jobId);
  const jobStatus = useScraperJobStore((s) => s.jobStatus);

  useEffect(() => {
    bindScraperQueryClient(queryClient);
  }, [queryClient]);

  useEffect(() => {
    syncOwner(userId);
  }, [userId, syncOwner]);

  useEffect(() => {
    if (!userId) return;
    if (jobId && jobStatus === "loading") {
      resumePolling();
      return;
    }
    if (!jobId && jobStatus === "idle") {
      void recoverActiveJob();
    }
  }, [userId, jobId, jobStatus, resumePolling, recoverActiveJob]);

  return <ScraperJobBanner />;
}
