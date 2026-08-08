"use client";

import { useCallback, useEffect, useState } from "react";
import { Brain, ChevronDown, Sparkles } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import type { ScrapeSuggestResponse } from "@/lib/types";
import { formatApiError } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

export type WebsitePreference = "without_website" | "with_website" | "all";

type Props = {
  scrapeSource?: "all" | "google_maps" | "google_search" | "meta_ads";
  websitePreference?: WebsitePreference;
  onApply: (payload: {
    keyword?: string;
    searchQuery?: string;
  }) => void;
  /** When false, do not auto-fetch on mount */
  autoLoad?: boolean;
};

export function CVScrapeAdvisor({
  scrapeSource = "google_maps",
  websitePreference = "without_website",
  onApply,
  autoLoad = true,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ScrapeSuggestResponse | null>(null);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);

  const loadSuggestions = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const apiSource = scrapeSource === "meta_ads" ? "google_maps" : scrapeSource;
      const { data: result } = await api.post<ScrapeSuggestResponse>("/ai/suggest-scrape", {
        scrape_source: apiSource,
        website_preference: websitePreference,
        randomize: true,
      });
      setData(result);
      setOpen(true);
    } catch (err: unknown) {
      setError(formatApiError(err, "Could not load Brain suggestions"));
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [scrapeSource, websitePreference]);

  useEffect(() => {
    if (!autoLoad) return;
    void loadSuggestions();
  }, [autoLoad, loadSuggestions]);

  const applyBest = () => {
    if (!data) return;
    onApply({
      keyword: data.recommended_keyword,
      searchQuery: data.recommended_search_query,
    });
    toast.success(`Apply keyword: ${data.recommended_keyword || "suggestion"}`);
  };

  const showMaps = scrapeSource !== "google_search";
  const showInternet = scrapeSource === "google_search" || scrapeSource === "all";

  return (
    <div className="rounded-xl border border-border/60 bg-muted/20">
      <div className="flex items-center gap-3 p-3.5">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
          <Brain className="h-4 w-4 text-primary" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">CV / Brain keyword suggestions</p>
          <p className="truncate text-xs text-muted-foreground">
            {loading
              ? "Reading your CV & Brain…"
              : data?.recommended_keyword || data?.recommended_search_query
                ? `Try: ${data.recommended_keyword || data.recommended_search_query}`
                : "Import CV + Generate Brain, then refresh suggestions"}
          </p>
        </div>
        <div className="flex shrink-0 gap-1.5">
          <Button
            type="button"
            size="sm"
            variant="outline"
            isLoading={loading}
            onClick={() => void loadSuggestions()}
          >
            Refresh
          </Button>
          {data ? (
            <Button type="button" size="sm" onClick={applyBest}>
              Apply
            </Button>
          ) : null}
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="h-8 w-8 p-0"
            onClick={() => (data ? setOpen((v) => !v) : void loadSuggestions())}
            aria-label={open ? "Collapse suggestions" : "Expand suggestions"}
          >
            <ChevronDown className={cn("h-4 w-4 transition", open && "rotate-180")} />
          </Button>
        </div>
      </div>

      {error ? (
        <p className="border-t border-border/50 px-3.5 py-2 text-xs text-destructive">{error}</p>
      ) : null}

      {open && data ? (
        <div className="space-y-3 border-t border-border/50 px-3.5 py-3">
          {data.strategy_tips ? (
            <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
              <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
              {data.strategy_tips}
            </p>
          ) : null}
          <div className="flex flex-wrap gap-1.5">
            {showMaps
              ? (data.keyword_suggestions || []).slice(0, 6).map((item) => (
                  <button
                    key={`kw-${item}`}
                    type="button"
                    className="rounded-md border border-border/60 bg-background px-2 py-1 text-xs hover:border-primary/40 hover:text-primary"
                    onClick={() => {
                      onApply({ keyword: item });
                      toast.success(`Keyword applied: ${item}`);
                    }}
                  >
                    {item}
                  </button>
                ))
              : null}
            {showInternet
              ? (data.search_queries || []).slice(0, 4).map((item) => (
                  <button
                    key={`sq-${item}`}
                    type="button"
                    className="max-w-full rounded-md border border-border/60 bg-background px-2 py-1 text-left text-xs hover:border-primary/40 hover:text-primary"
                    onClick={() => {
                      onApply({ searchQuery: item });
                      toast.success("Search query applied");
                    }}
                  >
                    {item.length > 48 ? `${item.slice(0, 48)}…` : item}
                  </button>
                ))
              : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
