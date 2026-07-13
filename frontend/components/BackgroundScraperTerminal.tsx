"use client";

import Link from "next/link";
import { ChevronDown, ChevronUp, Radio } from "lucide-react";
import { useEffect, useState } from "react";
import { ScraperTerminal } from "@/components/scraper/ScraperTerminal";
import { Button } from "@/components/ui/Button";
import { useBackgroundScraperStatus } from "@/hooks/useBackgroundScraper";
import { cn } from "@/lib/utils";

type Props = {
  /** Full-width docked layout for settings/database page */
  docked?: boolean;
  /** Always show expanded terminal (no collapse) */
  expanded?: boolean;
};

export function BackgroundScraperTerminal({ docked = false, expanded = false }: Props) {
  const { data: status } = useBackgroundScraperStatus();
  const [open, setOpen] = useState(expanded);
  const isActive = Boolean(status?.active);
  const isRunning = Boolean(status?.running);
  const logs = status?.logs ?? [];

  useEffect(() => {
    if (isRunning && !expanded) {
      setOpen(true);
    }
  }, [isRunning, expanded]);

  const showPanel = isActive || logs.length > 0;

  if (!showPanel && !docked) return null;

  const isOpen = expanded || open;

  return (
    <div
      className={cn(
        docked ? "space-y-3" : "border-t border-border/60 bg-background/95 backdrop-blur-sm"
      )}
    >
      {!docked ? (
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-2 lg:px-8">
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="flex min-w-0 flex-1 items-center gap-2 text-left"
          >
            <Radio
              className={cn(
                "h-4 w-4 shrink-0",
                isRunning ? "animate-pulse text-emerald-500" : isActive ? "text-amber-500" : "text-muted-foreground"
              )}
            />
            <div className="min-w-0">
              <p className="text-sm font-medium">
                Background scraper
                {isRunning ? " · working" : isActive ? " · idle" : ""}
              </p>
              <p className="truncate text-xs text-muted-foreground">
                {status?.message || "Login par silently leads collect hoti hain"}
                {status && status.total_saved > 0 ? ` · ${status.total_saved} saved this session` : ""}
              </p>
            </div>
            {isOpen ? (
              <ChevronDown className="ml-auto h-4 w-4 shrink-0 text-muted-foreground" />
            ) : (
              <ChevronUp className="ml-auto h-4 w-4 shrink-0 text-muted-foreground" />
            )}
          </button>
          <Link href="/settings/database">
            <Button type="button" variant="outline" size="sm">
              Database
            </Button>
          </Link>
        </div>
      ) : null}

      {isOpen || docked ? (
        <div className={cn(!docked && "border-t border-border/40 px-4 pb-4 pt-3 lg:px-8")}>
          <div className={cn(!docked && "mx-auto max-w-7xl")}>
            {docked ? (
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Live terminal
                {isRunning ? (
                  <span className="ml-2 font-normal normal-case tabular-nums">
                    {status?.progress ?? 0}% · {status?.message || "Running…"}
                  </span>
                ) : null}
              </p>
            ) : null}
            <ScraperTerminal
              docked={docked}
              logs={logs}
              progress={status?.progress ?? 0}
              stage={status?.stage ?? "idle"}
              message={status?.message ?? ""}
              isRunning={isRunning}
              title="Background scraper"
              emptyHint="Login rehne par yahan live steps dikhenge — round, query, crawl, save"
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
