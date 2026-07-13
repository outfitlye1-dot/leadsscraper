"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import type { Lead, LeadStatus } from "@/lib/types";
import type { LeadCreatePayload } from "@/hooks/useLeads";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";

const STATUSES: LeadStatus[] = [
  "new",
  "contacted",
  "interested",
  "follow_up",
  "closed",
  "lost",
];

interface LeadFormModalProps {
  open: boolean;
  lead?: Lead | null;
  onClose: () => void;
  onSubmit: (data: LeadCreatePayload) => Promise<void>;
  isSubmitting?: boolean;
}

const emptyForm: LeadCreatePayload = {
  company_name: "",
  status: "new",
};

export function LeadFormModal({ open, lead, onClose, onSubmit, isSubmitting }: LeadFormModalProps) {
  const [form, setForm] = useState<LeadCreatePayload>(emptyForm);

  useEffect(() => {
    if (lead) {
      setForm({
        company_name: lead.company_name,
        contact_name: lead.contact_name || undefined,
        phone: lead.phone || undefined,
        email: lead.email || undefined,
        website: lead.website || undefined,
        linkedin_url: lead.linkedin_url || undefined,
        facebook_url: lead.facebook_url || undefined,
        instagram_url: lead.instagram_url || undefined,
        address: lead.address || undefined,
        postal_code: lead.postal_code || undefined,
        city: lead.city || undefined,
        country: lead.country || undefined,
        industry: lead.industry || undefined,
        category: lead.category || undefined,
        source: lead.source || undefined,
        notes: lead.notes || undefined,
        status: lead.status,
      });
    } else {
      setForm(emptyForm);
    }
  }, [lead, open]);

  if (!open) return null;

  const set = (key: keyof LeadCreatePayload, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value || undefined }));
  };

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/40" onClick={onClose} />
      <div className="fixed left-1/2 top-1/2 z-50 max-h-[90vh] w-full max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-lg border border-border bg-background p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{lead ? "Edit lead" : "Add lead"}</h2>
          <Button variant="ghost" size="sm" onClick={onClose} className="h-8 w-8 p-0">
            <X className="h-4 w-4" />
          </Button>
        </div>

        <form
          className="space-y-3"
          onSubmit={async (e) => {
            e.preventDefault();
            await onSubmit(form);
          }}
        >
          <div className="space-y-1">
            <Label>Company name *</Label>
            <Input
              required
              value={form.company_name}
              onChange={(e) => set("company_name", e.target.value)}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>Contact</Label>
              <Input value={form.contact_name || ""} onChange={(e) => set("contact_name", e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label>Phone</Label>
              <Input value={form.phone || ""} onChange={(e) => set("phone", e.target.value)} />
            </div>
          </div>
          <div className="space-y-1">
            <Label>Email</Label>
            <Input type="email" value={form.email || ""} onChange={(e) => set("email", e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label>Website</Label>
            <Input value={form.website || ""} onChange={(e) => set("website", e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label>LinkedIn URL</Label>
            <Input value={form.linkedin_url || ""} onChange={(e) => set("linkedin_url", e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>Facebook</Label>
              <Input value={form.facebook_url || ""} onChange={(e) => set("facebook_url", e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label>Instagram</Label>
              <Input value={form.instagram_url || ""} onChange={(e) => set("instagram_url", e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>City</Label>
              <Input value={form.city || ""} onChange={(e) => set("city", e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label>Country</Label>
              <Input value={form.country || ""} onChange={(e) => set("country", e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>Industry</Label>
              <Input value={form.industry || ""} onChange={(e) => set("industry", e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label>Source</Label>
              <Input value={form.source || ""} onChange={(e) => set("source", e.target.value)} placeholder="manual, meta_ads..." />
            </div>
          </div>
          <div className="space-y-1">
            <Label>Status</Label>
            <Select
              value={form.status || "new"}
              onChange={(e) => setForm((p) => ({ ...p, status: e.target.value as LeadStatus }))}
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s.replace("_", " ")}
                </option>
              ))}
            </Select>
          </div>
          <div className="space-y-1">
            <Label>Notes</Label>
            <Textarea rows={3} value={form.notes || ""} onChange={(e) => set("notes", e.target.value)} />
          </div>
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : lead ? "Update lead" : "Create lead"}
          </Button>
        </form>
      </div>
    </>
  );
}
