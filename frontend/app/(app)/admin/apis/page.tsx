"use client";

import { useState } from "react";
import {
  KeyRound,
  Loader2,
  Plus,
  RefreshCw,
  Trash2,
} from "lucide-react";
import {
  useBulkCreateUserApiKeys,
  useDeleteUserApiKey,
  useResetExhaustedApiKeys,
  useUpdateUserApiKey,
  useUserApiKeys,
} from "@/hooks/useUserApiKeys";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { PageHeader } from "@/components/PageHeader";
import { Textarea } from "@/components/ui/Textarea";
import { formatDate } from "@/lib/utils";
import type { ApiProvider, ApiKeyStatus, UserApiKey } from "@/lib/types";

const PROVIDERS: {
  id: ApiProvider;
  title: string;
  description: string;
  placeholder: string;
  docsUrl: string;
}[] = [
  {
    id: "apify",
    title: "Apify",
    description:
      "Platform keys for Google Maps scraping. All users share this pool — when one key hits its limit, the next is used automatically.",
    placeholder: "apify_api_xxxxxxxxxxxxxxxx\napify_api_yyyyyyyyyyyyyyyy",
    docsUrl: "https://console.apify.com/account/integrations",
  },
  {
    id: "groq",
    title: "Groq",
    description:
      "Platform keys for AI messages, CV parsing, and scrape suggestions. Shared by all users with auto rotation.",
    placeholder: "gsk_xxxxxxxxxxxxxxxx\ngsk_yyyyyyyyyyyyyyyy",
    docsUrl: "https://console.groq.com/keys",
  },
];

function statusVariant(status: ApiKeyStatus): "success" | "warning" | "destructive" {
  if (status === "active") return "success";
  if (status === "exhausted") return "warning";
  return "destructive";
}

function ProviderSection({ provider }: { provider: (typeof PROVIDERS)[number] }) {
  const { data: keys = [], isLoading } = useUserApiKeys(provider.id);
  const bulkCreate = useBulkCreateUserApiKeys();
  const deleteKey = useDeleteUserApiKey();
  const updateKey = useUpdateUserApiKey();
  const resetExhausted = useResetExhaustedApiKeys();
  const [bulkText, setBulkText] = useState("");
  const [error, setError] = useState<string | null>(null);

  const activeCount = keys.filter((k) => k.status === "active").length;
  const exhaustedCount = keys.filter((k) => k.status === "exhausted").length;

  const handleBulkAdd = async () => {
    setError(null);
    const lines = bulkText
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    if (!lines.length) {
      setError("Enter at least one API key (one key per line).");
      return;
    }
    try {
      const result = await bulkCreate.mutateAsync({
        provider: provider.id,
        api_keys: lines,
        label_prefix: provider.title,
      });
      setBulkText("");
      if (result.created < lines.length) {
        setError(
          `${result.created} key(s) added — duplicates or invalid keys were skipped.`
        );
      }
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Could not add API keys.";
      setError(String(msg));
    }
  };

  const toggleDisabled = async (key: UserApiKey) => {
    await updateKey.mutateAsync({
      id: key.id,
      status: key.status === "disabled" ? "active" : "disabled",
    });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2">
              <KeyRound className="h-5 w-5" />
              {provider.title}
            </CardTitle>
            <CardDescription className="mt-1 max-w-2xl">{provider.description}</CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="success">{activeCount} active</Badge>
            {exhaustedCount > 0 && (
              <Badge variant="warning">{exhaustedCount} exhausted</Badge>
            )}
            <a
              href={provider.docsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-primary underline-offset-4 hover:underline"
            >
              Get API key
            </a>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="rounded-lg border border-border bg-muted/30 p-4">
          <p className="text-sm font-medium">Bulk add (one key per line)</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Keys are used in priority order across all users. When a key hits its limit, the next
            active key is used automatically.
          </p>
          <Textarea
            className="mt-3 font-mono text-xs"
            rows={4}
            placeholder={provider.placeholder}
            value={bulkText}
            onChange={(e) => setBulkText(e.target.value)}
          />
          {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              size="sm"
              onClick={handleBulkAdd}
              disabled={bulkCreate.isPending || !bulkText.trim()}
            >
              {bulkCreate.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Plus className="mr-2 h-4 w-4" />
              )}
              Add keys
            </Button>
            {exhaustedCount > 0 && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => resetExhausted.mutate(provider.id)}
                disabled={resetExhausted.isPending}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Reset exhausted
              </Button>
            )}
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading keys...
          </div>
        ) : keys.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No {provider.title} keys yet. Add platform keys above so all users can scrape and use AI.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-left text-xs text-muted-foreground">
                  <th className="px-3 py-2 font-medium">#</th>
                  <th className="px-3 py-2 font-medium">Label</th>
                  <th className="px-3 py-2 font-medium">Key</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2 font-medium">Used</th>
                  <th className="px-3 py-2 font-medium">Last used</th>
                  <th className="px-3 py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {keys.map((key) => (
                  <tr key={key.id} className="border-b border-border last:border-0">
                    <td className="px-3 py-2 text-muted-foreground">{key.priority + 1}</td>
                    <td className="px-3 py-2 font-medium">{key.label}</td>
                    <td className="px-3 py-2 font-mono text-xs">{key.masked_key}</td>
                    <td className="px-3 py-2">
                      <Badge variant={statusVariant(key.status)}>{key.status}</Badge>
                    </td>
                    <td className="px-3 py-2">{key.usage_count}</td>
                    <td className="px-3 py-2 text-xs text-muted-foreground">
                      {key.last_used_at ? formatDate(key.last_used_at) : "—"}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => toggleDisabled(key)}
                          disabled={updateKey.isPending || key.status === "exhausted"}
                        >
                          {key.status === "disabled" ? "Enable" : "Disable"}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-destructive"
                          onClick={() => deleteKey.mutate(key.id)}
                          disabled={deleteKey.isPending}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                      {key.last_error && (
                        <p
                          className="mt-1 max-w-xs truncate text-xs text-destructive"
                          title={key.last_error}
                        >
                          {key.last_error}
                        </p>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function AdminApiKeysPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Admin"
        title="Platform API Keys"
        description="Only admins manage Apify & Groq keys. All users share this pool when scraping or using AI."
      />

      <Card className="border-border/70 bg-muted/30">
        <CardContent className="pt-6 text-sm">
          <strong>Shared pool:</strong> Keys you add here are used by every user. When one key
          reaches its quota, the system rotates to the next active key. Use &quot;Reset
          exhausted&quot; after your Apify/Groq quota resets.
        </CardContent>
      </Card>

      {PROVIDERS.map((provider) => (
        <ProviderSection key={provider.id} provider={provider} />
      ))}
    </div>
  );
}
