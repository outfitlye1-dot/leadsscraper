"use client";

import { toast } from "sonner";
import { XCircle } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { PageLoader } from "@/components/Loader";
import { PageError } from "@/components/PageError";
import { Table } from "@/components/Table";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { useAdminScraperJobs, useCancelAdminScraperJob } from "@/hooks/useAdmin";
import { formatDate } from "@/lib/utils";

export default function AdminScraperPage() {
  const { data, isLoading, isError, refetch } = useAdminScraperJobs();
  const cancelJob = useCancelAdminScraperJob();

  const handleCancel = async (jobId: string) => {
    try {
      await cancelJob.mutateAsync(jobId);
      toast.success("Job cancelled");
    } catch {
      toast.error("Failed to cancel job");
    }
  };

  if (isLoading) return <PageLoader />;
  if (isError || !data) {
    return <PageError message="Failed to load scraper jobs" onRetry={() => refetch()} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Scraper jobs"
        description="Live and recent scraper jobs across all users."
      />

      <Table
        data={data.items}
        keyExtractor={(item) => item.job_id}
        emptyMessage="No scraper jobs in memory"
        columns={[
          { key: "job_id", header: "Job ID", className: "font-mono text-xs" },
          { key: "user_email", header: "User" },
          {
            key: "status",
            header: "Status",
            render: (job) => <Badge variant="secondary">{job.status}</Badge>,
          },
          { key: "mode", header: "Mode" },
          { key: "progress", header: "Progress", render: (job) => `${job.progress}%` },
          { key: "stage", header: "Stage" },
          { key: "message", header: "Message" },
          {
            key: "updated_at",
            header: "Updated",
            render: (job) => formatDate(job.updated_at),
          },
          {
            key: "actions",
            header: "",
            render: (job) =>
              ["pending", "running", "paused"].includes(job.status) ? (
                <Button size="sm" variant="outline" onClick={() => handleCancel(job.job_id)}>
                  <XCircle className="h-3.5 w-3.5" />
                </Button>
              ) : null,
          },
        ]}
      />
    </div>
  );
}
