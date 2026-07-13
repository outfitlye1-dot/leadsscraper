import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type {
  AdminDashboard,
  AdminLeadList,
  AdminOutreachSummary,
  AdminScraperJobList,
  AdminSystemInfo,
  AdminUserDetail,
  AdminUserList,
} from "@/lib/types";

export function useAdminDashboard() {
  return useQuery({
    queryKey: ["admin-dashboard"],
    queryFn: async () => {
      const { data } = await api.get<AdminDashboard>("/admin/dashboard");
      return data;
    },
  });
}

export function useAdminUsers(params?: {
  search?: string;
  role?: string;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: ["admin-users", params],
    queryFn: async () => {
      const { data } = await api.get<AdminUserList>("/admin/users", { params });
      return data;
    },
  });
}

export function useAdminUser(userId: number | null) {
  return useQuery({
    queryKey: ["admin-user", userId],
    enabled: userId != null,
    queryFn: async () => {
      const { data } = await api.get<AdminUserDetail>(`/admin/users/${userId}`);
      return data;
    },
  });
}

export function useAdminLeads(params?: {
  search?: string;
  user_id?: number;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: ["admin-leads", params],
    queryFn: async () => {
      const { data } = await api.get<AdminLeadList>("/admin/leads", { params });
      return data;
    },
  });
}

export function useAdminScraperJobs() {
  return useQuery({
    queryKey: ["admin-scraper-jobs"],
    queryFn: async () => {
      const { data } = await api.get<AdminScraperJobList>("/admin/scraper/jobs");
      return data;
    },
    refetchInterval: 5000,
  });
}

export function useAdminOutreachSummary() {
  return useQuery({
    queryKey: ["admin-outreach-summary"],
    queryFn: async () => {
      const { data } = await api.get<AdminOutreachSummary>("/admin/outreach/summary");
      return data;
    },
  });
}

export function useAdminSystem() {
  return useQuery({
    queryKey: ["admin-system"],
    queryFn: async () => {
      const { data } = await api.get<AdminSystemInfo>("/admin/system");
      return data;
    },
  });
}

export function useCreateAdminUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      name: string;
      email: string;
      password: string;
      role: string;
    }) => {
      const { data } = await api.post("/admin/users", body);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      qc.invalidateQueries({ queryKey: ["admin-dashboard"] });
    },
  });
}

export function useUpdateAdminUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      userId,
      body,
    }: {
      userId: number;
      body: {
        name?: string;
        email?: string;
        password?: string;
        role?: string;
      };
    }) => {
      const { data } = await api.patch(`/admin/users/${userId}`, body);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      qc.invalidateQueries({ queryKey: ["admin-user"] });
      qc.invalidateQueries({ queryKey: ["admin-dashboard"] });
    },
  });
}

export function useDeleteAdminUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (userId: number) => {
      await api.delete(`/admin/users/${userId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      qc.invalidateQueries({ queryKey: ["admin-dashboard"] });
    },
  });
}

export function useDeleteAdminLead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (leadId: number) => {
      await api.delete(`/admin/leads/${leadId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-leads"] });
      qc.invalidateQueries({ queryKey: ["admin-dashboard"] });
    },
  });
}

export function useCancelAdminScraperJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (jobId: string) => {
      await api.post(`/admin/scraper/jobs/${jobId}/cancel`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-scraper-jobs"] });
    },
  });
}
