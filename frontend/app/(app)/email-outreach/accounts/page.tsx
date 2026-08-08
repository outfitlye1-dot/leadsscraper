"use client";

import { PageHeader } from "@/components/PageHeader";
import { EmailAccountsSection } from "@/components/email-outreach/EmailAccountsSection";
import { EmailOutreachSubNav } from "@/components/email-outreach/EmailOutreachSubNav";

export default function EmailOutreachAccountsPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Email Outreach"
        title="Email accounts"
        description="Connect Gmail, Outlook, or SMTP for your AI Agent. Send limits and automation are managed by your admin."
      />
      <EmailOutreachSubNav />
      <EmailAccountsSection />
    </div>
  );
}
