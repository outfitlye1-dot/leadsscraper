"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  BarChart3,
  Bot,
  Brain,
  Check,
  CheckCircle2,
  ChevronRight,
  Clock,
  FileText,
  Globe,
  Linkedin,
  Lock,
  Mail,
  MapPin,
  Menu,
  MessageCircle,
  Search,
  ShieldCheck,
  Sparkles,
  Star,
  Target,
  Users,
  X,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { cn } from "@/lib/utils";
import { LandingLeadDemo } from "@/components/LandingLeadDemo";

function useReveal(threshold = 0.12) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [threshold]);

  return { ref, visible };
}

function RevealSection({
  children,
  className,
  delay = 0,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: 0 | 1 | 2 | 3;
}) {
  const { ref, visible } = useReveal();
  return (
    <div
      ref={ref}
      className={cn(
        "landing-reveal",
        visible && "landing-reveal-visible",
        delay === 1 && "landing-reveal-delay-1",
        delay === 2 && "landing-reveal-delay-2",
        delay === 3 && "landing-reveal-delay-3",
        className
      )}
    >
      {children}
    </div>
  );
}

function SectionHeader({
  eyebrow,
  title,
  description,
  align = "left",
}: {
  eyebrow: string;
  title: string;
  description?: string;
  align?: "left" | "center";
}) {
  return (
    <div className={cn("max-w-2xl", align === "center" && "mx-auto text-center")}>
      <div className={cn("flex items-center gap-3", align === "center" && "justify-center")}>
        <span className="h-px w-8 bg-foreground/20" />
        <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-muted-foreground">{eyebrow}</p>
        <span className="h-px w-8 bg-foreground/20" />
      </div>
      <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">{title}</h2>
      {description ? (
        <p className="mt-3 text-sm font-light leading-relaxed text-muted-foreground">{description}</p>
      ) : null}
    </div>
  );
}

const navLinks = [
  { href: "#try-demo", label: "Try demo" },
  { href: "#ai-agent", label: "AI Agent" },
  { href: "#features", label: "Features" },
  { href: "#pipeline", label: "Pipeline" },
  { href: "#channels", label: "Channels" },
  { href: "#pricing", label: "Pricing" },
  { href: "#faq", label: "FAQ" },
];

const stats = [
  { value: "100", label: "Daily leads", icon: Sparkles },
  { value: "4", label: "Outreach channels", icon: MessageCircle },
  { value: "$300+", label: "Paid packages from", icon: Target },
  { value: "24/7", label: "AI Agent running", icon: Bot },
];

const markets = [
  "Germany",
  "France",
  "Netherlands",
  "Sweden",
  "Spain",
  "Italy",
  "Belgium",
  "Austria",
  "Poland",
  "Denmark",
];

const integrations = [
  { name: "Google Maps", desc: "Business discovery", icon: MapPin, color: "text-blue-600 bg-blue-500/10" },
  { name: "Gmail", desc: "AI email outreach", icon: Mail, color: "text-red-600 bg-red-500/10" },
  { name: "AI Intelligence", desc: "Smart message generation", icon: Bot, color: "text-amber-600 bg-amber-500/10" },
  { name: "WhatsApp", desc: "Direct outreach", icon: MessageCircle, color: "text-emerald-600 bg-emerald-500/10" },
];

const pipelineSteps = [
  { icon: Search, label: "Discover", desc: "Maps + web scrape" },
  { icon: ShieldCheck, label: "Verify", desc: "Contacts validated" },
  { icon: Brain, label: "Personalize", desc: "CV + Brain AI" },
  { icon: Mail, label: "Email Agent", desc: "Auto-send + follow-ups" },
  { icon: MessageCircle, label: "Outreach", desc: "WA, email, LinkedIn" },
];

const channels = [
  {
    id: "whatsapp",
    icon: MessageCircle,
    name: "WhatsApp",
    description: "AI-crafted messages with verified mobile numbers ready to send.",
    tag: "Most popular",
    sample:
      "Hi! I came across your studio and loved your recent project in sustainable interiors. I offer 3D rendering services and thought there might be a fit for your next campaign.",
    meta: "Avg. reply rate: 18%",
  },
  {
    id: "email",
    icon: Mail,
    name: "Email",
    description: "AI Agent connects Gmail and sends personalized cold emails automatically.",
    tag: "AI Agent",
    sample:
      "Subject: Quick idea for your restaurant website\n\nHi team — I help local restaurants with professional websites ($300–$1,000 packages). Noticed you're on Instagram only — happy to share options if useful.",
    meta: "Auto follow-ups included",
  },
  {
    id: "linkedin",
    icon: Linkedin,
    name: "LinkedIn",
    description: "Professional connection requests and follow-up sequences.",
    tag: "B2B focus",
    sample:
      "I'd love to connect — your work in sustainable design aligns perfectly with the visualization services I offer agencies across Europe.",
    meta: "Professional tone",
  },
];

const bentoFeatures = [
  {
    icon: Bot,
    title: "AI Email Agent",
    description: "Connect Gmail, click Start — pilot email goes out instantly, then daily batches + follow-ups.",
    className: "sm:col-span-2",
    highlight: true,
  },
  {
    icon: Search,
    title: "All-in-One Scraper",
    description: "Web + Google Maps discovery with auto enrichment on every result.",
    className: "sm:col-span-2",
    highlight: true,
  },
  {
    icon: ShieldCheck,
    title: "Verified Contacts",
    description: "Precision-first emails and WhatsApp numbers — empty beats wrong.",
    className: "",
  },
  {
    icon: Bot,
    title: "AI Outreach",
    description: "Messages generated from your CV and Brain profile.",
    className: "",
  },
  {
    icon: Brain,
    title: "AI Brain",
    description: "Your skills, services, and tone — the engine behind every campaign.",
    className: "sm:col-span-2",
    highlight: true,
  },
  {
    icon: Globe,
    title: "JS Rendering",
    description: "Playwright scrapes SPAs and modern sites basic tools miss.",
    className: "",
  },
  {
    icon: Sparkles,
    title: "Daily 100 Leads",
    description: "One click, once per day — fresh leads matched to your profile.",
    className: "",
  },
  {
    icon: Users,
    title: "Lead Pipeline",
    description: "Filter, track, export, and one-click outreach from one table.",
    className: "sm:col-span-2 lg:col-span-1",
  },
  {
    icon: BarChart3,
    title: "Analytics",
    description: "Conversion rates, campaign stats, and pipeline health at a glance.",
    className: "sm:col-span-2 lg:col-span-2",
    highlight: true,
  },
];

const steps = [
  {
    step: "01",
    icon: FileText,
    title: "Upload your CV",
    description: "Add skills and services so AI personalizes every outreach message.",
  },
  {
    step: "02",
    icon: Target,
    title: "Scrape leads",
    description: "Target local businesses with verified emails and WhatsApp numbers.",
  },
  {
    step: "03",
    icon: Mail,
    title: "Start AI Agent",
    description: "Connect Gmail — agent sends pilot email, then daily batches with follow-ups.",
  },
  {
    step: "04",
    icon: Zap,
    title: "Close deals",
    description: "Track replies, approve AI drafts, and convert interested leads.",
  },
];

const testimonials = [
  {
    quote:
      "I went from spending 4 hours a day on Google to 100 verified leads every morning. The WhatsApp numbers actually work.",
    name: "Marco R.",
    role: "Freelance 3D Artist",
    location: "Milan, Italy",
    initials: "MR",
    featured: true,
  },
  {
    quote:
      "The AI messages sound like me — not generic templates. My reply rate on cold email doubled in the first week.",
    name: "Sophie L.",
    role: "Marketing Consultant",
    location: "Paris, France",
    initials: "SL",
  },
  {
    quote:
      "Daily 100 Leads is a game changer. Upload your CV once, click one button, and your pipeline fills itself.",
    name: "Erik J.",
    role: "Web Development Agency",
    location: "Stockholm, Sweden",
    initials: "EJ",
  },
];

const planFeatures = [
  "Unlimited lead storage",
  "Daily 100 Leads scrape",
  "AI Email Agent + Gmail",
  "Auto follow-ups & inbox sync",
  "WhatsApp, Email & LinkedIn",
  "Google Maps + web scraping",
  "Pipeline & analytics dashboard",
];

const comparison = {
  manual: [
    "Hours searching Google manually",
    "Wrong phone numbers in spreadsheets",
    "Writing & sending emails one by one",
    "No tracking or follow-up system",
  ],
  leadgen: [
    "Automated web + Maps scraping",
    "Precision-verified contacts only",
    "AI Agent emails from $300 packages",
    "Full pipeline + sent message log",
  ],
};

const faqs = [
  {
    q: "What is the AI Email Agent?",
    a: "Connect Gmail, configure settings once, and click Start AI Agent. It immediately sends a pilot email, then processes today's leads on a daily schedule with automatic follow-ups.",
  },
  {
    q: "What pricing do outreach messages mention?",
    a: "AI messages reference professional paid packages from $300 to $1,000 USD depending on scope — never free audits or trials.",
  },
  {
    q: "How accurate are the phone numbers?",
    a: "We use precision-first extraction — only high-confidence numbers enter your pipeline. An empty field is better than a wrong contact.",
  },
  {
    q: "What is Daily 100 Leads?",
    a: "Once per day, one click runs a scrape of up to 100 leads tailored to your CV profile and Brain settings, with enrichment and verification forced on.",
  },
  {
    q: "Does it work on JavaScript websites?",
    a: "Yes. Playwright automatically handles SPAs and JS-heavy sites when a basic fetch isn't enough.",
  },
  {
    q: "Which markets are supported?",
    a: "The platform is built for European B2B outreach — Germany, France, Netherlands, Nordics, and more via web and Google Maps search.",
  },
  {
    q: "Is it really free to start?",
    a: "Yes. Create an account, upload your CV, and run your first scrape at no cost. No credit card required.",
  },
];

const previewLeads = [
  { company: "Nordic Design Studio", email: "hello@nordicdesign.se", phone: "+46 70 ••• ••••", status: "Verified" },
  { company: "Berlin Tech GmbH", email: "info@berlintech.de", phone: "+49 30 ••• ••••", status: "Verified" },
  { company: "Amsterdam Logistics", email: "sales@amslogistics.nl", phone: "+31 20 ••• ••••", status: "New" },
];

const avatarStack = ["MR", "SL", "EJ", "AK", "LP"];
const trustBadges = [
  { icon: Lock, label: "Secure accounts" },
  { icon: Mail, label: "Gmail integration" },
  { icon: Clock, label: "Setup in 5 min" },
];

function AiAgentShowcase() {
  const agentSteps = [
    { label: "Connect Gmail", desc: "OAuth in one click", done: true },
    { label: "Start AI Agent", desc: "Pilot email sends instantly", done: true },
    { label: "Daily batch", desc: "Up to your daily limit", done: true },
    { label: "Auto follow-ups", desc: "Scheduled if no reply", done: false },
  ];

  return (
    <div className="grid gap-6 lg:grid-cols-2 lg:items-center">
      <div className="space-y-4">
        {agentSteps.map(({ label, desc, done }, i) => (
          <div
            key={label}
            className={cn(
              "flex items-start gap-4 rounded-xl border p-4 transition-all",
              done ? "border-emerald-500/25 bg-emerald-500/5" : "border-border/60 bg-card"
            )}
          >
            <div
              className={cn(
                "flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-xs font-semibold tabular-nums",
                done
                  ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
                  : "border-border bg-muted/40 text-muted-foreground"
              )}
            >
              {done ? <Check className="h-4 w-4" /> : i + 1}
            </div>
            <div>
              <p className="text-sm font-semibold">{label}</p>
              <p className="mt-0.5 text-xs font-light text-muted-foreground">{desc}</p>
            </div>
          </div>
        ))}
      </div>

      <Card className="landing-gradient-border app-panel overflow-hidden border-0 shadow-xl">
        <CardContent className="p-0">
          <div className="flex items-center justify-between border-b border-border/60 px-5 py-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-foreground text-background">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-semibold">AI Email Agent</p>
                <p className="text-xs font-light text-muted-foreground">Running · Gmail connected</p>
              </div>
            </div>
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
            </span>
          </div>

          <div className="space-y-3 p-5">
            <div className="rounded-lg border border-emerald-500/25 bg-emerald-500/5 p-4">
              <div className="flex items-center justify-between gap-2">
                <p className="text-[10px] font-medium uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
                  Pilot email — sent
                </p>
                <span className="text-[10px] text-muted-foreground">Just now</span>
              </div>
              <p className="mt-2 text-xs font-medium">To: hello@nordicdesign.se</p>
              <p className="mt-1 text-xs font-light leading-relaxed text-muted-foreground">
                Subject: Quick idea for your restaurant website — $300–$1,000 packages for local businesses...
              </p>
            </div>

            <div className="rounded-lg border border-border/60 bg-muted/20 p-4">
              <div className="flex items-center justify-between gap-2">
                <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  Follow-up scheduled
                </p>
                <span className="text-[10px] text-muted-foreground">In 3 days</span>
              </div>
              <p className="mt-2 text-xs font-light text-muted-foreground">
                12 leads in today&apos;s batch · 4 follow-ups queued
              </p>
            </div>
          </div>

          <div className="flex items-center justify-between border-t border-border/60 px-5 py-3">
            <p className="text-xs font-light text-muted-foreground">View full log in Sent messages</p>
            <Link href="/register">
              <Button size="sm" className="gap-1.5">
                Try AI Agent
                <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function FloatingBadge({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "app-surface absolute z-10 flex items-center gap-2 rounded-full px-3 py-2 text-xs font-medium shadow-lg backdrop-blur-md",
        className
      )}
    >
      {children}
    </div>
  );
}

function OutreachDemo() {
  const [active, setActive] = useState("email");
  const current = channels.find((c) => c.id === active)!;
  const Icon = current.icon;

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <div className="lg:col-span-3">
        <Card className="landing-gradient-border app-panel h-full overflow-hidden border-0 shadow-xl">
          <CardContent className="p-0">
            <div className="flex items-center justify-between border-b border-border/60 px-5 py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-foreground text-background">
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-semibold">{current.name} preview</p>
                  <p className="text-xs font-light text-muted-foreground">{current.meta}</p>
                </div>
              </div>
              <span className="rounded-full border border-border/60 px-2.5 py-1 text-[10px] font-medium text-muted-foreground">
                {current.tag}
              </span>
            </div>
            <div className="bg-muted/20 p-5 sm:p-6">
              <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">AI-generated</p>
              <p className="mt-3 whitespace-pre-line text-sm font-light leading-relaxed text-foreground/90">
                {current.sample}
              </p>
            </div>
            <div className="flex items-center justify-between border-t border-border/60 px-5 py-3">
              <p className="text-xs font-light text-muted-foreground">Personalized from your CV profile</p>
              <Link href="/register">
                <Button size="sm" className="gap-1.5">
                  Try it free
                  <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
      <div className="flex flex-col gap-2 lg:col-span-2">
        {channels.map((channel) => {
          const ChIcon = channel.icon;
          const isActive = active === channel.id;
          return (
            <button
              key={channel.id}
              type="button"
              onClick={() => setActive(channel.id)}
              className={cn(
                "flex items-start gap-3 rounded-xl border p-4 text-left transition-all",
                isActive
                  ? "border-foreground/20 bg-foreground/[0.03] shadow-md ring-1 ring-foreground/10"
                  : "border-border/60 bg-card hover:border-foreground/10 hover:bg-muted/30"
              )}
            >
              <div
                className={cn(
                  "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border transition-colors",
                  isActive ? "border-foreground/20 bg-foreground text-background" : "border-border/70 bg-muted/40"
                )}
              >
                <ChIcon className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-semibold">{channel.name}</p>
                <p className="mt-0.5 text-xs font-light text-muted-foreground">{channel.description}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function ProductPreview() {
  const navItems = ["Dashboard", "Leads", "Email Agent", "Scraper"];

  return (
    <div className="relative pb-10 pl-0 sm:pb-8 sm:pl-4">
      <div className="pointer-events-none absolute -right-12 top-1/4 h-48 w-48 rounded-full bg-foreground/[0.04] blur-3xl landing-glow-orb" />
      <div
        className="pointer-events-none absolute -left-8 bottom-1/3 h-36 w-36 rounded-full bg-foreground/[0.03] blur-3xl landing-glow-orb"
        style={{ animationDelay: "2s" }}
      />

      <FloatingBadge className="landing-float -left-2 top-6 hidden sm:flex">
        <ShieldCheck className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
        612 verified
      </FloatingBadge>
      <FloatingBadge className="landing-float-delay -right-3 top-1/2 hidden sm:flex">
        <Mail className="h-3.5 w-3.5 text-red-500/80" />
        Pilot email sent
      </FloatingBadge>

      <div className="app-panel relative overflow-hidden p-1 shadow-[0_32px_100px_rgba(0,0,0,0.12)] ring-1 ring-border/40">
        <div className="flex overflow-hidden rounded-[0.55rem] border border-border/60 bg-card">
          <div className="hidden w-[140px] shrink-0 border-r border-border/60 bg-muted/20 p-3 sm:block">
            <div className="mb-4 flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-foreground">
                <Zap className="h-3 w-3 text-background" />
              </div>
              <span className="text-[10px] font-semibold">LeadGen</span>
            </div>
            <div className="space-y-1">
              {navItems.map((item, i) => (
                <div
                  key={item}
                  className={cn(
                    "rounded-md px-2 py-1.5 text-[10px]",
                    i === 2 ? "bg-foreground/5 font-medium text-foreground" : "text-muted-foreground"
                  )}
                >
                  {item}
                </div>
              ))}
            </div>
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 border-b border-border/60 px-4 py-3">
              <div className="flex gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-red-400/70" />
                <span className="h-2.5 w-2.5 rounded-full bg-amber-400/70" />
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/70" />
              </div>
              <span className="ml-2 text-[11px] font-medium text-muted-foreground">LeadGen AI — Email Agent</span>
            </div>

            <div className="grid grid-cols-3 gap-2 border-b border-border/60 p-3 sm:gap-3 sm:p-4">
              {[
                { label: "Sent today", value: "18", trend: "+3 pilot" },
                { label: "Scheduled", value: "24", trend: "Follow-ups" },
                { label: "Replies", value: "6", trend: "+2 new" },
              ].map((item) => (
                <div key={item.label} className="rounded-lg border border-border/60 bg-muted/30 px-2 py-2 sm:px-3 sm:py-2.5">
                  <p className="text-[9px] font-medium uppercase tracking-wider text-muted-foreground sm:text-[10px]">
                    {item.label}
                  </p>
                  <p className="mt-0.5 text-lg font-light tabular-nums tracking-tight sm:mt-1 sm:text-xl">{item.value}</p>
                  <p className="text-[9px] text-emerald-600 dark:text-emerald-400 sm:text-[10px]">{item.trend}</p>
                </div>
              ))}
            </div>

            <div className="space-y-2 p-3 sm:p-4">
              <div className="mb-2 flex items-center justify-between sm:mb-3">
                <p className="text-xs font-medium">Recent outreach</p>
                <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[9px] text-emerald-700 dark:text-emerald-400 sm:text-[10px]">
                  Agent active
                </span>
              </div>
              {previewLeads.map((lead) => (
                <div
                  key={lead.company}
                  className="flex items-center justify-between rounded-lg border border-border/60 px-2.5 py-2 transition-colors hover:bg-muted/30 sm:px-3 sm:py-2.5"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-medium sm:text-sm">{lead.company}</p>
                    <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px] text-muted-foreground sm:gap-x-3 sm:text-[11px]">
                      <span className="flex items-center gap-1">
                        <Mail className="h-3 w-3 shrink-0" />
                        <span className="truncate">{lead.email}</span>
                      </span>
                      <span className="hidden items-center gap-1 sm:flex">
                        <MessageCircle className="h-3 w-3" />
                        {lead.phone}
                      </span>
                    </div>
                  </div>
                  <span
                    className={cn(
                      "ml-2 shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-medium sm:ml-3 sm:px-2 sm:text-[10px]",
                      lead.status === "Verified"
                        ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
                        : "bg-muted text-muted-foreground"
                    )}
                  >
                    {lead.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="app-surface landing-float-delay absolute -bottom-2 -left-2 max-w-[240px] border-emerald-500/20 p-3 shadow-2xl sm:-left-6 sm:bottom-0">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            <Bot className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
            AI Agent
          </div>
          <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[9px] text-emerald-700 dark:text-emerald-400">
            Live
          </span>
        </div>
        <p className="mt-1.5 text-[11px] leading-relaxed text-muted-foreground">
          &ldquo;Hi Nordic Design — I help local businesses with professional websites ($300–$1,000 packages).
          Happy to share options if useful.&rdquo;
        </p>
      </div>
    </div>
  );
}

export function LandingPage() {
  const [scrolled, setScrolled] = useState(false);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => {
      setScrolled(window.scrollY > 12);
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      setScrollProgress(docHeight > 0 ? window.scrollY / docHeight : 0);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    document.body.style.overflow = mobileOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileOpen]);

  const closeMobile = () => setMobileOpen(false);

  return (
    <div className="min-h-screen text-foreground">
      <div className="fixed top-0 left-0 right-0 z-[60] h-0.5 bg-border/40">
        <div
          className="h-full origin-left bg-foreground transition-transform duration-150"
          style={{ transform: `scaleX(${scrollProgress})` }}
        />
      </div>

      <header
        className={cn(
          "sticky top-0 z-50 liquid-glass border-b transition-shadow duration-300",
          scrolled ? "border-border/80 shadow-sm" : "border-border/40"
        )}
      >
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 lg:px-8">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-border/80 bg-foreground shadow-sm">
              <Zap className="h-4 w-4 text-background" />
            </div>
            <span className="text-sm font-semibold tracking-tight">LeadGen AI</span>
          </Link>

          <nav className="hidden items-center gap-5 lg:flex">
            {navLinks.map(({ href, label }) => (
              <a
                key={href}
                href={href}
                className="text-sm font-light text-muted-foreground transition-colors hover:text-foreground"
              >
                {label}
              </a>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <Link href="/login" className="hidden sm:block">
              <Button variant="ghost" size="sm" className="text-muted-foreground">
                Sign in
              </Button>
            </Link>
            <Link href="/register" className="hidden sm:block">
              <Button size="sm" className="gap-1.5">
                Get started
                <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </Link>
            <button
              type="button"
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-border/70 lg:hidden"
              onClick={() => setMobileOpen((v) => !v)}
              aria-label={mobileOpen ? "Close menu" : "Open menu"}
            >
              {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {mobileOpen ? (
          <div className="border-t border-border/60 bg-background px-5 py-4 lg:hidden">
            <nav className="flex flex-col gap-1">
              {navLinks.map(({ href, label }) => (
                <a
                  key={href}
                  href={href}
                  onClick={closeMobile}
                  className="rounded-lg px-3 py-2.5 text-sm font-light text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
                >
                  {label}
                </a>
              ))}
            </nav>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <Link href="/login" onClick={closeMobile}>
                <Button variant="outline" className="w-full">
                  Sign in
                </Button>
              </Link>
              <Link href="/register" onClick={closeMobile}>
                <Button className="w-full gap-1.5">
                  Get started
                  <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </Link>
            </div>
          </div>
        ) : null}
      </header>

      <main>
        {/* Hero */}
        <section className="relative overflow-hidden border-b border-border/60">
          <div className="landing-grid-bg pointer-events-none absolute inset-0" />
          <div className="pointer-events-none absolute inset-x-0 top-0 h-[560px] bg-[radial-gradient(ellipse_at_30%_0%,_hsl(var(--foreground)/0.08),_transparent_55%)]" />
          <div className="pointer-events-none absolute inset-x-0 top-0 h-[560px] bg-[radial-gradient(ellipse_at_80%_20%,_hsl(var(--foreground)/0.05),_transparent_50%)]" />

          <div className="relative mx-auto grid max-w-7xl gap-12 px-5 py-16 lg:grid-cols-2 lg:items-center lg:gap-16 lg:px-8 lg:py-28">
            <div className="landing-fade-up">
              <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-[11px] font-medium text-emerald-800 dark:text-emerald-300 shadow-sm">
                <Bot className="h-3 w-3" />
                New — AI Email Agent with Gmail
              </div>

              <h1 className="mt-6 text-4xl font-semibold leading-[1.06] tracking-tight sm:text-5xl lg:text-[3.5rem]">
                Scrape leads.
                <span className="mt-1 block font-light landing-shimmer-text">Let AI email them for you.</span>
              </h1>

              <p className="mt-6 max-w-xl text-base font-light leading-relaxed text-muted-foreground sm:text-lg">
                Discover verified businesses, connect Gmail, and start the AI Agent — it sends a pilot email
                instantly, then runs daily batches with follow-ups. WhatsApp and LinkedIn included.
              </p>

              <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
                <Link href="/register">
                  <Button size="lg" className="h-12 w-full gap-2 px-8 shadow-md sm:w-auto">
                    Start free — connect Gmail
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
                <Link href="#ai-agent">
                  <Button variant="outline" size="lg" className="h-12 w-full gap-2 px-8 sm:w-auto">
                    See AI Agent
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </Link>
              </div>

              <div className="mt-8 flex flex-wrap items-center gap-4">
                <div className="flex -space-x-2">
                  {avatarStack.map((initials) => (
                    <div
                      key={initials}
                      className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-background bg-muted text-[10px] font-medium text-muted-foreground"
                    >
                      {initials}
                    </div>
                  ))}
                </div>
                <div>
                  <div className="flex items-center gap-0.5">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Star key={i} className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                    ))}
                  </div>
                  <p className="mt-0.5 text-xs font-light text-muted-foreground">
                    Trusted by freelancers & agencies across Europe
                  </p>
                </div>
              </div>

              <div className="mt-6 flex flex-wrap gap-2">
                {trustBadges.map(({ icon: Icon, label }) => (
                  <span
                    key={label}
                    className="inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-card/80 px-3 py-1 text-[11px] font-light text-muted-foreground"
                  >
                    <Icon className="h-3 w-3" />
                    {label}
                  </span>
                ))}
              </div>

              <ul className="mt-8 grid gap-2.5 sm:grid-cols-2">
                {[
                  "AI Agent — pilot email on start",
                  "Gmail auto-send + follow-ups",
                  "Daily 100 leads — one click",
                  "$300–$1K packages in every pitch",
                ].map((item) => (
                  <li key={item} className="flex items-center gap-2.5 text-sm font-light text-muted-foreground">
                    <CheckCircle2
                      className="h-4 w-4 shrink-0 text-emerald-600/80 dark:text-emerald-400/80"
                      strokeWidth={1.5}
                    />
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            <div className="relative">
              <ProductPreview />
            </div>
          </div>
        </section>

        {/* Stats */}
        <section className="border-b border-border/60 bg-muted/30">
          <div className="mx-auto grid max-w-7xl grid-cols-2 gap-4 px-5 py-10 sm:grid-cols-4 lg:px-8">
            {stats.map(({ value, label, icon: Icon }, i) => (
              <RevealSection key={label} delay={(i % 4) as 0 | 1 | 2 | 3}>
                <div className="app-surface flex items-center gap-4 rounded-xl p-4 transition-all hover:-translate-y-1 hover:shadow-md">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-border/70 bg-muted/50">
                    <Icon className="h-4 w-4 text-foreground/80" strokeWidth={1.5} />
                  </div>
                  <div>
                    <p className="text-2xl font-light tabular-nums tracking-tight">{value}</p>
                    <p className="text-xs font-light text-muted-foreground">{label}</p>
                  </div>
                </div>
              </RevealSection>
            ))}
          </div>
        </section>

        {/* AI Email Agent */}
        <section id="ai-agent" className="scroll-mt-24 border-b border-border/60 bg-muted/20">
          <div className="mx-auto max-w-7xl px-5 py-20 lg:px-8 lg:py-24">
            <RevealSection>
              <SectionHeader
                eyebrow="AI Email Agent"
                title="Connect Gmail. Click Start. Emails go out."
                description="No manual copy-paste. The agent sends a pilot email the moment you start, then handles daily outreach and follow-ups while you focus on closing."
              />
            </RevealSection>
            <RevealSection delay={1}>
              <div className="mt-12">
                <AiAgentShowcase />
              </div>
            </RevealSection>
          </div>
        </section>

        <LandingLeadDemo />

        {/* Integrations */}
        <section className="border-b border-border/60 py-8">
          <div className="mx-auto max-w-7xl px-5 lg:px-8">
            <p className="mb-6 text-center text-[11px] font-medium uppercase tracking-[0.2em] text-muted-foreground">
              Powered by
            </p>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {integrations.map(({ name, desc, icon: Icon, color }) => (
                <div
                  key={name}
                  className="app-surface flex flex-col items-center rounded-xl px-4 py-5 text-center transition-all hover:-translate-y-0.5 hover:shadow-md"
                >
                  <div className={cn("mb-3 flex h-11 w-11 items-center justify-center rounded-xl", color)}>
                    <Icon className="h-5 w-5" strokeWidth={1.5} />
                  </div>
                  <p className="text-sm font-semibold tracking-tight">{name}</p>
                  <p className="mt-0.5 text-[11px] font-light text-muted-foreground">{desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Markets marquee */}
        <section className="overflow-hidden border-b border-border/60 py-5">
          <p className="mb-4 text-center text-[11px] font-medium uppercase tracking-[0.2em] text-muted-foreground">
            Target markets across Europe
          </p>
          <div className="relative">
            <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-16 bg-gradient-to-r from-background to-transparent" />
            <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-16 bg-gradient-to-l from-background to-transparent" />
            <div className="landing-marquee-track flex w-max gap-3">
              {[...markets, ...markets].map((country, i) => (
                <span
                  key={`${country}-${i}`}
                  className="shrink-0 rounded-full border border-border/70 bg-card px-5 py-2 text-sm font-light text-muted-foreground"
                >
                  {country}
                </span>
              ))}
            </div>
          </div>
        </section>

        {/* Pipeline flow */}
        <section id="pipeline" className="scroll-mt-24 border-b border-border/60 bg-muted/20">
          <div className="mx-auto max-w-7xl px-5 py-20 lg:px-8 lg:py-24">
            <RevealSection>
              <SectionHeader
                eyebrow="Pipeline"
                title="From scrape to outreach in one flow"
                description="No spreadsheets. No copy-paste. Every lead moves through discovery, verification, personalization, and outreach automatically."
                align="center"
              />
            </RevealSection>
            <RevealSection delay={1}>
              <div className="relative mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                <div className="landing-pipeline-line pointer-events-none absolute left-[12%] right-[12%] top-10 hidden h-px lg:block" />
                {pipelineSteps.map(({ icon: Icon, label, desc }, i) => (
                  <div
                    key={label}
                    className="landing-gradient-border relative rounded-xl p-5 text-center transition-transform hover:-translate-y-1"
                  >
                    <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border-2 border-border bg-background shadow-sm">
                      <Icon className="h-5 w-5" strokeWidth={1.5} />
                    </div>
                    <p className="text-[10px] font-medium tabular-nums text-muted-foreground">0{i + 1}</p>
                    <h3 className="mt-1 text-base font-semibold">{label}</h3>
                    <p className="mt-1 text-xs font-light text-muted-foreground">{desc}</p>
                  </div>
                ))}
              </div>
            </RevealSection>
          </div>
        </section>

        {/* Bento features */}
        <section id="features" className="mx-auto max-w-7xl scroll-mt-24 px-5 py-20 lg:px-8 lg:py-24">
          <RevealSection>
            <SectionHeader
              eyebrow="Platform"
              title="Everything you need to grow"
              description="A complete lead generation stack — from scraping and verification to AI outreach and analytics."
            />
          </RevealSection>
          <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {bentoFeatures.map(({ icon: Icon, title, description, className, highlight }, i) => (
              <RevealSection key={title} delay={(i % 3) as 0 | 1 | 2 | 3} className={className}>
                <Card
                  className={cn(
                    "group h-full border-border/70 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg",
                    highlight ? "landing-gradient-border app-panel border-0 bg-muted/20" : "app-surface"
                  )}
                >
                  <CardContent className="flex h-full flex-col p-6">
                    <div
                      className={cn(
                        "mb-4 flex h-11 w-11 items-center justify-center rounded-xl border border-border/70 transition-colors group-hover:bg-foreground group-hover:text-background",
                        highlight ? "bg-foreground text-background" : "bg-muted/40"
                      )}
                    >
                      <Icon className="h-5 w-5" strokeWidth={1.5} />
                    </div>
                    <h3 className="text-base font-semibold tracking-tight">{title}</h3>
                    <p className="mt-2 flex-1 text-sm font-light leading-relaxed text-muted-foreground">
                      {description}
                    </p>
                  </CardContent>
                </Card>
              </RevealSection>
            ))}
          </div>
        </section>

        {/* Manual vs LeadGen */}
        <section className="border-y border-border/60 bg-muted/20">
          <div className="mx-auto max-w-7xl px-5 py-20 lg:px-8 lg:py-24">
            <RevealSection>
              <SectionHeader
                eyebrow="Why switch"
                title="Stop doing it manually"
                description="See the difference between hours of manual work and one automated workspace."
                align="center"
              />
            </RevealSection>
            <div className="mt-12 grid gap-4 md:grid-cols-2">
              <RevealSection delay={1}>
                <Card className="app-surface h-full border-border/70 opacity-80">
                  <CardContent className="p-6">
                    <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-muted-foreground">
                      Manual outreach
                    </p>
                    <ul className="mt-5 space-y-3">
                      {comparison.manual.map((item) => (
                        <li key={item} className="flex items-start gap-3 text-sm font-light text-muted-foreground">
                          <X className="mt-0.5 h-4 w-4 shrink-0 text-red-500/70" strokeWidth={1.5} />
                          {item}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </RevealSection>
              <RevealSection delay={2}>
                <Card className="landing-gradient-border app-panel h-full border-0 shadow-xl">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-2">
                      <div className="flex h-6 w-6 items-center justify-center rounded-md bg-foreground">
                        <Zap className="h-3.5 w-3.5 text-background" />
                      </div>
                      <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-foreground">
                        With LeadGen AI
                      </p>
                    </div>
                    <ul className="mt-5 space-y-3">
                      {comparison.leadgen.map((item) => (
                        <li key={item} className="flex items-start gap-3 text-sm font-light">
                          <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" strokeWidth={2} />
                          {item}
                        </li>
                      ))}
                    </ul>
                    <Link href="/register" className="mt-6 block">
                      <Button className="w-full gap-2">
                        Start free today
                        <ArrowRight className="h-4 w-4" />
                      </Button>
                    </Link>
                  </CardContent>
                </Card>
              </RevealSection>
            </div>
          </div>
        </section>

        {/* Interactive channels */}
        <section id="channels" className="scroll-mt-24">
          <div className="mx-auto max-w-7xl px-5 py-20 lg:px-8 lg:py-24">
            <RevealSection>
              <SectionHeader
                eyebrow="Multi-channel"
                title="Reach leads everywhere"
                description="One lead list. Email Agent, WhatsApp, and LinkedIn — click to preview AI messages with your pricing."
                align="center"
              />
            </RevealSection>
            <RevealSection delay={1}>
              <div className="mt-12">
                <OutreachDemo />
              </div>
            </RevealSection>
          </div>
        </section>

        {/* Testimonials */}
        <section id="testimonials" className="scroll-mt-24 border-y border-border/60 bg-muted/20">
          <div className="mx-auto max-w-7xl px-5 py-20 lg:px-8 lg:py-24">
            <RevealSection>
              <SectionHeader eyebrow="Reviews" title="Loved by European pros" align="center" />
            </RevealSection>
            <div className="mt-12 space-y-4">
              {testimonials
                .filter((t) => t.featured)
                .map(({ quote, name, role, location, initials }) => (
                  <RevealSection key={name}>
                    <Card className="landing-gradient-border app-panel border-0 shadow-xl">
                      <CardContent className="flex flex-col gap-6 p-8 sm:flex-row sm:items-center">
                        <div className="text-6xl font-serif leading-none text-foreground/10">&ldquo;</div>
                        <div className="flex-1">
                          <div className="mb-4 flex gap-0.5">
                            {Array.from({ length: 5 }).map((_, j) => (
                              <Star key={j} className="h-4 w-4 fill-amber-400 text-amber-400" />
                            ))}
                          </div>
                          <p className="text-base font-light leading-relaxed text-muted-foreground sm:text-lg">
                            &ldquo;{quote}&rdquo;
                          </p>
                          <div className="mt-6 flex items-center gap-3">
                            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-foreground text-sm font-medium text-background">
                              {initials}
                            </div>
                            <div>
                              <p className="text-sm font-semibold">{name}</p>
                              <p className="text-xs font-light text-muted-foreground">
                                {role} · {location}
                              </p>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </RevealSection>
                ))}
              <div className="grid gap-4 md:grid-cols-2">
                {testimonials
                  .filter((t) => !t.featured)
                  .map(({ quote, name, role, location, initials }, i) => (
                    <RevealSection key={name} delay={(i % 2) as 0 | 1 | 2 | 3}>
                      <Card className="app-panel h-full border-border/70 transition-all hover:-translate-y-1 hover:shadow-lg">
                        <CardContent className="flex h-full flex-col p-6">
                          <div className="mb-4 flex gap-0.5">
                            {Array.from({ length: 5 }).map((_, j) => (
                              <Star key={j} className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                            ))}
                          </div>
                          <p className="flex-1 text-sm font-light leading-relaxed text-muted-foreground">
                            &ldquo;{quote}&rdquo;
                          </p>
                          <div className="mt-6 flex items-center gap-3 border-t border-border/60 pt-4">
                            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-foreground text-xs font-medium text-background">
                              {initials}
                            </div>
                            <div>
                              <p className="text-sm font-medium">{name}</p>
                              <p className="text-xs font-light text-muted-foreground">
                                {role} · {location}
                              </p>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </RevealSection>
                  ))}
              </div>
            </div>
          </div>
        </section>

        {/* How it works */}
        <section id="how-it-works" className="scroll-mt-24">
          <div className="mx-auto max-w-7xl px-5 py-20 lg:px-8 lg:py-24">
            <RevealSection>
              <SectionHeader
                eyebrow="Workflow"
                title="How it works"
                description="Four steps from signup to automated outreach."
                align="center"
              />
            </RevealSection>
            <div className="relative mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              <div className="pointer-events-none absolute left-[12%] right-[12%] top-12 hidden h-px bg-gradient-to-r from-transparent via-border to-transparent lg:block" />
              {steps.map(({ step, icon: Icon, title, description }, i) => (
                <RevealSection key={step} delay={(i % 3) as 0 | 1 | 2 | 3}>
                  <Card className="app-panel relative h-full border-border/70 transition-all hover:-translate-y-1 hover:shadow-lg">
                    <CardContent className="p-6 text-center md:text-left">
                      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border-2 border-border bg-background shadow-sm md:mx-0">
                        <Icon className="h-5 w-5 text-foreground/80" strokeWidth={1.5} />
                      </div>
                      <span className="text-sm font-medium tabular-nums text-muted-foreground">{step}</span>
                      <h3 className="mt-1 text-lg font-semibold tracking-tight">{title}</h3>
                      <p className="mt-2 text-sm font-light leading-relaxed text-muted-foreground">{description}</p>
                    </CardContent>
                  </Card>
                </RevealSection>
              ))}
            </div>
          </div>
        </section>

        {/* Pricing */}
        <section id="pricing" className="scroll-mt-24 border-y border-border/60 bg-muted/20">
          <div className="mx-auto max-w-7xl px-5 py-20 lg:px-8 lg:py-24">
            <RevealSection>
              <SectionHeader
                eyebrow="Pricing"
                title="Free to start, built to scale"
                description="Everything you need to launch your first campaign — no credit card required."
                align="center"
              />
            </RevealSection>
            <RevealSection delay={1}>
              <div className="mx-auto mt-12 max-w-lg">
                <Card className="landing-gradient-border app-panel overflow-hidden border-0 shadow-2xl">
                  <CardContent className="p-8">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-muted-foreground">Starter</p>
                        <div className="mt-2 flex items-baseline gap-1">
                          <span className="text-5xl font-light tracking-tight">Free</span>
                        </div>
                        <p className="mt-1 text-sm font-light text-muted-foreground">Perfect to get started</p>
                      </div>
                      <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-[11px] font-medium text-emerald-700 dark:text-emerald-400">
                        Popular
                      </span>
                    </div>
                    <ul className="mt-8 space-y-3">
                      {planFeatures.map((feature) => (
                        <li key={feature} className="flex items-center gap-3 text-sm font-light">
                          <Check className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                    <Link href="/register" className="mt-8 block">
                      <Button size="lg" className="h-12 w-full gap-2 shadow-md">
                        Create free account
                        <ArrowRight className="h-4 w-4" />
                      </Button>
                    </Link>
                    <p className="mt-4 text-center text-xs font-light text-muted-foreground">
                      No credit card · Setup in 5 minutes
                    </p>
                  </CardContent>
                </Card>
              </div>
            </RevealSection>
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" className="scroll-mt-24">
          <div className="mx-auto max-w-3xl px-5 py-20 lg:px-8 lg:py-24">
            <RevealSection>
              <SectionHeader eyebrow="FAQ" title="Common questions" align="center" />
            </RevealSection>
            <div className="mt-10 space-y-3">
              {faqs.map(({ q, a }, i) => (
                <RevealSection key={q} delay={(i % 3) as 0 | 1 | 2 | 3}>
                  <details className="group app-surface rounded-xl border-border/70 open:bg-card open:shadow-md">
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-4 p-5 text-sm font-medium [&::-webkit-details-marker]:hidden">
                      {q}
                      <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-90" />
                    </summary>
                    <p className="border-t border-border/60 px-5 pb-5 pt-3 text-sm font-light leading-relaxed text-muted-foreground">
                      {a}
                    </p>
                  </details>
                </RevealSection>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="mx-auto max-w-7xl px-5 py-20 lg:px-8 lg:py-24">
          <RevealSection>
            <Card className="landing-gradient-border app-panel relative overflow-hidden border-0 shadow-2xl">
              <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_hsl(var(--foreground)/0.06),_transparent_60%)]" />
              <div className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-foreground/[0.03] blur-3xl landing-glow-orb" />
              <CardContent className="relative flex flex-col items-center gap-6 p-10 text-center sm:p-16">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-border/70 bg-foreground shadow-lg">
                  <Zap className="h-6 w-6 text-background" />
                </div>
                <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-muted-foreground">Get started</p>
                <h2 className="max-w-xl text-2xl font-semibold tracking-tight sm:text-4xl">
                  Ready to let AI handle your outreach?
                </h2>
                <p className="max-w-lg text-sm font-light text-muted-foreground">
                  Free to start. Connect Gmail, scrape your first 100 leads, and watch the agent send your pilot email.
                </p>
                <div className="flex flex-col gap-3 sm:flex-row">
                  <Link href="/register">
                    <Button size="lg" className="h-12 gap-2 px-8 shadow-md">
                      Create free account
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  </Link>
                  <Link href="/login">
                    <Button variant="outline" size="lg" className="h-12 px-8">
                      Sign in
                    </Button>
                  </Link>
                </div>
                <p className="text-xs font-light text-muted-foreground">No credit card required</p>
              </CardContent>
            </Card>
          </RevealSection>
        </section>
      </main>

      {/* Mobile sticky CTA */}
      <div className="fixed bottom-0 left-0 right-0 z-40 border-t border-border/60 bg-background/95 p-3 backdrop-blur-md sm:hidden">
        <Link href="/register" className="block">
          <Button className="h-11 w-full gap-2 shadow-md">
            Start free
            <ArrowRight className="h-4 w-4" />
          </Button>
        </Link>
      </div>

      <footer className="border-t border-border/60 bg-muted/20 pb-20 sm:pb-12">
        <div className="mx-auto max-w-7xl px-5 py-12 lg:px-8">
          <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
            <div className="sm:col-span-2 lg:col-span-2">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-border/80 bg-foreground">
                  <Zap className="h-4 w-4 text-background" />
                </div>
                <div>
                  <p className="text-sm font-semibold">LeadGen AI</p>
                  <p className="text-xs font-light text-muted-foreground">AI-powered B2B lead generation</p>
                </div>
              </div>
              <p className="mt-4 max-w-sm text-xs font-light leading-relaxed text-muted-foreground">
                Scrape, verify, and reach European businesses with AI-powered outreach across WhatsApp, email, and
                LinkedIn.
              </p>
            </div>
            <div>
              <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-muted-foreground">Product</p>
              <div className="mt-4 flex flex-col gap-2 text-sm font-light text-muted-foreground">
                {navLinks.map(({ href, label }) => (
                  <a key={href} href={href} className="transition-colors hover:text-foreground">
                    {label}
                  </a>
                ))}
              </div>
            </div>
            <div>
              <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-muted-foreground">Account</p>
              <div className="mt-4 flex flex-col gap-2 text-sm font-light text-muted-foreground">
                <Link href="/register" className="transition-colors hover:text-foreground">
                  Create account
                </Link>
                <Link href="/login" className="transition-colors hover:text-foreground">
                  Sign in
                </Link>
              </div>
            </div>
          </div>
          <p className="mt-10 border-t border-border/60 pt-6 text-center text-xs font-light text-muted-foreground sm:text-left">
            © {new Date().getFullYear()} LeadGen AI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
