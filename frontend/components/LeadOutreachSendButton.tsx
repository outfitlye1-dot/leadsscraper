"use client";

import { useCallback, useEffect, useState } from "react";
import { Clock, Send } from "lucide-react";
import { toast } from "sonner";
import type { Lead } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { useSendLeadOutreach } from "@/hooks/useEmailOutreach";
import { getApiErrorMessage } from "@/lib/errors";
import {
  OutreachTruckLoader,
  type OutreachLoaderPhase,
} from "@/components/OutreachTruckLoader";

interface LeadOutreachSendButtonProps {
  lead: Lead;
  compact?: boolean;
}

export function LeadOutreachSendButton({ lead, compact }: LeadOutreachSendButtonProps) {
  const sendOutreach = useSendLeadOutreach();
  const [loaderOpen, setLoaderOpen] = useState(false);
  const [loaderPhase, setLoaderPhase] = useState<OutreachLoaderPhase>("loading");
  const [sentSubject, setSentSubject] = useState<string>();
  const [sentToEmail, setSentToEmail] = useState<string>();
  const [errorMessage, setErrorMessage] = useState<string>();
  const [localAwaitingReply, setLocalAwaitingReply] = useState(false);

  const awaitingReply =
    lead.outreach_email_status === "awaiting_reply" || localAwaitingReply;

  useEffect(() => {
    if (lead.outreach_email_status === "replied" || lead.outreach_email_status === "none") {
      setLocalAwaitingReply(false);
    }
  }, [lead.outreach_email_status]);

  const closeLoader = useCallback(() => {
    setLoaderOpen(false);
    setLoaderPhase("loading");
    setSentSubject(undefined);
    setSentToEmail(undefined);
    setErrorMessage(undefined);
  }, []);

  const startSend = useCallback(() => {
    if (awaitingReply) return;

    setLoaderOpen(true);
    setLoaderPhase("loading");
    setSentSubject(undefined);
    setSentToEmail(undefined);
    setErrorMessage(undefined);

    sendOutreach.mutate(lead.id, {
      onSuccess: (data) => {
        setSentSubject(data.subject);
        setSentToEmail(data.to_email);
        setLocalAwaitingReply(true);
        setLoaderPhase("complete");
        toast.success(`Email sent to ${data.to_email}`, {
          description: data.subject,
        });
      },
      onError: (error) => {
        setErrorMessage(getApiErrorMessage(error, "Failed to send outreach email"));
        setLoaderPhase("error");
      },
    });
  }, [awaitingReply, lead.id, sendOutreach]);

  if (!lead.email) return null;

  const isSending = sendOutreach.isPending && sendOutreach.variables === lead.id;

  if (awaitingReply) {
    return (
      <Button
        type="button"
        size="sm"
        variant="outline"
        className={compact ? "h-8 gap-1 px-2" : "h-8 gap-1 px-2"}
        title="Email sent — waiting for Gmail reply"
        disabled
      >
        <Clock className="h-3.5 w-3.5" />
        {!compact && <span className="text-xs">Awaiting reply</span>}
      </Button>
    );
  }

  return (
    <>
      <Button
        type="button"
        size="sm"
        variant="default"
        className={compact ? "h-8 gap-1 px-2" : "h-8 gap-1 px-2"}
        title="Generate AI email and send automatically"
        onClick={startSend}
        disabled={isSending || loaderOpen}
      >
        <Send className="h-3.5 w-3.5" />
        {!compact && <span className="text-xs">AI Email</span>}
      </Button>

      <OutreachTruckLoader
        open={loaderOpen}
        phase={loaderPhase}
        companyName={lead.company_name}
        toEmail={sentToEmail ?? lead.email}
        subject={sentSubject}
        error={errorMessage}
        onFinish={closeLoader}
        onRetry={() => {
          closeLoader();
          window.setTimeout(startSend, 200);
        }}
      />
    </>
  );
}
