"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Bot, Copy, FileUp, RefreshCw, Sparkles, User } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { useSavedLeads } from "@/hooks/useLeads";
import { useCampaigns } from "@/hooks/useCampaigns";
import type { CVProfile, GenerateMessageResponse, MessageType } from "@/lib/types";
import { formatApiError } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { PageHeader } from "@/components/PageHeader";
import { PageLoader } from "@/components/Loader";
import { Skeleton } from "@/components/Loader";
import { cn } from "@/lib/utils";

const messageTypes: { value: MessageType; label: string }[] = [
  { value: "whatsapp", label: "WhatsApp" },
  { value: "email", label: "Email" },
  { value: "linkedin", label: "LinkedIn" },
  { value: "follow_up", label: "Follow-up" },
];

const tones = ["Professional", "Friendly", "Direct", "Consultative"];
const languages = ["English", "Roman Urdu", "Urdu"];

export default function AIPage() {
  const [leadId, setLeadId] = useState("");
  const [messageType, setMessageType] = useState<MessageType>("whatsapp");
  const [campaignId, setCampaignId] = useState("");
  const [tone, setTone] = useState("Professional");
  const [language, setLanguage] = useState("English");
  const [generatedMessage, setGeneratedMessage] = useState("");

  const { data: savedLeadsData, isLoading: leadsLoading } = useSavedLeads({ page_size: 100 });
  const leads = savedLeadsData?.items ?? [];
  const { data: campaigns } = useCampaigns();

  const { data: cvProfile } = useQuery({
    queryKey: ["cv-profile"],
    queryFn: async () => {
      const { data } = await api.get<CVProfile | null>("/cv/profile");
      return data;
    },
    retry: false,
  });

  const generateMutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post<GenerateMessageResponse>(
        "/ai/generate",
        {
          lead_id: Number(leadId),
          message_type: messageType,
          campaign_id: campaignId ? Number(campaignId) : undefined,
        },
        { timeout: 60000 }
      );
      return data;
    },
    onSuccess: (data) => {
      setGeneratedMessage(data.message);
      toast.success("Message generated!");
    },
    onError: (err: unknown) => {
      toast.error(formatApiError(err, "Generation failed. Upload a CV or set up AI Brain first."));
    },
  });

  const copyToClipboard = () => {
    navigator.clipboard.writeText(generatedMessage);
    toast.success("Copied to clipboard");
  };

  if (leadsLoading) return <PageLoader />;

  const selectedLead = leads.find((l) => String(l.id) === leadId);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        eyebrow="AI"
        title="Message Generator"
        description="Chat-style outreach assistant powered by your CV and AI Brain"
      />

      {!cvProfile && (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="flex flex-wrap items-center gap-3 p-4">
            <FileUp className="h-5 w-5 text-amber-600" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">CV required for AI messages</p>
              <p className="text-xs text-muted-foreground">
                Upload your CV on{" "}
                <Link href="/brain" className="text-primary hover:underline">
                  CV & Brain
                </Link>{" "}
                for personalized outreach.
              </p>
            </div>
            <Link href="/brain#cv-upload">
              <Button size="sm" variant="outline">
                Open CV & Brain
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      <Card className="overflow-hidden">
        <CardHeader className="border-b border-border/60 bg-muted/10">
          <CardTitle className="flex items-center gap-2 text-base">
            <Bot className="h-5 w-5" />
            Compose
          </CardTitle>
          <CardDescription>Pick a lead, tune tone, and generate</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 p-0">
          <div className="max-h-[min(50vh,420px)] space-y-4 overflow-y-auto p-5">
            {selectedLead ? (
              <div className="flex gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border bg-muted/50">
                  <User className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="rounded-2xl rounded-tl-md border border-border/60 bg-muted/20 px-4 py-3 text-sm">
                  Generate a {messageType.replace("_", " ")} message for{" "}
                  <span className="font-medium">{selectedLead.company_name}</span>
                  {tone !== "Professional" ? ` in a ${tone.toLowerCase()} tone` : ""}
                  {language !== "English" ? ` (${language})` : ""}.
                </div>
              </div>
            ) : (
              <p className="text-center text-sm text-muted-foreground">
                Select a saved lead below to start
              </p>
            )}

            {generateMutation.isPending ? (
              <div className="flex gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border bg-foreground text-background">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="flex-1 space-y-2 rounded-2xl rounded-tl-md border border-border/60 bg-card px-4 py-3">
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-5/6" />
                  <Skeleton className="h-3 w-4/6" />
                </div>
              </div>
            ) : null}

            {generatedMessage ? (
              <div className="flex gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border bg-foreground text-background">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1 rounded-2xl rounded-tl-md border border-border/60 bg-card px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap">
                  {generatedMessage}
                </div>
              </div>
            ) : null}
          </div>

          <div className="space-y-4 border-t border-border/60 bg-muted/5 p-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2 sm:col-span-2">
                <Label>Saved lead</Label>
                <Select value={leadId} onChange={(e) => setLeadId(e.target.value)}>
                  <option value="">Choose a saved lead...</option>
                  {leads.map((lead) => (
                    <option key={lead.id} value={lead.id}>
                      {lead.company_name} {lead.contact_name ? `— ${lead.contact_name}` : ""}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Platform</Label>
                <Select
                  value={messageType}
                  onChange={(e) => setMessageType(e.target.value as MessageType)}
                >
                  {messageTypes.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Campaign</Label>
                <Select value={campaignId} onChange={(e) => setCampaignId(e.target.value)}>
                  <option value="">Optional</option>
                  {campaigns?.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Tone</Label>
                <Select value={tone} onChange={(e) => setTone(e.target.value)}>
                  {tones.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Language</Label>
                <Select value={language} onChange={(e) => setLanguage(e.target.value)}>
                  {languages.map((l) => (
                    <option key={l} value={l}>
                      {l}
                    </option>
                  ))}
                </Select>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                className="flex-1 sm:flex-none"
                onClick={() => generateMutation.mutate()}
                disabled={!leadId || !cvProfile}
                isLoading={generateMutation.isPending}
              >
                <Sparkles className="h-4 w-4" />
                Generate
              </Button>
              {generatedMessage ? (
                <>
                  <Button variant="outline" onClick={copyToClipboard}>
                    <Copy className="h-4 w-4" />
                    Copy
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => generateMutation.mutate()}
                    disabled={!leadId || !cvProfile || generateMutation.isPending}
                  >
                    <RefreshCw className={cn("h-4 w-4", generateMutation.isPending && "animate-spin")} />
                    Regenerate
                  </Button>
                </>
              ) : null}
            </div>

            <p className="text-[11px] text-muted-foreground">
              Tone and language preferences are applied in the prompt context when supported.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
