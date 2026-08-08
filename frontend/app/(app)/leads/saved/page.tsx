"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Download, Search } from "lucide-react";
import { toast } from "sonner";
import {
  useSavedLeads,
  useDeleteLead,
  useBulkDeleteLeads,
  useUnsaveLead,
  useExportLeads,
  type LeadFilters,
} from "@/hooks/useLeads";
import { ResizableTable } from "@/components/ui/resizable-table";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/PageHeader";
import { Input } from "@/components/ui/Input";
import { TableSkeleton } from "@/components/Loader";
import { PageError } from "@/components/PageError";
import { formatApiError } from "@/lib/utils";

function useDebouncedValue<T>(value: T, delay = 350): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

export default function SavedLeadsPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const debouncedSearch = useDebouncedValue(search);

  const listFilters: Omit<LeadFilters, "page" | "page_size"> = {
    saved: true,
    q: debouncedSearch || undefined,
  };

  const filters: LeadFilters = { ...listFilters, page, page_size: 10 };

  const { data, isLoading, isError, refetch } = useSavedLeads(filters);
  const deleteLead = useDeleteLead();
  const bulkDeleteLeads = useBulkDeleteLeads();
  const unsaveLead = useUnsaveLead();
  const exportLeads = useExportLeads();

  const isDeleting = deleteLead.isPending || bulkDeleteLeads.isPending;
  const isSaving = unsaveLead.isPending;

  const handleDelete = async (id: number) => {
    if (!confirm("Permanently delete this saved lead?")) return;
    try {
      await deleteLead.mutateAsync({ id, saved: true });
      toast.success("Saved lead deleted");
    } catch {
      toast.error("Failed to delete saved lead");
    }
  };

  const handleUnsave = async (id: number) => {
    try {
      await unsaveLead.mutateAsync(id);
      toast.success("Moved back to Leads");
    } catch {
      toast.error("Failed to move lead back");
    }
  };

  const handleBulkDelete = async (ids: number[]) => {
    if (!confirm(`Permanently delete ${ids.length} saved lead(s)?`)) return;
    try {
      const deleted = await bulkDeleteLeads.mutateAsync({
        ids,
        filters: { saved: true },
      });
      if (deleted === 0) {
        toast.info("No matching leads to delete");
      } else {
        toast.success(`${deleted} saved lead${deleted !== 1 ? "s" : ""} deleted`);
      }
      setPage(1);
    } catch (err: unknown) {
      toast.error(formatApiError(err, "Failed to delete selected leads"));
    }
  };

  const handleExport = async (ids?: number[]) => {
    try {
      await exportLeads.mutateAsync({
        format: "csv",
        ids,
        filters: ids?.length ? undefined : listFilters,
      });
      toast.success("Export downloaded");
    } catch {
      toast.error("Export failed");
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Saved Leads">
        <div className="flex flex-wrap gap-2">
          <Link href="/leads">
            <Button variant="outline" type="button">
              Back to Leads
            </Button>
          </Link>
          <Button
            variant="outline"
            onClick={() => handleExport()}
            isLoading={exportLeads.isPending}
          >
            <Download className="h-4 w-4" />
            Export CSV
          </Button>
        </div>
      </PageHeader>

      <div className="relative max-w-xl">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          className="pl-9"
          placeholder="Search saved leads..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
      </div>

      {isLoading ? (
        <TableSkeleton />
      ) : isError ? (
        <PageError message="Failed to load saved leads" onRetry={() => refetch()} />
      ) : (
        <ResizableTable
          leads={data?.items || []}
          currentPage={page}
          totalPages={data?.pages || 1}
          total={data?.total || 0}
          pageSize={data?.page_size || 10}
          onPageChange={setPage}
          onLeadClick={(lead) => router.push(`/leads/${lead.id}`)}
          onUnsave={handleUnsave}
          onDelete={handleDelete}
          onBulkDelete={handleBulkDelete}
          onExportSelected={(ids) => handleExport(ids)}
          isDeleting={isDeleting}
          isSaving={isSaving}
        />
      )}
    </div>
  );
}
