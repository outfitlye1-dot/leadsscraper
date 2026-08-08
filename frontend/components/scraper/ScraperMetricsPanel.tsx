"use client";

import type { ScrapeMetricsResponse } from "@/lib/types";

type Props = {
  metrics: ScrapeMetricsResponse | null | undefined;
};

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="min-w-0 rounded-lg border border-border/50 bg-muted/40 px-2.5 py-2">
      <p className="truncate text-[11px] font-medium leading-tight text-muted-foreground">
        {label}
      </p>
      <p className="mt-0.5 text-base font-semibold tabular-nums leading-none text-foreground">
        {value}
      </p>
    </div>
  );
}

export function ScraperMetricsPanel({ metrics }: Props) {
  if (!metrics) return null;

  return (
    <div className="no-glass rounded-xl border border-border/60 bg-card p-4">
      <p className="mb-3 text-sm font-semibold tracking-tight text-foreground">
        Live engine metrics
      </p>
      <div className="grid grid-cols-2 gap-2">
        <Stat label="Discovered" value={metrics.pages_discovered ?? 0} />
        <Stat label="Pages fetched" value={metrics.pages_fetched ?? 0} />
        <Stat label="Failed" value={metrics.pages_failed ?? 0} />
        <Stat label="Success rate" value={`${metrics.success_rate ?? 0}%`} />
        <Stat label="Leads parsed" value={metrics.leads_parsed ?? 0} />
        <Stat label="Workers" value={metrics.active_workers ?? 0} />
        <Stat label="Queue" value={metrics.queue_size ?? 0} />
        <Stat label="HTTP strategy" value={metrics.strategy_http ?? 0} />
        <Stat label="Retries" value={metrics.retry_count ?? 0} />
        <Stat label="Bot blocks" value={metrics.bot_blocks ?? 0} />
        <Stat
          label="Browser renders"
          value={metrics.browser_renders ?? metrics.js_render_used ?? 0}
        />
        <Stat label="Playwright" value={metrics.strategy_playwright ?? 0} />
        <Stat label="Req/min" value={metrics.requests_per_minute ?? 0} />
      </div>
      <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
        Fast mode uses HTTP only — Browser/Playwright stay 0 unless deep crawl is on.
      </p>
    </div>
  );
}
