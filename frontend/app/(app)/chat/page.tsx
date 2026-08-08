"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { Mic, MicOff, Paperclip, MessageCircle, MoreVertical, Plus, Search, Send, Smile, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import { PageLoader } from "@/components/Loader";
import { PageError } from "@/components/PageError";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  useChatThread,
  useChatThreads,
  useDeleteChatThread,
  useEmailAccounts,
  useMarkLeadNotificationsRead,
  useSendChatReply,
  useStartManualChat,
  useSyncChatInbox,
} from "@/hooks/useEmailOutreach";
import {
  useAdminSupportThreads,
  useMySupportThread,
} from "@/hooks/useSupportChat";
import type { ChatMessage, ChatThread } from "@/lib/types";
import { cn, formatApiError } from "@/lib/utils";
import { useAuthStore } from "@/store/authStore";
import {
  SupportChatPanel,
  SupportSidebarItem,
  SupportUserThreadItem,
} from "@/components/support/SupportChatPanel";

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
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString();
}

/** Strip quoted email history + JSON subject/body wrappers — show message text only. */
function cleanReplyBody(raw: string | null | undefined): string {
  if (!raw) return "";
  let text = raw.replace(/\r\n/g, "\n").replace(/\u202f/g, " ").trim();

  // Full or partial JSON from AI generation
  const jsonCandidates = [text];
  if (!text.startsWith("{")) {
    jsonCandidates.push(`{${text}}`, `{${text.replace(/,\s*$/, "")}}`);
  }
  for (const candidate of jsonCandidates) {
    try {
      const data = JSON.parse(candidate) as Record<string, unknown>;
      const body = String(data.body ?? data.draft_body ?? data.message ?? "").trim();
      if (body) return cleanReplyBody(body);
    } catch {
      /* try next */
    }
  }

  const bodyMatch = text.match(/"body"\s*:\s*"((?:\\.|[^"\\])*)"/is);
  if (bodyMatch) {
    return bodyMatch[1].replace(/\\n/g, "\n").replace(/\\"/g, '"').trim();
  }

  if (/^"subject"\s*:/i.test(text)) {
    const lines = text.split("\n");
    const bodyLines: string[] = [];
    let inBody = false;
    for (const line of lines) {
      if (/^\s*"subject"\s*:/i.test(line)) continue;
      if (/^\s*"body"\s*:/i.test(line)) {
        inBody = true;
        const rest = line.replace(/^\s*"body"\s*:\s*"?/i, "").replace(/",?\s*$/, "");
        if (rest) bodyLines.push(rest);
        continue;
      }
      if (inBody) bodyLines.push(line.replace(/",?\s*$/, ""));
    }
    if (bodyLines.length) {
      text = bodyLines.join("\n").trim();
    }
  }

  const cutPatterns = [
    /\nOn\s+[^\n]+wrote:\s*\n/i,
    /\nOn\s+[^\n]+<[^>]+>\s*wrote:\s*\n/i,
    /\n-{2,}\s*Original Message\s*-{2,}/i,
    /\nFrom:\s*[^\n]+\nSent:\s*[^\n]+/i,
    /\n_{5,}\n/,
    /\nBegin forwarded message:\s*\n/i,
  ];
  for (const re of cutPatterns) {
    const idx = text.search(re);
    if (idx > 0) {
      text = text.slice(0, idx);
      break;
    }
  }

  text = text
    .split("\n")
    .filter((line) => !/^\s*>/.test(line))
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  return text || raw.trim().split("\n")[0] || "";
}

function replySubject(threadSubject: string | null | undefined): string {
  const sub = (threadSubject || "Chat").trim();
  return sub.toLowerCase().startsWith("re:") ? sub : `Re: ${sub}`;
}

function formatLastSeen(value: string | null | undefined) {
  if (!value) return "offline";
  const label = formatTime(value);
  if (!label) return "offline";
  if (label === "just now") return "last seen just now";
  return `last seen ${label}`;
}

function getThreadInitials(name: string, email?: string | null) {
  const cleanName = name.trim();
  if (cleanName) {
    const parts = cleanName.split(/\s+/).filter(Boolean);
    const initials = parts.slice(0, 2).map((part) => part[0]?.toUpperCase() || "").join("");
    if (initials) return initials;
  }
  const fallback = (email || "").trim();
  return (fallback.slice(0, 2) || "?").toUpperCase();
}

function PresenceDot({ online, active }: { online: boolean; active?: boolean }) {
  return (
    <span
      className={cn(
        "inline-block h-2 w-2 shrink-0 rounded-full",
        online
          ? "bg-emerald-500"
          : active
            ? "bg-background/40"
            : "bg-muted-foreground/40"
      )}
      title={online ? "Online" : "Offline"}
      aria-hidden
    />
  );
}

/** WhatsApp-style ticks: ✓ sent, ✓✓ delivered, blue ✓✓ read */
function DeliveryTicks({ status }: { status?: string | null }) {
  if (!status) return null;
  const read = status === "read";
  const double = status === "delivered" || status === "read";
  const title =
    status === "read" ? "Read" : status === "delivered" ? "Delivered" : "Sent";
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center leading-none",
        read ? "text-sky-400" : "opacity-70"
      )}
      title={title}
      aria-label={title}
    >
      <svg width="16" height="11" viewBox="0 0 16 11" fill="none" aria-hidden>
        <path
          d="M1.2 5.8L4.2 8.8L9.8 1.6"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {double ? (
          <path
            d="M5.2 5.8L8.2 8.8L14.8 1.6"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ) : null}
      </svg>
    </span>
  );
}

function formatBubbleTime(value: string | null | undefined) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function ThreadListItem({
  thread,
  active,
  onSelect,
  onDeleteChat,
  onDeleteContact,
}: {
  thread: ChatThread;
  active: boolean;
  onSelect: () => void;
  onDeleteChat: () => void;
  onDeleteContact?: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const email = thread.lead_email?.trim() || "";
  const name =
    thread.lead_name?.trim() ||
    (email.includes("@") ? email.split("@")[0] : "") ||
    `Lead #${thread.lead_id}`;
  // Hide badge while this chat is open
  const unread = active ? 0 : thread.unread_count ?? 0;
  const online = Boolean(thread.is_online);
  const initials = getThreadInitials(name, email);

  return (
    <div
      className={cn(
        "group relative flex items-stretch gap-1 rounded-xl transition",
        active ? "bg-foreground text-background" : "hover:bg-muted/70"
      )}
    >
      <button type="button" onClick={onSelect} className="min-w-0 flex-1 px-3 py-2.5 text-left">
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <div className="relative shrink-0">
              <div
                className={cn(
                  "flex h-9 w-9 items-center justify-center rounded-full text-[11px] font-semibold",
                  active ? "bg-background/15 text-background" : "bg-primary/10 text-foreground"
                )}
                aria-hidden
              >
                {initials}
              </div>
              <span className="absolute -bottom-0.5 -right-0.5">
                <PresenceDot online={online} active={active} />
              </span>
            </div>
            <p
              className={cn(
                "truncate text-sm font-semibold",
                active ? "text-background" : "text-foreground",
                unread > 0 ? "font-bold" : ""
              )}
              title={email || name}
            >
              {name}
            </p>
          </div>
          {unread > 0 ? (
            <span
              className="shrink-0 rounded-full bg-emerald-500 px-1.5 py-0.5 text-[10px] font-semibold tabular-nums text-white"
              title={`${unread} new ${unread === 1 ? "message" : "messages"}`}
            >
              {unread}
            </span>
          ) : null}
        </div>
      </button>
      <div className="relative mr-1 self-center">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setMenuOpen((v) => !v);
          }}
          className={cn(
            "rounded-lg p-1.5 opacity-100 transition sm:opacity-0 sm:group-hover:opacity-100",
            active
              ? "text-background/70 hover:bg-background/20 hover:text-background"
              : "text-muted-foreground hover:bg-muted hover:text-destructive"
          )}
          aria-label="Delete options"
          title="Delete"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
        {menuOpen ? (
          <>
            <button
              type="button"
              className="fixed inset-0 z-10 cursor-default"
              aria-label="Close menu"
              onClick={(e) => {
                e.stopPropagation();
                setMenuOpen(false);
              }}
            />
            <div className="absolute right-0 top-full z-20 mt-1 min-w-[160px] overflow-hidden rounded-lg border border-border bg-card py-1 text-foreground shadow-lg">
              <button
                type="button"
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-muted"
                onClick={(e) => {
                  e.stopPropagation();
                  setMenuOpen(false);
                  onDeleteChat();
                }}
              >
                <Trash2 className="h-3.5 w-3.5" />
                Delete chat
              </button>
              {onDeleteContact ? (
                <button
                  type="button"
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-destructive hover:bg-muted"
                  onClick={(e) => {
                    e.stopPropagation();
                    setMenuOpen(false);
                    onDeleteContact();
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Delete contact
                </button>
              ) : null}
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const outbound = message.direction === "outbound";
  const body = cleanReplyBody(message.body_text);
  const receipt =
    message.delivery_status ||
    (message.status === "opened" || message.status === "replied"
      ? "read"
      : message.status === "delivered"
        ? "delivered"
        : "sent");
  const timeLabel = formatBubbleTime(message.sent_at);

  return (
    <div className={cn("flex w-full", outbound ? "justify-end" : "justify-start")}>
      <div className={cn("flex max-w-[min(85%,26rem)] flex-col", outbound ? "items-end" : "items-start")}>
        <div
          className={cn(
            "w-fit max-w-full rounded-lg px-[9px] py-[6px] shadow-sm",
            outbound
              ? "rounded-br-[4px] bg-foreground text-background"
              : "rounded-bl-[4px] bg-muted/80 text-foreground ring-1 ring-border/50"
          )}
        >
          <p className="whitespace-pre-wrap break-words text-[14.2px] font-normal leading-[19px]">
            {body}
          </p>
        </div>
        <div
          className={cn(
            "mt-0.5 flex items-center gap-1 px-0.5 text-[10px] leading-none text-muted-foreground"
          )}
        >
          <span>{timeLabel}</span>
          {outbound ? <DeliveryTicks status={receipt} /> : null}
        </div>
      </div>
    </div>
  );
}

const CHAT_EMOJIS = [
  "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇",
  "🙂", "😉", "😌", "😍", "🥰", "😘", "😗", "😙", "😚", "😋",
  "😜", "🤪", "😝", "🤗", "🤭", "🤫", "🤔", "🤐", "🤨", "😐",
  "😏", "😒", "🙄", "😬", "😔", "😪", "😴", "😷", "🤒", "🤕",
  "🤢", "🤮", "🥴", "😵", "🤯", "🤠", "🥳", "😎", "🤓", "🧐",
  "😕", "😟", "🙁", "☹️", "😮", "😯", "😲", "😳", "🥺", "😦",
  "😧", "😨", "😰", "😥", "😢", "😭", "😱", "😖", "😣", "😞",
  "😓", "😩", "😫", "🥱", "😤", "😡", "😠", "🤬", "😈", "👿",
  "👍", "👎", "👌", "✌️", "🤞", "🤟", "🤘", "🤙", "👈", "👉",
  "👆", "👇", "☝️", "✋", "🤚", "🖐️", "🖖", "👋", "💪", "🙏",
  "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔",
  "❣️", "💕", "💞", "💓", "💗", "💖", "💘", "💝", "✨", "✅",
  "🔥", "⭐", "🌟", "💯", "🎉", "🎊", "🙌", "👏", "🤝", "💼",
];

function EmojiPickerButton({
  onPick,
  disabled,
}: {
  onPick: (emoji: string) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative shrink-0">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        className="flex h-9 w-9 items-center justify-center rounded-lg border border-input bg-background text-muted-foreground transition hover:bg-muted hover:text-foreground disabled:opacity-50"
        title="Emoji"
        aria-label="Insert emoji"
      >
        <Smile className="h-4 w-4" />
      </button>
      {open ? (
        <>
          <button
            type="button"
            className="fixed inset-0 z-20 cursor-default"
            aria-label="Close emoji picker"
            onClick={() => setOpen(false)}
          />
          <div className="absolute bottom-full left-0 z-30 mb-2 w-[280px] rounded-xl border border-border bg-card p-2 shadow-lg sm:w-[320px]">
            <div className="chat-scroll grid max-h-48 grid-cols-8 gap-0.5 overflow-y-auto sm:grid-cols-10">
              {CHAT_EMOJIS.map((emoji) => (
                <button
                  key={emoji}
                  type="button"
                  className="flex h-8 w-8 items-center justify-center rounded-md text-lg hover:bg-muted"
                  onClick={() => {
                    onPick(emoji);
                    setOpen(false);
                  }}
                >
                  {emoji}
                </button>
              ))}
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}

export default function ChatPage() {
  const isAdmin = useAuthStore((s) => s.user?.role === "admin");
  const { data: threads = [], isLoading, isError, refetch } = useChatThreads(true);
  const { data: supportThreads = [] } = useAdminSupportThreads(true, isAdmin);
  const { data: mySupportThread } = useMySupportThread(true, !isAdmin);
  const { data: accounts = [] } = useEmailAccounts();
  const [chatMode, setChatMode] = useState<"lead" | "support">("lead");
  const [selectedSupportUserId, setSelectedSupportUserId] = useState<number | null>(null);
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [showNewChat, setShowNewChat] = useState(false);
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newSubject, setNewSubject] = useState("Hello");
  const [newBody, setNewBody] = useState("");
  const [accountId, setAccountId] = useState<number | "">("");
  const [body, setBody] = useState("");
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [recording, setRecording] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaChunksRef = useRef<Blob[]>([]);
  const mediaStreamRef = useRef<MediaStream | null>(null);

  const startChat = useStartManualChat();
  const sendReply = useSendChatReply();
  const deleteChat = useDeleteChatThread();
  const syncInbox = useSyncChatInbox();
  const markLeadNotifsRead = useMarkLeadNotificationsRead();
  const syncInFlight = useRef(false);

  useEffect(() => {
    if (!accounts.length) return;
    let cancelled = false;
    const run = async () => {
      if (syncInFlight.current || cancelled) return;
      syncInFlight.current = true;
      try {
        const focusEmail =
          threads.find((t) => t.lead_id === selectedLeadId)?.lead_email ||
          undefined;
        const r = await syncInbox.mutateAsync(
          focusEmail ? { focusEmail } : undefined
        );
        if (!cancelled && (r.new_replies ?? 0) > 0) {
          toast.message(
            `${r.new_replies} new ${r.new_replies === 1 ? "reply" : "replies"} received`
          );
        }
      } catch {
        /* silent */
      } finally {
        syncInFlight.current = false;
      }
    };
    void run();
    const id = window.setInterval(() => void run(), 7_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accounts.length, selectedLeadId]);

  const defaultAccountId = useMemo(() => {
    const def = accounts.find((a) => a.is_default) || accounts[0];
    return def?.id ?? "";
  }, [accounts]);

  useEffect(() => {
    if (accountId === "" && defaultAccountId !== "") {
      setAccountId(defaultAccountId);
    }
  }, [accountId, defaultAccountId]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return threads;
    return threads.filter(
      (t) =>
        t.lead_name.toLowerCase().includes(q) ||
        t.lead_email.toLowerCase().includes(q) ||
        t.subject.toLowerCase().includes(q) ||
        (t.last_preview || "").toLowerCase().includes(q)
    );
  }, [threads, query]);

  const filteredSupportThreads = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return supportThreads;
    return supportThreads.filter(
      (t) =>
        t.user_name.toLowerCase().includes(q) ||
        t.user_email.toLowerCase().includes(q) ||
        (t.last_preview || "").toLowerCase().includes(q)
    );
  }, [supportThreads, query]);

  useEffect(() => {
    if (chatMode === "support" || selectedLeadId != null || showNewChat) return;
    if (filtered.length) {
      setSelectedLeadId(filtered[0].lead_id);
      return;
    }
    if (!isAdmin) {
      setChatMode("support");
    }
  }, [filtered, selectedLeadId, showNewChat, chatMode, isAdmin]);

  const { data: thread, isLoading: threadLoading } = useChatThread(selectedLeadId, true);

  useEffect(() => {
    if (selectedLeadId == null) return;
    markLeadNotifsRead.mutate(selectedLeadId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedLeadId]);

  useEffect(() => {
    setBody("");
    setPendingFiles([]);
    setMenuOpen(false);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
    mediaStreamRef.current = null;
    setRecording(false);
  }, [thread?.conversation_id, selectedLeadId]);

  useEffect(() => {
    return () => {
      mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const replySubjectValue = useMemo(
    () => replySubject(thread?.subject),
    [thread?.subject]
  );

  const activeThreadMeta = useMemo(
    () => threads.find((t) => t.lead_id === selectedLeadId) ?? null,
    [threads, selectedLeadId]
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [thread?.messages?.length, selectedLeadId]);

  const selectedAccountId = typeof accountId === "number" ? accountId : undefined;

  const handleStartNewChat = async () => {
    if (!newEmail.trim()) {
      toast.error("Email is required");
      return;
    }
    if (!newBody.trim()) {
      toast.error("Write a first message");
      return;
    }
    if (!accounts.length) {
      toast.error("Connect a Gmail/email account first");
      return;
    }
    try {
      const detail = await startChat.mutateAsync({
        email: newEmail.trim(),
        name: newName.trim() || undefined,
        subject: newSubject.trim() || "Hello",
        body: newBody.trim(),
        accountId: selectedAccountId,
      });
      setShowNewChat(false);
      setNewName("");
      setNewEmail("");
      setNewSubject("Hello");
      setNewBody("");
      setSelectedLeadId(detail.lead_id);
      toast.success("Chat started — message sent");
    } catch (err) {
      toast.error(formatApiError(err, "Failed to start chat"));
    }
  };

  const handleManualSend = async () => {
    if (!selectedLeadId) return;
    if (!body.trim() && pendingFiles.length === 0) {
      toast.error("Write a message or attach a file");
      return;
    }
    try {
      await sendReply.mutateAsync({
        leadId: selectedLeadId,
        subject: replySubjectValue,
        body: body.trim(),
        accountId: selectedAccountId,
        files: pendingFiles,
      });
      setBody("");
      setPendingFiles([]);
      toast.success("Message sent");
    } catch (err) {
      toast.error(formatApiError(err, "Failed to send"));
    }
  };

  const addFiles = (list: FileList | null) => {
    if (!list?.length) return;
    const next = [...pendingFiles];
    for (const file of Array.from(list)) {
      if (file.size > 12 * 1024 * 1024) {
        toast.error(`${file.name} is too large (max 12MB)`);
        continue;
      }
      if (next.length >= 8) {
        toast.error("Maximum 8 files per message");
        break;
      }
      next.push(file);
    }
    setPendingFiles(next);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const toggleVoice = async () => {
    if (recording) {
      mediaRecorderRef.current?.stop();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      const mime = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : MediaRecorder.isTypeSupported("audio/mp4")
          ? "audio/mp4"
          : "";
      const recorder = mime
        ? new MediaRecorder(stream, { mimeType: mime })
        : new MediaRecorder(stream);
      mediaChunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) mediaChunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const type = recorder.mimeType || "audio/webm";
        const blob = new Blob(mediaChunksRef.current, { type });
        stream.getTracks().forEach((t) => t.stop());
        mediaStreamRef.current = null;
        setRecording(false);
        if (blob.size < 400) {
          toast.error("Voice note too short");
          return;
        }
        const ext = type.includes("mp4") ? "m4a" : "webm";
        const file = new File(
          [blob],
          `voice-${new Date().toISOString().replace(/[:.]/g, "-")}.${ext}`,
          { type }
        );
        setPendingFiles((prev) => {
          if (prev.length >= 8) {
            toast.error("Maximum 8 files per message");
            return prev;
          }
          return [...prev, file];
        });
        toast.success("Voice note attached");
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      toast.error("Microphone permission needed for voice notes");
    }
  };

  const handleDeleteChat = async (leadId: number, deleteLead = false) => {
    const threadMeta = threads.find((t) => t.lead_id === leadId);
    const label =
      threadMeta?.lead_email?.trim() ||
      threadMeta?.lead_name?.trim() ||
      "this chat";

    if (deleteLead) {
      if (
        !window.confirm(
          `Delete ${label} and remove this contact from your leads? Chat history will be gone.`
        )
      ) {
        return;
      }
    } else if (
      !window.confirm(`Delete chat with ${label}? Messages will be removed (contact stays).`)
    ) {
      return;
    }

    try {
      await deleteChat.mutateAsync({ leadId, deleteLead });
      if (selectedLeadId === leadId) {
        setSelectedLeadId(null);
      }
      toast.success(deleteLead ? "Chat and contact deleted" : "Chat deleted");
    } catch (err) {
      toast.error(formatApiError(err, "Failed to delete chat"));
    }
  };

  if (isLoading) return <PageLoader />;
  if (isError) {
    return <PageError message="Failed to load chats" onRetry={() => refetch()} />;
  }

  const sending = startChat.isPending || sendReply.isPending || deleteChat.isPending;

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      <div className="flex shrink-0 items-center justify-between gap-3 border-b border-border/60 bg-card/80 px-4 py-3 backdrop-blur-sm sm:px-6">
        <div className="min-w-0">
          <h1 className="text-lg font-semibold tracking-tight sm:text-xl">Chat</h1>
          <p className="truncate text-xs text-muted-foreground">
            Email chats + direct admin support (no email needed)
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button
            type="button"
            size="sm"
            className="gap-1.5"
            onClick={() => {
              setShowNewChat(true);
              setSelectedLeadId(null);
            }}
          >
            <Plus className="h-3.5 w-3.5" />
            New chat
          </Button>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 bg-muted/20 lg:grid-cols-[300px_1fr]">
        <aside className="flex min-h-0 flex-col border-b border-border/60 bg-card lg:border-b-0 lg:border-r">
          <div className="border-b border-border/60 p-3">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search chats…"
                className="pl-9"
              />
            </div>
          </div>
          <div className="chat-scroll flex-1 space-y-1 overflow-y-auto p-2">
            {!isAdmin ? (
              <SupportSidebarItem
                active={chatMode === "support"}
                unread={mySupportThread?.unread_count ?? 0}
                onSelect={() => {
                  setChatMode("support");
                  setShowNewChat(false);
                  setSelectedLeadId(null);
                  setSelectedSupportUserId(null);
                }}
              />
            ) : filteredSupportThreads.length > 0 ? (
              <div className="space-y-1">
                <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                  User support
                </p>
                {filteredSupportThreads.map((thread) => (
                  <SupportUserThreadItem
                    key={thread.user_id}
                    thread={thread}
                    active={
                      chatMode === "support" && selectedSupportUserId === thread.user_id
                    }
                    onSelect={() => {
                      setChatMode("support");
                      setShowNewChat(false);
                      setSelectedLeadId(null);
                      setSelectedSupportUserId(thread.user_id);
                    }}
                  />
                ))}
              </div>
            ) : null}

            {filtered.length > 0 ? (
              <p className="px-2 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                {isAdmin ? "Email chats" : "Lead chats"}
              </p>
            ) : null}

            {filtered.length === 0 && (isAdmin ? filteredSupportThreads.length === 0 : false) ? (
              <div className="px-3 py-10 text-center text-sm text-muted-foreground">
                <MessageCircle className="mx-auto mb-2 h-8 w-8 opacity-40" />
                {isAdmin ? (
                  <>No chats yet.</>
                ) : (
                  <>
                    No lead chats yet. Use <span className="font-medium text-foreground">Admin Support</span>{" "}
                    above or tap <span className="font-medium text-foreground">New chat</span>.
                  </>
                )}
              </div>
            ) : (
              filtered.map((t) => (
                <ThreadListItem
                  key={t.lead_id}
                  thread={t}
                  active={chatMode === "lead" && !showNewChat && t.lead_id === selectedLeadId}
                  onSelect={() => {
                    setChatMode("lead");
                    setShowNewChat(false);
                    setSelectedLeadId(t.lead_id);
                    setSelectedSupportUserId(null);
                  }}
                  onDeleteChat={() => void handleDeleteChat(t.lead_id, false)}
                  onDeleteContact={
                    t.is_manual_chat
                      ? () => void handleDeleteChat(t.lead_id, true)
                      : undefined
                  }
                />
              ))
            )}
          </div>
        </aside>

        <section className="flex min-h-0 flex-col bg-card/40">
          {chatMode === "support" ? (
            <SupportChatPanel
              isAdmin={isAdmin}
              targetUserId={isAdmin ? selectedSupportUserId : null}
            />
          ) : showNewChat ? (
            <>
              <header className="flex items-center justify-between border-b border-border/60 bg-card px-4 py-3 sm:px-5">
                <div>
                  <p className="font-semibold tracking-tight">New chat</p>
                  <p className="text-xs text-muted-foreground">
                    Add any email and send the first message
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setShowNewChat(false)}
                  className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground"
                  aria-label="Close"
                >
                  <X className="h-4 w-4" />
                </button>
              </header>
              <div className="chat-scroll flex-1 space-y-3 overflow-y-auto px-4 py-4 sm:px-5">
                {!accounts.length ? (
                  <div className="rounded-xl border border-dashed border-border/80 bg-muted/30 p-4 text-sm">
                    <p className="font-medium">Connect a sending account first</p>
                    <p className="mt-1 text-muted-foreground">
                      Link Gmail / Outlook / SMTP so you can send from Chat.
                    </p>
                    <Link
                      href="/email-outreach/accounts"
                      className="mt-3 inline-flex text-sm font-medium underline underline-offset-4"
                    >
                      Open Email accounts
                    </Link>
                  </div>
                ) : null}
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Name (optional)</label>
                  <Input
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="Contact name"
                    disabled={sending}
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Email / Gmail</label>
                  <Input
                    type="email"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder="someone@gmail.com"
                    disabled={sending}
                  />
                </div>
                {accounts.length > 1 ? (
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-muted-foreground">Send from</label>
                    <select
                      value={accountId === "" ? "" : String(accountId)}
                      onChange={(e) =>
                        setAccountId(e.target.value ? Number(e.target.value) : "")
                      }
                      className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      disabled={sending || !accounts.length}
                    >
                      {accounts.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.email_address}
                          {a.is_default ? " (default)" : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                ) : null}
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Subject</label>
                  <Input
                    value={newSubject}
                    onChange={(e) => setNewSubject(e.target.value)}
                    placeholder="Hello"
                    disabled={sending}
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Message</label>
                  <textarea
                    value={newBody}
                    onChange={(e) => setNewBody(e.target.value)}
                    rows={5}
                    placeholder="Write your first message…"
                    className="w-full resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring"
                    disabled={sending}
                  />
                </div>
              </div>
              <footer className="border-t border-border/60 bg-card p-3 sm:p-4">
                <div className="flex justify-end">
                  <Button
                    type="button"
                    onClick={() => void handleStartNewChat()}
                    isLoading={startChat.isPending}
                    disabled={!newEmail.trim() || !newBody.trim() || !accounts.length}
                    className="gap-2"
                  >
                    <Send className="h-4 w-4" />
                    Start chat & send
                  </Button>
                </div>
              </footer>
            </>
          ) : !selectedLeadId ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
              <MessageCircle className="h-12 w-12 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">
                Select a conversation or start a new chat
              </p>
              <Button
                type="button"
                size="sm"
                className="gap-1.5"
                onClick={() => {
                  setShowNewChat(true);
                  setSelectedLeadId(null);
                }}
              >
                <Plus className="h-3.5 w-3.5" />
                New chat
              </Button>
            </div>
          ) : threadLoading && !thread ? (
            <div className="flex flex-1 items-center justify-center p-8 text-sm text-muted-foreground">
              Loading messages…
            </div>
          ) : (
            <>
              <header className="flex items-center justify-between gap-3 border-b border-border/60 bg-card px-4 py-3 sm:px-5">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <PresenceDot
                      online={Boolean(
                        thread?.is_online ?? activeThreadMeta?.is_online
                      )}
                    />
                    <p className="truncate font-semibold tracking-tight">
                      {(() => {
                        const email = (
                          thread?.lead_email ||
                          activeThreadMeta?.lead_email ||
                          ""
                        ).trim();
                        const name = (
                          thread?.lead_name ||
                          activeThreadMeta?.lead_name ||
                          ""
                        ).trim();
                        if (name) return name;
                        if (email.includes("@")) return email.split("@")[0];
                        return email || "Chat";
                      })()}
                    </p>
                  </div>
                  <p className="truncate pl-4 text-xs text-muted-foreground">
                    {thread?.is_online || activeThreadMeta?.is_online
                      ? "online"
                      : formatLastSeen(
                          thread?.last_seen_at ?? activeThreadMeta?.last_seen_at
                        )}
                  </p>
                </div>
                <div className="relative shrink-0">
                  <button
                    type="button"
                    onClick={() => setMenuOpen((v) => !v)}
                    className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground"
                    aria-label="Chat options"
                  >
                    <MoreVertical className="h-4 w-4" />
                  </button>
                  {menuOpen ? (
                    <>
                      <button
                        type="button"
                        className="fixed inset-0 z-10 cursor-default"
                        aria-label="Close menu"
                        onClick={() => setMenuOpen(false)}
                      />
                      <div className="absolute right-0 top-full z-20 mt-1 min-w-[180px] overflow-hidden rounded-lg border border-border bg-card py-1 shadow-lg">
                        <button
                          type="button"
                          className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-muted"
                          onClick={() => {
                            setMenuOpen(false);
                            if (selectedLeadId) void handleDeleteChat(selectedLeadId, false);
                          }}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          Delete chat
                        </button>
                        {activeThreadMeta?.is_manual_chat ? (
                          <button
                            type="button"
                            className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-destructive hover:bg-muted"
                            onClick={() => {
                              setMenuOpen(false);
                              if (selectedLeadId) void handleDeleteChat(selectedLeadId, true);
                            }}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Delete contact
                          </button>
                        ) : null}
                      </div>
                    </>
                  ) : null}
                </div>
              </header>

              <div className="chat-scroll flex-1 space-y-1.5 overflow-y-auto px-4 py-4 sm:px-5">
                {(thread?.messages || []).length === 0 ? (
                  <p className="py-12 text-center text-sm text-muted-foreground">
                    No messages in this thread yet.
                  </p>
                ) : (
                  thread?.messages.map((m) => <MessageBubble key={m.id} message={m} />)
                )}
                <div ref={bottomRef} />
              </div>

              <footer className="shrink-0 border-t border-border/60 bg-card px-3 py-2.5 sm:px-4">
                <div className="space-y-1.5">
                  {accounts.length > 1 ? (
                    <select
                      value={accountId === "" ? "" : String(accountId)}
                      onChange={(e) =>
                        setAccountId(e.target.value ? Number(e.target.value) : "")
                      }
                      className="max-w-xs rounded-lg border border-input bg-background px-2.5 py-1.5 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      disabled={sending}
                    >
                      {accounts.map((a) => (
                        <option key={a.id} value={a.id}>
                          From: {a.email_address}
                          {a.is_default ? " (default)" : ""}
                        </option>
                      ))}
                    </select>
                  ) : null}
                  {pendingFiles.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {pendingFiles.map((file, idx) => (
                        <span
                          key={`${file.name}-${idx}`}
                          className="inline-flex max-w-full items-center gap-1 rounded-full bg-muted px-2 py-1 text-[11px] text-foreground"
                        >
                          <span className="truncate">
                            {file.type.startsWith("audio/")
                              ? "🎤 "
                              : file.type.startsWith("image/")
                                ? "🖼️ "
                                : "📎 "}
                            {file.name}
                          </span>
                          <button
                            type="button"
                            className="rounded-full p-0.5 hover:bg-background"
                            aria-label="Remove file"
                            disabled={sending}
                            onClick={() =>
                              setPendingFiles((prev) => prev.filter((_, i) => i !== idx))
                            }
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  ) : null}
                  {recording ? (
                    <p className="text-[11px] font-medium text-destructive">
                      Recording voice… tap mic to stop
                    </p>
                  ) : null}
                  <div className="flex items-end gap-1.5 sm:gap-2">
                    <input
                      ref={fileInputRef}
                      type="file"
                      className="hidden"
                      multiple
                      accept="image/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.txt,.zip,.rar"
                      onChange={(e) => addFiles(e.target.files)}
                    />
                    <button
                      type="button"
                      disabled={sending}
                      onClick={() => fileInputRef.current?.click()}
                      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-input bg-background text-muted-foreground transition hover:bg-muted hover:text-foreground disabled:opacity-50"
                      title="Attach file or image"
                      aria-label="Attach file"
                    >
                      <Paperclip className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      disabled={sending}
                      onClick={() => void toggleVoice()}
                      className={cn(
                        "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-input transition disabled:opacity-50",
                        recording
                          ? "border-destructive/40 bg-destructive/10 text-destructive"
                          : "bg-background text-muted-foreground hover:bg-muted hover:text-foreground"
                      )}
                      title={recording ? "Stop recording" : "Record voice note"}
                      aria-label={recording ? "Stop recording" : "Record voice"}
                    >
                      {recording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                    </button>
                    <EmojiPickerButton
                      disabled={sending}
                      onPick={(emoji) => setBody((prev) => `${prev}${emoji}`)}
                    />
                    <textarea
                      value={body}
                      onChange={(e) => setBody(e.target.value)}
                      rows={1}
                      placeholder="Write a message…"
                      className="min-h-[36px] max-h-20 flex-1 resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring"
                      disabled={sending}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          if ((body.trim() || pendingFiles.length) && !sending) {
                            void handleManualSend();
                          }
                        }
                      }}
                    />
                    <Button
                      type="button"
                      size="sm"
                      onClick={() => void handleManualSend()}
                      isLoading={sendReply.isPending}
                      disabled={(!body.trim() && pendingFiles.length === 0) || sending}
                      className="h-9 shrink-0 gap-1.5 px-3"
                    >
                      <Send className="h-3.5 w-3.5" />
                      Send
                    </Button>
                  </div>
                </div>
              </footer>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
