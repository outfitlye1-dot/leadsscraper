"use client";

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { bindScraperQueryClient, useScraperJobStore } from "@/store/scraperJobStore";
import { ScraperJobBanner } from "@/components/ScraperJobBanner";

export function ScraperJobTracker() {
  const queryClient = useQueryClient();
  const resumePolling = useScraperJobStore((s) => s.resumePolling);
  const recoverActiveJob = useScraperJobStore((s) => s.recoverActiveJob);
  const jobId = useScraperJobStore((s) => s.jobId);
  const jobStatus = useScraperJobStore((s) => s.jobStatus);

  useEffect(() => {
    bindScraperQueryClient(queryClient);
  }, [queryClient]);

  useEffect(() => {
    if (jobId && jobStatus === "loading") {
      resumePolling();
      return;
    }
    if (!jobId && jobStatus === "idle") {
      void recoverActiveJob();
    }
  }, [jobId, jobStatus, resumePolling, recoverActiveJob]);

  return <ScraperJobBanner />;
}
