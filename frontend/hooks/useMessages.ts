import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { MessageBulkDeleteResponse, MessageListResponse, MessageType } from "@/lib/types";

interface MessageFilters {
  lead_id?: number;
  campaign_id?: number;
  message_type?: MessageType;
  page?: number;
  page_size?: number;
}

export function useMessages(filters: MessageFilters = {}) {
  return useQuery({
    queryKey: ["messages", filters],
    queryFn: async () => {
      const { data } = await api.get<MessageListResponse>("/messages", { params: filters });
      return data;
    },
  });
}

export function useDeleteMessages() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (filters: MessageFilters = {}) => {
      const params: Record<string, string | number> = {};
      if (filters.lead_id) params.lead_id = filters.lead_id;
      if (filters.campaign_id) params.campaign_id = filters.campaign_id;
      if (filters.message_type) params.message_type = filters.message_type;
      const { data } = await api.delete<MessageBulkDeleteResponse>("/messages", { params });
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["messages"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
  });
}
