"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Download, Filter, Plus, Search, Upload, Bookmark, Trash2 } from "lucide-react";
import { toast } from "sonner";
import {
  useLeads,
  useDeleteLead,
  useBulkDeleteLeads,
  useSaveLead,
  useBulkSaveLeads,
  useExportLeads,
  useCreateLead,
  useUpdateLead,
  useImportLeads,
  useCleanupLeadsWithoutContact,
  type LeadFilters,
} from "@/hooks/useLeads";
import { ResizableTable } from "@/components/ui/resizable-table";
import { LeadDetailDrawer } from "@/components/LeadDetailDrawer";
import { LeadFormModal } from "@/components/LeadFormModal";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/PageHeader";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { TableSkeleton } from "@/components/Loader";
import { PageError } from "@/components/PageError";
import type { Lead, LeadStatus } from "@/lib/types";
import axios from "axios";

function useDebouncedValue<T>(value: T, delay = 350): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

export default function LeadsPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<LeadStatus | "">("");
  const [city, setCity] = useState("");
  const [country, setCountry] = useState("");
  const [industry, setIndustry] = useState("");
  const [source, setSource] = useState("");
  const [qualityTier, setQualityTier] = useState<"" | "high" | "medium" | "low">("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [whatsappOnly, setWhatsappOnly] = useState(false);
  const [hasEmail, setHasEmail] = useState(false);
  const [hasWebsite, setHasWebsite] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [page, setPage] = useState(1);

  const [detailLead, setDetailLead] = useState<Lead | null>(null);
  const [formLead, setFormLead] = useState<Lead | null>(null);
  const [formOpen, setFormOpen] = useState(false);

  const importRef = useRef<HTMLInputElement>(null);
  const debouncedSearch = useDebouncedValue(search);

  const listFilters: Omit<LeadFilters, "page" | "page_size"> = {
    saved: false,
    q: debouncedSearch || undefined,
    status: status || undefined,
    city: city || undefined,
    country: country || undefined,
    industry: industry || undefined,
    source: source || undefined,
    quality_tier: qualityTier || undefined,
    whatsapp_ready: whatsappOnly || undefined,
    has_email: hasEmail || undefined,
    has_website: hasWebsite || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  };

  const filters: LeadFilters = { ...listFilters, page, page_size: 10 };

  const { data, isLoading, isError, refetch } = useLeads(filters);

  const deleteLead = useDeleteLead();
  const bulkDeleteLeads = useBulkDeleteLeads();
  const saveLead = useSaveLead();
  const bulkSaveLeads = useBulkSaveLeads();
  const exportLeads = useExportLeads();
  const createLead = useCreateLead();
  const updateLead = useUpdateLead();
  const importLeads = useImportLeads();
  const cleanupNoContact = useCleanupLeadsWithoutContact();

  const isDeleting = deleteLead.isPending || bulkDeleteLeads.isPending;
  const isSaving = saveLead.isPending || bulkSaveLeads.isPending;

  const resetPage = () => setPage(1);

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this lead? Saved leads are protected.")) return;
    try {
      await deleteLead.mutateAsync({ id });
      if (detailLead?.id === id) setDetailLead(null);
      toast.success("Lead deleted");
    } catch {
      toast.error("Failed to delete lead");
    }
  };

  const handleSave = async (id: number) => {
    try {
      await saveLead.mutateAsync(id);
      if (detailLead?.id === id) setDetailLead(null);
      toast.success("Lead saved — moved to Saved");
    } catch {
      toast.error("Failed to save lead");
    }
  };

  const handleBulkSave = async (ids: number[]) => {
    try {
      const saved = await bulkSaveLeads.mutateAsync(ids);
      toast.success(`${saved} lead${saved !== 1 ? "s" : ""} saved`);
      setPage(1);
    } catch {
      toast.error("Failed to save selected leads");
    }
  };

  const handleBulkDelete = async (ids: number[]) => {
    if (!confirm(`Delete ${ids.length} selected lead${ids.length !== 1 ? "s" : ""}?`)) return;
    try {
      const deleted = await bulkDeleteLeads.mutateAsync({ ids, filters: listFilters });
      toast.success(`${deleted} lead${deleted !== 1 ? "s" : ""} deleted`);
      setPage(1);
    } catch {
      toast.error("Failed to delete selected leads");
    }
  };

  const handleCleanupNoContact = async () => {
    if (
      !confirm(
        "Leads with a phone number will stay in Leads. Leads with only email (no number) or no contact will be deleted."
      )
    ) {
      return;
    }
    try {
      const result = await cleanupNoContact.mutateAsync();
      setPage(1);
      await refetch();
      if (result.deleted === 0 && result.kept === 0) {
        toast.info("No inbox leads to process");
      } else if (result.deleted === 0) {
        toast.info(
          `No leads deleted — all ${result.kept} inbox lead${result.kept !== 1 ? "s" : ""} already have a phone number`
        );
      } else {
        const parts: string[] = [];
        if (result.deleted > 0) {
          parts.push(`${result.deleted} deleted`);
        }
        if (result.kept > 0) {
          parts.push(`${result.kept} kept in Leads`);
        }
        toast.success(parts.join(", "));
      }
    } catch (error) {
      let message = "Failed to clean up leads";
      if (axios.isAxiosError(error)) {
        const detail = error.response?.data?.detail;
        if (typeof detail === "string") message = detail;
        else if (error.response?.status === 404) {
          message = "Cleanup API not found — restart the backend server";
        }
      }
      toast.error(message);
    }
  };

  const handleDeleteAll = async () => {
    const total = data?.total ?? 0;
    if (
      !confirm(
        `Delete all ${total} unsaved leads matching your filters? Saved leads will stay safe.`
      )
    ) {
      return;
    }
    try {
      const deleted = await bulkDeleteLeads.mutateAsync({
        select_all: true,
        filters: listFilters,
      });
      toast.success(`${deleted} lead${deleted !== 1 ? "s" : ""} deleted`);
      setPage(1);
    } catch {
      toast.error("Failed to delete leads");
    }
  };

  const handleExport = async (format: "csv" | "xlsx" = "csv", ids?: number[]) => {
    try {
      await exportLeads.mutateAsync({
        format,
        ids,
        filters: ids?.length ? undefined : listFilters,
      });
      toast.success("Export downloaded");
    } catch {
      toast.error("Export failed");
    }
  };

  const handleImport = async (file: File) => {
    try {
      const result = await importLeads.mutateAsync(file);
      toast.success(result.message || `Imported ${result.imported} lead(s)`);
      setPage(1);
    } catch {
      toast.error("Import failed — check CSV format");
    }
  };

  const handleSaveDetail = async (id: number, patch: { status?: LeadStatus; notes?: string }) => {
    try {
      const updated = await updateLead.mutateAsync({ id, data: patch });
      setDetailLead(updated);
      toast.success("Lead updated");
    } catch {
      toast.error("Failed to update lead");
    }
  };

  const handleFormSubmit = async (payload: Parameters<typeof createLead.mutateAsync>[0]) => {
    try {
      if (formLead) {
        await updateLead.mutateAsync({ id: formLead.id, data: payload });
        toast.success("Lead updated");
      } else {
        await createLead.mutateAsync(payload);
        toast.success("Lead created");
      }
      setFormOpen(false);
      setFormLead(null);
    } catch {
      toast.error(formLead ? "Failed to update lead" : "Failed to create lead");
    }
  };

  const activeFilterCount = [
    city,
    country,
    industry,
    source,
    qualityTier,
    dateFrom,
    dateTo,
    whatsappOnly,
    hasEmail,
    hasWebsite,
  ].filter(Boolean).length;

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Pipeline" title="Leads">
        <div className="flex flex-wrap gap-2">
          <Link href="/leads/saved">
            <Button variant="outline" type="button">
              <Bookmark className="h-4 w-4" />
              Saved
            </Button>
          </Link>
          <input
            ref={importRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleImport(file);
              e.target.value = "";
            }}
          />
          <Button
            variant="outline"
            onClick={() => importRef.current?.click()}
            isLoading={importLeads.isPending}
          >
            <Upload className="h-4 w-4" />
            Import CSV
          </Button>
          <Button
            variant="outline"
            onClick={handleCleanupNoContact}
            isLoading={cleanupNoContact.isPending}
          >
            <Trash2 className="h-4 w-4" />
            Remove no contact
          </Button>
          <Button
            variant="outline"
            onClick={() => handleExport("csv")}
            isLoading={exportLeads.isPending}
          >
            <Download className="h-4 w-4" />
            Export CSV
          </Button>
          <Button
            variant="outline"
            onClick={() => handleExport("xlsx")}
            isLoading={exportLeads.isPending}
          >
            <Download className="h-4 w-4" />
            Export Excel
          </Button>
          <Button
            onClick={() => {
              setFormLead(null);
              setFormOpen(true);
            }}
          >
            <Plus className="h-4 w-4" />
            Add lead
          </Button>
        </div>
      </PageHeader>

      <div className="space-y-3">
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-9"
              placeholder="Search company, email, phone, website..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                resetPage();
              }}
            />
          </div>
          <Select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value as LeadStatus | "");
              resetPage();
            }}
            className="sm:w-40"
          >
            <option value="">All statuses</option>
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="interested">Interested</option>
            <option value="follow_up">Follow Up</option>
            <option value="closed">Closed</option>
            <option value="lost">Lost</option>
          </Select>
          <Button
            variant="outline"
            onClick={() => setShowFilters((v) => !v)}
            className="sm:w-auto"
          >
            <Filter className="h-4 w-4" />
            Filters
            {activeFilterCount > 0 && (
              <span className="ml-1 rounded-full bg-primary px-1.5 text-xs text-primary-foreground">
                {activeFilterCount}
              </span>
            )}
          </Button>
        </div>

        {showFilters && (
          <div className="grid gap-3 rounded-lg border border-border bg-muted/20 p-4 sm:grid-cols-2 lg:grid-cols-4">
            <Input
              placeholder="City"
              value={city}
              onChange={(e) => {
                setCity(e.target.value);
                resetPage();
              }}
            />
            <Input
              placeholder="Country"
              value={country}
              onChange={(e) => {
                setCountry(e.target.value);
                resetPage();
              }}
            />
            <Input
              placeholder="Industry"
              value={industry}
              onChange={(e) => {
                setIndustry(e.target.value);
                resetPage();
              }}
            />
            <Input
              placeholder="Source"
              value={source}
              onChange={(e) => {
                setSource(e.target.value);
                resetPage();
              }}
            />
            <Select
              value={qualityTier}
              onChange={(e) => {
                setQualityTier(e.target.value as typeof qualityTier);
                resetPage();
              }}
            >
              <option value="">All quality</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </Select>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">From date</label>
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value);
                  resetPage();
                }}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">To date</label>
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value);
                  resetPage();
                }}
              />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={whatsappOnly}
                onChange={(e) => {
                  setWhatsappOnly(e.target.checked);
                  resetPage();
                }}
              />
              WhatsApp ready
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={hasEmail}
                onChange={(e) => {
                  setHasEmail(e.target.checked);
                  resetPage();
                }}
              />
              Has email
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={hasWebsite}
                onChange={(e) => {
                  setHasWebsite(e.target.checked);
                  resetPage();
                }}
              />
              Has website
            </label>
          </div>
        )}
      </div>

      {isLoading ? (
        <TableSkeleton />
      ) : isError ? (
        <PageError message="Failed to load leads" onRetry={() => refetch()} />
      ) : (
        <ResizableTable
          leads={data?.items || []}
          currentPage={page}
          totalPages={data?.pages || 1}
          total={data?.total || 0}
          pageSize={data?.page_size || 10}
          onPageChange={setPage}
          onLeadClick={(lead) => setDetailLead(lead)}
          onSave={handleSave}
          onBulkSave={handleBulkSave}
          onDelete={handleDelete}
          onBulkDelete={handleBulkDelete}
          onDeleteAll={handleDeleteAll}
          onExportSelected={(ids) => handleExport("csv", ids)}
          isDeleting={isDeleting}
          isSaving={isSaving}
        />
      )}

      <LeadDetailDrawer
        lead={detailLead}
        open={!!detailLead}
        onClose={() => setDetailLead(null)}
        onSave={handleSaveDetail}
        onEditFull={(lead) => {
          setDetailLead(null);
          setFormLead(lead);
          setFormOpen(true);
        }}
        isSaving={updateLead.isPending}
      />

      <LeadFormModal
        open={formOpen}
        lead={formLead}
        onClose={() => {
          setFormOpen(false);
          setFormLead(null);
        }}
        onSubmit={handleFormSubmit}
        isSubmitting={createLead.isPending || updateLead.isPending}
      />
    </div>
  );
}
