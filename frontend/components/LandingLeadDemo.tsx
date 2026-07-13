"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  ArrowRight,
  Building2,
  Download,
  Globe,
  Loader2,
  Lock,
  Mail,
  MapPin,
  MessageCircle,
  Search,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { Table } from "@/components/Table";
import { getApiBaseUrl } from "@/lib/apiBase";

const CATEGORIES = [
  "Web Design Agency",
  "Marketing Agency",
  "Restaurant",
  "Cleaning Service",
  "Consulting",
  "Real Estate Agency",
  "Auto Repair Shop",
  "Law Firm",
];

const COUNTRIES = [
  { label: "🇩🇪 Germany", value: "Berlin, Germany", city: "Berlin" },
  { label: "🇫🇷 France", value: "Paris, France", city: "Paris" },
  { label: "🇳🇱 Netherlands", value: "Amsterdam, Netherlands", city: "Amsterdam" },
  { label: "🇬🇧 United Kingdom", value: "London, United Kingdom", city: "London" },
  { label: "🇪🇸 Spain", value: "Madrid, Spain", city: "Madrid" },
  { label: "🇮🇹 Italy", value: "Milan, Italy", city: "Milan" },
  { label: "🇸🇪 Sweden", value: "Stockholm, Sweden", city: "Stockholm" },
  { label: "🇧🇪 Belgium", value: "Brussels, Belgium", city: "Brussels" },
];

export type DemoLead = {
  company_name: string;
  email?: string | null;
  phone?: string | null;
  website?: string | null;
  city?: string | null;
  country?: string | null;
  verified: boolean;
};

type DemoResponse = {
  success: boolean;
  count: number;
  total_estimated: number;
  message: string;
  leads: DemoLead[];
};

const progressSteps = [
  "Searching public business sources...",
  "Crawling company websites...",
  "Extracting emails & phones...",
  "Building preview list...",
];

function maskEmail(email: string): string {
  const [local, domain] = email.split("@");
  if (!domain) return "***@***.***";
  const maskedLocal = (local[0] || "*") + "***";
  const [host, ...tld] = domain.split(".");
  const maskedHost = (host[0] || "*") + "***";
  return `${maskedLocal}@${maskedHost}${tld.length ? "." + tld.join(".") : ""}`;
}

function maskPhone(phone: string): string {
  const trimmed = phone.trim();
  if (trimmed.length <= 4) return "***";
  const prefix = trimmed.slice(0, Math.min(4, trimmed.length));
  const suffix = trimmed.replace(/\D/g, "").slice(-2);
  return `${prefix} ** ** ${suffix}...`;
}

function LeadMobileCard({ lead }: { lead: DemoLead }) {
  return (
    <div className="rounded-xl border border-border/60 bg-card p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="font-medium leading-snug">{lead.company_name}</p>
        {lead.verified ? (
          <span className="shrink-0 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] text-emerald-700 dark:text-emerald-400">
            Verified
          </span>
        ) : null}
      </div>
      <div className="mt-3 space-y-1.5 text-xs font-light text-muted-foreground">
        {lead.email ? (
          <p className="flex items-center gap-2">
            <Mail className="h-3.5 w-3.5 shrink-0" />
            {maskEmail(lead.email)}
            <Lock className="h-3 w-3 text-muted-foreground/50" />
          </p>
        ) : null}
        {lead.phone ? (
          <p className="flex items-center gap-2">
            <MessageCircle className="h-3.5 w-3.5 shrink-0" />
            {maskPhone(lead.phone)}
            <Lock className="h-3 w-3 text-muted-foreground/50" />
          </p>
        ) : null}
        {lead.city || lead.country ? (
          <p className="flex items-center gap-2">
            <MapPin className="h-3.5 w-3.5 shrink-0" />
            {[lead.city, lead.country].filter(Boolean).join(", ")}
          </p>
        ) : null}
      </div>
    </div>
  );
}

export function LandingLeadDemo() {
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [countryIdx, setCountryIdx] = useState(0);
  const [city, setCity] = useState(COUNTRIES[0].city);
  const [loading, setLoading] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [leads, setLeads] = useState<DemoLead[]>([]);
  const [totalEstimated, setTotalEstimated] = useState(0);
  const [hasRun, setHasRun] = useState(false);

  const location = useMemo(() => {
    const country = COUNTRIES[countryIdx];
    const c = city.trim() || country.city;
    return `${c}, ${country.value.split(", ").slice(1).join(", ")}`;
  }, [countryIdx, city]);

  const runDemo = async () => {
    setLoading(true);
    setError("");
    setMessage("");
    setLeads([]);
    setTotalEstimated(0);
    setHasRun(true);
    setStepIndex(0);

    const stepTimer = window.setInterval(() => {
      setStepIndex((i) => Math.min(i + 1, progressSteps.length - 1));
    }, 3500);

    try {
      const res = await fetch(`${getApiBaseUrl()}/scraper/demo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keyword: category.trim(), location }),
      });
      const body = await res.json().catch(() => ({
        success: false,
        count: 0,
        total_estimated: 0,
        message: "Invalid response from server",
        leads: [] as DemoLead[],
      }));

      if (!res.ok) {
        const detail =
          typeof body === "object" && body && "detail" in body
            ? String((body as { detail?: string }).detail)
            : (body as DemoResponse).message || "Demo scrape failed";
        throw new Error(detail);
      }

      const data = body as DemoResponse;
      setLeads(data.leads || []);
      setTotalEstimated(data.total_estimated || data.count || 0);
      setMessage(data.message || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Demo scrape failed");
    } finally {
      window.clearInterval(stepTimer);
      setLoading(false);
      setStepIndex(progressSteps.length - 1);
    }
  };

  const tableColumns = [
    {
      key: "company",
      header: "Company",
      render: (lead: DemoLead) => (
        <span className="font-medium text-foreground">{lead.company_name}</span>
      ),
    },
    {
      key: "email",
      header: "Email",
      render: (lead: DemoLead) =>
        lead.email ? (
          <span className="inline-flex items-center gap-1.5 font-mono text-xs text-muted-foreground">
            {maskEmail(lead.email)}
            <Lock className="h-3 w-3 opacity-40" />
          </span>
        ) : (
          <span className="text-muted-foreground/50">—</span>
        ),
    },
    {
      key: "phone",
      header: "Phone",
      render: (lead: DemoLead) =>
        lead.phone ? (
          <span className="inline-flex items-center gap-1.5 font-mono text-xs text-muted-foreground">
            {maskPhone(lead.phone)}
            <Lock className="h-3 w-3 opacity-40" />
          </span>
        ) : (
          <span className="text-muted-foreground/50">—</span>
        ),
    },
    {
      key: "city",
      header: "City",
      render: (lead: DemoLead) => (
        <span className="text-muted-foreground">{lead.city || lead.country || "—"}</span>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (lead: DemoLead) =>
        lead.verified ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-400">
            <ShieldCheck className="h-3 w-3" />
            Verified
          </span>
        ) : (
          <span className="text-[10px] text-muted-foreground">New</span>
        ),
    },
  ];

  return (
    <section id="try-demo" className="scroll-mt-24 border-y border-border/60 bg-muted/20">
      <div className="mx-auto max-w-7xl px-5 py-20 lg:px-8 lg:py-24">
        <div className="mb-10 text-center">
          <div className="mx-auto mb-4 flex items-center justify-center gap-3">
            <span className="h-px w-8 bg-foreground/20" />
            <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-muted-foreground">
              Live preview
            </p>
            <span className="h-px w-8 bg-foreground/20" />
          </div>
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Search & preview local B2B leads
          </h2>
          <p className="mx-auto mt-3 max-w-2xl text-sm font-light text-muted-foreground">
            Like{" "}
            <a
              href="https://www.spherescout.io/"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-foreground underline-offset-4 hover:underline"
            >
              SphereScout
            </a>
            — pick industry and country, preview masked contacts, then sign up to unlock full emails,
            phones, and CSV export.
          </p>
        </div>

        <div className="mb-6 flex flex-wrap items-center justify-center gap-6 text-center text-xs font-light text-muted-foreground sm:gap-10">
          <span className="flex items-center gap-2">
            <Building2 className="h-4 w-4" />
            Live web scrape
          </span>
          <span className="flex items-center gap-2">
            <Globe className="h-4 w-4" />
            European markets
          </span>
          <span className="flex items-center gap-2">
            <Download className="h-4 w-4" />
            CSV on signup
          </span>
          <span className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4" />
            Verified contacts
          </span>
        </div>

        <Card className="landing-gradient-border app-panel mx-auto max-w-5xl border-0 shadow-xl">
          <CardContent className="p-6 sm:p-8">
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-2 sm:col-span-1">
                <Label htmlFor="demo-category">Business category</Label>
                <Select
                  id="demo-category"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  disabled={loading}
                >
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="demo-country">Country</Label>
                <Select
                  id="demo-country"
                  value={String(countryIdx)}
                  onChange={(e) => {
                    const idx = Number(e.target.value);
                    setCountryIdx(idx);
                    setCity(COUNTRIES[idx].city);
                  }}
                  disabled={loading}
                >
                  {COUNTRIES.map((c, i) => (
                    <option key={c.value} value={i}>
                      {c.label}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="demo-city">City</Label>
                <Input
                  id="demo-city"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder="e.g. Berlin"
                  disabled={loading}
                />
              </div>
            </div>

            <Button
              className="mt-5 w-full gap-2 sm:w-auto"
              size="lg"
              onClick={runDemo}
              disabled={loading || !category.trim()}
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Searching businesses...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4" />
                  Preview 4 leads
                </>
              )}
            </Button>

            {loading ? (
              <div className="mt-6 rounded-xl border border-border/60 bg-muted/30 p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-foreground/5">
                    <Search className="h-4 w-4 animate-pulse" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">{progressSteps[stepIndex]}</p>
                    <p className="text-xs font-light text-muted-foreground">
                      Real scrape — usually 30–90 seconds
                    </p>
                  </div>
                </div>
                <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-foreground transition-all duration-500"
                    style={{ width: `${((stepIndex + 1) / progressSteps.length) * 100}%` }}
                  />
                </div>
              </div>
            ) : null}

            {error ? (
              <p className="mt-4 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                {error}
              </p>
            ) : null}

            {leads.length > 0 && !loading ? (
              <div className="mt-8">
                <div className="mb-4 flex flex-col gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm font-medium text-amber-900 dark:text-amber-200">
                      Preview mode
                    </p>
                    <p className="text-xs font-light text-muted-foreground">
                      Showing first {leads.length} of ~{totalEstimated.toLocaleString()} business
                      contacts — emails & phones masked
                    </p>
                  </div>
                  <Link href="/register">
                    <Button size="sm" className="w-full gap-1.5 sm:w-auto">
                      <Lock className="h-3.5 w-3.5" />
                      Unlock all contacts
                    </Button>
                  </Link>
                </div>

                <div className="hidden md:block">
                  <Table
                    columns={tableColumns}
                    data={leads}
                    keyExtractor={(lead) => `${lead.company_name}-${lead.city}-${lead.email}`}
                    emptyMessage="No leads"
                  />
                </div>

                <div className="space-y-3 md:hidden">
                  {leads.map((lead, i) => (
                    <LeadMobileCard key={`${lead.company_name}-${i}`} lead={lead} />
                  ))}
                </div>

                <div className="relative mt-4 overflow-hidden rounded-xl border border-border/60">
                  <div className="pointer-events-none absolute inset-0 z-10 bg-gradient-to-t from-background via-background/80 to-transparent" />
                  <div className="p-6 pt-16 text-center">
                    <p className="text-sm font-medium">
                      Create account to access all ~{totalEstimated.toLocaleString()} leads
                    </p>
                    <p className="mt-1 text-xs font-light text-muted-foreground">
                      Full emails, WhatsApp numbers, daily 100 leads & CSV export
                    </p>
                    <Link href="/register" className="relative z-20 mt-4 inline-block">
                      <Button size="lg" className="gap-2 shadow-md">
                        Get 100 free leads
                        <ArrowRight className="h-4 w-4" />
                      </Button>
                    </Link>
                  </div>
                </div>

                {message ? (
                  <p className="mt-3 text-center text-xs font-light text-muted-foreground">{message}</p>
                ) : null}
              </div>
            ) : null}

            {hasRun && leads.length === 0 && !loading && !error ? (
              <p className="mt-4 text-sm font-light text-muted-foreground">
                No leads found. Try another category or city.
              </p>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
