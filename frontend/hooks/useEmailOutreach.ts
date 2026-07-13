import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type {
  AgentStartResponse,
  AgentStatus,
  AiReplyDraft,
  EmailAccount,
  EmailConversation,
  EmailOutreachCampaign,
  EmailOutreachDashboard,
  EmailOutreachSettings,
  OutreachEmail,
  OutreachNotification,
} from "@/lib/types";

function normalizeDashboard(data: Partial<EmailOutreachDashboard>): EmailOutreachDashboard {
  return {
    connected_accounts: data.connected_accounts ?? 0,
    active_campaigns: data.active_campaigns ?? 0,
    emails_sent: data.emails_sent ?? 0,
    emails_delivered: data.emails_delivered ?? 0,
    open_rate: data.open_rate ?? 0,
    reply_rate: data.reply_rate ?? 0,
    bounce_rate: data.bounce_rate ?? 0,
    follow_up_queue: data.follow_up_queue ?? 0,
    pending_ai_drafts: data.pending_ai_drafts ?? 0,
    automation_enabled: data.automation_enabled ?? false,
    pending_jobs: data.pending_jobs ?? 0,
    emails_sent_today: data.emails_sent_today ?? 0,
    emails_sent_this_week: data.emails_sent_this_week ?? 0,
    emails_sent_this_month: data.emails_sent_this_month ?? 0,
    pending_emails: data.pending_emails ?? 0,
    failed_emails: data.failed_emails ?? 0,
    queued_emails: data.queued_emails ?? 0,
    replies_received: data.replies_received ?? 0,
    positive_replies: data.positive_replies ?? 0,
    interested_leads: data.interested_leads ?? 0,
    meetings_requested: data.meetings_requested ?? 0,
    follow_ups_scheduled: data.follow_ups_scheduled ?? 0,
    follow_ups_completed: data.follow_ups_completed ?? 0,
    no_response_leads: data.no_response_leads ?? 0,
    completed_campaigns: data.completed_campaigns ?? 0,
    running_campaigns: data.running_campaigns ?? 0,
    paused_campaigns: data.paused_campaigns ?? 0,
    ai_emails_generated: data.ai_emails_generated ?? 0,
    ai_replies_generated: data.ai_replies_generated ?? 0,
    ai_tokens_used: data.ai_tokens_used ?? 0,
    estimated_ai_cost: data.estimated_ai_cost ?? 0,
    gmail_connected: data.gmail_connected ?? (data.connected_accounts ?? 0) > 0,
    gmail_email: data.gmail_email ?? null,
    daily_sending_limit: data.daily_sending_limit ?? 50,
    emails_remaining_today: data.emails_remaining_today ?? 0,
    sync_status: data.sync_status ?? "unknown",
    last_sync_time: data.last_sync_time ?? null,
    agent_running: data.agent_running ?? false,
    agent_paused: data.agent_paused ?? false,
    last_agent_run_at: data.last_agent_run_at ?? null,
    within_working_hours: data.within_working_hours ?? true,
    success_rate: data.success_rate ?? 0,
    conversion_rate: data.conversion_rate ?? 0,
    recent_activity: data.recent_activity ?? [],
    recent_replies: data.recent_replies ?? [],
    upcoming_followups: data.upcoming_followups ?? [],
    running_jobs: data.running_jobs ?? 0,
  };
}

export function useEmailOutreachDashboard() {
  return useQuery({
    queryKey: ["email-outreach-dashboard"],
    queryFn: async () => {
      const { data } = await api.get<Partial<EmailOutreachDashboard>>("/email-outreach/dashboard");
      return normalizeDashboard(data);
    },
    refetchInterval: 15000,
  });
}

export function useEmailOutreachSettings() {
  return useQuery({
    queryKey: ["email-outreach-settings"],
    queryFn: async () => {
      const { data } = await api.get<EmailOutreachSettings>("/email-outreach/settings");
      return data;
    },
  });
}

export function useUpdateEmailOutreachSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<EmailOutreachSettings>) => {
      const { data } = await api.put<EmailOutreachSettings>("/email-outreach/settings", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-outreach-settings"] });
      queryClient.invalidateQueries({ queryKey: ["email-outreach-dashboard"] });
    },
  });
}

export function useEmailAccounts() {
  return useQuery({
    queryKey: ["email-accounts"],
    queryFn: async () => {
      const { data } = await api.get<EmailAccount[]>("/email-outreach/accounts");
      return data;
    },
  });
}

export function useConnectSmtpAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      email_address: string;
      password: string;
      display_name?: string;
      smtp_host?: string;
      smtp_port?: number;
      imap_host?: string;
      imap_port?: number;
    }) => {
      const { data } = await api.post<EmailAccount>("/email-outreach/accounts/smtp", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-accounts"] });
      queryClient.invalidateQueries({ queryKey: ["email-outreach-dashboard"] });
    },
  });
}

export function useDeleteEmailAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (accountId: number) => {
      await api.delete(`/email-outreach/accounts/${accountId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-accounts"] });
      queryClient.invalidateQueries({ queryKey: ["email-outreach-dashboard"] });
    },
  });
}

export function useStartGoogleOAuth() {
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.get<{ authorization_url: string }>(
        "/email-outreach/oauth/google/start"
      );
      return data.authorization_url;
    },
  });
}

export function useStartMicrosoftOAuth() {
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.get<{ authorization_url: string }>(
        "/email-outreach/oauth/microsoft/start"
      );
      return data.authorization_url;
    },
  });
}

export function useEmailOutreachCampaigns() {
  return useQuery({
    queryKey: ["email-outreach-campaigns"],
    queryFn: async () => {
      const { data } = await api.get<EmailOutreachCampaign[]>("/email-outreach/campaigns");
      return data;
    },
  });
}

export function useCreateEmailOutreachCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      name: string;
      email_account_id?: number;
      follow_up_enabled?: boolean;
      lead_filter_saved_only?: boolean;
    }) => {
      const { data } = await api.post<EmailOutreachCampaign>("/email-outreach/campaigns", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-outreach-campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["email-outreach-dashboard"] });
    },
  });
}

export function useLaunchEmailOutreachCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (campaignId: number) => {
      const { data } = await api.post(`/email-outreach/campaigns/${campaignId}/launch`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-outreach-campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["email-outreach-emails"] });
      queryClient.invalidateQueries({ queryKey: ["email-outreach-dashboard"] });
    },
  });
}

export function useOutreachEmails(campaignId?: number, status?: string, fastPoll = false) {
  return useQuery({
    queryKey: ["email-outreach-emails", campaignId, status],
    queryFn: async () => {
      const params: Record<string, string | number> = {};
      if (campaignId) params.campaign_id = campaignId;
      if (status) params.status = status;
      const { data } = await api.get<OutreachEmail[]>("/email-outreach/emails", { params });
      return data;
    },
    refetchInterval: fastPoll ? 5000 : false,
  });
}

export function useApproveOutreachEmail() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (emailId: number) => {
      await api.post(`/email-outreach/emails/${emailId}/approve`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-outreach-emails"] });
      queryClient.invalidateQueries({ queryKey: ["email-outreach-dashboard"] });
    },
  });
}

export function useAiReplyDrafts() {
  return useQuery({
    queryKey: ["ai-reply-drafts"],
    queryFn: async () => {
      const { data } = await api.get<AiReplyDraft[]>("/email-outreach/ai-drafts");
      return data;
    },
  });
}

export function useAiDraftAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      draftId: number;
      action: "approve" | "reject" | "edit";
      draft_subject?: string;
      draft_body?: string;
    }) => {
      const { data } = await api.post<AiReplyDraft>(
        `/email-outreach/ai-drafts/${payload.draftId}/action`,
        {
          action: payload.action,
          draft_subject: payload.draft_subject,
          draft_body: payload.draft_body,
        }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-reply-drafts"] });
      queryClient.invalidateQueries({ queryKey: ["email-outreach-dashboard"] });
    },
  });
}

export function useEmailConversations() {
  return useQuery({
    queryKey: ["email-conversations"],
    queryFn: async () => {
      const { data } = await api.get<EmailConversation[]>("/email-outreach/conversations");
      return data;
    },
  });
}

export function useAgentStatus() {
  return useQuery({
    queryKey: ["agent-status"],
    queryFn: async () => {
      const { data } = await api.get<AgentStatus>("/email-outreach/agent/status");
      return data;
    },
    refetchInterval: 10000,
  });
}

function invalidateAgentQueries(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["agent-status"] });
  queryClient.invalidateQueries({ queryKey: ["email-outreach-dashboard"] });
  queryClient.invalidateQueries({ queryKey: ["email-outreach-settings"] });
  queryClient.invalidateQueries({ queryKey: ["email-outreach-emails"] });
}

export function useStartAgent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<AgentStartResponse>("/email-outreach/agent/start");
      return data;
    },
    onSuccess: () => invalidateAgentQueries(queryClient),
  });
}

export function useStopAgent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post("/email-outreach/agent/stop");
      return data;
    },
    onSuccess: () => invalidateAgentQueries(queryClient),
  });
}

export function usePauseAgent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post("/email-outreach/agent/pause");
      return data;
    },
    onSuccess: () => invalidateAgentQueries(queryClient),
  });
}

export function useResumeAgent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post("/email-outreach/agent/resume");
      return data;
    },
    onSuccess: () => invalidateAgentQueries(queryClient),
  });
}

export function useOutreachNotifications() {
  return useQuery({
    queryKey: ["outreach-notifications"],
    queryFn: async () => {
      try {
        const { data } = await api.get<OutreachNotification[]>("/email-outreach/notifications");
        return data ?? [];
      } catch {
        return [];
      }
    },
    refetchInterval: 20000,
    retry: false,
  });
}
