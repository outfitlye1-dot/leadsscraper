import type { OutreachEmail } from "@/lib/types";
import { formatDate } from "@/lib/utils";

export function statusVariant(
  status: string
): "default" | "secondary" | "success" | "warning" | "destructive" {
  if (["sent", "delivered", "active", "connected", "scheduled", "replied"].includes(status)) {
    return "success";
  }
  if (["pending_review", "review", "queued", "paused"].includes(status)) return "warning";
  if (["failed", "verification_failed", "bounced", "error"].includes(status)) return "destructive";
  return "secondary";
}

export function emailStatusLabel(email: OutreachEmail) {
  if (email.sent_at) return `Sent ${formatDate(email.sent_at)}`;
  if (email.status === "queued" && email.scheduled_at) {
    if (email.follow_up_step > 0) {
      return `Follow-up #${email.follow_up_step} — scheduled ${formatDate(email.scheduled_at)}`;
    }
    return `Scheduled ${formatDate(email.scheduled_at)}`;
  }
  return `Status: ${email.status}`;
}

export function emailBadgeLabel(email: OutreachEmail) {
  if (email.status === "queued" && email.scheduled_at && email.follow_up_step > 0) {
    return "scheduled";
  }
  return email.status;
}

export const SENT_STATUSES = new Set(["sent", "delivered", "opened", "replied"]);

export function isSentEmail(email: OutreachEmail) {
  return SENT_STATUSES.has(email.status) || Boolean(email.sent_at);
}
