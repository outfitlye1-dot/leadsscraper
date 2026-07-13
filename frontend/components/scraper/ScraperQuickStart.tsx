"use client";

import Link from "next/link";
import { Zap } from "lucide-react";
import type { DailyScrapeStatusResponse } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

type Props = {
  dailyStatus: DailyScrapeStatusResponse | null;
  dailyLoading: boolean;
  isSubmitting: boolean;
  onDailyScrape: () => void;
};

export function ScraperQuickStart({
  dailyStatus,
  dailyLoading,
  isSubmitting,
  onDailyScrape,
}: Props) {
  const canRun = dailyStatus?.can_run && dailyStatus?.has_profile;

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/60 bg-muted/30 px-4 py-3">
      <div className="min-w-0">
        <p className="text-sm font-medium">Daily 100 leads</p>
        <p className="text-xs text-muted-foreground">
          {!dailyStatus?.has_profile ? (
            <>
              <Link href="/brain" className="underline">
                Set up Brain
              </Link>{" "}
              to enable
            </>
          ) : dailyLoading ? (
            "Checking…"
          ) : canRun ? (
            "One click · businesses without websites"
          ) : (
            "Already used today"
          )}
        </p>
      </div>
      <Button
        type="button"
        size="sm"
        className="shrink-0 gap-1.5"
        onClick={onDailyScrape}
        disabled={dailyLoading || !canRun || isSubmitting}
        isLoading={isSubmitting}
      >
        <Zap className="h-3.5 w-3.5" />
        Run
      </Button>
    </div>
  );
}
