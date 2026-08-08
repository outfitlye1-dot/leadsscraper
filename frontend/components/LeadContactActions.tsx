"use client";

import { Facebook, Globe, Instagram, Linkedin, Mail, MessageCircle, Sparkles } from "lucide-react";
import type { Lead } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { LeadOutreachSendButton } from "@/components/LeadOutreachSendButton";
import { cn } from "@/lib/utils";

interface LeadContactActionsProps {
  lead: Lead;
  compact?: boolean;
  /** Larger primary WhatsApp + Offer Website row for profile drawer */
  profile?: boolean;
}

function openLink(url: string) {
  window.open(url, "_blank", "noopener,noreferrer");
}

export function LeadContactActions({ lead, compact, profile }: LeadContactActionsProps) {
  const links = lead.contact_links;

  if (!links) {
    if (!lead.email) {
      return profile ? (
        <p className="text-sm text-muted-foreground">No WhatsApp or email actions available</p>
      ) : (
        <span className="text-xs text-muted-foreground">—</span>
      );
    }
    return (
      <div className="flex flex-wrap items-center gap-1">
        <LeadOutreachSendButton lead={lead} compact={compact} />
      </div>
    );
  }

  const offerUrl = links.website_offer_whatsapp_url || links.website_offer_email_url;

  if (profile) {
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {links.whatsapp_url ? (
            <Button
              type="button"
              size="lg"
              variant="outline"
              className="h-11 gap-2"
              onClick={() => openLink(links.whatsapp_url!)}
            >
              <MessageCircle className="h-4 w-4" />
              WhatsApp
            </Button>
          ) : null}
          {links.needs_website_pitch && offerUrl ? (
            <Button
              type="button"
              size="lg"
              className="h-11 gap-2 bg-amber-600 text-white hover:bg-amber-700"
              onClick={() => openLink(offerUrl)}
            >
              <Sparkles className="h-4 w-4" />
              Offer Website
            </Button>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <LeadOutreachSendButton lead={lead} compact />
          {links.email_url ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-8 gap-1 px-2"
              title="Email"
              onClick={() => openLink(links.email_url!)}
            >
              <Mail className="h-3.5 w-3.5" />
              <span className="text-xs">Email</span>
            </Button>
          ) : null}
          {links.website_url ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-8 gap-1 px-2"
              title="Website"
              onClick={() => openLink(links.website_url!)}
            >
              <Globe className="h-3.5 w-3.5" />
              <span className="text-xs">Website</span>
            </Button>
          ) : null}
          {links.linkedin_url ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-8 px-2"
              title="LinkedIn"
              onClick={() => openLink(links.linkedin_url!)}
            >
              <Linkedin className="h-3.5 w-3.5" />
            </Button>
          ) : null}
          {links.facebook_url ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-8 px-2"
              title="Facebook"
              onClick={() => openLink(links.facebook_url!)}
            >
              <Facebook className="h-3.5 w-3.5" />
            </Button>
          ) : null}
          {links.instagram_url ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-8 px-2"
              title="Instagram"
              onClick={() => openLink(links.instagram_url!)}
            >
              <Instagram className="h-3.5 w-3.5" />
            </Button>
          ) : null}
        </div>
        {lead.phone ? (
          <p className="text-sm text-muted-foreground">
            Phone <span className="font-medium text-foreground">{lead.phone}</span>
          </p>
        ) : null}
      </div>
    );
  }

  const btn = (
    url: string | null,
    icon: React.ReactNode,
    label: string,
    variant: "default" | "outline" = "outline",
    className?: string
  ) => {
    if (!url) return null;
    return (
      <Button
        type="button"
        size="sm"
        variant={variant}
        className={cn(compact ? "h-8 px-2" : "h-8 gap-1 px-2", className)}
        title={label}
        onClick={() => openLink(url)}
      >
        {icon}
        {!compact && <span className="text-xs">{label}</span>}
      </Button>
    );
  };

  return (
    <div className="flex flex-wrap items-center gap-1">
      <LeadOutreachSendButton lead={lead} compact={compact} />
      {btn(links.whatsapp_url, <MessageCircle className="h-3.5 w-3.5" />, "WhatsApp")}
      {btn(links.email_url, <Mail className="h-3.5 w-3.5" />, "Gmail")}
      {btn(links.linkedin_url, <Linkedin className="h-3.5 w-3.5" />, "LinkedIn")}
      {btn(links.facebook_url, <Facebook className="h-3.5 w-3.5" />, "Facebook")}
      {btn(links.instagram_url, <Instagram className="h-3.5 w-3.5" />, "Instagram")}
      {btn(links.website_url, <Globe className="h-3.5 w-3.5" />, "Website")}
      {links.needs_website_pitch && offerUrl
        ? btn(
            offerUrl,
            <Sparkles className="h-3.5 w-3.5" />,
            "Offer Website",
            "default",
            "bg-amber-600 hover:bg-amber-700"
          )
        : null}
    </div>
  );
}
