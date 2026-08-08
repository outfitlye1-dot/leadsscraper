"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  Bot,
  Check,
  Copy,
  MessageSquare,
  MoreVertical,
  Search,
  Send,
  Sparkles,
  Trash2,
  UserX,
} from "lucide-react";
import { toast } from "sonner";
import { PageError } from "@/components/PageError";
import { PageLoader } from "@/components/Loader";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useDeleteLead } from "@/hooks/useLeads";
import {
  useClearWhatsAppThread,
  useWhatsAppCloudSend,
  useWhatsAppCloudStatus,
  useWhatsAppContacts,
  useWhatsAppManualOutbound,
  useWhatsAppOpener,
  useWhatsAppReply,
  useWhatsAppThread,
} from "@/hooks/useWhatsAppChat";
import { cn, formatApiError } from "@/lib/utils";
import type { WhatsAppChatContact, WhatsAppChatMessage } from "@/lib/types";
import { useQueryClient } from "@tanstack/react-query";

function formatTime(value: string | null | undefined) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const diffMs = Date.now() - date.getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return date.toLocaleDateString();
}

function contactLabel(c: Pick<WhatsAppChatContact, "company_name" | "contact_name" | "phone">) {
  return c.company_name || c.contact_name || c.phone;
}

export default function MessagesPage() {
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [customerInput, setCustomerInput] = useState("");
  const [firstMessage, setFirstMessage] = useState("");
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  const contactsQuery = useWhatsAppContacts();
  const threadQuery = useWhatsAppThread(selectedLeadId);
  const replyMutation = useWhatsAppReply();
  const openerMutation = useWhatsAppOpener();
  const manualOutbound = useWhatsAppManualOutbound();
  const clearMutation = useClearWhatsAppThread();
  const deleteLead = useDeleteLead();
  const cloudStatus = useWhatsAppCloudStatus();
  const cloudSend = useWhatsAppCloudSend();
  const [sendingId, setSendingId] = useState<number | null>(null);

  const contacts = contactsQuery.data || [];
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return contacts;
    return contacts.filter((c) => {
      const hay = [c.company_name, c.contact_name, c.phone, c.city, c.country]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }, [contacts, search]);

  useEffect(() => {
    if (selectedLeadId != null) return;
    if (filtered.length > 0) setSelectedLeadId(filtered[0].lead_id);
  }, [filtered, selectedLeadId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [threadQuery.data?.messages?.length, replyMutation.isPending]);

  useEffect(() => {
    setMenuOpen(false);
  }, [selectedLeadId]);

  useEffect(() => {
    if (!menuOpen) return;
    const onPointerDown = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  const thread = threadQuery.data;
  const messages = thread?.messages || [];

  const copyReply = async (msg: WhatsAppChatMessage) => {
    try {
      await navigator.clipboard.writeText(msg.body);
      setCopiedId(msg.id);
      toast.success("Copied — paste into WhatsApp");
      window.setTimeout(() => setCopiedId((id) => (id === msg.id ? null : id)), 2000);
    } catch {
      toast.error("Could not copy");
    }
  };

  const handleReply = async () => {
    if (!selectedLeadId) return;
    const text = customerInput.trim();
    if (!text) {
      toast.error("Paste the customer's WhatsApp message first");
      return;
    }
    try {
      await replyMutation.mutateAsync({
        leadId: selectedLeadId,
        customer_message: text,
      });
      setCustomerInput("");
      toast.success("Brain drafted a reply — copy & send on WhatsApp");
    } catch (err) {
      toast.error(formatApiError(err, "Failed to draft reply"));
    }
  };

  useEffect(() => {
    setFirstMessage("");
    setCustomerInput("");
  }, [selectedLeadId]);

  const handleOpener = async () => {
    if (!selectedLeadId) return;
    try {
      const data = await openerMutation.mutateAsync(selectedLeadId);
      toast.success("Brain suggestion ready — edit if you want, then copy to WhatsApp");
      await copyReply(data.reply);
    } catch (err) {
      toast.error(formatApiError(err, "Failed to draft first message"));
    }
  };

  const handleCloudSend = async (msg: WhatsAppChatMessage) => {
    if (!selectedLeadId) return;
    if (!cloudStatus.data?.configured) {
      toast.error("WhatsApp Cloud API not configured in .env");
      return;
    }
    setSendingId(msg.id);
    try {
      await cloudSend.mutateAsync({
        leadId: selectedLeadId,
        message_id: msg.id,
        mode: "text",
      });
      toast.success("Sent via WhatsApp Cloud API");
    } catch (err) {
      toast.error(formatApiError(err, "Failed to send via WhatsApp API"));
    } finally {
      setSendingId(null);
    }
  };

  const handleSaveFirstMessage = async (alsoSend = false) => {
    if (!selectedLeadId) return;
    const text = firstMessage.trim();
    if (!text) {
      toast.error("Write your first WhatsApp message");
      return;
    }
    try {
      const data = await manualOutbound.mutateAsync({
        leadId: selectedLeadId,
        body: text,
      });
      setFirstMessage("");
      if (alsoSend && cloudStatus.data?.configured) {
        await cloudSend.mutateAsync({
          leadId: selectedLeadId,
          message_id: data.reply.id,
          mode: "text",
        });
        toast.success("Saved & sent via WhatsApp Cloud API");
      } else {
        toast.success("Saved — copy & send on WhatsApp");
        await copyReply(data.reply);
      }
    } catch (err) {
      toast.error(formatApiError(err, alsoSend ? "Failed to save & send" : "Failed to save message"));
    }
  };

  const handleTemplateSend = async () => {
    if (!selectedLeadId) return;
    if (!cloudStatus.data?.configured) {
      toast.error("WhatsApp Cloud API not configured in .env");
      return;
    }
    try {
      await cloudSend.mutateAsync({
        leadId: selectedLeadId,
        mode: "template",
        template_name: "hello_world",
        language_code: "en_US",
      });
      toast.success("hello_world template sent (opens 24h window)");
    } catch (err) {
      toast.error(formatApiError(err, "Failed to send template"));
    }
  };

  const handleDeleteChat = async () => {
    if (!selectedLeadId) return;
    setMenuOpen(false);
    if (!confirm("Delete this chat history? The number stays in your list.")) return;
    try {
      await clearMutation.mutateAsync(selectedLeadId);
      toast.success("Chat deleted");
    } catch (err) {
      toast.error(formatApiError(err, "Failed to delete chat"));
    }
  };

  const handleDeleteNumber = async () => {
    if (!selectedLeadId) return;
    setMenuOpen(false);
    if (!confirm("Delete this number/contact from saved leads? Chat will be removed too.")) return;
    const leadId = selectedLeadId;
    try {
      await clearMutation.mutateAsync(leadId).catch(() => undefined);
      await deleteLead.mutateAsync({ id: leadId, saved: true });
      await queryClient.invalidateQueries({ queryKey: ["whatsapp-chat-contacts"] });
      await queryClient.invalidateQueries({ queryKey: ["whatsapp-chat-thread", leadId] });
      setSelectedLeadId(null);
      toast.success("Number deleted");
    } catch (err) {
      toast.error(formatApiError(err, "Failed to delete number"));
    }
  };

  if (contactsQuery.isLoading) return <PageLoader />;
  if (contactsQuery.isError) {
    return (
      <PageError
        message="Failed to load saved contacts"
        onRetry={() => contactsQuery.refetch()}
      />
    );
  }

  const apiReady = Boolean(cloudStatus.data?.configured);

  return (
    <div className="flex h-[calc(100vh-7.5rem)] min-h-[520px] flex-col overflow-hidden rounded-2xl border border-border/70 bg-background/40 shadow-sm">
      <div
        className={cn(
          "flex flex-wrap items-center justify-between gap-2 border-b px-4 py-2 text-xs",
          apiReady
            ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-900 dark:text-emerald-100"
            : "border-amber-500/25 bg-amber-500/10 text-amber-950 dark:text-amber-100"
        )}
      >
        <p>
          {apiReady ? (
            <>
              Cloud API connected
              {cloudStatus.data?.display_number
                ? ` · from ${cloudStatus.data.display_number}`
                : ""}
              {" · "}Send from chat, or use template for first outreach. Inbound needs a public webhook URL.
            </>
          ) : (
            <>Cloud API not set — replies are copy/paste only. Add WHATSAPP_* keys in .env to enable Send API.</>
          )}{" "}
          <Link href="/settings/whatsapp-web" className="underline underline-offset-2">
            WhatsApp Web AI connect
          </Link>
        </p>
        {apiReady ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-7 border-emerald-600/30 bg-background/60 text-[11px]"
            onClick={() => void handleTemplateSend()}
            disabled={!selectedLeadId || cloudSend.isPending}
            isLoading={cloudSend.isPending}
          >
            <Send className="h-3 w-3" />
            Send hello_world template
          </Button>
        ) : null}
      </div>

      <div className="flex min-h-0 flex-1">
      {/* Contacts */}
      <aside className="flex w-full max-w-[320px] shrink-0 flex-col border-r border-border/60 bg-muted/20">
        <div className="border-b border-border/50 px-4 py-4">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-emerald-600" />
            <div>
              <h1 className="text-base font-semibold tracking-tight">WhatsApp</h1>
              <p className="text-xs text-muted-foreground">
                Saved numbers · Brain drafts
                {apiReady ? " · live send" : " · manual copy"}
              </p>
            </div>
          </div>
          <div className="relative mt-3">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search saved contacts…"
              className="pl-9"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="space-y-3 p-6 text-center text-sm text-muted-foreground">
              <p>No saved leads with a phone number.</p>
              <Link href="/leads/saved" className="text-primary underline-offset-2 hover:underline">
                Go to Saved leads
              </Link>
            </div>
          ) : (
            filtered.map((c) => {
              const active = c.lead_id === selectedLeadId;
              return (
                <button
                  key={c.lead_id}
                  type="button"
                  onClick={() => setSelectedLeadId(c.lead_id)}
                  className={cn(
                    "flex w-full flex-col gap-0.5 border-b border-border/40 px-4 py-3 text-left transition-colors",
                    active ? "bg-emerald-500/10" : "hover:bg-muted/40"
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm font-medium">{contactLabel(c)}</span>
                    <span className="shrink-0 text-[10px] text-muted-foreground">
                      {formatTime(c.last_message_at)}
                    </span>
                  </div>
                  <span className="truncate text-xs text-muted-foreground">{c.phone}</span>
                  {c.last_message ? (
                    <span className="line-clamp-1 text-xs text-muted-foreground/80">
                      {c.last_message}
                    </span>
                  ) : (
                    <span className="text-xs text-emerald-700/80 dark:text-emerald-400/80">
                      New · write first message
                    </span>
                  )}
                </button>
              );
            })
          )}
        </div>
      </aside>

      {/* Thread */}
      <section className="flex min-w-0 flex-1 flex-col">
        {!selectedLeadId || !thread ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center text-muted-foreground">
            <Bot className="h-10 w-10 opacity-40" />
            <p className="text-sm">Select a saved contact to start</p>
          </div>
        ) : (
          <>
            <header className="flex flex-col gap-2 border-b border-border/50 px-5 py-3">
              <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <h2 className="truncate text-sm font-semibold">{contactLabel(thread)}</h2>
                <p className="truncate text-xs text-muted-foreground">
                  {thread.phone}
                  {thread.city || thread.country
                    ? ` · ${[thread.city, thread.country].filter(Boolean).join(", ")}`
                    : ""}
                  {thread.deal_status ? ` · ${thread.deal_status}` : ""}
                </p>
              </div>
              <div className="relative shrink-0" ref={menuRef}>
                <button
                  type="button"
                  aria-label="Chat options"
                  aria-expanded={menuOpen}
                  onClick={() => setMenuOpen((open) => !open)}
                  className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border/70 bg-background/50 text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                >
                  <MoreVertical className="h-4 w-4" />
                </button>
                {menuOpen ? (
                  <div className="absolute right-0 z-20 mt-1.5 min-w-[180px] overflow-hidden rounded-xl border border-border/70 bg-background py-1 shadow-lg">
                    <button
                      type="button"
                      disabled={clearMutation.isPending || messages.length === 0}
                      onClick={() => void handleDeleteChat()}
                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-foreground hover:bg-muted/60 disabled:opacity-50"
                    >
                      <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
                      Delete chat
                    </button>
                    <button
                      type="button"
                      disabled={deleteLead.isPending || clearMutation.isPending}
                      onClick={() => void handleDeleteNumber()}
                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-red-600 hover:bg-red-500/10 disabled:opacity-50 dark:text-red-400"
                    >
                      <UserX className="h-3.5 w-3.5" />
                      Delete number
                    </button>
                  </div>
                ) : null}
              </div>
              </div>
              {thread.memory_summary || thread.last_price_quoted != null ? (
                <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-2 text-[11px] text-muted-foreground">
                  <span className="font-medium text-emerald-700 dark:text-emerald-400">
                    Memory for this number only:
                  </span>{" "}
                  {thread.memory_summary || "—"}
                  {thread.last_price_quoted != null
                    ? ` · last quote ~${thread.last_price_quoted}`
                    : ""}
                  {thread.customer_budget != null
                    ? ` · their budget ~${thread.customer_budget}`
                    : ""}
                </div>
              ) : null}
            </header>

            <div className="relative flex-1 overflow-y-auto bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-emerald-500/5 via-transparent to-transparent px-4 py-5">
              {threadQuery.isLoading ? (
                <p className="text-center text-sm text-muted-foreground">Loading chat…</p>
              ) : messages.length === 0 ? (
                <div className="mx-auto flex w-full max-w-lg flex-col gap-3 py-10">
                  <div className="space-y-1 text-center">
                    <p className="text-sm font-medium">Write your first message</p>
                  </div>
                  <textarea
                    value={firstMessage}
                    onChange={(e) => setFirstMessage(e.target.value)}
                    placeholder="Hi sir, I help local businesses with websites. Open to a quick chat?"
                    rows={4}
                    className="min-h-[110px] w-full resize-none rounded-xl border border-border/70 bg-background/90 px-3 py-2.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                  <div className="flex flex-wrap items-center justify-center gap-2">
                    {apiReady ? (
                      <Button
                        type="button"
                        onClick={() => void handleSaveFirstMessage(true)}
                        isLoading={manualOutbound.isPending || cloudSend.isPending}
                        disabled={!firstMessage.trim()}
                      >
                        <Send className="h-4 w-4" />
                        Save & Send API
                      </Button>
                    ) : null}
                    <Button
                      type="button"
                      variant={apiReady ? "outline" : "default"}
                      onClick={() => void handleSaveFirstMessage(false)}
                      isLoading={manualOutbound.isPending}
                      disabled={!firstMessage.trim()}
                    >
                      <Copy className="h-4 w-4" />
                      Save & copy
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => void handleOpener()}
                      isLoading={openerMutation.isPending}
                    >
                      <Sparkles className="h-4 w-4" />
                      Suggest with Brain
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="mx-auto flex max-w-2xl flex-col gap-3">
                  {messages.map((m) => {
                    const isOut = m.direction === "outbound";
                    return (
                      <div
                        key={m.id}
                        className={cn("flex", isOut ? "justify-end" : "justify-start")}
                      >
                        <div
                          className={cn(
                            "max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm shadow-sm",
                            isOut
                              ? "rounded-br-md bg-emerald-600 text-white"
                              : "rounded-bl-md border border-border/60 bg-background/90 text-foreground"
                          )}
                        >
                          <p className="mb-1 text-[10px] font-medium uppercase tracking-wide opacity-70">
                            {isOut
                              ? apiReady
                                ? "You · Send API / copy"
                                : "You · copy"
                              : apiReady
                                ? "Customer"
                                : "Customer (pasted)"}
                          </p>
                          <p className="whitespace-pre-wrap leading-relaxed">{m.body}</p>
                          <div
                            className={cn(
                              "mt-2 flex flex-wrap items-center gap-2",
                              isOut ? "justify-between" : "justify-end"
                            )}
                          >
                            {isOut ? (
                              <div className="flex flex-wrap gap-1.5">
                                <button
                                  type="button"
                                  onClick={() => void copyReply(m)}
                                  className="inline-flex items-center gap-1 rounded-md bg-white/15 px-2 py-1 text-[11px] font-medium hover:bg-white/25"
                                >
                                  {copiedId === m.id ? (
                                    <Check className="h-3 w-3" />
                                  ) : (
                                    <Copy className="h-3 w-3" />
                                  )}
                                  {copiedId === m.id ? "Copied" : "Copy"}
                                </button>
                                {cloudStatus.data?.configured ? (
                                  <button
                                    type="button"
                                    disabled={sendingId === m.id || cloudSend.isPending}
                                    onClick={() => void handleCloudSend(m)}
                                    className="inline-flex items-center gap-1 rounded-md bg-white/15 px-2 py-1 text-[11px] font-medium hover:bg-white/25 disabled:opacity-60"
                                  >
                                    <Send className="h-3 w-3" />
                                    {sendingId === m.id ? "Sending…" : "Send API"}
                                  </button>
                                ) : null}
                              </div>
                            ) : (
                              <span />
                            )}
                            <span className="text-[10px] opacity-60">{formatTime(m.created_at)}</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  {replyMutation.isPending ? (
                    <div className="flex justify-end">
                      <div className="rounded-2xl rounded-br-md bg-emerald-600/80 px-4 py-3 text-xs text-white">
                        Brain is drafting…
                      </div>
                    </div>
                  ) : null}
                  <div ref={bottomRef} />
                </div>
              )}
            </div>

            <footer className="border-t border-border/50 bg-background/60 p-4">
              {messages.length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  {apiReady
                    ? "Pehla message upar likho → Save & Send API, ya pehle hello_world template bhejo. Customer reply webhook se aa sakta hai (public URL chahiye)."
                    : "Pehla message upar likho. Jab customer WhatsApp pe reply kare, yahan paste karke Brain se jawab lo."}
                </p>
              ) : (
                <>
                  <div className="flex gap-2">
                    <textarea
                      value={customerInput}
                      onChange={(e) => setCustomerInput(e.target.value)}
                      placeholder="Paste customer WhatsApp message here…"
                      rows={2}
                      className="min-h-[72px] flex-1 resize-none rounded-xl border border-border/70 bg-background/80 px-3 py-2 text-sm outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring"
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                          e.preventDefault();
                          void handleReply();
                        }
                      }}
                    />
                    <Button
                      type="button"
                      className="self-end"
                      onClick={() => void handleReply()}
                      isLoading={replyMutation.isPending}
                      disabled={!customerInput.trim()}
                    >
                      <Bot className="h-4 w-4" />
                      Get reply
                    </Button>
                  </div>
                  <p className="mt-1.5 text-[11px] text-muted-foreground">Ctrl+Enter to send</p>
                </>
              )}            </footer>
          </>
        )}
      </section>
      </div>
    </div>
  );
}
