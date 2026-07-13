"use client";

import { PageHeader } from "@/components/PageHeader";
import { PageLoader } from "@/components/Loader";
import { PageError } from "@/components/PageError";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useAdminSystem } from "@/hooks/useAdmin";

function Flag({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-border/60 px-4 py-3">
      <span className="text-sm">{label}</span>
      <Badge variant={ok ? "default" : "secondary"}>{ok ? "On" : "Off"}</Badge>
    </div>
  );
}

export default function AdminSystemPage() {
  const { data, isLoading, isError, refetch } = useAdminSystem();

  if (isLoading) return <PageLoader />;
  if (isError || !data) {
    return <PageError message="Failed to load system info" onRetry={() => refetch()} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="System"
        description="Platform configuration, integrations, and runtime flags."
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Application</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Name</span>
              <span>{data.app_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Version</span>
              <span>{data.app_version}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Database</span>
              <span className="font-mono text-xs">{data.database_url}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Scraper workers</span>
              <span>{data.scraper_workers}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Integrations & workers</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Flag ok={data.outreach_worker_enabled} label="Outreach worker" />
            <Flag ok={data.smtp_configured} label="SMTP configured" />
            <Flag ok={data.google_oauth_configured} label="Google OAuth" />
            <Flag ok={data.microsoft_oauth_configured} label="Microsoft OAuth" />
            <Flag ok={data.scraper_fast_mode} label="Scraper fast mode" />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
