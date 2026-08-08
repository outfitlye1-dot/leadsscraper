"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Loader2, Square, X } from "lucide-react";
import { useScraperJobStore } from "@/store/scraperJobStore";
import { Button } from "@/components/ui/Button";

export function ScraperJobBanner() {
  const pathname = usePathname();
  const jobStatus = useScraperJobStore((s) => s.jobStatus);
  const isAutoMode = useScraperJobStore((s) => s.isAutoMode);
  const progress = useScraperJobStore((s) => s.progress);
  const progressMessage = useScraperJobStore((s) => s.progressMessage);
  const iteration = useScraperJobStore((s) => s.iteration);
  const autoKeptTotal = useScraperJobStore((s) => s.autoKeptTotal);
  const autoDeletedTotal = useScraperJobStore((s) => s.autoDeletedTotal);
  const cancelRequested = useScraperJobStore((s) => s.cancelRequested);
  const result = useScraperJobStore((s) => s.result);
  const errorMsg = useScraperJobStore((s) => s.errorMsg);
  const clearJob = useScraperJobStore((s) => s.clearJob);
  const stopAutoScrape = useScraperJobStore((s) => s.stopAutoScrape);

  if (pathname !== "/scraper" || jobStatus === "idle") return null;

  const isRunning = jobStatus === "loading";

  return (
    <div
      className={`border-b px-4 py-2.5 lg:px-8 ${
        jobStatus === "failed"
          ? "border-destructive/30 bg-destructive/5"
          : jobStatus === "success"
            ? "border-emerald-500/30 bg-emerald-500/5"
            : "border-primary/20 bg-primary/5"
      }`}
    >
      <div className="mx-auto flex max-w-7xl flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 flex-1 items-start gap-3 sm:items-center">
          {isRunning ? (
            <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-primary sm:mt-0" />
          ) : null}
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium">
              {isRunning
                ? isAutoMode
                  ? `Auto scraping${iteration > 0 ? ` · round ${iteration}` : ""}`
                  : "Scraping in background"
                : jobStatus === "success"
                  ? isAutoMode
                    ? "Auto scraping stopped"
                    : "Scraping complete"
                  : "Scraping failed"}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              {isRunning
                ? isAutoMode
                  ? `${progressMessage || "Working..."}${autoKeptTotal > 0 ? ` · ${autoKeptTotal} phone leads kept` : ""}`
                  : progressMessage || "Working..."
                : jobStatus === "success"
                  ? isAutoMode
                    ? progressMessage || `${autoKeptTotal} phone leads kept, ${autoDeletedTotal} removed`
                    : result?.message || `${result?.count ?? 0} leads saved`
                  : errorMsg}
            </p>
            {isRunning ? (
              <div className="mt-2 h-1.5 max-w-md overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary transition-all duration-500"
                  style={{ width: `${Math.max(progress, 4)}%` }}
                />
              </div>
            ) : null}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {isRunning && !isAutoMode ? (
            <span className="text-xs font-medium tabular-nums text-muted-foreground">{progress}%</span>
          ) : null}
          {isRunning && isAutoMode ? (
            <Button
              type="button"
              variant="destructive"
              size="sm"
              onClick={() => void stopAutoScrape()}
            >
              <Square className="mr-1.5 h-3 w-3" />
              Stop
            </Button>
          ) : null}
          <Link href="/scraper">
            <Button type="button" variant="outline" size="sm">
              {isRunning ? "View progress" : "Open scraper"}
            </Button>
          </Link>
          {!isRunning ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0"
              onClick={clearJob}
              aria-label="Dismiss"
            >
              <X className="h-4 w-4" />
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
