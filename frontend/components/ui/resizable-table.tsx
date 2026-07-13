"use client";

import { useEffect, useMemo, useState } from "react";
import { Bookmark, BookmarkMinus, ChevronDown, Download, Trash2 } from "lucide-react";
import { LeadContactActions } from "@/components/LeadContactActions";
import { Button } from "@/components/ui/Button";
import { LeadStatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Users } from "lucide-react";
import type { Lead, LeadStatus } from "@/lib/types";

interface ResizableTableProps {
  leads?: Lead[];
  currentPage?: number;
  totalPages?: number;
  total?: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
  onLeadSelect?: (leadId: number) => void;
  onLeadClick?: (lead: Lead) => void;
  onDelete?: (leadId: number) => void;
  onSave?: (leadId: number) => void;
  onUnsave?: (leadId: number) => void;
  onBulkDelete?: (ids: number[]) => void | Promise<void>;
  onBulkSave?: (ids: number[]) => void | Promise<void>;
  onDeleteAll?: () => void | Promise<void>;
  onExportSelected?: (ids: number[]) => void | Promise<void>;
  className?: string;
  isDeleting?: boolean;
  isSaving?: boolean;
}

type SortField = "company_name" | "category" | "location" | "status" | "created_at";
type SortOrder = "asc" | "desc";

function getLocationLines(lead: Lead): string[] {
  const address = lead.address?.trim();
  const city = lead.city?.trim();
  const postal = lead.postal_code?.trim();
  const country = lead.country?.trim();
  const lines: string[] = [];

  if (address) lines.push(address);

  const cityLine = [city, postal].filter(Boolean).join(", ");
  if (cityLine) {
    const alreadyShown = lines.some((line) =>
      line.toLowerCase().includes(cityLine.toLowerCase())
    );
    if (!alreadyShown) lines.push(cityLine);
  }

  if (country) {
    const alreadyShown = lines.some((line) =>
      line.toLowerCase().includes(country.toLowerCase())
    );
    if (!alreadyShown) lines.push(country);
  }

  if (lines.length === 0) return ["—"];
  return lines.slice(0, 3);
}

function formatLocation(lead: Lead) {
  return getLocationLines(lead).join(" · ");
}

const CATEGORY_PREVIEW_COUNT = 3;

function getAllCategoryLines(lead: Lead): string[] {
  const category = lead.category?.trim();
  const industry = lead.industry?.trim();
  const raw = category || industry || "";
  if (!raw) return ["—"];

  const parts = raw
    .split(/[,;|/]/)
    .map((part) => part.trim())
    .filter(Boolean);

  const unique: string[] = [];
  for (const part of parts) {
    if (!unique.some((item) => item.toLowerCase() === part.toLowerCase())) {
      unique.push(part);
    }
  }

  return unique.length === 0 ? ["—"] : unique;
}

function formatCategory(lead: Lead) {
  const category = lead.category?.trim();
  const industry = lead.industry?.trim();
  if (category && industry && category !== industry) {
    return `${category} · ${industry}`;
  }
  return category || industry || "—";
}

export function ResizableTable({
  leads = [],
  currentPage = 1,
  totalPages = 1,
  total = 0,
  pageSize = 10,
  onPageChange,
  onLeadSelect,
  onLeadClick,
  onDelete,
  onSave,
  onUnsave,
  onBulkDelete,
  onBulkSave,
  onDeleteAll,
  onExportSelected,
  className = "",
  isDeleting = false,
  isSaving = false,
}: ResizableTableProps) {
  const [selectedLeads, setSelectedLeads] = useState<number[]>([]);
  const [selectAllAcrossPages, setSelectAllAcrossPages] = useState(false);
  const [sortField, setSortField] = useState<SortField | null>(null);
  const [sortOrder, setSortOrder] = useState<SortOrder>("asc");
  const [showSortMenu, setShowSortMenu] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState<Set<number>>(new Set());

  useEffect(() => {
    setSelectedLeads([]);
    setSelectAllAcrossPages(false);
    setExpandedCategories(new Set());
  }, [leads, currentPage]);

  const handleLeadSelect = (leadId: number) => {
    setSelectedLeads((prev) =>
      prev.includes(leadId) ? prev.filter((id) => id !== leadId) : [...prev, leadId]
    );
    onLeadSelect?.(leadId);
  };

  const sortedLeads = useMemo(() => {
    if (!sortField) return leads;

    return [...leads].sort((a, b) => {
      let aVal: string | number = "";
      let bVal: string | number = "";

      if (sortField === "company_name") {
        aVal = a.company_name.toLowerCase();
        bVal = b.company_name.toLowerCase();
      } else if (sortField === "category") {
        aVal = (a.category || a.industry || "").toLowerCase();
        bVal = (b.category || b.industry || "").toLowerCase();
      } else if (sortField === "location") {
        aVal = formatLocation(a).toLowerCase();
        bVal = formatLocation(b).toLowerCase();
      } else if (sortField === "status") {
        aVal = a.status;
        bVal = b.status;
      } else if (sortField === "created_at") {
        aVal = new Date(a.created_at).getTime();
        bVal = new Date(b.created_at).getTime();
      }

      if (aVal < bVal) return sortOrder === "asc" ? -1 : 1;
      if (aVal > bVal) return sortOrder === "asc" ? 1 : -1;
      return 0;
    });
  }, [leads, sortField, sortOrder]);

  const handleSelectAll = () => {
    if (selectedLeads.length === sortedLeads.length && !selectAllAcrossPages) {
      setSelectedLeads([]);
      setSelectAllAcrossPages(false);
    } else {
      setSelectedLeads(sortedLeads.map((l) => l.id));
      setSelectAllAcrossPages(false);
    }
  };

  const selectedCount = selectAllAcrossPages ? total : selectedLeads.length;

  const handleBulkDeleteClick = async () => {
    if (selectAllAcrossPages && onDeleteAll) {
      await onDeleteAll();
      setSelectedLeads([]);
      setSelectAllAcrossPages(false);
      return;
    }
    if (selectedLeads.length > 0 && onBulkDelete) {
      await onBulkDelete(selectedLeads);
      setSelectedLeads([]);
      setSelectAllAcrossPages(false);
    }
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
    setShowSortMenu(false);
  };

  const rangeStart = total === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const rangeEnd = Math.min(currentPage * pageSize, total);

  return (
    <div className={`w-full ${className}`}>
      {selectedCount > 0 && (onBulkDelete || onDeleteAll || onExportSelected || onBulkSave) && (
        <div className="mb-3 flex flex-col gap-2 rounded-lg border border-border/50 bg-muted/10 px-3 py-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm">
            <span className="font-medium">{selectedCount}</span>{" "}
            <span className="text-muted-foreground">selected</span>
          </div>
          <div className="flex gap-2">
            {onBulkSave && !selectAllAcrossPages && selectedLeads.length > 0 && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={async () => {
                  await onBulkSave(selectedLeads);
                  setSelectedLeads([]);
                  setSelectAllAcrossPages(false);
                }}
                disabled={isSaving}
                className="gap-1.5"
              >
                <Bookmark className="h-4 w-4" />
                Save
              </Button>
            )}
            {onExportSelected && !selectAllAcrossPages && selectedLeads.length > 0 && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onExportSelected(selectedLeads)}
                className="gap-1.5"
              >
                <Download className="h-4 w-4" />
                Export
              </Button>
            )}
            {onBulkDelete && (
              <Button
                type="button"
                variant="destructive"
                size="sm"
                onClick={handleBulkDeleteClick}
                disabled={isDeleting}
                className="gap-1.5"
              >
                <Trash2 className="h-4 w-4" />
                Delete
              </Button>
            )}
          </div>
        </div>
      )}

      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-muted-foreground">
          {total > 0 ? `Showing ${rangeStart}–${rangeEnd} of ${total}` : "No leads found"}
        </p>
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowSortMenu(!showSortMenu)}
            className="flex items-center gap-2 rounded-md border border-border/50 bg-background px-3 py-1.5 text-sm hover:bg-muted/30"
          >
            Sort
            {sortField && (
              <span className="rounded-sm bg-primary px-1.5 py-0.5 text-xs text-primary-foreground">
                {sortOrder === "asc" ? "↑" : "↓"}
              </span>
            )}
            <ChevronDown size={14} className="opacity-50" />
          </button>
          {showSortMenu && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setShowSortMenu(false)} />
              <div className="absolute right-0 z-20 mt-1 w-44 rounded-md border border-border/50 bg-background py-1 shadow-lg">
                {(
                  [
                    ["company_name", "Business"],
                    ["category", "Category"],
                    ["location", "Location"],
                    ["status", "Status"],
                  ] as const
                ).map(([field, label]) => (
                  <button
                    key={field}
                    type="button"
                    onClick={() => handleSort(field)}
                    className={`w-full px-3 py-2 text-left text-sm hover:bg-muted/50 ${
                      sortField === field ? "bg-muted/30" : ""
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      <div className="overflow-x-auto overflow-y-auto rounded-lg border border-border/50 bg-background max-h-[min(70vh,720px)]">
        <table className="w-full table-fixed text-sm">
          <colgroup>
            <col className="w-10" />
            <col className="w-[20%]" />
            <col className="w-[14%]" />
            <col className="w-[14%]" />
            <col className="w-[22%]" />
            <col className="w-[16%]" />
            <col className="w-[10%]" />
            <col className="w-10" />
            <col className="w-10" />
          </colgroup>
          <thead className="sticky top-0 z-10 bg-card/95 backdrop-blur-sm">
            <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground">
              <th className="px-2 py-3">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-border/40"
                  checked={
                    sortedLeads.length > 0 &&
                    (selectAllAcrossPages ||
                      (selectedLeads.length === sortedLeads.length && sortedLeads.length > 0))
                  }
                  onChange={handleSelectAll}
                />
              </th>
              <th className="px-3 py-3">Business</th>
              <th className="px-3 py-3">Category</th>
              <th className="px-3 py-3">Location</th>
              <th className="px-3 py-3">Phone / Email</th>
              <th className="px-3 py-3">Outreach</th>
              <th className="px-3 py-3">Status</th>
              <th className="px-2 py-3" aria-label="Save" />
              <th className="px-2 py-3" aria-label="Delete" />
            </tr>
          </thead>
          <tbody>
            {sortedLeads.length === 0 ? (
              <tr>
                <td colSpan={9} className="p-4">
                  <EmptyState
                    icon={Users}
                    title="No leads found"
                    description="Try adjusting your search or filters to see more results."
                  />
                </td>
              </tr>
            ) : (
              sortedLeads.map((lead, rowIndex) => {
                const selected = selectAllAcrossPages || selectedLeads.includes(lead.id);
                const allCategories = getAllCategoryLines(lead);
                const categoryExpanded = expandedCategories.has(lead.id);
                const hiddenCategoryCount = Math.max(
                  0,
                  allCategories.length - CATEGORY_PREVIEW_COUNT
                );
                const visibleCategories =
                  categoryExpanded || hiddenCategoryCount === 0
                    ? allCategories
                    : allCategories.slice(0, CATEGORY_PREVIEW_COUNT);

                return (
                  <tr
                    key={lead.id}
                    className={`border-b border-border/60 transition-colors ${
                      selected
                        ? "bg-muted/25"
                        : rowIndex % 2 === 1
                          ? "bg-muted/[0.03] hover:bg-muted/10"
                          : "hover:bg-muted/10"
                    }`}
                  >
                    <td className="px-2 py-3 align-middle">
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-border/40"
                        checked={selected}
                        onChange={() => {
                          if (selectAllAcrossPages) {
                            setSelectAllAcrossPages(false);
                            setSelectedLeads(
                              sortedLeads.map((l) => l.id).filter((id) => id !== lead.id)
                            );
                          } else {
                            handleLeadSelect(lead.id);
                          }
                        }}
                      />
                    </td>
                    <td className="px-3 py-3 align-middle">
                      <button
                        type="button"
                        onClick={() => onLeadClick?.(lead)}
                        className={`block max-w-full truncate text-left font-medium ${
                          onLeadClick ? "text-primary hover:underline" : ""
                        }`}
                        title={lead.company_name}
                      >
                        {lead.company_name}
                      </button>
                      {lead.contact_name && (
                        <p className="truncate text-xs text-muted-foreground" title={lead.contact_name}>
                          {lead.contact_name}
                        </p>
                      )}
                    </td>
                    <td className="px-3 py-3 align-top">
                      <div
                        className="space-y-0.5 text-[11px] leading-snug text-foreground/85 break-words"
                        title={formatCategory(lead)}
                      >
                        {visibleCategories.map((line, i) => (
                          <p key={`${lead.id}-cat-${i}`}>{line}</p>
                        ))}
                        {!categoryExpanded && hiddenCategoryCount > 0 && (
                          <button
                            type="button"
                            className="text-left text-[11px] font-medium text-primary hover:underline"
                            onClick={(e) => {
                              e.stopPropagation();
                              setExpandedCategories((prev) => new Set(prev).add(lead.id));
                            }}
                          >
                            +{hiddenCategoryCount} more
                          </button>
                        )}
                        {categoryExpanded && hiddenCategoryCount > 0 && (
                          <button
                            type="button"
                            className="text-left text-[11px] text-muted-foreground hover:text-foreground hover:underline"
                            onClick={(e) => {
                              e.stopPropagation();
                              setExpandedCategories((prev) => {
                                const next = new Set(prev);
                                next.delete(lead.id);
                                return next;
                              });
                            }}
                          >
                            Show less
                          </button>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-3 align-top">
                      <div
                        className="space-y-0.5 text-[11px] leading-snug text-foreground/85 break-words"
                        title={formatLocation(lead)}
                      >
                        {getLocationLines(lead).map((line, i) => (
                          <p key={`${lead.id}-loc-${i}`}>{line}</p>
                        ))}
                      </div>
                    </td>
                    <td className="px-3 py-3 align-top">
                      <div className="space-y-1 text-[11px] leading-snug text-foreground/85">
                        <p className="break-all" title={lead.phone || undefined}>
                          {lead.phone || "—"}
                        </p>
                        {lead.email ? (
                          <a
                            href={`mailto:${lead.email}`}
                            className="block break-all text-blue-600 hover:underline dark:text-blue-400"
                            title={lead.email}
                            onClick={(e) => e.stopPropagation()}
                          >
                            {lead.email}
                          </a>
                        ) : (
                          <p className="text-muted-foreground">—</p>
                        )}
                      </div>
                    </td>
                    <td className="px-2 py-3 align-middle">
                      <LeadContactActions lead={lead} compact />
                    </td>
                    <td className="px-3 py-3 align-middle">
                      <LeadStatusBadge status={lead.status} />
                    </td>
                    <td className="px-2 py-3 align-middle">
                      {onSave && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onSave(lead.id)}
                          disabled={isSaving}
                          className="h-8 w-8 p-0"
                          title="Save lead"
                        >
                          <Bookmark className="h-4 w-4 text-primary" />
                        </Button>
                      )}
                      {onUnsave && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onUnsave(lead.id)}
                          disabled={isSaving}
                          className="h-8 w-8 p-0"
                          title="Move back to leads"
                        >
                          <BookmarkMinus className="h-4 w-4 text-muted-foreground" />
                        </Button>
                      )}
                    </td>
                    <td className="px-2 py-3 align-middle">
                      {onDelete && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onDelete(lead.id)}
                          disabled={isDeleting}
                          className="h-8 w-8 p-0"
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && onPageChange && (
        <div className="mt-4 flex items-center justify-between px-1">
          <p className="text-xs text-muted-foreground">
            Page {currentPage} of {totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onPageChange(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
            >
              Previous
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
