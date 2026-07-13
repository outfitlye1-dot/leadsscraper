"use client";

import { useEffect, useRef } from "react";
import { Terminal } from "lucide-react";
import type { ScraperLogEntry } from "@/lib/types";
import { scraperStageLabel } from "@/lib/scraperStages";
import { cn } from "@/lib/utils";

type Props = {
  logs: ScraperLogEntry[];
  progress: number;
  stage: string;
  message: string;
  isRunning: boolean;
  /** Taller layout when docked at page bottom */
  docked?: boolean;
  title?: string;
  emptyHint?: string;
};

const LEVEL_CLASS: Record<string, string> = {
  info: "text-zinc-300",
  success: "text-emerald-400",
  lead: "text-sky-300",
  warn: "text-amber-400",
  error: "text-red-400",
};

function formatTime(ts: string) {
  try {
    return new Date(ts).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "";
  }
}

export function ScraperTerminal({
  logs,
  progress,
  stage,
  message,
  isRunning,
  docked = false,
  title = "Scraper live",
  emptyHint = "Query, crawl steps, and leads appear here when scraping starts",
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length, message]);

  if (!isRunning && logs.length === 0) {
    return (
      <div
        className={cn(
          "rounded-xl border border-dashed border-border/60 bg-zinc-950/40 px-4 text-center",
          docked ? "py-10" : "py-8"
        )}
      >
        <Terminal className="mx-auto mb-2 h-5 w-5 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Live terminal</p>
        <p className="mt-1 text-xs text-muted-foreground">{emptyHint}</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950 text-zinc-100 shadow-inner">
      <div className="flex items-center justify-between border-b border-zinc-800 bg-zinc-900/80 px-3 py-2">
        <div className="flex items-center gap-2 text-xs text-zinc-400">
          <span className="flex gap-1">
            <span className="h-2.5 w-2.5 rounded-full bg-red-500/80" />
            <span className="h-2.5 w-2.5 rounded-full bg-amber-500/80" />
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500/80" />
          </span>
          <Terminal className="h-3.5 w-3.5" />
          <span>{title}</span>
        </div>
        {isRunning ? (
          <span className="text-xs tabular-nums text-zinc-500">
            {scraperStageLabel(stage)} · {progress}%
          </span>
        ) : null}
      </div>

      <div
        className={cn(
          "overflow-y-auto p-3 font-mono text-[11px] leading-relaxed sm:text-xs",
          docked
            ? "min-h-[220px] max-h-[min(50vh,420px)]"
            : "max-h-[320px] sm:max-h-[420px]"
        )}
      >
        {logs.map((line) => (
          <div key={line.seq} className="flex gap-2 py-0.5">
            <span className="shrink-0 text-zinc-600">{formatTime(line.ts)}</span>
            <span className={cn("min-w-0 break-words", LEVEL_CLASS[line.level] || LEVEL_CLASS.info)}>
              {line.level === "lead" ? "◆ " : line.level === "success" ? "✓ " : line.level === "error" ? "✗ " : "› "}
              {line.text}
            </span>
          </div>
        ))}
        {message && isRunning ? (
          <div className="flex gap-2 py-0.5 text-zinc-500">
            <span className="shrink-0">···</span>
            <span className="animate-pulse">{message}</span>
          </div>
        ) : null}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
