"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { toast } from "sonner";
import {
  Database,
  KeyRound,
  Moon,
  Settings,
  Sun,
  User,
  Zap,
  Brain,
  Mail,
  Coins,
  Crown,
  MessageSquare,
} from "lucide-react";
import api from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { useTheme } from "@/components/ThemeProvider";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { PageHeader } from "@/components/PageHeader";
import { getApiBaseUrl } from "@/lib/apiBase";
import { formatDate } from "@/lib/utils";
import type { CVProfile, UsageQuota } from "@/lib/types";

export default function SettingsPage() {
  const { user, fetchUser } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const queryClient = useQueryClient();

  const { data: cvProfile } = useQuery({
    queryKey: ["cv-profile"],
    queryFn: async () => {
      const { data } = await api.get<CVProfile | null>("/cv/profile");
      return data;
    },
    retry: false,
  });

  const { data: usage } = useQuery({
    queryKey: ["usage-quota"],
    queryFn: async () => {
      const { data } = await api.get<UsageQuota>("/settings/usage");
      return data;
    },
    enabled: !!user && user.role !== "admin",
  });

  const requestOwnKeys = useMutation({
    mutationFn: async () => {
      const { data } = await api.post<UsageQuota>("/settings/request-own-api-keys");
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["usage-quota"] });
      fetchUser?.();
      toast.success("Request sent — admin will review");
    },
    onError: () => toast.error("Could not send request"),
  });

  const requestPaid = useMutation({
    mutationFn: async () => {
      const { data } = await api.post<UsageQuota>("/settings/request-paid-plan");
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["usage-quota"] });
      fetchUser?.();
      toast.success("Paid plan request sent — admin will review");
    },
    onError: () => toast.error("Could not send request"),
  });

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await fetch("/health");
      return res.json() as Promise<{ status: string; version?: string }>;
    },
    retry: 1,
  });

  const quota = usage ?? {
    plan: user?.plan || "free",
    daily_token_limit: user?.daily_token_limit ?? 50,
    tokens_used_today: user?.tokens_used_today ?? 0,
    tokens_remaining:
      user?.tokens_remaining ??
      Math.max(0, (user?.daily_token_limit ?? 50) - (user?.tokens_used_today ?? 0)),
    own_api_keys_enabled: !!user?.own_api_keys_enabled,
    own_api_keys_requested: !!user?.own_api_keys_requested,
    paid_plan_requested: !!user?.paid_plan_requested,
    paid_plan_tokens: 500,
    is_unlimited: false,
    api_access: user?.api_access ?? true,
    tokens_reset_on: "",
  };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Account"
        title="Settings"
        description="Account, preferences, and system status"
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Profile
            </CardTitle>
            <CardDescription>Your account information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between border-b border-border py-2">
              <span className="text-sm text-muted-foreground">Name</span>
              <span className="text-sm font-medium">{user?.name || "—"}</span>
            </div>
            <div className="flex justify-between border-b border-border py-2">
              <span className="text-sm text-muted-foreground">Email</span>
              <span className="text-sm font-medium">{user?.email || "—"}</span>
            </div>
            <div className="flex justify-between border-b border-border py-2">
              <span className="text-sm text-muted-foreground">Role</span>
              <Badge>{user?.role || "user"}</Badge>
            </div>
            {user?.created_at && (
              <div className="flex justify-between py-2">
                <span className="text-sm text-muted-foreground">Member since</span>
                <span className="text-sm">{formatDate(user.created_at)}</span>
              </div>
            )}
          </CardContent>
        </Card>

        {user?.role !== "admin" && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Coins className="h-5 w-5" />
                API tokens
              </CardTitle>
              <CardDescription>
                Daily limit for platform APIs. Own keys (if approved) do not use these tokens.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <p className="text-3xl font-semibold tabular-nums">
                    {quota.tokens_used_today}
                    <span className="text-lg font-normal text-muted-foreground">
                      {" "}
                      / {quota.daily_token_limit}
                    </span>
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {quota.tokens_remaining} remaining today · plan{" "}
                    <Badge variant={quota.plan === "paid" ? "success" : "secondary"}>
                      {quota.plan}
                    </Badge>
                  </p>
                </div>
                {!quota.api_access && (
                  <Badge variant="destructive">Platform APIs off</Badge>
                )}
              </div>

              <div className="h-2 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{
                    width: `${Math.min(
                      100,
                      quota.daily_token_limit > 0
                        ? (quota.tokens_used_today / quota.daily_token_limit) * 100
                        : 0
                    )}%`,
                  }}
                />
              </div>

              <div className="flex flex-wrap gap-2">
                {quota.plan !== "paid" && (
                  <Link href="/settings/plans">
                    <Button size="sm" className="gap-1.5">
                      <Crown className="h-3.5 w-3.5" />
                      Purchase Pro Plan
                    </Button>
                  </Link>
                )}
                {quota.plan !== "paid" && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={requestPaid.isPending || !!quota.paid_plan_requested}
                    onClick={() => requestPaid.mutate()}
                  >
                    {quota.paid_plan_requested
                      ? "Paid plan requested"
                      : `Request paid (${quota.paid_plan_tokens}/day)`}
                  </Button>
                )}
                {quota.own_api_keys_enabled ? (
                  <Link href="/settings/apis">
                    <Button size="sm">Manage my API keys</Button>
                  </Link>
                ) : (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={requestOwnKeys.isPending || !!quota.own_api_keys_requested}
                    onClick={() => requestOwnKeys.mutate()}
                  >
                    {quota.own_api_keys_requested
                      ? "Own APIs requested"
                      : "Request own API keys"}
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Preferences
            </CardTitle>
            <CardDescription>App appearance and defaults</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-lg border border-border p-4">
              <div className="flex items-center gap-3">
                {theme === "dark" ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
                <div>
                  <p className="text-sm font-medium">Theme</p>
                  <p className="text-xs text-muted-foreground">
                    {theme === "dark" ? "Dark mode" : "Light mode"}
                  </p>
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={toggleTheme}>
                Toggle
              </Button>
            </div>
            {user?.role === "admin" && (
              <div className="flex items-center justify-between rounded-lg border border-border p-4">
                <div className="flex items-center gap-3">
                  <Database className="h-5 w-5" />
                  <div>
                    <p className="text-sm font-medium">Lead Database</p>
                    <p className="text-xs text-muted-foreground">
                      Background leads + total count in DB (leadgen.db)
                    </p>
                  </div>
                </div>
                <Link href="/settings/database">
                  <Button variant="outline" size="sm">
                    View
                  </Button>
                </Link>
              </div>
            )}
            {user?.role === "admin" && (
              <div className="flex items-center justify-between rounded-lg border border-border p-4">
                <div className="flex items-center gap-3">
                  <KeyRound className="h-5 w-5" />
                  <div>
                    <p className="text-sm font-medium">API Keys</p>
                    <p className="text-xs text-muted-foreground">
                      Apify & Groq — platform keys used by all users
                    </p>
                  </div>
                </div>
                <Link href="/admin/apis">
                  <Button variant="outline" size="sm">
                    Manage
                  </Button>
                </Link>
              </div>
            )}
            {user?.role !== "admin" && quota.own_api_keys_enabled && (
              <div className="flex items-center justify-between rounded-lg border border-border p-4">
                <div className="flex items-center gap-3">
                  <KeyRound className="h-5 w-5" />
                  <div>
                    <p className="text-sm font-medium">My API Keys</p>
                    <p className="text-xs text-muted-foreground">
                      Your Apify & Groq keys — no daily token charge
                    </p>
                  </div>
                </div>
                <Link href="/settings/apis">
                  <Button variant="outline" size="sm">
                    Manage
                  </Button>
                </Link>
              </div>
            )}
            <div className="flex items-center justify-between rounded-lg border border-border p-4">
              <div className="flex items-center gap-3">
                <Brain className="h-5 w-5" />
                <div>
                  <p className="text-sm font-medium">CV & Brain</p>
                  <p className="text-xs text-muted-foreground">
                    {cvProfile
                      ? "CV uploaded — manage profile & generate Brain"
                      : "Upload CV and generate AI Brain"}
                  </p>
                </div>
              </div>
              <Link href="/brain">
                <Button variant="outline" size="sm">
                  Open
                </Button>
              </Link>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-border p-4">
              <div className="flex items-center gap-3">
                <MessageSquare className="h-5 w-5" />
                <div>
                  <p className="text-sm font-medium">WhatsApp Web + AI</p>
                  <p className="text-xs text-muted-foreground">
                    QR connect phone — auto-reply from your Saved leads & Brain
                  </p>
                </div>
              </div>
              <Link href="/settings/whatsapp-web">
                <Button variant="outline" size="sm">
                  Connect
                </Button>
              </Link>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-border p-4">
              <div className="flex items-center gap-3">
                <Mail className="h-5 w-5" />
                <div>
                  <p className="text-sm font-medium">Email Outreach</p>
                  <p className="text-xs text-muted-foreground">
                    {user?.role === "admin"
                      ? "Platform-wide automation limits for all users"
                      : "Connect your email on the Email Outreach page"}
                  </p>
                </div>
              </div>
              <Link href={user?.role === "admin" ? "/admin/outreach" : "/email-outreach/accounts"}>
                <Button variant="outline" size="sm">
                  {user?.role === "admin" ? "Manage" : "Connect email"}
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              System Status
            </CardTitle>
            <CardDescription>Backend and API connectivity</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-lg border border-border p-4">
                <p className="text-sm text-muted-foreground">API Server</p>
                <div className="mt-1 flex items-center gap-2">
                  <Badge
                    variant={
                      healthLoading
                        ? "secondary"
                        : health?.status === "healthy"
                          ? "success"
                          : "destructive"
                    }
                  >
                    {healthLoading ? "Checking..." : health?.status === "healthy" ? "Online" : "Offline"}
                  </Badge>
                </div>
              </div>
              <div className="rounded-lg border border-border p-4">
                <p className="text-sm text-muted-foreground">API URL</p>
                <p className="mt-1 truncate text-sm font-mono">
                  {getApiBaseUrl()}
                </p>
              </div>
              <div className="rounded-lg border border-border p-4">
                <p className="text-sm text-muted-foreground">Version</p>
                <p className="mt-1 text-sm font-medium">{health?.version || "—"}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
