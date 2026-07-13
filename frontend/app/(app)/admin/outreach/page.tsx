"use client";

import { PageHeader } from "@/components/PageHeader";
import { PageLoader } from "@/components/Loader";
import { PageError } from "@/components/PageError";
import { StatCard } from "@/components/ui/StatCard";
import { Mail, RefreshCw, Send, Users } from "lucide-react";
import { useAdminOutreachSummary } from "@/hooks/useAdmin";

export default function AdminOutreachPage() {
  const { data, isLoading, isError, refetch } = useAdminOutreachSummary();

  if (isLoading) return <PageLoader />;
  if (isError || !data) {
    return <PageError message="Failed to load outreach summary" onRetry={() => refetch()} />;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Email outreach"
        description="Platform-wide outreach accounts, sends, replies, and agent activity."
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Email accounts" value={data.total_accounts} icon={Users} iconTone="blue" />
        <StatCard label="Connected" value={data.connected_accounts} icon={Mail} iconTone="emerald" />
        <StatCard label="Agents running" value={data.agents_running} icon={RefreshCw} iconTone="violet" />
        <StatCard label="Pending jobs" value={data.pending_jobs} icon={RefreshCw} iconTone="amber" />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <StatCard label="Emails sent" value={data.emails_sent} icon={Send} iconTone="sky" />
        <StatCard label="Queued" value={data.emails_queued} icon={Mail} iconTone="indigo" />
        <StatCard label="Replies received" value={data.replies_received} icon={Mail} iconTone="rose" />
      </div>
    </div>
  );
}
