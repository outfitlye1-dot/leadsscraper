"use client";

import Link from "next/link";
import {
  ArrowRight,
  Bot,
  Megaphone,
  MessageSquare,
  Search,
  Sparkles,
  TrendingUp,
  UserCheck,
  Users,
  XCircle,
} from "lucide-react";
import { useDashboardStats } from "@/hooks/useDashboard";
import { useScraperJobStore } from "@/store/scraperJobStore";
import { StatCard } from "@/components/ui/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { PageLoader } from "@/components/Loader";
import { PageHeader } from "@/components/PageHeader";
import { PageError } from "@/components/PageError";
import { Button } from "@/components/ui/Button";
import { JobStatusBadge } from "@/components/ui/StatusBadge";
import { cn } from "@/lib/utils";

const primaryStats = [
  { key: "total_leads" as const, label: "Total leads", icon: Users, iconTone: "blue" as const },
  { key: "new_leads" as const, label: "New", icon: Sparkles, iconTone: "violet" as const },
  { key: "interested_leads" as const, label: "Interested", icon: TrendingUp, iconTone: "emerald" as const },
  { key: "closed_leads" as const, label: "Closed", icon: UserCheck, iconTone: "sky" as const },
];

const secondaryStats = [
  { key: "contacted_leads" as const, label: "Contacted", icon: MessageSquare, iconTone: "indigo" as const },
  { key: "follow_up_leads" as const, label: "Follow up", icon: Users, iconTone: "amber" as const },
  { key: "lost_leads" as const, label: "Lost", icon: XCircle, iconTone: "rose" as const },
  { key: "campaign_count" as const, label: "Campaigns", icon: Megaphone, iconTone: "indigo" as const },
  { key: "messages_generated" as const, label: "AI messages", icon: Bot, iconTone: "violet" as const },
];

export default function DashboardPage() {
  const { data: stats, isLoading, error, refetch } = useDashboardStats();
  const jobStatus = useScraperJobStore((s) => s.jobStatus);
  const progress = useScraperJobStore((s) => s.progress);
  const stage = useScraperJobStore((s) => s.stage);
  const progressMessage = useScraperJobStore((s) => s.progressMessage);
  const isAutoMode = useScraperJobStore((s) => s.isAutoMode);

  if (isLoading) return <PageLoader />;
  if (error || !stats) {
    return <PageError message="Failed to load dashboard stats" onRetry={() => refetch()} />;
  }

  const conversion =
    stats.total_leads > 0 ? Math.round((stats.closed_leads / stats.total_leads) * 100) : 0;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Workspace"
        title="Dashboard"
        description="Your lead pipeline, scraping activity, and quick actions in one place."
      >
        <div className="flex flex-wrap gap-2">
          <Link href="/scraper">
            <Button size="sm">New scrape</Button>
          </Link>
          <Link href="/leads">
            <Button size="sm" variant="outline">
              View leads
            </Button>
          </Link>
        </div>
      </PageHeader>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {primaryStats.map(({ key, label, icon, iconTone }) => (
          <StatCard key={key} label={label} value={stats[key]} icon={icon} iconTone={iconTone} />
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Pipeline</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { label: "New", value: stats.new_leads },
              { label: "Contacted", value: stats.contacted_leads },
              { label: "Interested", value: stats.interested_leads },
              { label: "Follow up", value: stats.follow_up_leads },
              { label: "Closed", value: stats.closed_leads },
              { label: "Lost", value: stats.lost_leads },
            ].map((item) => {
              const pct = stats.total_leads
                ? Math.round((item.value / stats.total_leads) * 100)
                : 0;
              return (
                <div key={item.label}>
                  <div className="mb-1.5 flex justify-between text-sm">
                    <span className="font-medium">{item.label}</span>
                    <span className="tabular-nums text-muted-foreground">
                      {item.value} · {pct}%
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-foreground/80 transition-all duration-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Active scraper</CardTitle>
            </CardHeader>
            <CardContent>
              {jobStatus === "loading" ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <JobStatusBadge status="running" />
                    <span className="text-sm font-semibold tabular-nums">{progress}%</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {isAutoMode ? "Auto mode" : stage} · {progressMessage}
                  </p>
                  <div className="h-1 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-foreground transition-all"
                      style={{ width: `${Math.max(progress, 4)}%` }}
                    />
                  </div>
                  <Link href="/scraper">
                    <Button variant="outline" size="sm" className="w-full gap-1.5">
                      Open scraper
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-3 text-sm text-muted-foreground">
                  <p>No scrape running right now.</p>
                  <Link href="/scraper" className="mt-2 block">
                    <Button size="sm" className="gap-1.5">
                      <Search className="h-3.5 w-3.5" />
                      Start scraping
                    </Button>
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Quick actions</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-2">
              {[
                { href: "/scraper", label: "Run scraper", icon: Search },
                { href: "/ai", label: "Generate message", icon: Bot },
                { href: "/messages", label: "View messages", icon: MessageSquare },
                { href: "/brain", label: "AI Brain", icon: Sparkles },
              ].map(({ href, label, icon: Icon }) => (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    "flex items-center gap-2.5 rounded-lg border border-border/60 px-3 py-2.5 text-sm font-medium transition-colors hover:bg-muted/50"
                  )}
                >
                  <Icon className="h-4 w-4 text-muted-foreground" strokeWidth={1.75} />
                  {label}
                </Link>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {secondaryStats.map(({ key, label, icon, iconTone }) => (
          <StatCard key={key} label={label} value={stats[key]} icon={icon} iconTone={iconTone} />
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="flex items-center justify-between p-5">
            <div>
              <p className="text-xs text-muted-foreground">Conversion rate</p>
              <p className="text-2xl font-semibold tabular-nums">{conversion}%</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center justify-between p-5">
            <div>
              <p className="text-xs text-muted-foreground">Messages per lead</p>
              <p className="text-2xl font-semibold tabular-nums">
                {stats.total_leads
                  ? (stats.messages_generated / stats.total_leads).toFixed(1)
                  : "0"}
              </p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center justify-between p-5">
            <div>
              <p className="text-xs text-muted-foreground">Active campaigns</p>
              <p className="text-2xl font-semibold tabular-nums">{stats.campaign_count}</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
