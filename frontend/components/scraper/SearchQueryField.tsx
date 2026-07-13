"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Sparkles, Wand2 } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { formatApiError } from "@/lib/utils";
import type { ScrapeSuggestResponse, SearchQueryOptimizeResponse } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";

type Props = {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  location?: string;
};

const FALLBACK_SUGGESTIONS = [
  "web design agency London contact phone",
  "restaurant Berlin Germany whatsapp",
  "salon Paris France email phone",
  "gym Amsterdam Netherlands contact",
];

function ensureLocationInQuery(query: string, location?: string): string {
  const loc = location?.trim();
  if (!loc) return query.trim();
  const city = loc.split(",")[0].trim().toLowerCase();
  const low = query.toLowerCase();
  if (low.includes(city) || low.includes(loc.toLowerCase())) {
    return query.trim();
  }
  return `${query.trim()} ${loc}`.replace(/\s+/g, " ").trim();
}

export function SearchQueryField({ value, onChange, error, location }: Props) {
  const [aiLoading, setAiLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>(FALLBACK_SUGGESTIONS);
  const [aiTip, setAiTip] = useState("");
  const lastFixedRef = useRef("");
  const locationRef = useRef(location);
  locationRef.current = location;

  const runOptimize = useCallback(
    async (query: string, applyFix: boolean) => {
      const trimmed = query.trim();
      if (trimmed.length < 2 && !applyFix) return;

      setAiLoading(true);
      try {
        const loc = locationRef.current?.trim() || undefined;
        const { data } = await api.post<SearchQueryOptimizeResponse>(
          "/ai/optimize-search-query",
          {
            query: trimmed || "local business leads contact phone",
            location: loc,
          }
        );
        if (data.suggestions?.length) {
          setSuggestions(
            data.suggestions.map((s) => ensureLocationInQuery(s, loc))
          );
        }
        if (data.tips) setAiTip(data.tips);

        if (applyFix && data.optimized_query) {
          const fixed = ensureLocationInQuery(data.optimized_query, loc);
          onChange(fixed);
          lastFixedRef.current = fixed.toLowerCase();
          if (data.was_corrected || fixed.toLowerCase() !== trimmed.toLowerCase()) {
            toast.success(loc ? `Query fixed with ${loc.split(",")[0]}` : "Query fixed");
          }
        }
      } catch (err: unknown) {
        if (applyFix) toast.error(formatApiError(err, "AI fix failed"));
      } finally {
        setAiLoading(false);
      }
    },
    [onChange]
  );

  const loadBrainSuggestions = useCallback(async () => {
    try {
      const { data } = await api.post<ScrapeSuggestResponse>("/ai/suggest-scrape", {
        scrape_source: "google_search",
      });
      const loc = locationRef.current?.trim();
      const fromBrain = (data.search_queries || [])
        .filter(Boolean)
        .slice(0, 4)
        .map((q) => ensureLocationInQuery(q, loc));
      if (fromBrain.length) setSuggestions(fromBrain);
    } catch {
      /* keep fallback suggestions */
    }
  }, []);

  useEffect(() => {
    void loadBrainSuggestions();
  }, [loadBrainSuggestions]);

  useEffect(() => {
    const loc = location?.trim();
    if (!loc) return;
    setSuggestions((prev) =>
      prev.map((s) => ensureLocationInQuery(s, loc))
    );
  }, [location]);

  const handleBlur = () => {
    const trimmed = value.trim();
    if (trimmed.length < 3) return;
    if (trimmed.toLowerCase() === lastFixedRef.current) return;
    void runOptimize(trimmed, true);
  };

  const applySuggestion = (text: string) => {
    const withLocation = ensureLocationInQuery(text, location);
    onChange(withLocation);
    lastFixedRef.current = withLocation.toLowerCase();
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <Label htmlFor="search_query" className="text-xs text-muted-foreground">
          Search query
        </Label>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-7 gap-1 px-2 text-xs"
          isLoading={aiLoading}
          onClick={() => void runOptimize(value, true)}
        >
          <Wand2 className="h-3 w-3" />
          AI Fix
        </Button>
      </div>

      <div className="relative">
        <Input
          id="search_query"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onBlur={handleBlur}
          placeholder="web design agency London contact phone"
        />
        {aiLoading ? (
          <Loader2 className="absolute right-3 top-2.5 h-4 w-4 animate-spin text-muted-foreground" />
        ) : null}
      </div>

      {aiTip ? (
        <p className="flex items-start gap-1 text-xs text-muted-foreground">
          <Sparkles className="mt-0.5 h-3 w-3 shrink-0" />
          {aiTip}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-1.5">
        {suggestions.slice(0, 5).map((item) => (
          <button
            key={item}
            type="button"
            className="rounded-md bg-muted/60 px-2 py-0.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
            onClick={() => applySuggestion(item)}
          >
            {item.length > 42 ? `${item.slice(0, 42)}…` : item}
          </button>
        ))}
        <button
          type="button"
          className="rounded-md border border-dashed border-border/60 px-2 py-0.5 text-xs text-muted-foreground hover:text-foreground"
          disabled={aiLoading}
          onClick={() => void runOptimize(value || "business leads contact phone", false)}
        >
          More ideas
        </button>
      </div>

      {error ? <p className="text-xs text-destructive">{error}</p> : null}
    </div>
  );
}
