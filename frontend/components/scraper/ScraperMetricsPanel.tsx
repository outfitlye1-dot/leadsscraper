"use client";

import type { ScrapeMetricsResponse } from "@/lib/types";

type Props = {
  metrics: ScrapeMetricsResponse | null | undefined;
};

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-border/50 bg-muted/30 px-3 py-2">
      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="text-sm font-semibold tabular-nums">{value}</p>
    </div>
  );
}

export function ScraperMetricsPanel({ metrics }: Props) {
  if (!metrics) return null;

  return (
    <div className="rounded-xl border border-border/60 bg-card p-4">
      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Live engine metrics
      </p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
        <Stat label="Pages fetched" value={metrics.pages_fetched ?? 0} />
        <Stat label="Failed" value={metrics.pages_failed ?? 0} />
        <Stat label="Success rate" value={`${metrics.success_rate ?? 0}%`} />
        <Stat label="Leads parsed" value={metrics.leads_parsed ?? 0} />
        <Stat label="Browser renders" value={metrics.browser_renders ?? metrics.js_render_used ?? 0} />
        <Stat label="Retries" value={metrics.retry_count ?? 0} />
        <Stat label="Bot blocks" value={metrics.bot_blocks ?? 0} />
        <Stat label="Req/min" value={metrics.requests_per_minute ?? 0} />
        <Stat label="Queue" value={metrics.queue_size ?? 0} />
        <Stat label="Workers" value={metrics.active_workers ?? 0} />
        <Stat label="HTTP strategy" value={metrics.strategy_http ?? 0} />
        <Stat label="Playwright" value={metrics.strategy_playwright ?? 0} />
      </div>
    </div>
  );
}
