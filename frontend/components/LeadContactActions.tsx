"use client";

import { Facebook, Globe, Instagram, Linkedin, Mail, MessageCircle, Sparkles } from "lucide-react";
import type { Lead } from "@/lib/types";
import { Button } from "@/components/ui/Button";

interface LeadContactActionsProps {
  lead: Lead;
  compact?: boolean;
}

function openLink(url: string) {
  window.open(url, "_blank", "noopener,noreferrer");
}

export function LeadContactActions({ lead, compact }: LeadContactActionsProps) {
  const links = lead.contact_links;
  if (!links) return <span className="text-xs text-muted-foreground">—</span>;

  const btn = (url: string | null, icon: React.ReactNode, label: string, variant: "default" | "outline" = "outline") => {
    if (!url) return null;
    return (
      <Button
        type="button"
        size="sm"
        variant={variant}
        className={compact ? "h-8 px-2" : "h-8 gap-1 px-2"}
        title={label}
        onClick={() => openLink(url)}
      >
        {icon}
        {!compact && <span className="text-xs">{label}</span>}
      </Button>
    );
  };

  const offerUrl = links.website_offer_whatsapp_url || links.website_offer_email_url;

  return (
    <div className="flex flex-wrap items-center gap-1">
      {btn(links.whatsapp_url, <MessageCircle className="h-3.5 w-3.5" />, "WhatsApp")}
      {btn(links.email_url, <Mail className="h-3.5 w-3.5" />, "Gmail")}
      {btn(links.linkedin_url, <Linkedin className="h-3.5 w-3.5" />, "LinkedIn")}
      {btn(links.facebook_url, <Facebook className="h-3.5 w-3.5" />, "Facebook")}
      {btn(links.instagram_url, <Instagram className="h-3.5 w-3.5" />, "Instagram")}
      {btn(links.website_url, <Globe className="h-3.5 w-3.5" />, "Website")}
      {links.needs_website_pitch && offerUrl && (
        <Button
          type="button"
          size="sm"
          variant="default"
          className="h-8 gap-1 bg-amber-600 px-2 hover:bg-amber-700"
          title="Offer website build"
          onClick={() => openLink(offerUrl)}
        >
          <Sparkles className="h-3.5 w-3.5" />
          {!compact && <span className="text-xs">Offer Website</span>}
        </Button>
      )}
    </div>
  );
}
