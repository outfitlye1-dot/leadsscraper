"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Brain, Play, RefreshCw, Square } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import api from "@/lib/api";
import type { DailyScrapeStatusResponse, ScrapeSuggestResponse } from "@/lib/types";
import { useScraperJobStore } from "@/store/scraperJobStore";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { ScraperQuickStart } from "@/components/scraper/ScraperQuickStart";
import { ScraperRunStatus } from "@/components/scraper/ScraperRunStatus";
import { ScraperTerminal } from "@/components/scraper/ScraperTerminal";
import { SearchQueryField } from "@/components/scraper/SearchQueryField";
import { useExportLeads } from "@/hooks/useLeads";
import { cn, formatApiError } from "@/lib/utils";

const LOCATIONS = ["London, UK", "Berlin, Germany", "Paris, France", "Amsterdam, NL"];
const LIMITS = [10, 20, 50, 100];
const DEFAULT_AUTO_LOCATION = "London, United Kingdom";

function ensureLocationInQuery(query: string, location?: string): string {
  const loc = location?.trim();
  if (!loc) return query.trim();
  const city = loc.split(",")[0].trim().toLowerCase();
  const low = query.toLowerCase();
  if (low.includes(city) || low.includes(loc.toLowerCase())) {
    return query.trim();
  }
  return `${query.trim()} ${loc}`.replace(/\s+/g, " ").trim();
}

const schema = z
  .object({
    keyword: z.string().optional(),
    location: z.string().optional(),
    search_query: z.string().optional(),
    limit: z.coerce.number().min(1).max(500),
    scrape_source: z.enum(["all", "google_maps", "google_search", "meta_ads"]),
    include_meta_ads: z.boolean(),
    enrich_contacts: z.boolean().optional(),
    only_verified_contacts: z.boolean().optional(),
    auto_generate_whatsapp: z.boolean().optional(),
    campaign_id: z.string().optional(),
  })
  .superRefine((data, ctx) => {
    if (data.scrape_source === "google_search") {
      if (!data.keyword?.trim()) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["keyword"], message: "Required" });
      }
      if (!data.location?.trim()) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["location"], message: "Required" });
      }
    } else if (data.scrape_source === "meta_ads") {
      if (!data.keyword?.trim() && !data.search_query?.trim()) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["keyword"], message: "Required" });
      }
      if (!data.location?.trim()) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["location"], message: "Required" });
      }
    } else {
      if (!data.keyword?.trim()) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["keyword"], message: "Required" });
      }
      if (!data.location?.trim()) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["location"], message: "Required" });
      }
    }
  });

type FormData = z.infer<typeof schema>;

const SOURCES = [
  { value: "google_maps" as const, label: "Maps" },
  { value: "google_search" as const, label: "Internet" },
  { value: "meta_ads" as const, label: "Meta Ads" },
  { value: "all" as const, label: "All" },
];

export default function ScraperPage() {
  const jobStatus = useScraperJobStore((s) => s.jobStatus);
  const isAutoMode = useScraperJobStore((s) => s.isAutoMode);
  const iteration = useScraperJobStore((s) => s.iteration);
  const autoKeptTotal = useScraperJobStore((s) => s.autoKeptTotal);
  const cancelRequested = useScraperJobStore((s) => s.cancelRequested);
  const result = useScraperJobStore((s) => s.result);
  const errorMsg = useScraperJobStore((s) => s.errorMsg);
  const progress = useScraperJobStore((s) => s.progress);
  const stage = useScraperJobStore((s) => s.stage);
  const progressMessage = useScraperJobStore((s) => s.progressMessage);
  const logs = useScraperJobStore((s) => s.logs);
  const isSubmitting = useScraperJobStore((s) => s.isSubmitting);
  const trackJob = useScraperJobStore((s) => s.trackJob);
  const resetForNewRun = useScraperJobStore((s) => s.resetForNewRun);
  const clearJob = useScraperJobStore((s) => s.clearJob);
  const recoverActiveJob = useScraperJobStore((s) => s.recoverActiveJob);
  const resumePolling = useScraperJobStore((s) => s.resumePolling);
  const stopAutoScrape = useScraperJobStore((s) => s.stopAutoScrape);
  const liveMetrics = useScraperJobStore((s) => s.liveMetrics);
  const pauseJob = useScraperJobStore((s) => s.pauseJob);
  const resumeJob = useScraperJobStore((s) => s.resumeJob);
  const cancelJob = useScraperJobStore((s) => s.cancelJob);
  const jobId = useScraperJobStore((s) => s.jobId);
  const jobApiStatus = useScraperJobStore((s) => s.jobApiStatus);

  const [dailyStatus, setDailyStatus] = useState<DailyScrapeStatusResponse | null>(null);
  const [dailyLoading, setDailyLoading] = useState(true);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [autoPreparing, setAutoPreparing] = useState(false);
  const exportLeads = useExportLeads();

  const handleDownloadResults = () => {
    void exportLeads.mutateAsync({ format: "csv" }).then(() => toast.success("Export downloaded"));
  };

  const handleRestart = () => {
    clearJob();
  };

  const { register, handleSubmit, watch, setValue, getValues, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      keyword: "",
      location: "London, United Kingdom",
      search_query: "",
      limit: 20,
      scrape_source: "google_search",
      include_meta_ads: false,
    },
  });

  const scrapeSource = watch("scrape_source");
  const limit = watch("limit");
  const searchQuery = watch("search_query") || "";
  const location = watch("location") || "";
  const isInternet = scrapeSource === "google_search";
  const showAdvancedQuery = scrapeSource === "all";

  const loadDailyStatus = async () => {
    setDailyLoading(true);
    try {
      const { data } = await api.get<DailyScrapeStatusResponse>("/scraper/daily/status");
      setDailyStatus(data);
    } catch {
      setDailyStatus(null);
    } finally {
      setDailyLoading(false);
    }
  };

  useEffect(() => { loadDailyStatus(); }, []);

  useEffect(() => {
    const resume = async () => {
      const { jobId, jobStatus } = useScraperJobStore.getState();
      if (jobId && jobStatus === "loading") {
        resumePolling();
        return;
      }
      if (await recoverActiveJob()) return;
    };
    void resume();
  }, [trackJob, resumePolling, recoverActiveJob]);

  useEffect(() => {
    if (jobStatus === "success") void loadDailyStatus();
  }, [jobStatus]);

  const applyBrainSuggest = async () => {
    setSuggestLoading(true);
    try {
      const apiSource = scrapeSource === "meta_ads" ? "google_maps" : scrapeSource;
      const { data } = await api.post<ScrapeSuggestResponse>("/ai/suggest-scrape", {
        scrape_source: apiSource,
      });
      if (data.recommended_keyword) setValue("keyword", data.recommended_keyword, { shouldValidate: true });
      if (isInternet) {
        const loc = getValues("location")?.trim() || DEFAULT_AUTO_LOCATION;
        const kw = data.recommended_keyword?.trim() || getValues("keyword")?.trim() || "";
        const sq =
          data.recommended_search_query?.trim() ||
          data.search_queries?.[0]?.trim() ||
          (kw ? `${kw} ${loc} contact email phone` : "");
        if (sq) setValue("search_query", ensureLocationInQuery(sq, loc), { shouldValidate: true });
      } else if (data.recommended_search_query) {
        setValue("search_query", data.recommended_search_query, { shouldValidate: true });
      }
      toast.success("Suggestion applied");
    } catch (err: unknown) {
      toast.error(formatApiError(err, "Could not load suggestion"));
    } finally {
      setSuggestLoading(false);
    }
  };

  const startScrape = async (data: FormData) => {
    if (jobStatus === "loading" || isSubmitting) {
      toast.info("Scrape already running.");
      resumePolling();
      return;
    }
    resetForNewRun();
    try {
      const { data: start } = await api.post<{ job_id: string }>("/scraper/start", {
        keyword: data.keyword?.trim() || "",
        location: data.location?.trim() || "",
        search_query: data.search_query?.trim() || undefined,
        limit: data.limit,
        scrape_source: data.scrape_source,
        include_meta_ads: data.scrape_source === "all" ? data.include_meta_ads : false,
        website_filter: "without_website",
        enrich_contacts: true,
        only_verified_contacts: false,
        auto_generate_whatsapp: false,
        campaign_id: undefined,
      });
      trackJob(start.job_id);
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        if (await recoverActiveJob()) return;
      }
      clearJob();
      const message = formatApiError(err, "Failed to start");
      useScraperJobStore.setState({ jobStatus: "failed", errorMsg: message, isSubmitting: false });
      toast.error(message);
    }
  };

  const startAutoScrape = async () => {
    if (isSubmitting) return;

    resetForNewRun(true);
    setAutoPreparing(true);
    useScraperJobStore.setState({
      progressMessage: "Preparing location & query…",
      isSubmitting: true,
      jobStatus: "loading",
    });

    const formLimit = getValues("limit") || 20;
    let resolvedLocation =
      getValues("location")?.trim() || DEFAULT_AUTO_LOCATION;
    let keyword = getValues("keyword")?.trim() || "";
    let searchQuery = getValues("search_query")?.trim() || "";

    try {
      const { data: suggest } = await api.post<ScrapeSuggestResponse>("/ai/suggest-scrape", {
        scrape_source: "google_search",
      });

      if (suggest.user_location?.trim()) {
        resolvedLocation = suggest.user_location.trim();
      }

      keyword = keyword || suggest.recommended_keyword?.trim() || "";
      searchQuery =
        searchQuery ||
        suggest.recommended_search_query?.trim() ||
        suggest.search_queries?.[0]?.trim() ||
        "";

      if (!keyword && suggest.keyword_suggestions?.[0]) {
        keyword = suggest.keyword_suggestions[0].trim();
      }

      if (!searchQuery && keyword) {
        searchQuery = `${keyword} ${resolvedLocation} contact email phone`;
      } else if (!searchQuery) {
        searchQuery = `local business ${resolvedLocation} contact email phone whatsapp`;
      }

      searchQuery = ensureLocationInQuery(searchQuery, resolvedLocation);
      if (!keyword) {
        keyword = suggest.keyword_suggestions?.[0]?.trim() || "restaurant";
      }

      setValue("scrape_source", "google_search", { shouldValidate: true });
      setValue("location", resolvedLocation, { shouldValidate: true });
      setValue("keyword", keyword, { shouldValidate: true });
      setValue("search_query", searchQuery, { shouldValidate: true });

      const { data: start } = await api.post<{ job_id: string }>("/scraper/auto/start", {
        keyword,
        location: resolvedLocation,
        search_query: searchQuery,
        limit: formLimit,
        scrape_source: "google_search",
        include_meta_ads: false,
        website_filter: "all",
        enrich_contacts: true,
        only_verified_contacts: false,
        auto_generate_whatsapp: false,
        interval_seconds: 15,
      });
      trackJob(start.job_id, `Auto · ${searchQuery}`, true);
      toast.success(`Auto started — ${resolvedLocation.split(",")[0]}`);
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        if (await recoverActiveJob()) return;
      }
      clearJob();
      const message = formatApiError(err, "Auto mode failed");
      useScraperJobStore.setState({ jobStatus: "failed", errorMsg: message, isSubmitting: false });
      toast.error(message);
    } finally {
      setAutoPreparing(false);
    }
  };

  const handleDailyScrape = async () => {
    if (!dailyStatus?.can_run || isSubmitting) return;
    resetForNewRun();
    try {
      const { data: start } = await api.post<{ job_id: string; message: string }>("/scraper/daily/start");
      setDailyStatus((prev) => (prev ? { ...prev, can_run: false } : prev));
      toast.success(start.message || "Daily scrape started");
      trackJob(start.job_id, "Daily scrape…");
    } catch (err: unknown) {
      clearJob();
      toast.error(formatApiError(err, "Daily scrape failed"));
      void loadDailyStatus();
    }
  };

  return (
    <div className="w-full space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Scraper</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {isInternet
              ? "Internet — free search for businesses without a website (Maps & Facebook listings)"
              : "Find leads from Maps, Internet, or Meta Ads"}
          </p>
        </div>
        <Link
          href="/leads"
          className="shrink-0 text-sm font-medium text-muted-foreground hover:text-foreground"
        >
          Inbox →
        </Link>
      </div>

      <ScraperQuickStart
        dailyStatus={dailyStatus}
        dailyLoading={dailyLoading}
        isSubmitting={isSubmitting && jobStatus === "loading"}
        onDailyScrape={handleDailyScrape}
      />

      <div className="grid gap-6 lg:grid-cols-12 lg:items-start">
        <form
          onSubmit={handleSubmit(startScrape)}
          className="space-y-6 rounded-2xl border border-border/60 bg-card p-5 sm:p-6 lg:col-span-8 lg:p-8"
        >
        {/* Source */}
        <div className="flex gap-1 rounded-lg bg-muted/50 p-1 sm:max-w-xl">
          {SOURCES.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              onClick={() => {
                setValue("scrape_source", value, { shouldValidate: true });
                if (value !== "all") setValue("include_meta_ads", false);
              }}
              className={cn(
                "flex-1 rounded-md py-2 text-sm font-medium transition",
                scrapeSource === value
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {label}
            </button>
          ))}
        </div>
        <input type="hidden" {...register("scrape_source")} />

        <div className="grid gap-5 sm:grid-cols-2">
          {showAdvancedQuery ? (
            <div className="sm:col-span-2">
              <SearchQueryField
                value={searchQuery}
                onChange={(v) => setValue("search_query", v, { shouldValidate: true })}
                error={errors.search_query?.message}
                location={location}
              />
            </div>
          ) : null}

          <div className="space-y-1.5">
            <Label htmlFor="keyword" className="text-xs text-muted-foreground">
              {isInternet ? "Keyword" : showAdvancedQuery ? "Maps keyword" : "Keyword"}
            </Label>
            <Input
              id="keyword"
              placeholder={isInternet ? "Restaurant, Salon, Gym…" : "Restaurant, Salon, Gym…"}
              {...register("keyword")}
            />
            {errors.keyword ? (
              <p className="text-xs text-destructive">{errors.keyword.message}</p>
            ) : isInternet ? (
              <p className="text-xs text-muted-foreground">
                Maps jaisa — sirf keyword + location, query auto ban jati hai
              </p>
            ) : null}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="location" className="text-xs text-muted-foreground">
              Location
            </Label>
            <Input id="location" placeholder="London, United Kingdom" {...register("location")} />
            {errors.location ? (
              <p className="text-xs text-destructive">{errors.location.message}</p>
            ) : null}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {LOCATIONS.map((loc) => (
                <button
                  key={loc}
                  type="button"
                  className="rounded-md bg-muted/60 px-2.5 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                  onClick={() => setValue("location", loc, { shouldValidate: true })}
                >
                  {loc.split(",")[0]}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-1.5 sm:min-w-[220px]">
            <Label className="text-xs text-muted-foreground">Lead count</Label>
            <div className="flex gap-1.5">
              {LIMITS.map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setValue("limit", n)}
                  className={cn(
                    "h-10 min-w-[3rem] flex-1 rounded-lg text-sm font-medium tabular-nums transition sm:flex-none sm:px-4",
                    limit === n
                      ? "bg-foreground text-background"
                      : "bg-muted/50 text-muted-foreground hover:text-foreground"
                  )}
                >
                  {n}
                </button>
              ))}
            </div>
            <input type="hidden" {...register("limit")} />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {scrapeSource === "all" ? (
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <input type="checkbox" {...register("include_meta_ads")} />
                Meta Ads
              </label>
            ) : null}
            <button
              type="button"
              onClick={() => void applyBrainSuggest()}
              disabled={suggestLoading}
              className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground disabled:opacity-50"
            >
              <Brain className="h-4 w-4" />
              {suggestLoading ? "Loading…" : "Brain suggest"}
            </button>
          </div>
        </div>

        <div className="flex flex-col gap-3 border-t border-border/50 pt-5 sm:flex-row">
          <Button
            type="submit"
            size="lg"
            className="h-11 flex-1 gap-2 sm:min-w-[200px]"
            isLoading={isSubmitting && !isAutoMode}
            disabled={isSubmitting && isAutoMode}
          >
            <Play className="h-4 w-4" />
            Start scraping
          </Button>

          {isAutoMode && jobStatus === "loading" ? (
            <Button
              type="button"
              variant="destructive"
              className="h-11 flex-1"
              onClick={() => void stopAutoScrape()}
              disabled={cancelRequested}
            >
              <Square className="mr-2 h-3.5 w-3.5" />
              {cancelRequested ? "Stopping…" : "Stop auto"}
            </Button>
          ) : (
            <Button
              type="button"
              variant="outline"
              className="h-11 flex-1"
              disabled={isSubmitting}
              isLoading={autoPreparing}
              onClick={() => void startAutoScrape()}
            >
              <RefreshCw className="mr-2 h-3.5 w-3.5" />
              Auto mode
            </Button>
          )}
        </div>
      </form>

        <aside className="lg:col-span-4">
          <div className="lg:sticky lg:top-6">
            <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Status
            </p>
            <ScraperRunStatus
              jobStatus={jobStatus}
              isAutoMode={isAutoMode}
              iteration={iteration}
              progress={progress}
              stage={stage}
              progressMessage={progressMessage}
              result={result}
              errorMsg={errorMsg}
              autoKeptTotal={autoKeptTotal}
              liveMetrics={liveMetrics}
              apiStatus={jobApiStatus}
              onPause={jobId && !isAutoMode && jobApiStatus === "running" ? () => void pauseJob(jobId) : undefined}
              onResume={jobId && !isAutoMode && jobApiStatus === "paused" ? () => void resumeJob(jobId) : undefined}
              onCancel={jobId ? () => void cancelJob(jobId) : undefined}
              onRestart={handleRestart}
              onDownload={result?.count ? handleDownloadResults : undefined}
            />
          </div>
        </aside>
      </div>

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Live terminal
          </p>
          {jobStatus === "loading" ? (
            <span className="text-xs text-muted-foreground tabular-nums">
              {progress}% · {progressMessage || "Running…"}
            </span>
          ) : null}
        </div>
        <ScraperTerminal
          docked
          logs={logs}
          progress={progress}
          stage={stage}
          message={progressMessage}
          isRunning={jobStatus === "loading"}
        />
      </section>
    </div>
  );
}
