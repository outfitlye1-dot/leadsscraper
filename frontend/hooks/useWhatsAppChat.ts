import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  WhatsAppChatContact,
  WhatsAppChatOpenerResponse,
  WhatsAppChatReplyResponse,
  WhatsAppChatThread,
} from "@/lib/types";

export function useWhatsAppContacts() {
  return useQuery({
    queryKey: ["whatsapp-chat-contacts"],
    queryFn: async () => {
      const { data } = await api.get<WhatsAppChatContact[]>("/whatsapp-chat/contacts");
      return data;
    },
    refetchInterval: 30000,
  });
}

export function useWhatsAppThread(leadId: number | null) {
  return useQuery({
    queryKey: ["whatsapp-chat-thread", leadId],
    enabled: Boolean(leadId),
    queryFn: async () => {
      const { data } = await api.get<WhatsAppChatThread>(`/whatsapp-chat/${leadId}`);
      return data;
    },
    // Pick up Cloud API / webhook inbound quickly while the thread is open
    refetchInterval: leadId ? 5000 : false,
  });
}

export function useWhatsAppReply() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      leadId: number;
      customer_message: string;
      hint?: string;
    }) => {
      const { data } = await api.post<WhatsAppChatReplyResponse>(
        `/whatsapp-chat/${payload.leadId}/reply`,
        {
          customer_message: payload.customer_message,
          hint: payload.hint || undefined,
        }
      );
      return data;
    },
    onSuccess: async (_data, vars) => {
      await queryClient.invalidateQueries({ queryKey: ["whatsapp-chat-thread", vars.leadId] });
      await queryClient.invalidateQueries({ queryKey: ["whatsapp-chat-contacts"] });
    },
  });
}

export function useWhatsAppOpener() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (leadId: number) => {
      const { data } = await api.post<WhatsAppChatOpenerResponse>(
        `/whatsapp-chat/${leadId}/opener`
      );
      return data;
    },
    onSuccess: async (_data, leadId) => {
      await queryClient.invalidateQueries({ queryKey: ["whatsapp-chat-thread", leadId] });
      await queryClient.invalidateQueries({ queryKey: ["whatsapp-chat-contacts"] });
    },
  });
}

export function useWhatsAppManualOutbound() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { leadId: number; body: string }) => {
      const { data } = await api.post<WhatsAppChatOpenerResponse>(
        `/whatsapp-chat/${payload.leadId}/outbound`,
        { body: payload.body }
      );
      return data;
    },
    onSuccess: async (_data, vars) => {
      await queryClient.invalidateQueries({ queryKey: ["whatsapp-chat-thread", vars.leadId] });
      await queryClient.invalidateQueries({ queryKey: ["whatsapp-chat-contacts"] });
    },
  });
}

export function useClearWhatsAppThread() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (leadId: number) => {
      const { data } = await api.delete<{ deleted: number }>(`/whatsapp-chat/${leadId}`);
      return data;
    },
    onSuccess: async (_data, leadId) => {
      await queryClient.invalidateQueries({ queryKey: ["whatsapp-chat-thread", leadId] });
      await queryClient.invalidateQueries({ queryKey: ["whatsapp-chat-contacts"] });
    },
  });
}

export function useWhatsAppCloudStatus() {
  return useQuery({
    queryKey: ["whatsapp-cloud-status"],
    queryFn: async () => {
      const { data } = await api.get<{
        configured: boolean;
        phone_number_id?: string | null;
        business_account_id?: string | null;
        display_number?: string | null;
        api_version?: string | null;
      }>("/whatsapp-chat/cloud/status");
      return data;
    },
    staleTime: 60_000,
  });
}

export function useWhatsAppCloudSend() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      leadId: number;
      body?: string;
      message_id?: number;
      mode?: "text" | "template";
      template_name?: string;
      language_code?: string;
    }) => {
      const { data } = await api.post<{
        success: boolean;
        message_id?: string | null;
        to?: string | null;
        local_message_id?: number | null;
        detail?: string | null;
      }>(`/whatsapp-chat/${payload.leadId}/send`, {
        body: payload.body,
        message_id: payload.message_id,
        mode: payload.mode || "text",
        template_name: payload.template_name,
        language_code: payload.language_code || "en_US",
      });
      return data;
    },
    onSuccess: async (_data, vars) => {
      await queryClient.invalidateQueries({ queryKey: ["whatsapp-chat-thread", vars.leadId] });
      await queryClient.invalidateQueries({ queryKey: ["whatsapp-chat-contacts"] });
    },
  });
}
