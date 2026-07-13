"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import {
  Bot,
  CheckCircle2,
  ExternalLink,
  Mail,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Send,
  Settings2,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/PageHeader";
import { PageLoader } from "@/components/Loader";
import { PageError } from "@/components/PageError";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { StatCard } from "@/components/ui/StatCard";
import { IconBox } from "@/components/ui/IconBox";
import {
  useAiDraftAction,
  useAiReplyDrafts,
  useApproveOutreachEmail,
  useCreateEmailOutreachCampaign,
  useEmailConversations,
  useEmailOutreachCampaigns,
  useEmailOutreachDashboard,
  useEmailOutreachSettings,
  useLaunchEmailOutreachCampaign,
  useOutreachEmails,
  useOutreachNotifications,
  usePauseAgent,
  useResumeAgent,
  useStartAgent,
  useStopAgent,
} from "@/hooks/useEmailOutreach";
import { formatDate } from "@/lib/utils";
import type { PilotEmail } from "@/lib/types";
import { EmailOutreachOAuthHandler } from "@/components/EmailOutreachOAuthHandler";
import { EmailOutreachSubNav } from "@/components/email-outreach/EmailOutreachSubNav";
import {
  emailBadgeLabel,
  emailStatusLabel,
  isSentEmail,
  statusVariant,
} from "@/components/email-outreach/outreachEmailUtils";

export default function EmailOutreachPage() {
  const { data: dashboard, isLoading, isError, refetch } = useEmailOutreachDashboard();
  const { data: settings } = useEmailOutreachSettings();
  const { data: campaigns = [] } = useEmailOutreachCampaigns();
  const agentActive = Boolean(dashboard?.agent_running && !dashboard?.agent_paused);
  const { data: emails = [] } = useOutreachEmails(undefined, undefined, agentActive);
  const { data: drafts = [] } = useAiReplyDrafts();
  const { data: conversations = [] } = useEmailConversations();

  const createCampaign = useCreateEmailOutreachCampaign();
  const launchCampaign = useLaunchEmailOutreachCampaign();
  const approveEmail = useApproveOutreachEmail();
  const draftAction = useAiDraftAction();
  const startAgent = useStartAgent();
  const stopAgent = useStopAgent();
  const pauseAgent = usePauseAgent();
  const resumeAgent = useResumeAgent();
  const { data: notifications = [] } = useOutreachNotifications();

  const [campaignName, setCampaignName] = useState("");
  const [pilotEmail, setPilotEmail] = useState<PilotEmail | null>(null);

  if (isLoading) return <PageLoader />;
  if (isError || !dashboard) {
    return <PageError message="Failed to load email outreach dashboard" onRetry={() => refetch()} />;
  }

  const pendingReview = emails.filter((e) => e.status === "pending_review");
  const sentCount = emails.filter(isSentEmail).length;
  const recentActivity = dashboard.recent_activity ?? [];
  const recentReplies = dashboard.recent_replies ?? [];
  const upcomingFollowups = dashboard.upcoming_followups ?? [];

  return (
    <div className="space-y-8">
      <Suspense fallback={null}>
        <EmailOutreachOAuthHandler />
      </Suspense>
      <PageHeader
        eyebrow="Automation"
        title="AI Outreach Agent"
        description="Connect Gmail, configure settings, and start the AI Agent. New saved leads are automatically verified, personalized, and emailed."
      >
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={dashboard.agent_running && !dashboard.agent_paused ? "success" : "secondary"}>
            {dashboard.agent_running
              ? dashboard.agent_paused
                ? "Agent Paused"
                : "Agent Running"
              : "Agent Stopped"}
          </Badge>
          {!dashboard.agent_running ? (
            <Button
              size="sm"
              onClick={() =>
                startAgent.mutate(undefined, {
                  onSuccess: (data) => {
                    toast.success(data?.message || "AI Agent started");
                    if (data?.pilot_email) {
                      setPilotEmail(data.pilot_email);
                    }
                  },
                  onError: (e: Error) => toast.error(e.message || "Connect Gmail first"),
                })
              }
              disabled={!dashboard.gmail_connected || startAgent.isPending}
            >
              <Play className="mr-1 h-3 w-3" />
              Start AI Agent
            </Button>
          ) : dashboard.agent_paused ? (
            <Button
              size="sm"
              onClick={() =>
                resumeAgent.mutate(undefined, {
                  onSuccess: () => toast.success("AI Agent resumed"),
                })
              }
            >
              <Play className="mr-1 h-3 w-3" />
              Resume
            </Button>
          ) : (
            <>
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  pauseAgent.mutate(undefined, {
                    onSuccess: () => toast.success("AI Agent paused"),
                  })
                }
              >
                <Pause className="mr-1 h-3 w-3" />
                Pause
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() =>
                  stopAgent.mutate(undefined, {
                    onSuccess: () => toast.success("AI Agent stopped"),
                  })
                }
              >
                Stop
              </Button>
            </>
          )}
        </div>
      </PageHeader>

      {!dashboard.gmail_connected && (
        <Card className="border-amber-500/40 bg-amber-500/5">
          <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
            <p className="text-sm">
              Connect Gmail in settings before starting the AI Agent.
            </p>
            <Link href="/settings/email-outreach">
              <Button size="sm">Open outreach settings</Button>
            </Link>
          </CardContent>
        </Card>
      )}

      <EmailOutreachSubNav />

      <Card className="border-primary/20 bg-primary/5">
        <CardContent className="flex flex-wrap items-center justify-between gap-4 py-4">
          <div className="space-y-1 text-sm">
            <p className="font-medium">
              Gmail: {dashboard.gmail_connected ? dashboard.gmail_email : "Not connected"}
            </p>
            <p className="text-muted-foreground">
              {dashboard.emails_remaining_today} emails remaining today ·{" "}
              {dashboard.within_working_hours ? "Within working hours" : "Outside working hours"} ·
              Sync: {dashboard.sync_status}
              {settings?.agent_batch_delay_minutes
                ? ` · Batch delay: ${settings.agent_batch_delay_minutes} min`
                : ""}
            </p>
          </div>
          <div className="flex flex-wrap gap-4 text-sm">
            <span>Sent today: <strong>{dashboard.emails_sent_today}</strong></span>
            <span>This week: <strong>{dashboard.emails_sent_this_week}</strong></span>
            <span>Reply rate: <strong>{dashboard.reply_rate}%</strong></span>
            <span>Queue: <strong>{dashboard.queued_emails}</strong></span>
          </div>
        </CardContent>
      </Card>

      {pilotEmail && (
        <Card className="border-emerald-500/30">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-base">
                <Send className="h-4 w-4" />
                Latest pilot email
              </CardTitle>
              <CardDescription>First email sent when agent started.</CardDescription>
            </div>
            <Link href="/email-outreach/sent">
              <Button size="sm" variant="outline">
                View all sent
                <ExternalLink className="ml-1 h-3 w-3" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-medium">
                {pilotEmail.company_name || "Lead"} → {pilotEmail.to_email}
              </p>
              <Badge variant={statusVariant(pilotEmail.status)}>{pilotEmail.status}</Badge>
            </div>
            <p className="text-sm font-medium">{pilotEmail.subject}</p>
            <pre className="max-h-40 overflow-y-auto whitespace-pre-wrap rounded-lg bg-muted/50 p-3 text-sm font-sans">
              {pilotEmail.body_text}
            </pre>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <Link href="/settings/email-outreach">
          <Card className="h-full transition-colors hover:bg-muted/30">
            <CardContent className="flex items-center gap-4 py-5">
              <IconBox icon={Settings2} tone="slate" size="md" />
              <div>
                <p className="font-medium">Outreach settings</p>
                <p className="text-xs text-muted-foreground">
                  Limits, auto-send, Gmail, working hours — auto-applies here
                </p>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link href="/email-outreach/sent">
          <Card className="h-full transition-colors hover:bg-muted/30">
            <CardContent className="flex items-center gap-4 py-5">
              <IconBox icon={Send} tone="blue" size="md" />
              <div>
                <p className="font-medium">Sent messages ({sentCount})</p>
                <p className="text-xs text-muted-foreground">
                  Full log — who received what email and when
                </p>
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Emails sent (total)" value={dashboard.emails_sent} icon={Send} iconTone="blue" />
        <StatCard label="Replies received" value={dashboard.replies_received} icon={RefreshCw} iconTone="sky" />
        <StatCard label="Interested leads" value={dashboard.interested_leads} icon={CheckCircle2} iconTone="emerald" />
        <StatCard label="AI emails generated" value={dashboard.ai_emails_generated} icon={Bot} iconTone="violet" />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Sent today" value={dashboard.emails_sent_today} icon={Send} iconTone="blue" />
        <StatCard label="Pending review" value={dashboard.pending_emails} icon={Mail} iconTone="amber" />
        <StatCard label="Follow-ups scheduled" value={dashboard.follow_ups_scheduled} icon={RefreshCw} iconTone="indigo" />
        <StatCard label="Success rate" value={`${dashboard.success_rate}%`} icon={CheckCircle2} iconTone="emerald" />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Live activity</CardTitle>
            <CardDescription>Agent actions in real time</CardDescription>
          </CardHeader>
          <CardContent className="max-h-72 space-y-2 overflow-y-auto">
            {recentActivity.length === 0 && (
              <p className="text-sm text-muted-foreground">No activity yet.</p>
            )}
            {recentActivity.map((item) => (
              <div key={item.id} className="rounded border border-border/50 px-3 py-2 text-sm">
                <p>{item.message}</p>
                <p className="text-xs text-muted-foreground">{formatDate(item.created_at)}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent replies</CardTitle>
          </CardHeader>
          <CardContent className="max-h-72 space-y-2 overflow-y-auto">
            {recentReplies.length === 0 && (
              <p className="text-sm text-muted-foreground">No replies yet.</p>
            )}
            {recentReplies.map((reply) => (
              <div key={reply.conversation_id} className="rounded border border-border/50 px-3 py-2 text-sm">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">{reply.intent || "reply"}</Badge>
                  <span className="text-xs text-muted-foreground">Lead #{reply.lead_id}</span>
                </div>
                <p className="mt-1">{reply.summary}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Upcoming follow-ups</CardTitle>
          </CardHeader>
          <CardContent className="max-h-72 space-y-2 overflow-y-auto">
            {upcomingFollowups.length === 0 && (
              <p className="text-sm text-muted-foreground">No follow-ups scheduled.</p>
            )}
            {upcomingFollowups.map((fu) => (
              <div key={fu.id} className="rounded border border-border/50 px-3 py-2 text-sm">
                <p className="font-medium">{fu.subject}</p>
                <p className="text-xs text-muted-foreground">
                  Step {fu.follow_up_step} · {fu.scheduled_at ? formatDate(fu.scheduled_at) : "TBD"}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {notifications.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Notifications</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {notifications.slice(0, 8).map((n) => (
              <div
                key={n.id}
                className={`rounded-lg border px-3 py-2 text-sm ${n.is_read ? "opacity-60" : ""}`}
              >
                <p className="font-medium">{n.title}</p>
                <p className="text-muted-foreground">{n.message}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Campaigns</CardTitle>
          <CardDescription>
            Scrape → Verify → Generate AI email → Review → Send → Follow-ups
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Input
              placeholder="Campaign name"
              value={campaignName}
              onChange={(e) => setCampaignName(e.target.value)}
              className="max-w-xs"
            />
            <Button
              size="sm"
              onClick={() =>
                createCampaign.mutate(
                  { name: campaignName || "Email outreach campaign" },
                  {
                    onSuccess: () => {
                      toast.success("Campaign created");
                      setCampaignName("");
                    },
                  }
                )
              }
            >
              <Plus className="mr-1 h-3 w-3" />
              New campaign
            </Button>
          </div>

          <div className="space-y-2">
            {campaigns.map((campaign) => (
              <div
                key={campaign.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 px-4 py-3"
              >
                <div>
                  <p className="font-medium">{campaign.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {campaign.stats
                      ? `${campaign.stats.generated ?? 0} generated · ${campaign.stats.verified ?? 0} verified`
                      : "Not started"}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={statusVariant(campaign.status)}>{campaign.status}</Badge>
                  {["draft", "paused"].includes(campaign.status) && (
                    <Button
                      size="sm"
                      onClick={() =>
                        launchCampaign.mutate(campaign.id, {
                          onSuccess: () => toast.success("Campaign launched"),
                          onError: (err: Error & { response?: { data?: { detail?: string } } }) =>
                            toast.error(err.response?.data?.detail || "Launch failed"),
                        })
                      }
                    >
                      <Play className="mr-1 h-3 w-3" />
                      Launch
                    </Button>
                  )}
                </div>
              </div>
            ))}
            {campaigns.length === 0 && (
              <p className="text-sm text-muted-foreground">Create a campaign to start outreach.</p>
            )}
          </div>
        </CardContent>
      </Card>

      {pendingReview.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Pending review ({pendingReview.length})</CardTitle>
            <CardDescription>Approve AI-generated emails before sending.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {pendingReview.map((email) => (
              <div key={email.id} className="rounded-lg border border-border/60 p-4">
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-sm font-medium">{email.to_email}</p>
                  <Button
                    size="sm"
                    onClick={() =>
                      approveEmail.mutate(email.id, {
                        onSuccess: () => toast.success("Email approved for sending"),
                      })
                    }
                  >
                    <CheckCircle2 className="mr-1 h-3 w-3" />
                    Approve & send
                  </Button>
                </div>
                <p className="text-sm font-semibold">{email.subject}</p>
                <p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground">
                  {email.body_text}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {drafts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>AI reply suggestions</CardTitle>
            <CardDescription>Review and approve before sending replies.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {drafts.map((draft) => (
              <div key={draft.id} className="rounded-lg border border-border/60 p-4">
                <div className="mb-2 flex items-center gap-2">
                  <Badge>{draft.detected_intent}</Badge>
                  <span className="text-xs text-muted-foreground">{draft.summary}</span>
                </div>
                <p className="text-sm font-semibold">{draft.draft_subject}</p>
                <p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground">
                  {draft.draft_body}
                </p>
                <div className="mt-3 flex gap-2">
                  <Button
                    size="sm"
                    onClick={() =>
                      draftAction.mutate(
                        { draftId: draft.id, action: "approve" },
                        { onSuccess: () => toast.success("Reply approved") }
                      )
                    }
                  >
                    Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      draftAction.mutate(
                        { draftId: draft.id, action: "reject" },
                        { onSuccess: () => toast.success("Draft rejected") }
                      )
                    }
                  >
                    <XCircle className="mr-1 h-3 w-3" />
                    Reject
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent emails</CardTitle>
            <Link href="/email-outreach/sent">
              <Button size="sm" variant="ghost">
                View all
                <ExternalLink className="ml-1 h-3 w-3" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="space-y-2">
            {emails.slice(0, 10).map((email) => (
              <div
                key={email.id}
                className="flex items-center justify-between rounded border border-border/40 px-3 py-2 text-sm"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium">{email.subject}</p>
                  <p className="truncate text-xs text-muted-foreground">{email.to_email}</p>
                </div>
                <Badge variant={statusVariant(email.status)}>{email.status}</Badge>
              </div>
            ))}
            {emails.length === 0 && (
              <p className="text-sm text-muted-foreground">No outreach emails yet.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Conversations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {conversations.slice(0, 10).map((conv) => (
              <div
                key={conv.id}
                className="flex items-center justify-between rounded border border-border/40 px-3 py-2 text-sm"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium">{conv.subject}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {conv.reply_summary || conv.status}
                  </p>
                </div>
                <span className="text-xs text-muted-foreground">
                  {conv.last_message_at ? formatDate(conv.last_message_at) : "—"}
                </span>
              </div>
            ))}
            {conversations.length === 0 && (
              <p className="text-sm text-muted-foreground">No conversations yet.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Delivery metrics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-4 text-sm">
            <div>
              <p className="text-muted-foreground">Delivered</p>
              <p className="text-2xl font-semibold">{dashboard.emails_delivered}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Open rate</p>
              <p className="text-2xl font-semibold">{dashboard.open_rate}%</p>
            </div>
            <div>
              <p className="text-muted-foreground">Reply rate</p>
              <p className="text-2xl font-semibold">{dashboard.reply_rate}%</p>
            </div>
            <div>
              <p className="text-muted-foreground">Follow-up queue</p>
              <p className="text-2xl font-semibold">{dashboard.follow_up_queue}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
