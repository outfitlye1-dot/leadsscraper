"use client";

import Link from "next/link";
import { Send } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { PageLoader } from "@/components/Loader";
import { PageError } from "@/components/PageError";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { EmailOutreachSubNav } from "@/components/email-outreach/EmailOutreachSubNav";
import { SentMessagesList } from "@/components/email-outreach/SentMessagesList";
import { isSentEmail } from "@/components/email-outreach/outreachEmailUtils";
import {
  useEmailOutreachDashboard,
  useOutreachEmails,
} from "@/hooks/useEmailOutreach";

export default function SentMessagesPage() {
  const { data: dashboard } = useEmailOutreachDashboard();
  const agentActive = Boolean(dashboard?.agent_running && !dashboard?.agent_paused);
  const { data: emails = [], isLoading, isError, refetch } = useOutreachEmails(
    undefined,
    undefined,
    agentActive
  );

  const sentCount = emails.filter(isSentEmail).length;

  if (isLoading) return <PageLoader />;
  if (isError) {
    return <PageError message="Failed to load sent messages" onRetry={() => refetch()} />;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Email Outreach"
        title="Sent messages"
        description="Every email the AI Agent sent — full subject, body, and delivery status."
      >
        <Link href="/email-outreach">
          <Button size="sm" variant="outline">
            <Send className="mr-1 h-3 w-3" />
            Back to Agent
          </Button>
        </Link>
      </PageHeader>

      <EmailOutreachSubNav />

      <Card>
        <CardContent className="grid gap-4 py-6 sm:grid-cols-3">
          <div>
            <p className="text-sm text-muted-foreground">Total sent</p>
            <p className="text-2xl font-semibold">{sentCount}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Sent today</p>
            <p className="text-2xl font-semibold">{dashboard?.emails_sent_today ?? 0}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Reply rate</p>
            <p className="text-2xl font-semibold">{dashboard?.reply_rate ?? 0}%</p>
          </div>
        </CardContent>
      </Card>

      <SentMessagesList
        emails={emails}
        emptyMessage="No sent messages yet. Start the AI Agent from the Agent page."
      />
    </div>
  );
}
