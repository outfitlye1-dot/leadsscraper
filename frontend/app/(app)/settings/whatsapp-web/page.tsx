"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  ArrowLeft,
  Loader2,
  MessageSquare,
  QrCode,
  RefreshCw,
  RotateCcw,
  Square,
  Zap,
} from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/hooks/useAuth";
import {
  useWhatsAppWebJobs,
  useWhatsAppWebLaunchChrome,
  useWhatsAppWebPairCode,
  useWhatsAppWebReadPairCode,
  useWhatsAppWebRefreshQr,
  useWhatsAppWebReset,
  useWhatsAppWebStart,
  useWhatsAppWebStatus,
  useWhatsAppWebStop,
  useWhatsAppWebUpdateSettings,
} from "@/hooks/useWhatsAppWeb";
import { formatApiError } from "@/lib/utils";

export default function WhatsAppWebSettingsPage() {
  const { user } = useAuth();
  const { data: status, isLoading, error, refetch } = useWhatsAppWebStatus();
  const start = useWhatsAppWebStart();
  const stop = useWhatsAppWebStop();
  const refreshQr = useWhatsAppWebRefreshQr();
  const reset = useWhatsAppWebReset();
  const pairCode = useWhatsAppWebPairCode();
  const readPairCode = useWhatsAppWebReadPairCode();
  const launchChrome = useWhatsAppWebLaunchChrome();
  const updateSettings = useWhatsAppWebUpdateSettings();
  const { data: jobs } = useWhatsAppWebJobs(15, Boolean(status?.enabled));
  const [qr, setQr] = useState<string | null>(null);
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState<string | null>(null);

  useEffect(() => {
    if (status?.logged_in) setQr(null);
  }, [status?.logged_in]);

  const applyStartResult = (data: {
    qr_data_url?: string | null;
    message?: string | null;
    logged_in?: boolean;
  }) => {
    if (data.qr_data_url) setQr(data.qr_data_url);
    else if (data.logged_in) setQr(null);
    toast.success(data.message || "Done");
    void refetch();
  };

  const onConnect = async () => {
    try {
      const data = await start.mutateAsync();
      applyStartResult(data);
    } catch (err) {
      toast.error(formatApiError(err, "Connect failed — restart backend and try again"));
    }
  };

  const onRefreshQr = async () => {
    try {
      const data = await refreshQr.mutateAsync();
      applyStartResult(data);
    } catch (err) {
      toast.error(formatApiError(err, "Refresh QR failed — Open Chrome for link, phir dubara try"));
    }
  };

  const onStop = async () => {
    try {
      const data = await stop.mutateAsync();
      toast.success(data.message || "Worker stopped");
      void refetch();
    } catch (err) {
      toast.error(formatApiError(err, "Stop failed"));
    }
  };

  const onReset = async () => {
    if (!confirm("Reset WhatsApp Web session? Old link clear hoga — naya QR milega.")) return;
    try {
      const data = await reset.mutateAsync();
      setCode(null);
      applyStartResult(data);
    } catch (err) {
      toast.error(formatApiError(err, "Reset failed"));
    }
  };

  const onPairCode = async () => {
    try {
      const data = await pairCode.mutateAsync(phone);
      if (data.pair_code) setCode(data.pair_code);
      if (data.logged_in) setQr(null);
      toast.success(data.message || "Pair code ready");
      void refetch();
    } catch (err) {
      toast.error(formatApiError(err, "Pair code failed"));
    }
  };

  const onReadPairCode = async () => {
    try {
      const data = await readPairCode.mutateAsync();
      if (data.pair_code) setCode(data.pair_code);
      if (data.logged_in) {
        setQr(null);
        setCode(null);
      }
      toast.success(data.message || "Code read");
      void refetch();
    } catch (err) {
      toast.error(formatApiError(err, "No code on Chrome screen yet"));
    }
  };

  const onLaunchChrome = async () => {
    try {
      const data = await launchChrome.mutateAsync();
      if (!data.ok) {
        toast.error(data.message || "Chrome start failed");
        return;
      }
      // Chrome pe pehle se linked ho to backend attach kar deta hai; warna Connect.
      if (data.logged_in) {
        toast.success(data.message || "Connected — AI on");
        setQr(null);
        void refetch();
        return;
      }
      toast.success(data.message || "Chrome opened — ab Connect dabao");
      try {
        const connected = await start.mutateAsync();
        applyStartResult(connected);
      } catch (connectErr) {
        toast.message(
          "Chrome open hai. Us window mein chats dikhne ke baad Connect / Start AI dabao."
        );
        void refetch();
      }
    } catch (err) {
      toast.error(formatApiError(err, "Chrome launch failed — close all Chrome and retry"));
    }
  };

  const toggleAutoReply = async () => {
    const next = !(status?.auto_reply ?? true);
    try {
      await updateSettings.mutateAsync({ auto_reply: next });
      toast.success(next ? "AI auto-reply on" : "AI auto-reply off");
      void refetch();
    } catch (err) {
      toast.error(formatApiError(err, "Could not update settings"));
    }
  };

  const toggleIgnoreGroups = async () => {
    const next = !(status?.ignore_groups ?? true);
    try {
      await updateSettings.mutateAsync({ ignore_groups: next });
      toast.success(next ? "Groups ignored" : "Groups allowed");
      void refetch();
    } catch (err) {
      toast.error(formatApiError(err, "Could not update settings"));
    }
  };

  const toggleDailyOutreach = async () => {
    const next = !(status?.daily_outreach_enabled ?? false);
    try {
      await updateSettings.mutateAsync({ daily_outreach_enabled: next });
      toast.success(next ? "Daily outreach on" : "Daily outreach off");
      void refetch();
    } catch (err) {
      toast.error(formatApiError(err, "Could not update settings"));
    }
  };

  const saveDailyLimit = async (raw: string) => {
    const n = Math.max(1, Math.min(10, Number.parseInt(raw, 10) || 5));
    try {
      await updateSettings.mutateAsync({ daily_outreach_limit: n });
      toast.success(`Daily limit set to ${n}`);
      void refetch();
    } catch (err) {
      toast.error(formatApiError(err, "Could not update daily limit"));
    }
  };

  const busy =
    start.isPending ||
    stop.isPending ||
    refreshQr.isPending ||
    reset.isPending ||
    pairCode.isPending ||
    readPairCode.isPending ||
    launchChrome.isPending;

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-3">
        <Link href="/settings">
          <Button variant="outline" size="sm" className="gap-1.5">
            <ArrowLeft className="h-3.5 w-3.5" />
            Settings
          </Button>
        </Link>
      </div>

      <PageHeader
        eyebrow="WhatsApp Web"
        title="Connect & AI auto-reply"
        description="Saved lead (phone match) → professional Brain reply. Unknown chat → friendly sales reply. Test personal chats (e.g. Hamza) lead nahi hote jab tak number Saved lead se match na ho."
      />
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Status
          </CardTitle>
          <CardDescription>
            Owner is taken from your current login ({user?.email || "—"}). AI pehle message read
            karti hai, phir reply: Saved lead → professional, random → friendly AI (koi fixed
            script nahi). Cloud API alag hai.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Checking…</p>
          ) : error ? (
            <p className="text-sm text-destructive">{formatApiError(error)}</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              <Badge variant={status?.enabled ? "success" : "destructive"}>
                {status?.enabled ? "Enabled" : "Disabled in .env"}
              </Badge>
              <Badge variant={status?.logged_in ? "success" : "secondary"}>
                {status?.logged_in ? "WhatsApp linked" : "Not linked"}
              </Badge>
              <Badge variant={status?.worker_running ? "success" : "secondary"}>
                {status?.worker_running ? "AI worker on" : "AI worker off"}
              </Badge>
              <Badge variant={status?.auto_reply ? "success" : "secondary"}>
                Auto-reply {status?.auto_reply ? "on" : "off"}
              </Badge>
              <Badge
                variant={status?.daily_outreach_enabled ? "success" : "secondary"}
              >
                Daily outreach{" "}
                {status?.daily_outreach_enabled
                  ? `${status?.daily_outreach_sent_count ?? 0}/${status?.daily_outreach_limit ?? 5}`
                  : "off"}
              </Badge>
            </div>
          )}

          {(status?.owner_email || user?.email) && (
            <p className="text-sm text-muted-foreground">
              AI owner:{" "}
              <span className="font-medium text-foreground">
                {status?.owner_email || user?.email}
              </span>
            </p>
          )}

          {status?.message && (
            <p className="text-sm text-muted-foreground">{status.message}</p>
          )}

          {status?.browser_started && !status?.logged_in && (
            <p className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm">
              Chrome/app attach ho chuka hai magar chats detect nahi hui. WhatsApp Business wali{" "}
              <strong>alag Chrome window</strong> open rakho (left side pe chats), phir{" "}
              <strong>Connect / Start AI</strong> dubara dabao. LeadGen wali tab alag hai — usme
              WhatsApp chalna enough nahi.
            </p>
          )}

          {!status?.enabled && (
            <div className="space-y-2 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm">
              <p className="font-medium text-foreground">
                WhatsApp Web AI is off on the live server (Railway).
              </p>
              <p className="text-muted-foreground">
                Railway pe Chrome/QR nahi chal sakta. Live site pe messages ke liye{" "}
                <strong>Cloud API</strong> (Messages page) use karo.
              </p>
              <p className="text-muted-foreground">
                Web AI + daily outreach ke liye app <strong>is PC pe local</strong> chalao:
                backend <code className="text-xs">WA_WEB_ENABLED=true</code> (already in{" "}
                <code className="text-xs">backend/.env</code>), then{" "}
                <code className="text-xs">http://localhost:3000</code> se Connect karo.
              </p>
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            <Button
              onClick={() => void onConnect()}
              disabled={!status?.enabled || busy}
              className="gap-1.5"
            >
              {start.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <QrCode className="h-4 w-4" />
              )}
              Connect / Start AI
            </Button>
            <Button
              variant="outline"
              onClick={() => void onRefreshQr()}
              disabled={!status?.enabled || busy || !!status?.logged_in}
              className="gap-1.5"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh QR
            </Button>
            <Button
              variant="outline"
              onClick={() => void onReset()}
              disabled={!status?.enabled || busy}
              className="gap-1.5"
            >
              <RotateCcw className="h-4 w-4" />
              Reset session
            </Button>
            <Button
              variant="outline"
              onClick={() => void onStop()}
              disabled={!status?.enabled || busy || !status?.worker_running}
              className="gap-1.5"
            >
              <Square className="h-4 w-4" />
              Stop AI
            </Button>
            <Button
              variant="outline"
              onClick={() => void toggleAutoReply()}
              disabled={!status?.enabled || updateSettings.isPending}
              className="gap-1.5"
            >
              <Zap className="h-4 w-4" />
              Auto-reply {status?.auto_reply ? "Off" : "On"}
            </Button>
            <Button
              variant="outline"
              onClick={() => void toggleIgnoreGroups()}
              disabled={!status?.enabled || updateSettings.isPending}
            >
              Groups {status?.ignore_groups ? "ignored" : "allowed"}
            </Button>
            <Button
              variant="outline"
              onClick={() => void toggleDailyOutreach()}
              disabled={!status?.enabled || updateSettings.isPending}
              className="gap-1.5"
            >
              Daily outreach {status?.daily_outreach_enabled ? "Off" : "On"}
            </Button>
          </div>

          <div className="rounded-lg border border-border bg-muted/30 p-4 space-y-3">
            <div>
              <p className="text-sm font-medium">Daily outreach to Saved leads</p>
              <p className="text-xs text-muted-foreground mt-1">
                Sends a personalized English AI opener via WhatsApp Web to up to N saved leads
                with phone (skips leads already messaged). Limit 1–10, default 5.{" "}
                <strong>1 message every {status?.daily_outreach_interval_minutes ?? 60} min</strong>{" "}
                (not back-to-back). Sent today:{" "}
                {status?.daily_outreach_sent_count ?? 0}/{status?.daily_outreach_limit ?? 5}
                {typeof status?.daily_outreach_remaining === "number"
                  ? ` (${status.daily_outreach_remaining} left)`
                  : ""}
                .
              </p>
            </div>
            <div className="flex flex-wrap items-end gap-3">
              <label className="space-y-1.5 text-sm">
                <span className="text-muted-foreground">Leads per day (1–10)</span>
                <Input
                  type="number"
                  min={1}
                  max={10}
                  className="w-28"
                  defaultValue={status?.daily_outreach_limit ?? 5}
                  key={`daily-limit-${status?.daily_outreach_limit ?? 5}`}
                  disabled={!status?.enabled || updateSettings.isPending}
                  onBlur={(e) => void saveDailyLimit(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.currentTarget.blur();
                    }
                  }}
                />
              </label>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>WhatsApp Business link (important)</CardTitle>
          <CardDescription>
            Automated Playwright Chrome pe Business aksar “Couldn’t link” deta hai. Real Chrome + CDP
            use karo — pehle khud link, phir app Connect kare.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <ol className="list-decimal space-y-1.5 pl-5 text-sm text-muted-foreground">
            <li>Pehle saari normal Chrome windows band karo</li>
            <li>
              <strong>Open Chrome for link</strong> dabao — alag Chrome window (tab nahi) khulegi
            </li>
            <li>Us Chrome mein Business link karo jab tak left side pe chats dikhen</li>
            <li>
              App status pe <strong>Linked</strong> / <strong>Attached to real Chrome</strong> aana
              chahiye. Na aaye to <strong>Connect / Start AI</strong> dabao
            </li>
          </ol>
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={() => void onLaunchChrome()}
              disabled={!status?.enabled || busy}
              className="gap-1.5"
            >
              {launchChrome.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Open Chrome for link
            </Button>
            <Badge variant={status?.cdp_configured ? "success" : "secondary"}>
              CDP {status?.cdp_configured ? "configured" : "off"}
            </Badge>
            <Badge variant={status?.cdp_alive ? "success" : "secondary"}>
              {status?.cdp_alive ? "Chrome debug live" : "Chrome debug off"}
            </Badge>
            <Badge variant={status?.cdp_mode ? "success" : "secondary"}>
              {status?.cdp_mode ? "Attached to real Chrome" : "Not attached"}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            Cloud API (Messages page) alag hai — official Meta send ke liye. Web AI auto-reply ke liye
            upar wala link zaroori hai.
          </p>
          <div className="border-t border-border pt-3">
            <p className="mb-2 text-sm font-medium">Optional: pair code (agar Chrome pe code dikhe)</p>
            <div className="flex flex-wrap gap-2">
              <Input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="923001234567"
                className="max-w-xs"
              />
              <Button
                variant="outline"
                onClick={() => void onPairCode()}
                disabled={!status?.enabled || busy || phone.trim().length < 10}
              >
                {pairCode.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Auto get code
              </Button>
              <Button onClick={() => void onReadPairCode()} disabled={!status?.enabled || busy}>
                {readPairCode.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Read code from Chrome
              </Button>
            </div>
            {code ? (
              <p className="mt-2 text-2xl font-semibold tracking-[0.35em]">{code}</p>
            ) : null}
          </div>
        </CardContent>
      </Card>

      {(qr || (!status?.logged_in && status?.browser_started)) && (
        <Card>
          <CardHeader>
            <CardTitle>Scan QR</CardTitle>
            <CardDescription>
              Phone → WhatsApp → Linked devices → Link a device. Agar QR yahan na dikhe to pehle Chromium
              window mein WhatsApp load hone do, phir Refresh QR.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {qr ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={qr}
                alt="WhatsApp Web QR"
                className="mx-auto max-w-[280px] rounded-lg border border-border bg-white p-3"
              />
            ) : (
              <p className="text-sm text-muted-foreground">
                QR abhi ready nahi — browser window check karo, 10–20s wait, phir{" "}
                <button
                  type="button"
                  className="underline underline-offset-2"
                  onClick={() => void onRefreshQr()}
                  disabled={busy}
                >
                  Refresh QR
                </button>
                .
              </p>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Recent auto-replies</CardTitle>
          <CardDescription>
            Saved leads → professional. Unknown numbers → friendly. FAILED means send/AI error
            (details under each row).
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!jobs?.length ? (
            <p className="text-sm text-muted-foreground">No jobs yet.</p>
          ) : (
            <ul className="divide-y divide-border">
              {jobs.map((job) => (
                <li key={job.id} className="flex flex-col gap-1 py-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{job.chat_title || "Chat"}</p>
                    <p className="truncate text-xs text-muted-foreground">{job.body}</p>
                    {job.reply_body && (
                      <p className="mt-1 truncate text-xs text-foreground/80">→ {job.reply_body}</p>
                    )}
                    {job.error_message && (
                      <p className="mt-1 text-xs text-destructive">{job.error_message}</p>
                    )}
                  </div>
                    <div className="flex shrink-0 items-center gap-2">
                    <Badge variant={job.lead_id ? "success" : "secondary"}>
                      {job.lead_id ? "Lead" : "Random"}
                    </Badge>
                    <Badge
                      variant={
                        job.status === "failed"
                          ? "destructive"
                          : job.ai_replied || job.status === "done"
                            ? "success"
                            : "secondary"
                      }
                    >
                      {job.status}
                    </Badge>
                    {job.lead_id ? (
                      <Link href={`/leads/${job.lead_id}`} className="text-xs text-muted-foreground underline">
                        Lead #{job.lead_id}
                      </Link>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
