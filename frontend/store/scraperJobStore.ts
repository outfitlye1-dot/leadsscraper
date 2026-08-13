import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { QueryClient } from "@tanstack/react-query";
import axios from "axios";
import { toast } from "sonner";
import api from "@/lib/api";
import { formatApiDetail, formatApiError } from "@/lib/utils";
import type {
  ScraperAgentStatus,
  ScraperJobStatusResponse,
  ScraperLogEntry,
  ScraperResponse,
  ScraperRoundStatus,
  ScrapeMetricsResponse,
} from "@/lib/types";

export type ScraperJobUiStatus = "idle" | "loading" | "success" | "failed";

const POLL_INTERVAL_MS = 3000;

let pollInterval: ReturnType<typeof setInterval> | null = null;
let pollGeneration = 0;
let queryClient: QueryClient | null = null;
let lastAutoInvalidationIteration = 0;

export function bindScraperQueryClient(client: QueryClient) {
  queryClient = client;
}

function stopPolling() {
  // Invalidate in-flight pollOnce calls + orphaned HMR intervals
  pollGeneration += 1;
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
  ownerUserId: number | null;
  isAutoMode: boolean;
  jobStatus: ScraperJobUiStatus;
  progress: number;
  stage: string;
  progressMessage: string;
  iteration: number;
  autoKeptTotal: number;
  autoDeletedTotal: number;
  autoScrapedTotal: number;
  cancelRequested: boolean;
  result: ScraperResponse | null;
  errorMsg: string;
  isSubmitting: boolean;
  logs: ScraperLogEntry[];
  agents: ScraperAgentStatus[];
  rounds: ScraperRoundStatus[];
  liveMetrics: ScrapeMetricsResponse | null;
  jobApiStatus: ScraperJobStatusResponse["status"] | null;
  syncOwner: (userId: number | null) => void;
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
      const pollOnce = async (jobId: string, generation: number) => {
        if (generation !== pollGeneration || get().jobId !== jobId) return;
        try {
          const { data } = await api.get<ScraperJobStatusResponse>(`/scraper/jobs/${jobId}`);
          if (generation !== pollGeneration || get().jobId !== jobId) return;
          const isAuto = data.mode === "auto";

          set({
            progress: data.progress,
            stage: data.stage,
            progressMessage: data.message,
            isAutoMode: isAuto,
            iteration: data.iteration ?? 0,
            autoKeptTotal: data.auto_kept_total ?? 0,
            autoDeletedTotal: data.auto_deleted_total ?? 0,
            autoScrapedTotal: data.auto_scraped_total ?? 0,
            cancelRequested: data.cancel_requested ?? false,
            logs: data.logs ?? [],
            agents: data.agents ?? [],
            rounds: data.rounds ?? [],
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

          if (data.status === "cancelled") {
            stopPolling();
            set({
              jobId: null,
              jobStatus: "idle",
              isSubmitting: false,
              cancelRequested: true,
              progressMessage: data.message || "Stopped",
              stage: "cancelled",
              jobApiStatus: "cancelled",
            });
            toast.message("Scrape stopped");
            invalidateAfterScrape();
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
          if (generation !== pollGeneration || get().jobId !== jobId) return;
          stopPolling();
          if (axios.isAxiosError(err) && err.response?.status === 404) {
            // Job lost after backend restart/reload — drop stale localStorage job
            get().clearJob();
            toast.message("Previous scrape expired — start again");
            return;
          }
          // Transient proxy/backend reloads — keep job, retry shortly
          if (
            axios.isAxiosError(err) &&
            (!err.response || err.response.status >= 500)
          ) {
            const gen = pollGeneration;
            pollInterval = setInterval(() => {
              if (get().jobId !== jobId || gen !== pollGeneration) {
                stopPolling();
                return;
              }
              void pollOnce(jobId, gen);
            }, POLL_INTERVAL_MS * 2);
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
        const generation = pollGeneration;
        void pollOnce(jobId, generation);
        pollInterval = setInterval(() => {
          if (get().jobId !== jobId) {
            stopPolling();
            return;
          }
          void pollOnce(jobId, generation);
        }, POLL_INTERVAL_MS);
      };

      return {
        jobId: null,
        ownerUserId: null,
        isAutoMode: false,
        jobStatus: "idle",
        progress: 0,
        stage: "",
        progressMessage: "",
        iteration: 0,
        autoKeptTotal: 0,
        autoDeletedTotal: 0,
        autoScrapedTotal: 0,
        cancelRequested: false,
        result: null,
        errorMsg: "",
        isSubmitting: false,
        logs: [],
        agents: [],
        rounds: [],
        liveMetrics: null,
        jobApiStatus: null,

        syncOwner: (userId: number | null) => {
          const { ownerUserId, jobId, clearJob } = get();
          if (userId == null) {
            if (jobId || ownerUserId != null) clearJob();
            set({ ownerUserId: null });
            return;
          }
          if (ownerUserId != null && ownerUserId !== userId) {
            // Another account's persisted scrape UI — drop it so it cannot look shared
            clearJob();
          }
          set({ ownerUserId: userId });
        },

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
            autoScrapedTotal: 0,
            cancelRequested: false,
            logs: [],
            agents: [],
            rounds: [],
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
            autoScrapedTotal: 0,
            cancelRequested: false,
            logs: [{ seq: 0, ts: new Date().toISOString(), level: "info", stage: "init", text: initialMessage }],
            agents: [],
            rounds: [],
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
          const { jobId } = get();
          // Optimistic UI — stop immediately in the client
          stopPolling();
          set({
            jobId: null,
            cancelRequested: true,
            isSubmitting: false,
            isAutoMode: false,
            jobStatus: "idle",
            progressMessage: "Stopped",
            stage: "cancelled",
            jobApiStatus: "cancelled",
          });
          try {
            // Prefer auto/stop (clears active auto). Ignore 404 = already stopped.
            await api.post("/scraper/auto/stop").catch(() => undefined);
            if (jobId) {
              await api.post(`/scraper/jobs/${jobId}/cancel`).catch(() => undefined);
            }
            toast.message("Stopped");
            invalidateAfterScrape();
          } catch (err: unknown) {
            toast.error(formatApiError(err, "Failed to stop"));
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
          // Optimistic UI — stop immediately and drop local job id
          stopPolling();
          set({
            jobId: null,
            cancelRequested: true,
            isSubmitting: false,
            isAutoMode: false,
            jobStatus: "idle",
            progressMessage: "Stopped",
            stage: "cancelled",
            jobApiStatus: "cancelled",
          });
          try {
            await api.post(`/scraper/jobs/${jobId}/cancel`).catch(() => undefined);
            toast.message("Stopped");
            invalidateAfterScrape();
          } catch (err: unknown) {
            toast.error(formatApiError(err, "Failed to stop"));
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
            void pollOnce(jobId, pollGeneration);
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
            autoScrapedTotal: 0,
            cancelRequested: false,
            result: null,
            errorMsg: "",
            isSubmitting: false,
            logs: [],
            agents: [],
            rounds: [],
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
        ownerUserId: state.ownerUserId,
        isAutoMode: state.isAutoMode,
        jobStatus: state.jobStatus,
        progress: state.progress,
        stage: state.stage,
        progressMessage: state.progressMessage,
        iteration: state.iteration,
        autoKeptTotal: state.autoKeptTotal,
        autoDeletedTotal: state.autoDeletedTotal,
        cancelRequested: state.cancelRequested,
        // Do not persist logs/agents — they bloat localStorage and slow every page load
        result: state.result,
        errorMsg: state.errorMsg,
      }),
    }
  )
);
