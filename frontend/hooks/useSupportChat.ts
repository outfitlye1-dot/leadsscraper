import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { SupportMessage, SupportThread, SupportThreadDetail } from "@/lib/types";

export function useMySupportThread(poll = false, enabled = true) {
  return useQuery({
    queryKey: ["support-thread", "me"],
    enabled,
    queryFn: async () => {
      const { data } = await api.get<SupportThreadDetail>("/support/thread");
      return data;
    },
    refetchInterval: poll ? 3000 : false,
  });
}

export function useAdminSupportThreads(poll = false, enabled = true) {
  return useQuery({
    queryKey: ["support-threads", "admin"],
    enabled,
    queryFn: async () => {
      const { data } = await api.get<SupportThread[]>("/support/admin/threads");
      return data;
    },
    refetchInterval: poll ? 4000 : false,
  });
}

export function useAdminSupportThread(userId: number | null, poll = false) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: ["support-thread", "admin", userId],
    enabled: typeof userId === "number" && userId > 0,
    queryFn: async () => {
      const { data } = await api.get<SupportThreadDetail>(`/support/admin/threads/${userId}`);
      queryClient.setQueryData<SupportThread[]>(["support-threads", "admin"], (prev) => {
        if (!prev || userId == null) return prev;
        return prev.map((thread) =>
          thread.user_id === userId ? { ...thread, unread_count: 0 } : thread
        );
      });
      return data;
    },
    refetchInterval: poll ? 3000 : false,
  });
}

export function useSendSupportMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { body: string; userId?: number }) => {
      const path =
        payload.userId != null
          ? `/support/admin/threads/${payload.userId}/messages`
          : "/support/messages";
      const { data } = await api.post<SupportMessage>(path, { body: payload.body });
      return data;
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ["support-thread", "me"] });
      queryClient.invalidateQueries({ queryKey: ["support-threads", "admin"] });
      if (vars.userId != null) {
        queryClient.invalidateQueries({
          queryKey: ["support-thread", "admin", vars.userId],
        });
      }
    },
  });
}

export function useDeleteSupportMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { messageId: number; userId?: number }) => {
      await api.delete(`/support/messages/${payload.messageId}`);
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ["support-thread", "me"] });
      queryClient.invalidateQueries({ queryKey: ["support-threads", "admin"] });
      if (vars.userId != null) {
        queryClient.invalidateQueries({
          queryKey: ["support-thread", "admin", vars.userId],
        });
      }
    },
  });
}
