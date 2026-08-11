"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Brain, Mail, Play, RefreshCw, Square } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import api from "@/lib/api";
import type { ScrapeSuggestResponse } from "@/lib/types";
import { useScraperJobStore } from "@/store/scraperJobStore";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { ScraperRunStatus } from "@/components/scraper/ScraperRunStatus";
import { PageLoader } from "@/components/Loader";
import { useExportLeads } from "@/hooks/useLeads";
import { readScrapePrefs, writeScrapePrefs } from "@/lib/scrapePrefs";
import { cn, formatApiError } from "@/lib/utils";

type WebsiteFilterMode = "without_website" | "with_website" | "all";

const MAPS_SOURCE = "google_maps" as const;
const COUNTRY_CITIES: Record<string, string[]> = {
  "United Kingdom": [
    "London",
    "Manchester",
    "Birmingham",
    "Leeds",
    "Glasgow",
    "Liverpool",
    "Bristol",
    "Edinburgh",
    "Sheffield",
    "Newcastle",
    "Nottingham",
    "Cardiff",
  ],
  Germany: [
    "Berlin",
    "Munich",
    "Hamburg",
    "Frankfurt",
    "Cologne",
    "Stuttgart",
    "Düsseldorf",
    "Dortmund",
    "Leipzig",
    "Dresden",
  ],
  France: [
    "Paris",
    "Lyon",
    "Marseille",
    "Toulouse",
    "Nice",
    "Nantes",
    "Strasbourg",
    "Bordeaux",
    "Lille",
    "Rennes",
  ],
  Netherlands: [
    "Amsterdam",
    "Rotterdam",
    "The Hague",
    "Utrecht",
    "Eindhoven",
    "Groningen",
    "Tilburg",
    "Haarlem",
  ],
  Spain: ["Madrid", "Barcelona", "Valencia", "Seville", "Zaragoza", "Malaga", "Bilbao", "Murcia"],
  Italy: ["Milan", "Rome", "Naples", "Turin", "Florence", "Bologna", "Genoa", "Palermo"],
  Ireland: ["Dublin", "Cork", "Galway", "Limerick", "Waterford"],
  Belgium: ["Brussels", "Antwerp", "Ghent", "Bruges", "Liege"],
  Austria: ["Vienna", "Graz", "Linz", "Salzburg", "Innsbruck"],
  Poland: ["Warsaw", "Krakow", "Wroclaw", "Gdansk", "Poznan", "Lodz"],
  Portugal: ["Lisbon", "Porto", "Braga", "Coimbra", "Faro"],
  Sweden: ["Stockholm", "Gothenburg", "Malmo", "Uppsala"],
  Pakistan: [
    "Karachi",
    "Lahore",
    "Islamabad",
    "Rawalpindi",
    "Faisalabad",
    "Multan",
    "Peshawar",
    "Quetta",
  ],
  "United Arab Emirates": ["Dubai", "Abu Dhabi", "Sharjah", "Ajman"],
  "United States": [
    "New York",
    "Los Angeles",
    "Chicago",
    "Houston",
    "Phoenix",
    "Miami",
    "Dallas",
    "Atlanta",
    "Seattle",
    "Boston",
  ],
};
const COUNTRIES = Object.keys(COUNTRY_CITIES);

function citiesForCountry(country: string): string[] {
  return COUNTRY_CITIES[country] || [];
}

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

function locationFromParts(city: string, country: string): string {
  const c = city?.trim();
  const nation = country?.trim() || "United Kingdom";
  if (c) return `${c}, ${nation}`;
  const fallback = citiesForCountry(nation)[0] || nation;
  return `${fallback}, ${nation}`;
}

const schema = z.object({
  keyword: z.string().min(1, "Required"),
  country: z.string().min(1, "Required"),
  city: z.string().min(1, "Required"),
  location: z.string().optional(),
  search_query: z.string().optional(),
  limit: z.coerce.number().min(1).max(500),
  enrich_contacts: z.boolean().optional(),
  only_verified_contacts: z.boolean().optional(),
  auto_generate_whatsapp: z.boolean().optional(),
  campaign_id: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

function ScraperPageContent() {
  const searchParams = useSearchParams();
  const jobStatus = useScraperJobStore((s) => s.jobStatus);
  const isAutoMode = useScraperJobStore((s) => s.isAutoMode);
  const iteration = useScraperJobStore((s) => s.iteration);
  const autoKeptTotal = useScraperJobStore((s) => s.autoKeptTotal);
  const agents = useScraperJobStore((s) => s.agents ?? []);
  const result = useScraperJobStore((s) => s.result);
  const errorMsg = useScraperJobStore((s) => s.errorMsg);
  const progress = useScraperJobStore((s) => s.progress);
  const stage = useScraperJobStore((s) => s.stage);
  const progressMessage = useScraperJobStore((s) => s.progressMessage);
  const isSubmitting = useScraperJobStore((s) => s.isSubmitting);
  const trackJob = useScraperJobStore((s) => s.trackJob);
  const resetForNewRun = useScraperJobStore((s) => s.resetForNewRun);
  const clearJob = useScraperJobStore((s) => s.clearJob);
  const recoverActiveJob = useScraperJobStore((s) => s.recoverActiveJob);
  const resumePolling = useScraperJobStore((s) => s.resumePolling);
  const stopAutoScrape = useScraperJobStore((s) => s.stopAutoScrape);
  const cancelJob = useScraperJobStore((s) => s.cancelJob);
  const liveMetrics = useScraperJobStore((s) => s.liveMetrics);
  const pauseJob = useScraperJobStore((s) => s.pauseJob);
  const resumeJob = useScraperJobStore((s) => s.resumeJob);
  const jobId = useScraperJobStore((s) => s.jobId);
  const jobApiStatus = useScraperJobStore((s) => s.jobApiStatus);

  const [suggestLoading, setSuggestLoading] = useState(false);
  const [autoPreparing, setAutoPreparing] = useState(false);
  const [rotateKeywords, setRotateKeywords] = useState(true);
  const [websiteFilter, setWebsiteFilter] = useState<WebsiteFilterMode>("all");
  const [enrichEmails, setEnrichEmails] = useState(false);
  const [prefsReady, setPrefsReady] = useState(false);
  const exportLeads = useExportLeads();

  const handleDownloadResults = () => {
    void exportLeads.mutateAsync({ format: "csv" }).then(() => toast.success("Export downloaded"));
  };

  const handleRestart = () => {
    clearJob();
  };

  const { register, handleSubmit, setValue, getValues, watch, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      keyword: "",
      country: "United Kingdom",
      city: "London",
      location: "",
      search_query: "",
      limit: 20,
    },
  });

  const selectedCountry = watch("country") || "United Kingdom";
  const cityOptions = citiesForCountry(selectedCountry);

  useEffect(() => {
    const options = citiesForCountry(selectedCountry);
    const currentCity = getValues("city");
    if (!options.includes(currentCity)) {
      setValue("city", options[0] || "", { shouldValidate: true });
    }
  }, [selectedCountry, getValues, setValue]);

  // Brain CV section prefs + deep-link: /scraper?keyword=...&website_filter=...&enrich=1
  useEffect(() => {
    const saved = readScrapePrefs();
    const kw = searchParams.get("keyword")?.trim();
    if (kw) setValue("keyword", kw, { shouldValidate: true });

    const wfParam = searchParams.get("website_filter");
    const wfFromUrl =
      wfParam === "with_website" || wfParam === "without_website" || wfParam === "all"
        ? wfParam
        : null;
    const enrichParam = searchParams.get("enrich") === "1";

    let nextFilter: WebsiteFilterMode =
      wfFromUrl || saved?.website_filter || "all";
    let nextEnrich = enrichParam || Boolean(saved?.enrich_emails);

    if (enrichParam && nextFilter === "without_website") {
      nextFilter = "with_website";
    }
    if (nextFilter === "without_website") {
      nextEnrich = false;
    }

    setWebsiteFilter(nextFilter);
    setEnrichEmails(nextEnrich);
    setPrefsReady(true);
  }, [searchParams, setValue]);

  useEffect(() => {
    if (!prefsReady) return;
    if (websiteFilter === "without_website") setEnrichEmails(false);
    writeScrapePrefs({
      website_filter: websiteFilter,
      enrich_emails: enrichEmails,
    });
  }, [websiteFilter, enrichEmails, prefsReady]);

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

  const applyBrainSuggest = async () => {
    setSuggestLoading(true);
    try {
      const country = getValues("country")?.trim() || "United Kingdom";
      const city = getValues("city")?.trim() || citiesForCountry(country)[0] || "";
      const loc = locationFromParts(city, country);
      const { data } = await api.post<ScrapeSuggestResponse>("/ai/suggest-scrape", {
        scrape_source: MAPS_SOURCE,
        randomize: true,
        current_keyword: getValues("keyword")?.trim() || "",
        current_search_query: getValues("search_query")?.trim() || "",
        location: loc,
        website_preference: websiteFilter,
      });
      if (data.recommended_keyword) {
        setValue("keyword", data.recommended_keyword, { shouldValidate: true });
      }
      if (data.recommended_search_query) {
        setValue(
          "search_query",
          ensureLocationInQuery(data.recommended_search_query, loc),
          { shouldValidate: true }
        );
      }
      toast.success("New suggestion applied");
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
      const country = data.country?.trim() || "United Kingdom";
      const city = data.city?.trim() || citiesForCountry(country)[0] || "";
      const resolvedLocation =
        data.location?.trim() || locationFromParts(city, country);
      const resolvedSearchQuery = data.search_query?.trim()
        ? ensureLocationInQuery(data.search_query, resolvedLocation)
        : undefined;
      const { data: start } = await api.post<{ job_id: string }>("/scraper/start", {
        keyword: data.keyword?.trim() || "",
        location: resolvedLocation,
        search_query: resolvedSearchQuery,
        limit: data.limit,
        scrape_source: MAPS_SOURCE,
        include_meta_ads: false,
        website_filter: websiteFilter,
        enrich_contacts: websiteFilter !== "without_website" && enrichEmails,
        only_verified_contacts: false,
        auto_generate_whatsapp: false,
        campaign_id: undefined,
      });
      trackJob(start.job_id);
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        if (await recoverActiveJob()) return;
        toast.error("Auto scrape is running — stop it first, then start again.");
        useScraperJobStore.setState({ isSubmitting: false, jobStatus: "idle" });
        return;
      }
      clearJob();
      const message = formatApiError(err, "Failed to start");
      useScraperJobStore.setState({ jobStatus: "failed", errorMsg: message, isSubmitting: false });
      toast.error(message);
    }
  };

  const startAutoScrape = async () => {
    if (isSubmitting) return;

    const country = getValues("country")?.trim() || "United Kingdom";
    const city = getValues("city")?.trim() || citiesForCountry(country)[0] || "";
    const resolvedLocation = locationFromParts(city, country);
    const keyword = getValues("keyword")?.trim() || "";
    if (!keyword) {
      toast.error("Enter a keyword first (e.g. plumber, cafe)");
      return;
    }

    const rawLimit = Number(getValues("limit"));
    const limit = Math.min(Math.max(Number.isFinite(rawLimit) ? rawLimit : 15, 1), 15);

    resetForNewRun(true);
    setAutoPreparing(true);
    useScraperJobStore.setState({
      progressMessage: "Starting country agents…",
      isSubmitting: true,
      jobStatus: "loading",
    });

    try {
      const { data: start } = await api.post<{ job_id: string }>("/scraper/auto/start", {
        keyword,
        location: resolvedLocation,
        search_query: `${keyword} ${resolvedLocation}`,
        limit,
        scrape_source: MAPS_SOURCE,
        include_meta_ads: false,
        website_filter: websiteFilter,
        enrich_contacts: websiteFilter !== "without_website" && enrichEmails,
        only_verified_contacts: false,
        auto_generate_whatsapp: false,
        rotate_keywords: rotateKeywords,
        interval_seconds: 8,
        country,
        parallel_agents: 2,
      });
      trackJob(start.job_id, `Auto · ${country}`, true);
      toast.success(
        rotateKeywords
          ? `Country auto started — ${country} (keywords rotate)`
          : `Country auto started — ${country} (fixed: ${keyword})`
      );
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

  return (
    <div className="w-full space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Scraper</h1>
        </div>
        <Link
          href="/leads"
          className="shrink-0 text-sm font-medium text-muted-foreground hover:text-foreground"
        >
          Inbox →
        </Link>
      </div>

      <div className="grid gap-6 lg:grid-cols-12 lg:items-start">
        <form
          onSubmit={handleSubmit(startScrape)}
          className="space-y-6 rounded-2xl border border-border/60 bg-card p-5 sm:p-6 lg:col-span-8 lg:p-8"
        >
        <div className="grid gap-5 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="keyword" className="text-xs text-muted-foreground">
              Keyword
            </Label>
            <div className="relative">
              <Input
                id="keyword"
                placeholder="Restaurant, Salon, Gym…"
                className="pr-10"
                {...register("keyword")}
              />
              <button
                type="button"
                onClick={() => void applyBrainSuggest()}
                disabled={suggestLoading}
                title="Brain suggest"
                aria-label="Brain suggest"
                className="absolute right-1.5 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground transition hover:bg-muted hover:text-foreground disabled:opacity-50"
              >
                <Brain className={cn("h-4 w-4", suggestLoading && "animate-pulse")} />
              </button>
            </div>
            {errors.keyword ? (
              <p className="text-xs text-destructive">{errors.keyword.message}</p>
            ) : null}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="limit" className="text-xs text-muted-foreground">
              Lead count
            </Label>
            <Input
              id="limit"
              type="number"
              min={1}
              max={500}
              className="h-10 tabular-nums"
              {...register("limit")}
            />
            {errors.limit ? (
              <p className="text-xs text-destructive">{errors.limit.message}</p>
            ) : null}
          </div>
        </div>

        <div className="space-y-2">
          <Label className="text-xs text-muted-foreground">Lead type</Label>
          <div className="flex flex-wrap gap-2">
            {(
              [
                { id: "without_website" as const, label: "Without website" },
                { id: "with_website" as const, label: "With website" },
                { id: "all" as const, label: "Both" },
              ] as const
            ).map((opt) => (
              <button
                key={opt.id}
                type="button"
                onClick={() => setWebsiteFilter(opt.id)}
                className={cn(
                  "rounded-lg border px-3 py-2 text-sm transition-colors",
                  websiteFilter === opt.id
                    ? "border-foreground bg-foreground text-background"
                    : "border-border/70 bg-background/60 hover:bg-muted/50"
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            {websiteFilter === "without_website"
              ? "Only businesses with no website on Google Maps (fewer results, takes longer)."
              : websiteFilter === "with_website"
                ? "Only businesses that list a website on Google Maps."
                : "All phone leads, with or without a website."}
          </p>
          {websiteFilter !== "without_website" ? (
            <button
              type="button"
              onClick={() => setEnrichEmails((v) => !v)}
              className={cn(
                "mt-1 flex w-full items-center gap-2 rounded-xl border px-3 py-2.5 text-left text-sm transition-colors",
                enrichEmails
                  ? "border-emerald-500/40 bg-emerald-500/10"
                  : "border-border/70 hover:bg-muted/40"
              )}
            >
              <Mail className={cn("h-4 w-4", enrichEmails ? "text-emerald-600" : "text-muted-foreground")} />
              <span className="flex-1">Also scrape Gmail / emails from websites</span>
              <span className="text-xs font-medium text-muted-foreground">
                {enrichEmails ? "ON" : "OFF"}
              </span>
            </button>
          ) : null}
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="country" className="text-xs text-muted-foreground">
              Country
            </Label>
            <Select id="country" {...register("country")}>
              {COUNTRIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
            {errors.country ? (
              <p className="text-xs text-destructive">{errors.country.message}</p>
            ) : (
              <p className="text-xs text-muted-foreground">
                Auto mode rotates cities in this country
              </p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="city" className="text-xs text-muted-foreground">
              City
            </Label>
            <Select id="city" {...register("city")}>
              {cityOptions.map((city) => (
                <option key={city} value={city}>
                  {city}
                </option>
              ))}
            </Select>
            {errors.city ? (
              <p className="text-xs text-destructive">{errors.city.message}</p>
            ) : (
              <p className="text-xs text-muted-foreground">
                Start scraping uses this city
              </p>
            )}
          </div>
        </div>

        <div className="space-y-3 border-t border-border/50 pt-5">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Run
            </p>
            {jobStatus === "loading" || isSubmitting ? null : (
              <button
                type="button"
                onClick={() => setRotateKeywords((v) => !v)}
                title={
                  rotateKeywords
                    ? "ON — auto changes keyword each wave"
                    : "OFF — keeps the same keyword"
                }
                className={cn(
                  "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
                  rotateKeywords
                    ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
                    : "border-border/70 text-muted-foreground hover:bg-muted/40"
                )}
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Keyword rotate {rotateKeywords ? "ON" : "OFF"}
              </button>
            )}
          </div>

          <div className="grid gap-2 sm:grid-cols-2">
            {jobStatus === "loading" || isSubmitting ? (
              <Button
                type="button"
                variant="destructive"
                size="lg"
                className="h-11 gap-2 sm:col-span-2"
                onClick={() => {
                  if (isAutoMode) {
                    void stopAutoScrape();
                    return;
                  }
                  if (jobId) {
                    void cancelJob(jobId);
                    return;
                  }
                  clearJob();
                }}
              >
                <Square className="h-4 w-4" />
                Stop
              </Button>
            ) : (
              <>
                <Button type="submit" size="lg" className="h-11 gap-2">
                  <Play className="h-4 w-4" />
                  Start scraping
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="lg"
                  className="h-11 gap-2"
                  isLoading={autoPreparing}
                  onClick={() => void startAutoScrape()}
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Auto country
                </Button>
              </>
            )}
          </div>

          {jobStatus === "loading" || isSubmitting ? null : (
            <p className="text-[11px] text-muted-foreground">
              {rotateKeywords
                ? "Keyword rotate ON — each auto wave uses a related keyword."
                : "Keyword rotate OFF — every agent keeps your entered keyword."}
            </p>
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
              agents={agents}
              liveMetrics={liveMetrics}
              apiStatus={jobApiStatus}
              onPause={jobId && !isAutoMode && jobApiStatus === "running" ? () => void pauseJob(jobId) : undefined}
              onResume={jobId && !isAutoMode && jobApiStatus === "paused" ? () => void resumeJob(jobId) : undefined}
              onRestart={handleRestart}
              onDownload={result?.count ? handleDownloadResults : undefined}
            />
          </div>
        </aside>
      </div>
    </div>
  );
}

export default function ScraperPage() {
  return (
    <Suspense fallback={<PageLoader />}>
      <ScraperPageContent />
    </Suspense>
  );
}
