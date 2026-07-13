"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Sparkles, Wand2 } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { formatApiError } from "@/lib/utils";
import type { SearchQueryOptimizeResponse } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";

type Props = {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  inputId?: string;
  label?: string;
  showStaticExamples?: boolean;
  staticExamples?: string[];
  autoFixOnBlur?: boolean;
};

const DEFAULT_EXAMPLES = [
  "web design agency London UK contact email",
  "digital marketing agency Berlin Germany phone number",
  "restaurant Paris France contact whatsapp",
  "software company Amsterdam Netherlands email",
];

export function SearchQueryAI({
  value,
  onChange,
  error,
  inputId = "search_query",
  label = "Search Query",
  showStaticExamples = true,
  staticExamples = DEFAULT_EXAMPLES,
  autoFixOnBlur = false,
}: Props) {
  const [aiLoading, setAiLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [aiTips, setAiTips] = useState("");
  const lastOptimizedRef = useRef("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runOptimize = useCallback(
    async (query: string, autoApply: boolean) => {
      const trimmed = query.trim();
      if (trimmed.length < 2) return;

      setAiLoading(true);
      try {
        const { data } = await api.post<SearchQueryOptimizeResponse>(
          "/ai/optimize-search-query",
          { query: trimmed }
        );
        setSuggestions(data.suggestions || []);
        setAiTips(data.tips || "");

        if (autoApply && data.was_corrected && data.optimized_query) {
          onChange(data.optimized_query);
          lastOptimizedRef.current = data.optimized_query.toLowerCase();
          toast.success("AI ne query theek kar di", { description: data.tips });
        }
      } catch (err: unknown) {
        toast.error(formatApiError(err, "AI query fix failed"));
      } finally {
        setAiLoading(false);
      }
    },
    [onChange]
  );

  const handleBlur = () => {
    if (!autoFixOnBlur) return;
    const trimmed = value.trim();
    if (trimmed.length < 3) return;
    if (trimmed.toLowerCase() === lastOptimizedRef.current) return;

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      runOptimize(trimmed, true);
    }, 600);
  };

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const displaySuggestions =
    suggestions.length > 0 ? suggestions : showStaticExamples ? staticExamples : [];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <Label htmlFor={inputId}>{label}</Label>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-8 gap-1 text-xs"
          isLoading={aiLoading}
          onClick={() => runOptimize(value, true)}
        >
          <Wand2 className="h-3.5 w-3.5" />
          AI Fix Query
        </Button>
      </div>

      <div className="relative">
        <Input
          id={inputId}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onBlur={handleBlur}
          placeholder="web design agency London UK contact email phone"
        />
        {aiLoading && (
          <Loader2 className="absolute right-3 top-2.5 h-4 w-4 animate-spin text-primary" />
        )}
      </div>

      <p className="text-xs text-muted-foreground">
        Galat query ho to &quot;AI Fix Query&quot; dabao — auto refresh nahi hoga
      </p>

      {aiTips && (
        <p className="flex items-start gap-1.5 rounded-md bg-primary/5 px-2 py-1.5 text-xs text-primary">
          <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {aiTips}
        </p>
      )}

      <div className="space-y-1">
        <p className="text-xs font-medium text-muted-foreground">AI Suggestions</p>
        <div className="flex flex-wrap gap-2">
          {displaySuggestions.map((example) => (
            <button
              key={example}
              type="button"
              className="rounded-full border px-2 py-1 text-left text-xs text-muted-foreground hover:border-primary hover:text-primary"
              onClick={() => {
                onChange(example);
                lastOptimizedRef.current = example.toLowerCase();
              }}
            >
              {example.length > 48 ? `${example.slice(0, 48)}…` : example}
            </button>
          ))}
          {!aiLoading && suggestions.length === 0 && (
            <button
              type="button"
              className="rounded-full border border-dashed px-2 py-1 text-xs text-primary hover:bg-primary/5"
              onClick={() => runOptimize(value || "business leads", false)}
            >
              <Sparkles className="mr-1 inline h-3 w-3" />
              Load AI suggestions
            </button>
          )}
        </div>
      </div>

      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
