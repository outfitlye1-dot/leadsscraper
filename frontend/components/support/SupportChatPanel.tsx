"use client";

import { type MouseEvent, type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { Send, Shield, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/Button";
import {
  useAdminSupportThread,
  useDeleteSupportMessage,
  useMySupportThread,
  useSendSupportMessage,
} from "@/hooks/useSupportChat";
import type { SupportMessage, SupportThread } from "@/lib/types";
import { cn, formatApiError } from "@/lib/utils";

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

function formatBubbleTime(value: string | null | undefined) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function SupportAvatar({
  name,
  email,
  avatarUrl,
  active = false,
  icon,
}: {
  name: string;
  email?: string | null;
  avatarUrl?: string | null;
  active?: boolean;
  icon?: ReactNode;
}) {
  const initials = getThreadInitials(name, email);
  const [imageFailed, setImageFailed] = useState(false);
  const showImage = Boolean(avatarUrl) && !imageFailed;

  useEffect(() => {
    setImageFailed(false);
  }, [avatarUrl]);

  if (showImage) {
    return (
      <img
        src={avatarUrl || undefined}
        alt={name || "User"}
        className="h-9 w-9 shrink-0 rounded-full object-cover"
        onError={() => setImageFailed(true)}
      />
    );
  }
  return (
    <div
      className={cn(
        "flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold",
        active ? "bg-background/15 text-background" : "bg-primary/10 text-foreground"
      )}
    >
      {icon ?? initials}
    </div>
  );
}

function SupportMessageBubble({
  message,
  canDelete,
  deleting,
  onDelete,
}: {
  message: SupportMessage;
  canDelete: boolean;
  deleting?: boolean;
  onDelete?: () => void;
}) {
  const outbound = message.direction === "outbound";
  const [menu, setMenu] = useState<{ x: number; y: number } | null>(null);

  useEffect(() => {
    if (!menu) return;
    const close = () => setMenu(null);
    window.addEventListener("click", close);
    window.addEventListener("scroll", close, true);
    window.addEventListener("resize", close);
    return () => {
      window.removeEventListener("click", close);
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("resize", close);
    };
  }, [menu]);

  const handleContextMenu = (event: MouseEvent) => {
    if (!canDelete) return;
    event.preventDefault();
    setMenu({ x: event.clientX, y: event.clientY });
  };

  return (
    <>
      <div className={cn("flex w-full", outbound ? "justify-end" : "justify-start")}>
        <div className={cn("flex max-w-[min(85%,26rem)] flex-col", outbound ? "items-end" : "items-start")}>
          <div
            onContextMenu={handleContextMenu}
            className={cn(
              "w-fit max-w-full rounded-lg px-[9px] py-[6px] shadow-sm",
              canDelete && "cursor-context-menu",
              outbound
                ? "rounded-br-[4px] bg-foreground text-background"
                : "rounded-bl-[4px] bg-muted/80 text-foreground ring-1 ring-border/50"
            )}
          >
            <p className="whitespace-pre-wrap break-words text-[14.2px] font-normal leading-[19px]">
              {message.body_text}
            </p>
          </div>
          <div className="mt-0.5 px-0.5 text-[10px] leading-none text-muted-foreground">
            {formatBubbleTime(message.sent_at)}
          </div>
        </div>
      </div>

      {menu ? (
        <div
          className="fixed z-50 min-w-[140px] overflow-hidden rounded-lg border border-border bg-card py-1 shadow-lg"
          style={{ left: menu.x, top: menu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            disabled={deleting}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-destructive hover:bg-muted disabled:opacity-50"
            onClick={() => {
              setMenu(null);
              onDelete?.();
            }}
          >
            <Trash2 className="h-3.5 w-3.5" />
            Delete
          </button>
        </div>
      ) : null}
    </>
  );
}

export function SupportSidebarItem({
  active,
  unread = 0,
  onSelect,
}: {
  active: boolean;
  unread?: number;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-left transition",
        active ? "bg-foreground text-background" : "hover:bg-muted/70"
      )}
    >
      <SupportAvatar
        name="Admin Support"
        active={active}
        icon={<Shield className="h-4 w-4" />}
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className={cn("truncate text-sm font-semibold", active ? "text-background" : "text-foreground")}>
            Admin Support
          </p>
          {unread > 0 ? (
            <span className="shrink-0 rounded-full bg-emerald-500 px-1.5 py-0.5 text-[10px] font-semibold text-white">
              {unread}
            </span>
          ) : null}
        </div>
        <p className={cn("truncate text-[10px]", active ? "text-background/60" : "text-muted-foreground")}>
          Direct chat — no email needed
        </p>
      </div>
    </button>
  );
}

export function SupportUserThreadItem({
  thread,
  active,
  onSelect,
}: {
  thread: SupportThread;
  active: boolean;
  onSelect: () => void;
}) {
  const unread = thread.unread_count ?? 0;

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-left transition",
        active ? "bg-foreground text-background" : "hover:bg-muted/70"
      )}
    >
      <SupportAvatar
        name={thread.user_name}
        email={thread.user_email}
        avatarUrl={thread.user_avatar_url}
        active={active}
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className={cn("truncate text-sm font-semibold", active ? "text-background" : "text-foreground")}>
            {thread.user_name}
          </p>
          {unread > 0 ? (
            <span className="shrink-0 rounded-full bg-emerald-500 px-1.5 py-0.5 text-[10px] font-semibold text-white">
              {unread}
            </span>
          ) : null}
        </div>
        <p className={cn("truncate text-[10px]", active ? "text-background/60" : "text-muted-foreground")}>
          {thread.last_preview || thread.user_email || "No messages yet"}
        </p>
      </div>
    </button>
  );
}

export function SupportChatPanel({
  isAdmin,
  targetUserId,
}: {
  isAdmin: boolean;
  targetUserId: number | null;
}) {
  const [body, setBody] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const sendMessage = useSendSupportMessage();
  const deleteMessage = useDeleteSupportMessage();
  const myThread = useMySupportThread(!isAdmin);
  const adminThread = useAdminSupportThread(isAdmin ? targetUserId : null, isAdmin && targetUserId != null);

  const detail = isAdmin ? adminThread.data : myThread.data;
  const loading = isAdmin ? adminThread.isLoading : myThread.isLoading;
  const messages = detail?.messages ?? [];

  useEffect(() => {
    setBody("");
  }, [detail?.user_id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, detail?.user_id]);

  const title = useMemo(() => {
    if (isAdmin) return detail?.user_name || "User support";
    return "Admin Support";
  }, [detail?.user_name, isAdmin]);

  const subtitle = useMemo(() => {
    if (isAdmin) return detail?.user_email || "In-app support chat";
    return "Message admin directly — no email account needed";
  }, [detail?.user_email, isAdmin]);

  const handleSend = async () => {
    const text = body.trim();
    if (!text) return;
    try {
      await sendMessage.mutateAsync({
        body: text,
        userId: isAdmin && targetUserId != null ? targetUserId : undefined,
      });
      setBody("");
    } catch (err) {
      toast.error(formatApiError(err, "Failed to send message"));
    }
  };

  const handleDelete = async (message: SupportMessage) => {
    if (!window.confirm("Delete this message?")) return;
    try {
      await deleteMessage.mutateAsync({
        messageId: message.id,
        userId: isAdmin && targetUserId != null ? targetUserId : undefined,
      });
      toast.success("Message deleted");
    } catch (err) {
      toast.error(formatApiError(err, "Failed to delete message"));
    }
  };

  if (isAdmin && !targetUserId) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
        <Shield className="h-12 w-12 text-muted-foreground/40" />
        <p className="text-sm text-muted-foreground">Select a user support chat from the sidebar</p>
      </div>
    );
  }

  if (loading && !detail) {
    return (
      <div className="flex flex-1 items-center justify-center p-8 text-sm text-muted-foreground">
        Loading support chat…
      </div>
    );
  }

  return (
    <>
      <header className="flex items-center justify-between gap-3 border-b border-border/60 bg-card px-4 py-3 sm:px-5">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <div className="shrink-0">
              <SupportAvatar
                name={detail?.user_name || "Admin Support"}
                email={detail?.user_email}
                avatarUrl={isAdmin ? detail?.user_avatar_url : undefined}
                icon={!isAdmin ? <Shield className="h-4 w-4" /> : undefined}
              />
            </div>
            <p className="truncate font-semibold tracking-tight">{title}</p>
          </div>
          <p className="truncate pl-10 text-xs text-muted-foreground">{subtitle}</p>
        </div>
      </header>

      <div className="chat-scroll flex-1 space-y-1.5 overflow-y-auto px-4 py-4 sm:px-5">
        {messages.length === 0 ? (
          <p className="py-12 text-center text-sm text-muted-foreground">
            {isAdmin
              ? "No messages yet. Reply to help this user."
              : "Say hello to admin — your message appears here instantly."}
          </p>
        ) : (
          messages.map((message) => (
            <SupportMessageBubble
              key={message.id}
              message={message}
              canDelete={message.direction === "outbound" || isAdmin}
              deleting={deleteMessage.isPending}
              onDelete={() => void handleDelete(message)}
            />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      <footer className="shrink-0 border-t border-border/60 bg-card px-3 py-2.5 sm:px-4">
        <div className="flex items-end gap-2">
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={1}
            placeholder={isAdmin ? "Reply to user…" : "Message admin…"}
            className="min-h-[36px] max-h-20 flex-1 resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring"
            disabled={sendMessage.isPending}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (body.trim() && !sendMessage.isPending) {
                  void handleSend();
                }
              }
            }}
          />
          <Button
            type="button"
            size="sm"
            onClick={() => void handleSend()}
            isLoading={sendMessage.isPending}
            disabled={!body.trim()}
            className="h-9 shrink-0 gap-1.5 px-3"
          >
            <Send className="h-3.5 w-3.5" />
            Send
          </Button>
        </div>
      </footer>
    </>
  );
}
