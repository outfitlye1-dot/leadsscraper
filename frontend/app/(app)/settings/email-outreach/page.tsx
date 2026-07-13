"use client";

import Link from "next/link";
import { ArrowLeft, Mail } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { EmailOutreachSettingsForm } from "@/components/email-outreach/EmailOutreachSettingsForm";
import { EmailOutreachSubNav } from "@/components/email-outreach/EmailOutreachSubNav";

export default function EmailOutreachSettingsPage() {
  return (
    <div className="space-y-8">
      <Link
        href="/settings"
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Settings
      </Link>

      <PageHeader
        eyebrow="Email Outreach"
        title="Outreach settings"
        description="Configure automation, limits, working hours, and connected email accounts. Changes apply automatically on the AI Agent page."
      >
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Mail className="h-4 w-4" />
          Synced with AI Agent
        </div>
      </PageHeader>

      <EmailOutreachSubNav />
      <EmailOutreachSettingsForm />
    </div>
  );
}
