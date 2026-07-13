import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type {
  Campaign,
  CampaignRunResponse,
  CampaignStatus,
  MessageType,
} from "@/lib/types";

export function useCampaigns() {
  return useQuery({
    queryKey: ["campaigns"],
    queryFn: async () => {
      const { data } = await api.get<Campaign[]>("/campaigns");
      return data;
    },
  });
}

export function useCampaign(id: number | null) {
  return useQuery({
    queryKey: ["campaigns", id],
    queryFn: async () => {
      const { data } = await api.get<Campaign>(`/campaigns/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCreateCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      name: string;
      message_type: MessageType;
      status?: CampaignStatus;
    }) => {
      const { data } = await api.post<Campaign>("/campaigns", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
  });
}

export function useUpdateCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: {
      id: number;
      name?: string;
      message_type?: MessageType;
      status?: CampaignStatus;
    }) => {
      const { data } = await api.put<Campaign>(`/campaigns/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
      queryClient.invalidateQueries({ queryKey: ["messages"] });
    },
  });
}

export function useRunCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: {
      id: number;
      lead_status?: string;
      limit?: number;
      skip_existing?: boolean;
    }) => {
      const { data } = await api.post<CampaignRunResponse>(`/campaigns/${id}/run`, payload, {
        timeout: 300000,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["messages"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
      queryClient.invalidateQueries({ queryKey: ["leads"] });
    },
  });
}

export function useDeleteCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/campaigns/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
      queryClient.invalidateQueries({ queryKey: ["messages"] });
    },
  });
}
