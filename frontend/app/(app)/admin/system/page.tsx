"use client";

import Link from "next/link";
import {
  Activity,
  Bot,
  Cpu,
  Database,
  ExternalLink,
  Mail,
  RefreshCw,
  Server,
  Shield,
  Users,
  Zap,
} from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { PageLoader } from "@/components/Loader";
import { PageError } from "@/components/PageError";
import { StatCard } from "@/components/ui/StatCard";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useAdminSystem } from "@/hooks/useAdmin";
import { formatDate } from "@/lib/utils";

function StatusFlag({ ok, label, hint }: { ok: boolean; label: string; hint?: string }) {
  return (
    <div className="flex items-start justify-between gap-4 rounded-lg border border-border/60 px-4 py-3">
      <div>
        <p className="text-sm font-medium">{label}</p>
        {hint ? <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p> : null}
      </div>
      <Badge variant={ok ? "success" : "secondary"}>{ok ? "On" : "Off"}</Badge>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="max-w-[60%] text-right font-medium">{value}</span>
    </div>
  );
}

export default function AdminSystemPage() {
  const { data, isLoading, isError, refetch, isFetching } = useAdminSystem();

  if (isLoading) return <PageLoader />;
  if (isError || !data) {
    return <PageError message="Failed to load system info" onRetry={() => refetch()} />;
  }

  const healthOk = data.status === "healthy" && !data.default_secret_key;

  return (
    <div className="space-y-8">
      <PageHeader
        title="System"
        description="Live platform health, runtime configuration, integrations, and database status."
      >
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={healthOk ? "success" : "warning"} className="gap-1.5 px-3 py-1">
            <Shield className="h-3.5 w-3.5" />
            {healthOk ? "Healthy" : "Needs attention"}
          </Badge>
          <Button size="sm" variant="outline" className="gap-1.5" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </PageHeader>

      {data.default_secret_key ? (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="py-4 text-sm text-amber-800 dark:text-amber-300">
            Default <code className="rounded bg-background/60 px-1">SECRET_KEY</code> is still in use. Change it in
            `.env` before production.
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Users" value={data.total_users} icon={Users} iconTone="blue" />
        <StatCard label="Leads" value={data.total_leads} icon={Database} iconTone="emerald" />
        <StatCard label="Active scraper jobs" value={data.active_scraper_jobs} icon={Activity} iconTone="amber" />
        <StatCard label="API keys" value={data.total_api_keys} icon={Zap} iconTone="violet" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Server className="h-4 w-4" />
              Application
            </CardTitle>
            <CardDescription>Core app metadata and runtime paths.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <InfoRow label="Name" value={data.app_name} />
            <InfoRow label="Version" value={data.app_version} />
            <InfoRow label="Status" value={data.status} />
            <InfoRow label="Frontend URL" value={data.frontend_url} />
            <InfoRow label="Upload dir" value={data.upload_dir} />
            <InfoRow label="Export dir" value={data.export_dir} />
            <InfoRow label="Last checked" value={formatDate(data.checked_at)} />
            <div className="flex flex-wrap gap-2 pt-2">
              <Link href="http://127.0.0.1:8001/docs" target="_blank">
                <Button size="sm" variant="outline" className="gap-1.5">
                  API docs
                  <ExternalLink className="h-3.5 w-3.5" />
                </Button>
              </Link>
              <Link href="http://127.0.0.1:8001/health" target="_blank">
                <Button size="sm" variant="outline" className="gap-1.5">
                  Health endpoint
                  <ExternalLink className="h-3.5 w-3.5" />
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Database className="h-4 w-4" />
              Database
            </CardTitle>
            <CardDescription>Storage engine and platform data totals.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <InfoRow label="Type" value={data.database_type} />
            <InfoRow label="Connection" value={<span className="font-mono text-xs">{data.database_url}</span>} />
            <InfoRow
              label="Size"
              value={data.database_size_mb != null ? `${data.database_size_mb} MB` : "N/A"}
            />
            <InfoRow label="AI messages" value={data.total_messages} />
            <InfoRow label="Outreach agents running" value={data.outreach_agents_running} />
            <InfoRow label="Outreach pending jobs" value={data.outreach_pending_jobs} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Cpu className="h-4 w-4" />
              Scraper
            </CardTitle>
            <CardDescription>Scraping engine configuration.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <InfoRow label="Workers" value={data.scraper_workers} />
            <InfoRow label="Timeout" value={`${data.scraper_timeout}s`} />
            <InfoRow label="Groq model" value={data.groq_model} />
            <StatusFlag ok={data.scraper_fast_mode} label="Fast mode" />
            <StatusFlag ok={data.scraper_playwright_enabled} label="Playwright enabled" />
            <Link href="/admin/scraper">
              <Button size="sm" variant="outline" className="mt-2 w-full">
                View scraper jobs
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Mail className="h-4 w-4" />
              Email & outreach
            </CardTitle>
            <CardDescription>Workers, OAuth, and SMTP integration status.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <StatusFlag
              ok={data.outreach_worker_enabled}
              label="Outreach worker enabled"
              hint="Controlled by OUTREACH_WORKER_ENABLED in .env"
            />
            <StatusFlag
              ok={data.outreach_worker_running}
              label="Outreach worker running"
              hint={`Poll every ${data.outreach_worker_poll_seconds}s`}
            />
            <StatusFlag ok={data.smtp_configured} label="SMTP configured" />
            <StatusFlag ok={data.google_oauth_configured} label="Google OAuth" />
            <StatusFlag ok={data.microsoft_oauth_configured} label="Microsoft OAuth" />
            <StatusFlag ok={!data.otp_dev_mode} label="OTP production mode" hint="Off means dev OTP logging" />
            <InfoRow label="Inbox sync interval" value={`${data.outreach_sync_interval_seconds}s`} />
            <Link href="/admin/outreach">
              <Button size="sm" variant="outline" className="mt-2 w-full">
                View outreach summary
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Bot className="h-4 w-4" />
            Quick admin actions
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Link href="/admin/users">
            <Button size="sm" variant="outline">Manage users</Button>
          </Link>
          <Link href="/admin/leads">
            <Button size="sm" variant="outline">All leads</Button>
          </Link>
          <Link href="/admin/outreach">
            <Button size="sm" variant="outline">Outreach settings</Button>
          </Link>
          <Link href="/admin/apis">
            <Button size="sm" variant="outline">API keys</Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
