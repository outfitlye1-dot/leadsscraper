"use client";

import { Shield, Users, Search, Mail, Bot, Activity } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { PageLoader } from "@/components/Loader";
import { PageError } from "@/components/PageError";
import { StatCard } from "@/components/ui/StatCard";
import { Badge } from "@/components/ui/Badge";
import { useAdminDashboard } from "@/hooks/useAdmin";

export default function AdminOverviewPage() {
  const { data, isLoading, isError, refetch } = useAdminDashboard();

  if (isLoading) return <PageLoader />;
  if (isError || !data) {
    return <PageError message="Failed to load admin dashboard" onRetry={() => refetch()} />;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Administration"
        title="Admin Panel"
        description="Full platform control — users, leads, outreach, scraper jobs, and system health."
      >
        <Badge className="gap-1.5 px-3 py-1">
          <Shield className="h-3.5 w-3.5" />
          Super Admin
        </Badge>
      </PageHeader>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total users" value={data.total_users} icon={Users} iconTone="blue" />
        <StatCard label="Admins" value={data.admin_users} icon={Shield} iconTone="violet" />
        <StatCard label="Total leads" value={data.total_leads} icon={Search} iconTone="emerald" />
        <StatCard label="Active scraper jobs" value={data.active_scraper_jobs} icon={Activity} iconTone="amber" />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Campaigns" value={data.total_campaigns} icon={Bot} iconTone="indigo" />
        <StatCard label="AI messages" value={data.total_messages} icon={Bot} iconTone="sky" />
        <StatCard label="Outreach emails" value={data.total_outreach_emails} icon={Mail} iconTone="rose" />
        <StatCard
          label="Outreach worker"
          value={data.outreach_worker_enabled ? "Running" : "Off"}
          icon={Mail}
          iconTone={data.outreach_worker_enabled ? "emerald" : "slate"}
        />
      </div>
    </div>
  );
}
