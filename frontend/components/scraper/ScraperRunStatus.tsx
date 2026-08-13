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
  XCircle,
} from "lucide-react";
import type { ScraperAgentStatus, ScraperResponse, ScraperRoundStatus, ScrapeMetricsResponse } from "@/lib/types";
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
  autoDeletedTotal?: number;
  autoScrapedTotal?: number;
  agents?: ScraperAgentStatus[];
  rounds?: ScraperRoundStatus[];
  liveMetrics?: ScrapeMetricsResponse | null;
  apiStatus?: string | null;
  onPause?: () => void;
  onResume?: () => void;
  onRestart?: () => void;
  onDownload?: () => void;
};

function estimateEta(progress: number): string | null {
  if (progress < 8 || progress >= 100) return null;
  const remaining = 100 - progress;
  const mins = Math.max(1, Math.round((remaining / progress) * 0.8));
  return mins < 2 ? "~1 min left" : `~${mins} min left`;
}

function agentStatusLabel(status?: string) {
  switch (status) {
    case "running":
      return "Running";
    case "queued":
      return "Queued";
    case "waiting":
      return "Waiting";
    case "done":
      return "Done";
    case "failed":
      return "Failed";
    default:
      return "Idle";
  }
}

function RoundStatusPanel({
  rounds,
  iteration,
  isAutoMode,
  autoKeptTotal,
  autoScrapedTotal,
  autoDeletedTotal,
  liveLeads,
}: {
  rounds: ScraperRoundStatus[];
  iteration: number;
  isAutoMode: boolean;
  autoKeptTotal: number;
  autoScrapedTotal?: number;
  autoDeletedTotal?: number;
  liveLeads?: number;
}) {
  const sorted = [...rounds].sort((a, b) => a.round - b.round);
  const currentRound = iteration || sorted[sorted.length - 1]?.round || 1;

  if (!sorted.length && !isAutoMode) {
    return (
      <div className="border-t border-border/60 px-4 py-3">
        <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Round</p>
        <div className="mt-2 flex items-center justify-between rounded-lg border border-border/50 bg-muted/15 px-3 py-2.5">
          <div>
            <p className="text-xs font-semibold">Round 1</p>
            <p className="text-xs text-muted-foreground">Manual scrape</p>
          </div>
          <span className="text-sm font-semibold tabular-nums text-emerald-700">
            {liveLeads ?? 0} leads
          </span>
        </div>
      </div>
    );
  }

  if (!sorted.length) return null;

  const doneRounds = sorted.filter((r) => r.status === "done").length;
  const totalKept = autoKeptTotal || sorted.reduce((sum, r) => sum + (r.kept ?? 0), 0);

  return (
    <div className="border-t border-border/60 px-4 py-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          {isAutoMode ? "Rounds" : "Round status"}
        </p>
        <span className="text-xs font-medium text-foreground">
          Round {currentRound}
          {isAutoMode && doneRounds > 0 ? ` · ${doneRounds} done` : ""}
        </span>
      </div>

      {(autoKeptTotal > 0 || (autoScrapedTotal ?? 0) > 0) && isAutoMode ? (
        <p className="mb-2 text-xs text-muted-foreground">
          Total: <span className="font-medium text-foreground">{totalKept} kept</span>
          {(autoScrapedTotal ?? 0) > 0 ? ` · ${autoScrapedTotal} scraped` : ""}
          {(autoDeletedTotal ?? 0) > 0 ? ` · ${autoDeletedTotal} removed` : ""}
        </p>
      ) : null}

      <ul className="max-h-52 space-y-1.5 overflow-y-auto">
        {sorted.map((round) => {
          const isRunning = round.status === "running";
          const leads = round.kept ?? round.scraped ?? 0;
          return (
            <li
              key={round.round}
              className={cn(
                "flex items-start justify-between gap-2 rounded-lg border px-3 py-2",
                isRunning ? "border-emerald-500/30 bg-emerald-500/5" : "border-border/50 bg-muted/10"
              )}
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold tabular-nums">Round {round.round}</span>
                  {isRunning ? (
                    <span className="inline-flex items-center gap-1 text-[10px] font-medium uppercase tracking-wide text-emerald-700">
                      <span className="relative flex h-1.5 w-1.5">
                        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-60" />
                        <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
                      </span>
                      Running
                    </span>
                  ) : (
                    <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                      Done
                    </span>
                  )}
                </div>
                {round.label ? (
                  <p className="mt-0.5 truncate text-xs text-muted-foreground" title={round.label}>
                    {round.label}
                  </p>
                ) : null}
              </div>
              <div className="shrink-0 text-right">
                <p className="text-sm font-semibold tabular-nums">{isRunning && !leads ? "…" : leads}</p>
                <p className="text-[10px] text-muted-foreground">leads</p>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function AgentRoster({ agents, roundLabel }: { agents: ScraperAgentStatus[]; roundLabel?: string }) {
  if (!agents.length) return null;
  return (
    <div className="space-y-2 border-t border-border/60 px-4 py-3">
      <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        {roundLabel ? `Agents · ${roundLabel}` : "Agents"}
      </p>
      <ul className="space-y-2">
        {agents.map((agent) => {
          const status = agent.status || "idle";
          const isLive = status === "running";
          return (
            <li
              key={agent.id}
              className="rounded-lg border border-border/50 bg-muted/15 px-3 py-2.5"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-xs font-semibold">{agent.label || agent.id}</p>
                  <p className="mt-0.5 truncate text-sm">
                    <span className="text-foreground">{agent.keyword || "—"}</span>
                    <span className="text-muted-foreground"> · </span>
                    <span className="text-foreground">{agent.city || "—"}</span>
                  </p>
                </div>
                <span
                  className={cn(
                    "shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide",
                    status === "running" && "bg-emerald-500/15 text-emerald-700",
                    status === "queued" && "bg-amber-500/15 text-amber-700",
                    status === "waiting" && "bg-muted text-muted-foreground",
                    status === "done" && "bg-emerald-500/10 text-emerald-700",
                    status === "failed" && "bg-destructive/10 text-destructive",
                    status === "idle" && "bg-muted text-muted-foreground"
                  )}
                >
                  {isLive ? (
                    <span className="inline-flex items-center gap-1">
                      <span className="relative flex h-1.5 w-1.5">
                        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-60" />
                        <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
                      </span>
                      {agentStatusLabel(status)}
                    </span>
                  ) : (
                    agentStatusLabel(status)
                  )}
                </span>
              </div>
              <p className="mt-1 truncate text-xs text-muted-foreground">
                {agent.message || "—"}
                {typeof agent.kept === "number" && agent.kept > 0
                  ? ` · ${agent.kept} kept`
                  : ""}
              </p>
            </li>
          );
        })}
      </ul>
    </div>
  );
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
  autoDeletedTotal = 0,
  autoScrapedTotal = 0,
  agents = [],
  rounds = [],
  liveMetrics,
  apiStatus,
  onPause,
  onResume,
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
        description="Configure your search and start a manual or auto scrape. Progress appears here."
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
                <span className="rounded-md bg-muted px-2 py-0.5 text-xs font-semibold tabular-nums">
                  Round {iteration || 1}
                </span>
              )}
            </div>
            <p className="mt-2 text-sm font-medium">
              {isAutoMode
                ? progressMessage || "Auto scraping in progress"
                : progressMessage || "Scraping in progress"}
            </p>
            <p className="mt-0.5 truncate text-xs text-muted-foreground">
              {isAutoMode
                ? [
                    autoKeptTotal > 0 ? `${autoKeptTotal} leads kept total` : null,
                    (autoScrapedTotal ?? 0) > 0 ? `${autoScrapedTotal} scraped` : null,
                  ]
                    .filter(Boolean)
                    .join(" · ") || "Starting rounds…"
                : [eta, (m?.leads_saved ?? m?.leads_parsed) ? `${m?.leads_saved ?? m?.leads_parsed} found` : null]
                    .filter(Boolean)
                    .join(" · ") || "Working…"}
            </p>
          </div>

          <RoundStatusPanel
            rounds={rounds}
            iteration={iteration}
            isAutoMode={isAutoMode}
            autoKeptTotal={autoKeptTotal}
            autoScrapedTotal={autoScrapedTotal}
            autoDeletedTotal={autoDeletedTotal}
            liveLeads={m?.leads_saved ?? m?.leads_parsed}
          />

          {isAutoMode && agents.length > 0 ? (
            <AgentRoster agents={agents} roundLabel={`Round ${iteration || 1}`} />
          ) : null}

          {!isAutoMode ? (
            <div className="flex items-center px-4 py-3">
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-foreground transition-all duration-500 ease-out"
                  style={{ width: `${Math.max(progress, 3)}%` }}
                />
              </div>
            </div>
          ) : null}

          {!isAutoMode ? (
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
          ) : null}

          {(onPause || onResume) ? (
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
            </div>
          ) : null}
        </div>
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

      {rounds.length > 0 ? (
        <RoundStatusPanel
          rounds={rounds}
          iteration={iteration}
          isAutoMode={isAutoMode}
          autoKeptTotal={autoKeptTotal}
          autoScrapedTotal={autoScrapedTotal}
          autoDeletedTotal={autoDeletedTotal}
        />
      ) : null}

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
