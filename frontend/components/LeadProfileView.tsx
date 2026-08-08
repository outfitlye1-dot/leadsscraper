"use client";

import { useEffect, useState } from "react";
import {
  Building2,
  Clock,
  Globe,
  MapPin,
  Phone,
  Sparkles,
  Target,
} from "lucide-react";
import type { Lead, LeadStatus } from "@/lib/types";
import { LeadContactActions } from "@/components/LeadContactActions";
import { IntentBadge, LeadStatusBadge, QualityBadge } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/Button";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { formatDate } from "@/lib/utils";

const STATUSES: LeadStatus[] = [
  "new",
  "contacted",
  "interested",
  "follow_up",
  "closed",
  "lost",
];

function ScoreCard({
  label,
  value,
  suffix = "",
}: {
  label: string;
  value: number | null | undefined;
  suffix?: string;
}) {
  if (value == null) return null;
  return (
    <div className="rounded-lg border border-border/60 bg-muted/15 px-3 py-2.5">
      <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="mt-0.5 text-lg font-semibold tabular-nums">
        {value}
        {suffix}
      </p>
    </div>
  );
}

type Props = {
  lead: Lead;
  onSave: (data: { status?: LeadStatus; notes?: string }) => Promise<void>;
  isSaving?: boolean;
  onEditFull?: () => void;
};

export function LeadProfileView({ lead, onSave, isSaving, onEditFull }: Props) {
  const [status, setStatus] = useState<LeadStatus>(lead.status);
  const [notes, setNotes] = useState(lead.notes || "");

  useEffect(() => {
    setStatus(lead.status);
    setNotes(lead.notes || "");
  }, [lead]);

  const timeline = [
    { label: "Added", date: lead.created_at },
    lead.saved_at ? { label: "Saved", date: lead.saved_at } : null,
    { label: "Updated", date: lead.updated_at },
  ].filter(Boolean) as { label: string; date: string }[];

  const socialLinks = [
    { label: "LinkedIn", url: lead.linkedin_url },
    { label: "Facebook", url: lead.facebook_url },
    { label: "Instagram", url: lead.instagram_url },
  ].filter((s) => s.url);

  const locationLine = [lead.address, lead.city, lead.postal_code, lead.country]
    .filter(Boolean)
    .join(", ");

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center gap-2">
          <Building2 className="h-5 w-5 shrink-0 text-muted-foreground" />
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            {lead.company_name}
          </h1>
        </div>
        {lead.contact_name ? (
          <p className="mt-1 text-sm text-muted-foreground">{lead.contact_name}</p>
        ) : null}
        <div className="mt-3 flex flex-wrap gap-1.5">
          <LeadStatusBadge status={lead.status} />
          <QualityBadge tier={lead.quality_tier} />
          <IntentBadge intent={lead.intent_tier} />
          {lead.whatsapp_ready ? (
            <span className="inline-flex items-center rounded-md border border-emerald-500/20 bg-emerald-500/5 px-2 py-0.5 text-[11px] font-medium text-emerald-700 dark:text-emerald-400">
              WhatsApp ready
            </span>
          ) : null}
          {lead.is_saved ? (
            <span className="inline-flex items-center rounded-md border border-border/60 bg-muted/30 px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
              Saved
            </span>
          ) : null}
        </div>
      </div>

      <section className="space-y-3 rounded-2xl border border-border/60 bg-card p-5">
        <h2 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Outreach
        </h2>
        <LeadContactActions lead={lead} profile />
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-border/60 bg-card p-5">
          <h2 className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Profile
          </h2>
          <div className="space-y-2.5 text-sm">
            {lead.phone ? (
              <p className="flex items-center gap-2">
                <Phone className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="font-medium">{lead.phone}</span>
              </p>
            ) : null}
            {lead.email ? (
              <p className="flex items-center gap-2">
                <span className="w-4 text-center text-muted-foreground">@</span>
                <span className="break-all font-medium">{lead.email}</span>
              </p>
            ) : null}
            {locationLine ? (
              <p className="flex items-start gap-2">
                <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                <span>{locationLine}</span>
              </p>
            ) : null}
            {lead.website && lead.contact_links?.website_url ? (
              <p className="flex items-start gap-2">
                <Globe className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                <a
                  href={lead.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="break-all text-primary hover:underline"
                >
                  {lead.website}
                </a>
              </p>
            ) : (
              <p className="text-xs text-amber-700 dark:text-amber-400">
                No website — Offer Website pitch available
              </p>
            )}
            {lead.category || lead.industry ? (
              <p className="text-muted-foreground">
                {[lead.category, lead.industry].filter(Boolean).join(" · ")}
              </p>
            ) : null}
            {lead.source ? (
              <p className="text-xs text-muted-foreground">Source: {lead.source}</p>
            ) : null}
          </div>
        </section>

        <section className="rounded-2xl border border-border/60 bg-card p-5">
          <h2 className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Intelligence
          </h2>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            <ScoreCard label="Quality" value={lead.quality_score} />
            <ScoreCard label="Buying intent" value={lead.buying_intent_score} />
            <ScoreCard label="Website" value={lead.website_quality_score} />
            <ScoreCard label="Google profile" value={lead.google_profile_score} />
            <ScoreCard label="Social" value={lead.social_activity_score} />
            {lead.rating != null ? (
              <ScoreCard
                label="Rating"
                value={lead.rating}
                suffix={` · ${lead.reviews_count ?? 0} reviews`}
              />
            ) : null}
          </div>
        </section>
      </div>

      {(lead.recommended_offer || lead.ai_qualification || lead.qualification_reason) && (
        <section className="rounded-2xl border border-border/60 bg-muted/10 p-5">
          <div className="mb-2 flex items-center gap-2 text-sm font-medium">
            <Sparkles className="h-4 w-4 text-muted-foreground" />
            AI recommendations
          </div>
          {lead.ai_qualification ? (
            <p className="text-sm capitalize">{lead.ai_qualification}</p>
          ) : null}
          {lead.recommended_offer ? (
            <p className="mt-2 text-sm text-muted-foreground">
              <span className="font-medium text-foreground">Offer:</span> {lead.recommended_offer}
            </p>
          ) : null}
          {lead.qualification_reason ? (
            <p className="mt-1 text-xs text-muted-foreground">{lead.qualification_reason}</p>
          ) : null}
        </section>
      )}

      {socialLinks.length > 0 ? (
        <section className="rounded-2xl border border-border/60 bg-card p-5">
          <h2 className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Social profiles
          </h2>
          <div className="flex flex-wrap gap-2">
            {socialLinks.map((s) => (
              <a
                key={s.label}
                href={s.url!}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-lg border border-border/60 px-3 py-1.5 text-xs font-medium transition-colors hover:bg-muted/50"
              >
                {s.label}
              </a>
            ))}
          </div>
        </section>
      ) : null}

      {lead.website_problems && lead.website_problems.length > 0 ? (
        <section className="rounded-2xl border border-border/60 bg-card p-5">
          <h2 className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Website audit
          </h2>
          <ul className="space-y-1.5 text-sm text-muted-foreground">
            {lead.website_problems.map((problem) => (
              <li key={problem} className="flex gap-2">
                <Target className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                {problem}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-border/60 bg-card p-5">
          <h2 className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            <Clock className="h-3.5 w-3.5" />
            Activity
          </h2>
          <ol className="relative space-y-4 border-l border-border pl-4">
            {timeline.map((item) => (
              <li key={item.label} className="relative">
                <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full bg-foreground/30" />
                <p className="text-sm font-medium">{item.label}</p>
                <p className="text-xs text-muted-foreground">{formatDate(item.date)}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="space-y-4 rounded-2xl border border-border/60 bg-card p-5">
          <div className="space-y-2">
            <Label>Status</Label>
            <Select value={status} onChange={(e) => setStatus(e.target.value as LeadStatus)}>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s.replace("_", " ")}
                </option>
              ))}
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Notes</Label>
            <Textarea
              rows={5}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Outreach notes, follow-up reminders..."
            />
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            {onEditFull ? (
              <Button variant="outline" className="flex-1" onClick={onEditFull}>
                Edit all fields
              </Button>
            ) : null}
            <Button
              className="flex-1"
              disabled={isSaving}
              onClick={() => void onSave({ status, notes })}
            >
              {isSaving ? "Saving..." : "Save changes"}
            </Button>
          </div>
        </section>
      </div>
    </div>
  );
}
