"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Bot,
  CheckCircle2,
  Edit2,
  ExternalLink,
  Megaphone,
  Pause,
  Play,
  Plus,
  Rocket,
  Trash2,
  Users,
  X,
} from "lucide-react";
import { toast } from "sonner";
import {
  useCampaigns,
  useCreateCampaign,
  useDeleteCampaign,
  useRunCampaign,
  useUpdateCampaign,
} from "@/hooks/useCampaigns";
import { useMessages } from "@/hooks/useMessages";
import { Table } from "@/components/Table";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/PageHeader";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { TableSkeleton } from "@/components/Loader";
import { PageError } from "@/components/PageError";
import { capitalize, formatDate } from "@/lib/utils";
import type { Campaign, CampaignRunResponse, CampaignStatus, Message } from "@/lib/types";

const createSchema = z.object({
  name: z.string().min(1, "Name is required"),
  message_type: z.enum(["whatsapp", "email", "linkedin", "follow_up"]),
});

const editSchema = createSchema.extend({
  status: z.enum(["draft", "active", "paused", "completed"]),
});

type CreateFormData = z.infer<typeof createSchema>;
type EditFormData = z.infer<typeof editSchema>;

const LEAD_STATUSES = ["new", "contacted", "interested", "follow_up", "closed", "lost"] as const;

function statusVariant(status: CampaignStatus): "default" | "secondary" | "success" | "warning" | "destructive" {
  switch (status) {
    case "active":
      return "success";
    case "paused":
      return "warning";
    case "completed":
      return "secondary";
    default:
      return "default";
  }
}

export default function CampaignsPage() {
  const [activeCampaignId, setActiveCampaignId] = useState<number | null>(null);
  const [editingCampaign, setEditingCampaign] = useState<Campaign | null>(null);
  const [messagePage, setMessagePage] = useState(1);
  const [runResult, setRunResult] = useState<CampaignRunResponse | null>(null);
  const [leadStatus, setLeadStatus] = useState<string>("new");
  const [runLimit, setRunLimit] = useState(10);
  const [skipExisting, setSkipExisting] = useState(true);

  const { data: campaigns, isLoading, isError, refetch } = useCampaigns();
  const { data: messages, isLoading: messagesLoading } = useMessages({
    campaign_id: activeCampaignId || undefined,
    page: messagePage,
    page_size: 10,
  });
  const createCampaign = useCreateCampaign();
  const updateCampaign = useUpdateCampaign();
  const deleteCampaign = useDeleteCampaign();
  const runCampaign = useRunCampaign();

  const activeCampaign = campaigns?.find((c) => c.id === activeCampaignId) || null;

  const stats = useMemo(() => {
    const list = campaigns || [];
    return {
      total: list.length,
      active: list.filter((c) => c.status === "active").length,
      draft: list.filter((c) => c.status === "draft").length,
      paused: list.filter((c) => c.status === "paused").length,
      completed: list.filter((c) => c.status === "completed").length,
      totalMessages: list.reduce((sum, c) => sum + (c.message_count || 0), 0),
    };
  }, [campaigns]);

  const createForm = useForm<CreateFormData>({
    resolver: zodResolver(createSchema),
    defaultValues: { message_type: "whatsapp" },
  });

  const editForm = useForm<EditFormData>({ resolver: zodResolver(editSchema) });

  const openEdit = (campaign: Campaign) => {
    setEditingCampaign(campaign);
    editForm.reset({
      name: campaign.name,
      message_type: campaign.message_type,
      status: campaign.status,
    });
  };

  const onCreate = async (data: CreateFormData) => {
    try {
      const created = await createCampaign.mutateAsync(data);
      createForm.reset({ message_type: "whatsapp" });
      setActiveCampaignId(created.id);
      toast.success("Campaign created — ab run kar sakte ho");
    } catch {
      toast.error("Failed to create campaign");
    }
  };

  const onEdit = async (data: EditFormData) => {
    if (!editingCampaign) return;
    try {
      await updateCampaign.mutateAsync({ id: editingCampaign.id, ...data });
      setEditingCampaign(null);
      toast.success("Campaign updated");
    } catch {
      toast.error("Failed to update campaign");
    }
  };

  const handleStatusChange = async (id: number, status: CampaignStatus) => {
    try {
      await updateCampaign.mutateAsync({ id, status });
      toast.success(`Campaign ${status}`);
    } catch {
      toast.error("Failed to update status");
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this campaign?")) return;
    try {
      await deleteCampaign.mutateAsync(id);
      if (activeCampaignId === id) setActiveCampaignId(null);
      if (editingCampaign?.id === id) setEditingCampaign(null);
      toast.success("Campaign deleted");
    } catch {
      toast.error("Failed to delete campaign");
    }
  };

  const handleRun = async () => {
    if (!activeCampaignId) {
      toast.error("Pehle campaign select karein");
      return;
    }
    try {
      const result = await runCampaign.mutateAsync({
        id: activeCampaignId,
        lead_status: leadStatus,
        limit: runLimit,
        skip_existing: skipExisting,
      });
      setRunResult(result);
      setMessagePage(1);
      toast.success(`${result.generated} messages generate ho gaye`);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Campaign run failed";
      toast.error(message);
    }
  };

  const messageColumns = [
    { key: "id", header: "ID" },
    {
      key: "lead_id",
      header: "Lead",
      render: (m: Message) => (m.lead_id ? `#${m.lead_id}` : "—"),
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
        <span className="line-clamp-2 max-w-md text-sm">{m.message_content}</span>
      ),
    },
    {
      key: "created_at",
      header: "Date",
      render: (m: Message) => formatDate(m.created_at),
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Outreach"
        title="Campaigns"
        description="Create campaigns, select leads, and run AI-powered messages at scale"
      >
        <Link href="/ai">
          <Button variant="outline" className="gap-2">
            <Bot className="h-4 w-4" />
            Single Message AI
          </Button>
        </Link>
      </PageHeader>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
        {[
          { label: "Total", value: stats.total },
          { label: "Active", value: stats.active },
          { label: "Draft", value: stats.draft },
          { label: "Paused", value: stats.paused },
          { label: "Done", value: stats.completed },
          { label: "Messages", value: stats.totalMessages },
        ].map((s) => (
          <Card key={s.label}>
            <CardContent className="pt-5">
              <p className="text-xs text-muted-foreground">{s.label}</p>
              <p className="text-xl font-bold">{s.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5" />
              New Campaign
            </CardTitle>
            <CardDescription>Kis type ki outreach chalani hai?</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={createForm.handleSubmit(onCreate)} className="space-y-4">
              <div className="space-y-2">
                <Label>Campaign Name</Label>
                <Input placeholder="WhatsApp Q1 Outreach" {...createForm.register("name")} />
              </div>
              <div className="space-y-2">
                <Label>Channel / Message Type</Label>
                <Select {...createForm.register("message_type")}>
                  <option value="whatsapp">WhatsApp</option>
                  <option value="email">Email</option>
                  <option value="linkedin">LinkedIn</option>
                  <option value="follow_up">Follow-up</option>
                </Select>
              </div>
              <Button type="submit" className="w-full" isLoading={createCampaign.isPending}>
                Create Campaign
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Megaphone className="h-5 w-5" />
              Select Campaign
            </CardTitle>
            <CardDescription>Konsi campaign chalani hai — select karein</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {isLoading ? (
              <TableSkeleton />
            ) : isError ? (
              <PageError message="Failed to load campaigns" onRetry={() => refetch()} />
            ) : !campaigns?.length ? (
              <p className="text-sm text-muted-foreground">Pehle campaign create karein</p>
            ) : (
              campaigns.map((c) => {
                const selected = activeCampaignId === c.id;
                return (
                  <div
                    key={c.id}
                    className={`rounded-lg border p-4 transition-colors ${
                      selected ? "border-primary bg-primary/5" : "border-border hover:bg-muted/30"
                    }`}
                  >
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <button
                        type="button"
                        className="min-w-0 flex-1 text-left"
                        onClick={() => {
                          setActiveCampaignId(c.id);
                          setMessagePage(1);
                          setRunResult(null);
                        }}
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="font-semibold">{c.name}</p>
                          <Badge variant={statusVariant(c.status)}>{capitalize(c.status)}</Badge>
                          <Badge>{capitalize(c.message_type)}</Badge>
                        </div>
                        <div className="mt-1 flex flex-wrap gap-3 text-xs text-muted-foreground">
                          <span>{c.message_count || 0} messages</span>
                          <span>{c.eligible_leads || 0} eligible leads</span>
                          <span>Created {formatDate(c.created_at)}</span>
                        </div>
                      </button>
                      <div className="flex flex-wrap gap-1">
                        {c.status !== "active" && c.status !== "completed" && (
                          <Button
                            variant="ghost"
                            size="sm"
                            title="Start"
                            onClick={() => handleStatusChange(c.id, "active")}
                          >
                            <Play className="h-4 w-4 text-emerald-600" />
                          </Button>
                        )}
                        {c.status === "active" && (
                          <Button
                            variant="ghost"
                            size="sm"
                            title="Pause"
                            onClick={() => handleStatusChange(c.id, "paused")}
                          >
                            <Pause className="h-4 w-4 text-amber-600" />
                          </Button>
                        )}
                        <Button variant="ghost" size="sm" onClick={() => openEdit(c)}>
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleDelete(c.id)}>
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>
      </div>

      {activeCampaign && (
        <Card className="border-primary/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Rocket className="h-5 w-5 text-primary" />
              Run Campaign — {activeCampaign.name}
            </CardTitle>
            <CardDescription>
              {capitalize(activeCampaign.message_type)} messages AI se generate hongi selected leads par
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-2">
                <Label>Lead Status</Label>
                <Select value={leadStatus} onChange={(e) => setLeadStatus(e.target.value)}>
                  {LEAD_STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {capitalize(s)}
                    </option>
                  ))}
                </Select>
                <p className="text-xs text-muted-foreground">Kis status wale leads par chalana hai</p>
              </div>
              <div className="space-y-2">
                <Label>Max Leads</Label>
                <Input
                  type="number"
                  min={1}
                  max={100}
                  value={runLimit}
                  onChange={(e) => setRunLimit(Number(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label>Options</Label>
                <label className="flex cursor-pointer items-center gap-2 rounded-md border p-3 text-sm">
                  <input
                    type="checkbox"
                    checked={skipExisting}
                    onChange={(e) => setSkipExisting(e.target.checked)}
                  />
                  Skip already messaged leads
                </label>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3 rounded-lg bg-muted/40 p-3 text-sm">
              <Users className="h-4 w-4 text-primary" />
              <span>
                <strong>{activeCampaign.eligible_leads || 0}</strong> leads ready for{" "}
                {capitalize(activeCampaign.message_type)}
              </span>
              <Badge variant={statusVariant(activeCampaign.status)}>
                {capitalize(activeCampaign.status)}
              </Badge>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                onClick={handleRun}
                isLoading={runCampaign.isPending}
                className="gap-2"
                disabled={activeCampaign.status === "completed"}
              >
                <Rocket className="h-4 w-4" />
                Run Campaign Now
              </Button>
              {activeCampaign.status === "active" && (
                <Button
                  variant="outline"
                  onClick={() => handleStatusChange(activeCampaign.id, "completed")}
                >
                  Mark Completed
                </Button>
              )}
            </div>

            {activeCampaign.status === "completed" && (
              <p className="text-sm text-amber-600">
                Ye campaign complete ho chuki hai. Dubara chalane ke liye status draft/active karein.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {runResult && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-emerald-500" />
              Run Results
            </CardTitle>
            <CardDescription>
              {runResult.generated} generated · {runResult.skipped} skipped · {runResult.failed} failed
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {runResult.results
              .filter((r) => r.success)
              .map((r) => (
                <div key={r.lead_id} className="rounded-lg border bg-muted/20 p-3 text-sm">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span className="font-medium">{r.company_name}</span>
                    {r.whatsapp_url && (
                      <a
                        href={r.whatsapp_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-primary hover:underline"
                      >
                        Open WhatsApp
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                  <p className="whitespace-pre-wrap text-xs text-muted-foreground">{r.message_preview}</p>
                </div>
              ))}
            {runResult.failed > 0 && (
              <div className="space-y-1">
                <p className="text-xs font-medium text-destructive">Failed / Skipped</p>
                {runResult.results
                  .filter((r) => !r.success)
                  .map((r) => (
                    <p key={`err-${r.lead_id}`} className="text-xs text-muted-foreground">
                      {r.company_name}: {r.error}
                    </p>
                  ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {editingCampaign && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Edit — {editingCampaign.name}</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => setEditingCampaign(null)}>
              <X className="h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent>
            <form onSubmit={editForm.handleSubmit(onEdit)} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-2">
                <Label>Name</Label>
                <Input {...editForm.register("name")} />
              </div>
              <div className="space-y-2">
                <Label>Type</Label>
                <Select {...editForm.register("message_type")}>
                  <option value="whatsapp">WhatsApp</option>
                  <option value="email">Email</option>
                  <option value="linkedin">LinkedIn</option>
                  <option value="follow_up">Follow-up</option>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Status</Label>
                <Select {...editForm.register("status")}>
                  <option value="draft">Draft</option>
                  <option value="active">Active</option>
                  <option value="paused">Paused</option>
                  <option value="completed">Completed</option>
                </Select>
              </div>
              <div className="flex items-end gap-2">
                <Button type="submit" isLoading={updateCampaign.isPending}>
                  Save
                </Button>
                <Button type="button" variant="outline" onClick={() => setEditingCampaign(null)}>
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {activeCampaign && (
        <Card>
          <CardHeader>
            <CardTitle>Message History — {activeCampaign.name}</CardTitle>
            <CardDescription>{messages?.total || 0} messages in this campaign</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {messagesLoading ? (
              <TableSkeleton />
            ) : (
              <>
                <Table
                  columns={messageColumns}
                  data={messages?.items || []}
                  keyExtractor={(m) => m.id}
                  emptyMessage="Abhi koi message nahi. Run Campaign dabao."
                />
                {(messages?.pages || 0) > 1 && (
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-muted-foreground">
                      Page {messagePage} of {messages?.pages}
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={messagePage <= 1}
                        onClick={() => setMessagePage((p) => p - 1)}
                      >
                        Previous
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={messagePage >= (messages?.pages || 1)}
                        onClick={() => setMessagePage((p) => p + 1)}
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
      )}
    </div>
  );
}
