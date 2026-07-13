"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import type { OutreachEmail } from "@/lib/types";
import {
  emailBadgeLabel,
  emailStatusLabel,
  isSentEmail,
  statusVariant,
} from "@/components/email-outreach/outreachEmailUtils";

type FilterTab = "sent" | "scheduled" | "all";

export function SentMessagesList({
  emails,
  emptyMessage = "No messages yet.",
}: {
  emails: OutreachEmail[];
  emptyMessage?: string;
}) {
  const [query, setQuery] = useState("");
  const [tab, setTab] = useState<FilterTab>("sent");

  const filtered = useMemo(() => {
    let list = emails;
    if (tab === "sent") {
      list = list.filter(isSentEmail);
    } else if (tab === "scheduled") {
      list = list.filter(
        (e) => e.status === "queued" && e.scheduled_at && e.follow_up_step > 0
      );
    }
    const q = query.trim().toLowerCase();
    if (!q) return list;
    return list.filter(
      (e) =>
        e.to_email.toLowerCase().includes(q) ||
        e.subject.toLowerCase().includes(q) ||
        e.body_text.toLowerCase().includes(q)
    );
  }, [emails, query, tab]);

  const tabs: { id: FilterTab; label: string; count: number }[] = [
    {
      id: "sent",
      label: "Sent",
      count: emails.filter(isSentEmail).length,
    },
    {
      id: "scheduled",
      label: "Scheduled",
      count: emails.filter(
        (e) => e.status === "queued" && e.scheduled_at && e.follow_up_step > 0
      ).length,
    },
    { id: "all", label: "All", count: emails.length },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                tab === t.id
                  ? "bg-foreground text-background"
                  : "bg-muted/60 text-muted-foreground hover:text-foreground"
              }`}
            >
              {t.label} ({t.count})
            </button>
          ))}
        </div>
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="Search email, subject, or message..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>

      {filtered.length === 0 ? (
        <p className="rounded-lg border border-dashed border-border/60 py-12 text-center text-sm text-muted-foreground">
          {emptyMessage}
        </p>
      ) : (
        <div className="space-y-4">
          {filtered.map((email) => (
            <article
              key={email.id}
              className="rounded-xl border border-border/60 bg-card p-4 shadow-sm"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 space-y-1">
                  <p className="font-semibold">{email.to_email}</p>
                  <p className="text-xs text-muted-foreground">{emailStatusLabel(email)}</p>
                  {email.follow_up_step > 0 && (
                    <p className="text-xs text-muted-foreground">
                      Follow-up step #{email.follow_up_step}
                    </p>
                  )}
                </div>
                <Badge variant={statusVariant(emailBadgeLabel(email))}>
                  {emailBadgeLabel(email)}
                </Badge>
              </div>
              <h3 className="mt-3 text-sm font-medium">{email.subject}</h3>
              <pre className="mt-2 max-h-64 overflow-y-auto whitespace-pre-wrap rounded-lg bg-muted/40 p-4 text-sm font-sans leading-relaxed">
                {email.body_text}
              </pre>
              {email.error_message && (
                <p className="mt-2 text-xs text-destructive">{email.error_message}</p>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
