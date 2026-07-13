"use client";

import Link from "next/link";
import { useMemo } from "react";
import {
  ArrowRight,
  CheckCircle,
  Download,
  Pause,
  Play,
  RefreshCw,
  Square,
  XCircle,
} from "lucide-react";
import type { ScraperResponse, ScrapeMetricsResponse } from "@/lib/types";
import { scraperStageLabel } from "@/lib/scraperStages";
import { ScraperMetricsPanel } from "@/components/scraper/ScraperMetricsPanel";
import { JobStatusBadge } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { cn } from "@/lib/utils";

type JobStatus = "idle" | "loading" | "success" | "failed";

type Props = {
  jobStatus: JobStatus;
  isAutoMode: boolean;
  iteration: number;
  progress: number;
  stage: string;
  progressMessage: string;
  result: ScraperResponse | null;
  errorMsg: string;
  autoKeptTotal: number;
  liveMetrics?: ScrapeMetricsResponse | null;
  apiStatus?: string | null;
  onPause?: () => void;
  onResume?: () => void;
  onCancel?: () => void;
  onRestart?: () => void;
  onDownload?: () => void;
};

function estimateEta(progress: number): string | null {
  if (progress < 8 || progress >= 100) return null;
  const remaining = 100 - progress;
  const mins = Math.max(1, Math.round((remaining / progress) * 0.8));
  return mins < 2 ? "~1 min left" : `~${mins} min left`;
}

export function ScraperRunStatus({
  jobStatus,
  isAutoMode,
  iteration,
  progress,
  stage,
  progressMessage,
  result,
  errorMsg,
  autoKeptTotal,
  liveMetrics,
  apiStatus,
  onPause,
  onResume,
  onCancel,
  onRestart,
  onDownload,
}: Props) {
  const eta = useMemo(() => estimateEta(progress), [progress]);
  const m = liveMetrics;
  const runningStatus =
    apiStatus === "paused" ? "paused" : isAutoMode ? "running" : stage === "error" ? "failed" : "running";

  if (jobStatus === "idle") {
    return (
      <EmptyState
        title="Ready to scrape"
        description="Configure your search and start a manual or auto scrape. Live metrics and logs appear here."
      />
    );
  }

  if (jobStatus === "loading") {
    return (
      <div className="space-y-4">
        <div className="app-panel overflow-hidden">
          <div className="border-b border-border/60 bg-muted/20 px-4 py-3">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-60" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
                </span>
                <JobStatusBadge status={runningStatus} />
              </div>
              {!isAutoMode ? (
                <span className="text-sm font-semibold tabular-nums">{progress}%</span>
              ) : (
                <span className="text-xs text-muted-foreground">Round {iteration || 1}</span>
              )}
            </div>
            <p className="mt-2 text-sm font-medium">
              {isAutoMode ? "Auto scraping in progress" : scraperStageLabel(stage)}
            </p>
            <p className="mt-0.5 truncate text-xs text-muted-foreground">
              {progressMessage}
              {autoKeptTotal > 0 ? ` · ${autoKeptTotal} kept` : ""}
              {eta ? ` · ${eta}` : ""}
            </p>
          </div>

          {!isAutoMode ? (
            <div className="px-4 pt-3">
              <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-foreground transition-all duration-500 ease-out"
                  style={{ width: `${Math.max(progress, 3)}%` }}
                />
              </div>
            </div>
          ) : null}

          <div className="grid grid-cols-2 gap-px border-t border-border/60 bg-border/40 sm:grid-cols-4">
            {[
              { label: "Pages", value: m?.pages_fetched ?? 0 },
              { label: "Leads found", value: m?.leads_parsed ?? 0 },
              { label: "Failed", value: m?.pages_failed ?? 0 },
              { label: "Success", value: `${m?.success_rate ?? 0}%` },
            ].map((item) => (
              <div key={item.label} className="bg-card px-3 py-2.5">
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{item.label}</p>
                <p className="text-sm font-semibold tabular-nums">{item.value}</p>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-2 border-t border-border/60 p-3">
            {onPause ? (
              <Button type="button" variant="outline" size="sm" onClick={onPause} className="gap-1.5">
                <Pause className="h-3.5 w-3.5" />
                Pause
              </Button>
            ) : null}
            {onResume ? (
              <Button type="button" variant="outline" size="sm" onClick={onResume} className="gap-1.5">
                <Play className="h-3.5 w-3.5" />
                Resume
              </Button>
            ) : null}
            {onCancel ? (
              <Button type="button" variant="destructive" size="sm" onClick={onCancel} className="gap-1.5">
                <Square className="h-3.5 w-3.5" />
                Stop
              </Button>
            ) : null}
          </div>
        </div>
        <ScraperMetricsPanel metrics={liveMetrics} />
      </div>
    );
  }

  if (jobStatus === "failed") {
    return (
      <div className="app-panel border-destructive/30 bg-destructive/5 p-4">
        <div className="flex items-start gap-3">
          <XCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-destructive">Scrape failed</p>
            <p className="mt-1 text-sm text-destructive/90">{errorMsg || "Something went wrong"}</p>
            {onRestart ? (
              <Button type="button" variant="outline" size="sm" className="mt-3 gap-1.5" onClick={onRestart}>
                <RefreshCw className="h-3.5 w-3.5" />
                Restart
              </Button>
            ) : null}
          </div>
        </div>
      </div>
    );
  }

  if (!result) return null;

  const saved = result.count ?? 0;
  const duplicates = result.skipped_duplicates ?? 0;

  return (
    <div
      className={cn(
        "app-panel overflow-hidden",
        saved > 0 ? "border-emerald-500/25" : "border-border/60"
      )}
    >
      <div
        className={cn(
          "flex items-start gap-3 border-b border-border/60 px-4 py-3",
          saved > 0 ? "bg-emerald-500/5" : "bg-muted/20"
        )}
      >
        <CheckCircle
          className={cn("mt-0.5 h-5 w-5 shrink-0", saved > 0 ? "text-emerald-600" : "text-amber-500")}
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold">{saved > 0 ? `${saved} leads saved` : "No leads saved"}</p>
            <JobStatusBadge status="completed" />
          </div>
          {result.message ? (
            <p className="mt-1 text-xs text-muted-foreground">{result.message}</p>
          ) : null}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-px bg-border/40 sm:grid-cols-3">
        {[
          { label: "Duplicates skipped", value: duplicates },
          { label: "Emails", value: result.emails_found ?? 0 },
          { label: "WhatsApp", value: result.whatsapp_numbers_found ?? 0 },
        ].map((item) => (
          <div key={item.label} className="bg-card px-3 py-2.5">
            <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{item.label}</p>
            <p className="text-sm font-semibold tabular-nums">{item.value}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2 p-3">
        {saved > 0 ? (
          <Link href="/leads">
            <Button size="sm" className="gap-1.5">
              Open inbox
              <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </Link>
        ) : null}
        {onDownload && saved > 0 ? (
          <Button type="button" variant="outline" size="sm" onClick={onDownload} className="gap-1.5">
            <Download className="h-3.5 w-3.5" />
            Download
          </Button>
        ) : null}
        {onRestart ? (
          <Button type="button" variant="outline" size="sm" onClick={onRestart} className="gap-1.5">
            <RefreshCw className="h-3.5 w-3.5" />
            Run again
          </Button>
        ) : null}
      </div>
    </div>
  );
}
