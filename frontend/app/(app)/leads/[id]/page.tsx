"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Bookmark, BookmarkMinus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import {
  useDeleteLead,
  useLead,
  useSaveLead,
  useUnsaveLead,
  useUpdateLead,
} from "@/hooks/useLeads";
import { LeadProfileView } from "@/components/LeadProfileView";
import { Button } from "@/components/ui/Button";
import { PageLoader } from "@/components/Loader";
import { PageError } from "@/components/PageError";
import type { LeadStatus } from "@/lib/types";
import { formatApiError } from "@/lib/utils";

export default function LeadProfilePage() {
  const params = useParams();
  const idParam = String(params?.id || "");
  const leadId = Number(idParam);
  const router = useRouter();

  const { data: lead, isLoading, isError, refetch } = useLead(
    Number.isFinite(leadId) && leadId > 0 ? leadId : null
  );
  const updateLead = useUpdateLead();
  const saveLead = useSaveLead();
  const unsaveLead = useUnsaveLead();
  const deleteLead = useDeleteLead();

  const handleSave = async (patch: { status?: LeadStatus; notes?: string }) => {
    if (!lead) return;
    try {
      await updateLead.mutateAsync({ id: lead.id, data: patch });
      toast.success("Lead updated");
    } catch (err: unknown) {
      toast.error(formatApiError(err, "Failed to update lead"));
    }
  };

  const handleToggleSave = async () => {
    if (!lead) return;
    try {
      if (lead.is_saved) {
        await unsaveLead.mutateAsync(lead.id);
        toast.success("Moved back to Leads");
      } else {
        await saveLead.mutateAsync(lead.id);
        toast.success("Lead saved");
      }
      await refetch();
    } catch (err: unknown) {
      toast.error(formatApiError(err, "Failed to update saved state"));
    }
  };

  const handleDelete = async () => {
    if (!lead) return;
    if (!confirm(lead.is_saved ? "Permanently delete this saved lead?" : "Delete this lead?")) {
      return;
    }
    try {
      await deleteLead.mutateAsync({ id: lead.id, saved: lead.is_saved });
      toast.success("Lead deleted");
      router.push(lead.is_saved ? "/leads/saved" : "/leads");
    } catch (err: unknown) {
      toast.error(formatApiError(err, "Failed to delete lead"));
    }
  };

  if (!Number.isFinite(leadId) || leadId <= 0) {
    return <PageError message="Invalid lead id" onRetry={() => router.push("/leads")} />;
  }

  if (isLoading) return <PageLoader />;
  if (isError || !lead) {
    return <PageError message="Lead not found" onRetry={() => void refetch()} />;
  }

  const backHref = lead.is_saved ? "/leads/saved" : "/leads";

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          href={backHref}
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          {lead.is_saved ? "Back to Saved" : "Back to Leads"}
        </Link>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => void handleToggleSave()}
            isLoading={saveLead.isPending || unsaveLead.isPending}
            className="gap-2"
          >
            {lead.is_saved ? (
              <>
                <BookmarkMinus className="h-4 w-4" />
                Unsave
              </>
            ) : (
              <>
                <Bookmark className="h-4 w-4" />
                Save lead
              </>
            )}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => void handleDelete()}
            isLoading={deleteLead.isPending}
            className="gap-2 text-destructive hover:text-destructive"
          >
            <Trash2 className="h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      <LeadProfileView lead={lead} onSave={handleSave} isSaving={updateLead.isPending} />
    </div>
  );
}
