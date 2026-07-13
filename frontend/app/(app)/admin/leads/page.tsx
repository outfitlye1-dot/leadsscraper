"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Trash2 } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { PageLoader } from "@/components/Loader";
import { PageError } from "@/components/PageError";
import { Table } from "@/components/Table";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { useAdminLeads, useDeleteAdminLead } from "@/hooks/useAdmin";
import { formatDate } from "@/lib/utils";

export default function AdminLeadsPage() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const { data, isLoading, isError, refetch } = useAdminLeads({
    search: search || undefined,
    page,
    page_size: 25,
  });
  const deleteLead = useDeleteAdminLead();

  const handleDelete = async (leadId: number) => {
    if (!confirm("Delete this lead?")) return;
    try {
      await deleteLead.mutateAsync(leadId);
      toast.success("Lead deleted");
    } catch {
      toast.error("Failed to delete lead");
    }
  };

  if (isLoading) return <PageLoader />;
  if (isError || !data) {
    return <PageError message="Failed to load leads" onRetry={() => refetch()} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="All leads"
        description="Cross-user lead database — search, review, and remove records."
      />

      <Input
        placeholder="Search company, email, city, owner..."
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setPage(1);
        }}
        className="max-w-md"
      />

      <Table
        data={data.items}
        keyExtractor={(item) => item.id}
        emptyMessage="No leads found"
        columns={[
          { key: "company_name", header: "Company" },
          { key: "email", header: "Email" },
          { key: "phone", header: "Phone" },
          { key: "city", header: "City" },
          {
            key: "status",
            header: "Status",
            render: (lead) => <Badge variant="secondary">{lead.status}</Badge>,
          },
          { key: "user_email", header: "Owner" },
          {
            key: "is_saved",
            header: "Saved",
            render: (lead) => (lead.is_saved ? "Yes" : "No"),
          },
          {
            key: "created_at",
            header: "Created",
            render: (lead) => formatDate(lead.created_at),
          },
          {
            key: "actions",
            header: "",
            render: (lead) => (
              <Button
                size="sm"
                variant="outline"
                className="text-destructive"
                onClick={() => handleDelete(lead.id)}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            ),
          },
        ]}
      />

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          Page {data.page} · {data.total} leads
        </span>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={page * data.page_size >= data.total}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
