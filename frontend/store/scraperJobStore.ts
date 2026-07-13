import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { QueryClient } from "@tanstack/react-query";
import axios from "axios";
import { toast } from "sonner";
import api from "@/lib/api";
import { formatApiDetail, formatApiError } from "@/lib/utils";
import type { ScraperJobStatusResponse, ScraperLogEntry, ScraperResponse, ScrapeMetricsResponse } from "@/lib/types";

export type ScraperJobUiStatus = "idle" | "loading" | "success" | "failed";

const POLL_INTERVAL_MS = 1500;

let pollInterval: ReturnType<typeof setInterval> | null = null;
let queryClient: QueryClient | null = null;
let lastAutoInvalidationIteration = 0;

export function bindScraperQueryClient(client: QueryClient) {
  queryClient = client;
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
}

function invalidateAfterScrape() {
  queryClient?.invalidateQueries({ queryKey: ["leads"] });
  queryClient?.invalidateQueries({ queryKey: ["saved-leads"] });
  queryClient?.invalidateQueries({ queryKey: ["dashboard-stats"] });
  queryClient?.invalidateQueries({ queryKey: ["messages"] });
}

interface ScraperJobState {
  jobId: string | null;
  isAutoMode: boolean;
  jobStatus: ScraperJobUiStatus;
  progress: number;
  stage: string;
  progressMessage: string;
  iteration: number;
  autoKeptTotal: number;
  autoDeletedTotal: number;
  cancelRequested: boolean;
  result: ScraperResponse | null;
  errorMsg: string;
  isSubmitting: boolean;
  logs: ScraperLogEntry[];
  liveMetrics: ScrapeMetricsResponse | null;
  jobApiStatus: ScraperJobStatusResponse["status"] | null;
  trackJob: (jobId: string, initialMessage?: string, auto?: boolean) => void;
  recoverActiveJob: () => Promise<boolean>;
  stopAutoScrape: () => Promise<void>;
  resumePolling: () => void;
  pauseJob: (jobId: string) => Promise<void>;
  resumeJob: (jobId: string) => Promise<void>;
  cancelJob: (jobId: string) => Promise<void>;
  clearJob: () => void;
  resetForNewRun: (auto?: boolean) => void;
}

export const useScraperJobStore = create<ScraperJobState>()(
  persist(
    (set, get) => {
      const pollOnce = async (jobId: string) => {
        try {
          const { data } = await api.get<ScraperJobStatusResponse>(`/scraper/jobs/${jobId}`);
          const isAuto = data.mode === "auto";

          set({
            progress: data.progress,
            stage: data.stage,
            progressMessage: data.message,
            isAutoMode: isAuto,
            iteration: data.iteration ?? 0,
            autoKeptTotal: data.auto_kept_total ?? 0,
            autoDeletedTotal: data.auto_deleted_total ?? 0,
            cancelRequested: data.cancel_requested ?? false,
            logs: data.logs ?? [],
            liveMetrics: data.live_metrics ?? null,
            jobApiStatus: data.status,
          });

          if (
            isAuto &&
            data.status === "running" &&
            (data.iteration ?? 0) > lastAutoInvalidationIteration &&
            (data.stage === "auto_wait" || data.stage === "done")
          ) {
            lastAutoInvalidationIteration = data.iteration ?? 0;
            invalidateAfterScrape();
          }

          if (data.status === "completed") {
            stopPolling();
            const finalResult = data.result ?? null;
            set({
              jobStatus: "success",
              isSubmitting: false,
              result: finalResult,
              progress: 100,
              stage: "done",
            });
            invalidateAfterScrape();
            if (isAuto) {
              toast.success(
                data.message ||
                  `Auto scrape stopped — ${data.auto_kept_total ?? 0} phone leads kept`
              );
            } else if (finalResult?.count && finalResult.count > 0) {
              toast.success(finalResult.message || `Scraped ${finalResult.count} leads`);
            } else {
              toast.warning(finalResult?.message || "No leads found. Try a different keyword or location.");
            }
            return;
          }

          if (data.status === "failed") {
            stopPolling();
            const message = formatApiDetail(data.error) || data.message || "Scraping failed";
            set({
              jobStatus: "failed",
              isSubmitting: false,
              errorMsg: message,
              stage: "error",
            });
            toast.error(message);
          }
        } catch (err: unknown) {
          stopPolling();
          if (axios.isAxiosError(err) && err.response?.status === 404) {
            get().clearJob();
            return;
          }
          const message = formatApiError(err, "Failed to fetch scraper progress");
          set({
            jobStatus: "failed",
            isSubmitting: false,
            errorMsg: message,
            stage: "error",
          });
          toast.error(message);
        }
      };

      const startPolling = (jobId: string) => {
        stopPolling();
        void pollOnce(jobId);
        pollInterval = setInterval(() => void pollOnce(jobId), POLL_INTERVAL_MS);
      };

      return {
        jobId: null,
        isAutoMode: false,
        jobStatus: "idle",
        progress: 0,
        stage: "",
        progressMessage: "",
        iteration: 0,
        autoKeptTotal: 0,
        autoDeletedTotal: 0,
        cancelRequested: false,
        result: null,
        errorMsg: "",
        isSubmitting: false,
        logs: [],
        liveMetrics: null,
        jobApiStatus: null,

        resetForNewRun: (auto = false) => {
          lastAutoInvalidationIteration = 0;
          set({
            jobStatus: "loading",
            isAutoMode: auto,
            result: null,
            errorMsg: "",
            progress: 0,
            stage: auto ? "auto" : "init",
            progressMessage: auto ? "Starting auto scraping..." : "Starting scraper...",
            isSubmitting: true,
            iteration: 0,
            autoKeptTotal: 0,
            autoDeletedTotal: 0,
            cancelRequested: false,
            logs: [],
          });
        },

        trackJob: (jobId: string, initialMessage = "Starting scraper...", auto = false) => {
          lastAutoInvalidationIteration = 0;
          set({
            jobId,
            isAutoMode: auto,
            jobStatus: "loading",
            result: null,
            errorMsg: "",
            progress: 0,
            stage: auto ? "auto" : "init",
            progressMessage: initialMessage,
            isSubmitting: true,
            iteration: 0,
            autoKeptTotal: 0,
            autoDeletedTotal: 0,
            cancelRequested: false,
            logs: [{ seq: 0, ts: new Date().toISOString(), level: "info", stage: "init", text: initialMessage }],
          });
          startPolling(jobId);
        },

        recoverActiveJob: async () => {
          try {
            const { data: active } = await api.get<ScraperJobStatusResponse | null>("/scraper/active");
            if (!active?.job_id) return false;
            get().trackJob(
              active.job_id,
              active.message || "Scrape in progress…",
              active.mode === "auto"
            );
            toast.info("Scrape already in progress — showing live progress.");
            return true;
          } catch {
            return false;
          }
        },

        stopAutoScrape: async () => {
          try {
            await api.post("/scraper/auto/stop");
            set({ cancelRequested: true, progressMessage: "Stopping after current round..." });
            toast.message("Auto scrape will stop after this round finishes.");
          } catch (err: unknown) {
            toast.error(formatApiError(err, "Failed to stop auto scraping"));
          }
        },

        pauseJob: async (jobId: string) => {
          try {
            await api.post(`/scraper/jobs/${jobId}/pause`);
            toast.message("Scrape paused");
          } catch (err: unknown) {
            toast.error(formatApiError(err, "Failed to pause"));
          }
        },

        resumeJob: async (jobId: string) => {
          try {
            await api.post(`/scraper/jobs/${jobId}/resume`);
            toast.message("Scrape resumed");
          } catch (err: unknown) {
            toast.error(formatApiError(err, "Failed to resume"));
          }
        },

        cancelJob: async (jobId: string) => {
          try {
            await api.post(`/scraper/jobs/${jobId}/cancel`);
            toast.message("Cancellation requested");
          } catch (err: unknown) {
            toast.error(formatApiError(err, "Failed to cancel"));
          }
        },

        resumePolling: () => {
          const { jobId, jobStatus } = get();
          if (!jobId) return;
          if (jobStatus === "loading") {
            set({ isSubmitting: true });
            startPolling(jobId);
            return;
          }
          if (jobStatus === "success" || jobStatus === "failed") {
            void pollOnce(jobId);
          }
        },

        clearJob: () => {
          stopPolling();
          lastAutoInvalidationIteration = 0;
          set({
            jobId: null,
            isAutoMode: false,
            jobStatus: "idle",
            progress: 0,
            stage: "",
            progressMessage: "",
            iteration: 0,
            autoKeptTotal: 0,
            autoDeletedTotal: 0,
            cancelRequested: false,
            result: null,
            errorMsg: "",
            isSubmitting: false,
            logs: [],
            liveMetrics: null,
            jobApiStatus: null,
          });
        },
      };
    },
    {
      name: "leadgen-scraper-job",
      partialize: (state) => ({
        jobId: state.jobId,
        isAutoMode: state.isAutoMode,
        jobStatus: state.jobStatus,
        progress: state.progress,
        stage: state.stage,
        progressMessage: state.progressMessage,
        iteration: state.iteration,
        autoKeptTotal: state.autoKeptTotal,
        autoDeletedTotal: state.autoDeletedTotal,
        cancelRequested: state.cancelRequested,
        result: state.result,
        errorMsg: state.errorMsg,
        logs: state.logs,
      }),
    }
  )
);
