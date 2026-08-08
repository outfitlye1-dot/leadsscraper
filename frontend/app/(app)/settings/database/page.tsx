"use client";

import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Database,
  HardDrive,
  Loader2,
  Radio,
  RefreshCw,
} from "lucide-react";
import api from "@/lib/api";
import { BackgroundScraperTerminal } from "@/components/BackgroundScraperTerminal";
import { PageLoader } from "@/components/Loader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { PageHeader } from "@/components/PageHeader";
import { useAuth } from "@/hooks/useAuth";
import type { LeadDatabaseStatsResponse } from "@/lib/types";

function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null || bytes <= 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function StatBox({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="rounded-lg border border-border p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      {hint ? <p className="mt-1 text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

export default function DatabaseSettingsPage() {
  const router = useRouter();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  useEffect(() => {
    if (user && !isAdmin) {
      router.replace("/settings");
    }
  }, [user, isAdmin, router]);

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["lead-database-stats"],
    enabled: isAdmin,
    queryFn: async () => {
      const { data: stats } = await api.get<LeadDatabaseStatsResponse>("/settings/database");
      return stats;
    },
    refetchInterval: 30_000,
  });

  if (!user || !isAdmin) {
    return <PageLoader />;
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          href="/settings"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Settings
        </Link>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void refetch()}
          disabled={isFetching}
          className="gap-2"
        >
          {isFetching ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          Refresh
        </Button>
      </div>

      <PageHeader
        eyebrow="Settings"
        title="Lead Database"
        description="Background scraper ne jo leads save ki hain aur aapke database ka summary"
      />

      {isLoading ? (
        <div className="flex items-center justify-center py-16 text-muted-foreground">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
          Loading database stats…
        </div>
      ) : data ? (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <HardDrive className="h-5 w-5" />
                Database file
              </CardTitle>
              <CardDescription>Local SQLite database jahan saari leads store hoti hain</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-3">
              <StatBox label="DB name" value={data.database_name} />
              <StatBox label="Type" value={data.database_type} />
              <StatBox label="File size" value={formatBytes(data.database_size_bytes)} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                Your leads
              </CardTitle>
              <CardDescription>Total leads aapke account ki database mein</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatBox label="Total in DB" value={data.total_leads} hint="Sab leads" />
              <StatBox label="Background" value={data.background_leads} hint="Silent scraper se" />
              <StatBox label="Manual scrape" value={data.manual_leads} hint="Aap ne khud start kiya" />
              <StatBox label="Inbox" value={data.inbox_leads} />
              <StatBox label="Saved" value={data.saved_leads} />
              <StatBox label="With phone" value={data.with_phone} />
              <StatBox label="Without website" value={data.without_website} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Radio className="h-5 w-5" />
                Background scraper
              </CardTitle>
              <CardDescription>Login rehne par silently leads collect karta hai</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={data.background_running ? "success" : data.background_active ? "secondary" : "outline"}>
                  {data.background_running
                    ? "Running"
                    : data.background_active
                      ? "Active (idle)"
                      : "Stopped"}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  Session saved: {data.background_total_saved} · Rounds: {data.background_iteration}
                </span>
              </div>
              {data.background_last_query ? (
                <p className="rounded-lg border border-border bg-muted/30 px-3 py-2 font-mono text-xs text-muted-foreground">
                  Last query: {data.background_last_query}
                </p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Abhi koi background round complete nahi hua. Login rehne par leads yahan badhti jayengi.
                </p>
              )}
              <BackgroundScraperTerminal docked expanded />
            </CardContent>
          </Card>

          <div className="flex flex-wrap gap-3">
            <Link href="/leads">
              <Button variant="outline">Open Inbox</Button>
            </Link>
            <Link href="/scraper">
              <Button>Start scraper</Button>
            </Link>
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">Could not load database stats.</p>
      )}
    </div>
  );
}
