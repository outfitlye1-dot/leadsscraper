"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { FileUp, Database, KeyRound, Moon, Settings, Sun, User, Zap, Brain, Mail } from "lucide-react";
import api from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { useTheme } from "@/components/ThemeProvider";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { PageHeader } from "@/components/PageHeader";
import { getApiBaseUrl } from "@/lib/apiBase";
import { formatDate } from "@/lib/utils";
import type { CVProfile } from "@/lib/types";

export default function SettingsPage() {
  const { user } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const { data: cvProfile } = useQuery({
    queryKey: ["cv-profile"],
    queryFn: async () => {
      const { data } = await api.get<CVProfile | null>("/cv/profile");
      return data;
    },
    retry: false,
  });

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await fetch("/health");
      return res.json() as Promise<{ status: string; version?: string }>;
    },
    retry: 1,
  });

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
            <div className="flex items-center justify-between rounded-lg border border-border p-4">
              <div className="flex items-center gap-3">
                <KeyRound className="h-5 w-5" />
                <div>
                  <p className="text-sm font-medium">API Keys</p>
                  <p className="text-xs text-muted-foreground">
                    Apify & Groq — bulk add, auto rotation, private to your account
                  </p>
                </div>
              </div>
              <Link href="/settings/apis">
                <Button variant="outline" size="sm">
                  Manage
                </Button>
              </Link>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-border p-4">
              <div className="flex items-center gap-3">
                <FileUp className="h-5 w-5" />
                <div>
                  <p className="text-sm font-medium">CV Profile</p>
                  <p className="text-xs text-muted-foreground">
                    {cvProfile ? "Uploaded — used for AI messages" : "Not uploaded yet"}
                  </p>
                </div>
              </div>
              <Link href="/cv">
                <Button variant="outline" size="sm">
                  {cvProfile ? "Manage" : "Upload"}
                </Button>
              </Link>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-border p-4">
              <div className="flex items-center gap-3">
                <Mail className="h-5 w-5" />
                <div>
                  <p className="text-sm font-medium">Email Outreach</p>
                  <p className="text-xs text-muted-foreground">
                    Automation limits, Gmail, working hours, auto-send
                  </p>
                </div>
              </div>
              <Link href="/settings/email-outreach">
                <Button variant="outline" size="sm">
                  Configure
                </Button>
              </Link>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-border p-4">
              <div className="flex items-center gap-3">
                <Brain className="h-5 w-5" />
                <div>
                  <p className="text-sm font-medium">AI Brain</p>
                  <p className="text-xs text-muted-foreground">Outreach system prompt & profile</p>
                </div>
              </div>
              <Link href="/brain">
                <Button variant="outline" size="sm">
                  Open
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
