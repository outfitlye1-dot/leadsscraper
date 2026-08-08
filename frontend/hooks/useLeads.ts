import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Lead, LeadListResponse, LeadStatus } from "@/lib/types";

export interface LeadFilters {
  q?: string;
  city?: string;
  country?: string;
  industry?: string;
  source?: string;
  quality_tier?: "high" | "medium" | "low";
  status?: LeadStatus;
  whatsapp_ready?: boolean;
  has_email?: boolean;
  has_website?: boolean;
  saved?: boolean;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

export interface BulkDeletePayload {
  ids?: number[];
  select_all?: boolean;
  filters?: Omit<LeadFilters, "page" | "page_size">;
  saved?: boolean;
}

export interface LeadCreatePayload {
  company_name: string;
  contact_name?: string;
  phone?: string;
  email?: string;
  website?: string;
  linkedin_url?: string;
  facebook_url?: string;
  instagram_url?: string;
  address?: string;
  postal_code?: string;
  category?: string;
  city?: string;
  country?: string;
  industry?: string;
  notes?: string;
  source?: string;
  status?: LeadStatus;
}

export type LeadUpdatePayload = Partial<LeadCreatePayload>;

export function useLeads(filters: LeadFilters = {}) {
  return useQuery({
    queryKey: ["leads", filters],
    queryFn: async () => {
      const { data } = await api.get<LeadListResponse>("/leads", {
        params: { saved: false, ...filters },
      });
      return data;
    },
    refetchInterval: 30000,
  });
}

export function useLead(leadId: number | null) {
  return useQuery({
    queryKey: ["lead", leadId],
    enabled: leadId != null,
    queryFn: async () => {
      const { data } = await api.get<Lead>(`/leads/${leadId}`);
      return data;
    },
  });
}

export function useCreateLead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: LeadCreatePayload) => {
      const { data } = await api.post<Lead>("/leads", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
  });
}

export function useUpdateLead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: LeadUpdatePayload }) => {
      const { data: lead } = await api.put<Lead>(`/leads/${id}`, data);
      return lead;
    },
    onSuccess: (lead, vars) => {
      queryClient.setQueryData(["lead", vars.id], lead);
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["saved-leads"] });
      queryClient.invalidateQueries({ queryKey: ["lead", vars.id] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
  });
}

export function useDeleteLead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, saved = false }: { id: number; saved?: boolean }) => {
      await api.delete(`/leads/${id}`, { params: saved ? { saved: true } : {} });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["saved-leads"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
  });
}

export function useBulkDeleteLeads() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: BulkDeletePayload) => {
      const { data } = await api.post<{ deleted: number }>(
        "/leads/bulk-delete",
        {
          ids: payload.ids ?? [],
          select_all: payload.select_all ?? false,
        },
        { params: payload.filters }
      );
      return data.deleted;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["saved-leads"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
  });
}

export function useSaveLead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await api.post<Lead>(`/leads/${id}/save`);
      return data;
    },
    onSuccess: (lead) => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["saved-leads"] });
      queryClient.invalidateQueries({ queryKey: ["lead", lead.id] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
  });
}

export function useUnsaveLead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await api.post<Lead>(`/leads/${id}/unsave`);
      return data;
    },
    onSuccess: (lead) => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["saved-leads"] });
      queryClient.invalidateQueries({ queryKey: ["lead", lead.id] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
  });
}

export function useBulkSaveLeads() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (ids: number[]) => {
      const { data } = await api.post<{ saved: number }>("/leads/bulk-save", { ids });
      return data.saved;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["saved-leads"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
  });
}

export function useCleanupLeadsWithoutContact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<{ saved?: number; kept: number; deleted: number }>(
        "/leads/cleanup-no-contact",
        {}
      );
      return data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["leads"] });
      await queryClient.invalidateQueries({ queryKey: ["saved-leads"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
  });
}

export function useSaveLeadsWithContact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<{ saved: number }>("/leads/save-with-contact");
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["saved-leads"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
  });
}

export function useSavedLeads(filters: LeadFilters = {}) {
  return useQuery({
    queryKey: ["saved-leads", filters],
    queryFn: async () => {
      const { data } = await api.get<LeadListResponse>("/leads", {
        params: { ...filters, saved: true },
      });
      return data;
    },
    refetchInterval: 30000,
  });
}

function downloadBlob(data: Blob, filename: string) {
  const url = window.URL.createObjectURL(data);
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export function useExportLeads() {
  return useMutation({
    mutationFn: async ({
      ids,
      format = "csv",
      filters,
    }: {
      ids?: number[];
      format?: "csv" | "xlsx";
      filters?: Omit<LeadFilters, "page" | "page_size">;
    }) => {
      const params: Record<string, string> = { format };
      if (ids?.length) params.ids = ids.join(",");
      const { data } = await api.get("/leads/export", {
        params: { ...params, ...filters },
        responseType: "blob",
      });
      const ext = format === "xlsx" ? "xlsx" : "csv";
      downloadBlob(new Blob([data]), `leads_export_${Date.now()}.${ext}`);
    },
  });
}

export function useImportLeads() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post<{ imported: number; skipped_duplicates: number; message: string }>(
        "/leads/import",
        form,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
  });
}

export function useAllLeads() {
  return useQuery({
    queryKey: ["leads-all"],
    queryFn: async () => {
      const { data } = await api.get<LeadListResponse>("/leads", {
        params: { page_size: 100 },
      });
      return data.items;
    },
  });
}

export type { Lead };
