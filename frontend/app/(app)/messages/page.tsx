"use client";

import { useState } from "react";
import Link from "next/link";
import { Loader2, MessageSquare, Trash2 } from "lucide-react";
import { useDeleteMessages, useMessages } from "@/hooks/useMessages";
import { useCampaigns } from "@/hooks/useCampaigns";
import { Table } from "@/components/Table";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { PageHeader } from "@/components/PageHeader";
import { TableSkeleton } from "@/components/Loader";
import { PageError } from "@/components/PageError";
import { capitalize, formatDate } from "@/lib/utils";
import { toast } from "sonner";
import type { Message, MessageType } from "@/lib/types";

export default function MessagesPage() {
  const [page, setPage] = useState(1);
  const [campaignId, setCampaignId] = useState<string>("");
  const [messageType, setMessageType] = useState<string>("");
  const [leadIdFilter, setLeadIdFilter] = useState("");

  const { data: campaigns } = useCampaigns();
  const { data: messages, isLoading, isError, refetch } = useMessages({
    campaign_id: campaignId ? Number(campaignId) : undefined,
    message_type: (messageType as MessageType) || undefined,
    lead_id: leadIdFilter ? Number(leadIdFilter) : undefined,
    page,
    page_size: 15,
  });
  const deleteMessages = useDeleteMessages();

  const hasFilters = Boolean(campaignId || messageType || leadIdFilter);
  const listFilters = {
    campaign_id: campaignId ? Number(campaignId) : undefined,
    message_type: (messageType as MessageType) || undefined,
    lead_id: leadIdFilter ? Number(leadIdFilter) : undefined,
  };

  const handleDeleteAll = async () => {
    const total = messages?.total ?? 0;
    if (total === 0) {
      toast.info("No messages to delete");
      return;
    }
    const label = hasFilters
      ? `Delete all ${total} message${total !== 1 ? "s" : ""} matching your filters?`
      : `Delete all ${total} messages? This cannot be undone.`;
    if (!confirm(label)) return;

    try {
      const result = await deleteMessages.mutateAsync(listFilters);
      setPage(1);
      toast.success(result.message);
    } catch {
      toast.error("Failed to delete messages");
    }
  };

  const columns = [
    { key: "id", header: "ID" },
    {
      key: "campaign_id",
      header: "Campaign",
      render: (m: Message) => {
        const name = campaigns?.find((c) => c.id === m.campaign_id)?.name;
        return name ? <span className="text-sm">{name}</span> : <span className="text-muted-foreground">—</span>;
      },
    },
    {
      key: "lead_id",
      header: "Lead",
      render: (m: Message) =>
        m.lead_id ? (
          <Link href={`/leads`} className="text-sm text-primary hover:underline">
            Lead #{m.lead_id}
          </Link>
        ) : (
          <span className="text-muted-foreground">—</span>
        ),
    },
    {
      key: "message_type",
      header: "Type",
      render: (m: Message) => <Badge>{capitalize(m.message_type)}</Badge>,
    },
    {
      key: "message_content",
      header: "Content",
      render: (m: Message) => (
        <span className="line-clamp-3 max-w-lg text-sm whitespace-pre-wrap">{m.message_content}</span>
      ),
    },
    {
      key: "created_at",
      header: "Date",
      render: (m: Message) => formatDate(m.created_at),
    },
  ];

  const resetFilters = () => {
    setCampaignId("");
    setMessageType("");
    setLeadIdFilter("");
    setPage(1);
  };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Outreach"
        title="Messages"
        description="View all AI-generated outreach messages"
      />

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-4 space-y-0">
          <div>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              All Messages
            </CardTitle>
            <CardDescription>{messages?.total || 0} messages total</CardDescription>
          </div>
          {(messages?.total ?? 0) > 0 ? (
            <Button
              type="button"
              variant="destructive"
              size="sm"
              className="gap-2"
              disabled={deleteMessages.isPending}
              onClick={() => void handleDeleteAll()}
            >
              {deleteMessages.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
              {hasFilters ? "Delete filtered" : "Delete all"}
            </Button>
          ) : null}
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-end gap-4">
            <div className="space-y-2">
              <Label>Campaign</Label>
              <Select
                value={campaignId}
                onChange={(e) => {
                  setCampaignId(e.target.value);
                  setPage(1);
                }}
                className="min-w-[180px]"
              >
                <option value="">All campaigns</option>
                {campaigns?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Type</Label>
              <Select
                value={messageType}
                onChange={(e) => {
                  setMessageType(e.target.value);
                  setPage(1);
                }}
                className="min-w-[140px]"
              >
                <option value="">All types</option>
                <option value="whatsapp">WhatsApp</option>
                <option value="email">Email</option>
                <option value="linkedin">LinkedIn</option>
                <option value="follow_up">Follow-up</option>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Lead ID</Label>
              <Input
                type="number"
                min={1}
                placeholder="e.g. 42"
                value={leadIdFilter}
                onChange={(e) => {
                  setLeadIdFilter(e.target.value);
                  setPage(1);
                }}
                className="min-w-[120px]"
              />
            </div>
            {(campaignId || messageType || leadIdFilter) && (
              <Button variant="outline" size="sm" onClick={resetFilters}>
                Clear filters
              </Button>
            )}
          </div>

          {isLoading ? (
            <TableSkeleton />
          ) : isError ? (
            <PageError message="Failed to load messages" onRetry={() => refetch()} />
          ) : (
            <>
              <Table
                columns={columns}
                data={messages?.items || []}
                keyExtractor={(m) => m.id}
                emptyMessage="No messages found. Generate messages from AI Generator or Campaigns."
              />
              {(messages?.pages || 0) > 1 && (
                <div className="flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    Page {page} of {messages?.pages}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => p - 1)}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= (messages?.pages || 1)}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
