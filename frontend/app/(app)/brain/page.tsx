"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Copy, FileUp, Save, Sparkles, Target } from "lucide-react";
import { toast } from "sonner";
import CpuArchitecture from "@/components/ui/cpu-architecture";
import {
  useBrain,
  useGenerateBrain,
  useImportCvToBrain,
  useUpdateBrain,
} from "@/hooks/useBrain";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Textarea } from "@/components/ui/Textarea";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { PageLoader } from "@/components/Loader";
import { PageHeader } from "@/components/PageHeader";
import type { BrainProfile } from "@/lib/types";
import { formatApiError } from "@/lib/utils";

function listToText(items: string[] | null | undefined) {
  return (items || []).join(", ");
}

function textToList(value: string) {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function experienceToText(items: Record<string, string>[] | null | undefined) {
  if (!items?.length) return "";
  return items
    .map((item) =>
      [item.title, item.company, item.duration, item.description].filter(Boolean).join(" — ")
    )
    .join("\n");
}

function textToExperience(value: string) {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [title, company, duration, description] = line.split(" — ");
      return { title, company, duration, description };
    });
}

function brainToForm(brain: BrainProfile | null | undefined) {
  return {
    name: brain?.name || "",
    skills: listToText(brain?.skills),
    services: listToText(brain?.services),
    tools: listToText(brain?.tools),
    technologies: listToText(brain?.technologies),
    professional_summary: brain?.professional_summary || "",
    experience: experienceToText(brain?.experience),
    education: experienceToText(brain?.education),
    projects: experienceToText(brain?.projects),
    custom_notes: brain?.custom_notes || "",
    system_prompt: brain?.system_prompt || "",
  };
}

export default function BrainPage() {
  const { data: brain, isLoading } = useBrain();
  const updateBrain = useUpdateBrain();
  const importCv = useImportCvToBrain();
  const generateBrain = useGenerateBrain();

  const [form, setForm] = useState(brainToForm(null));

  useEffect(() => {
    if (brain) {
      setForm(brainToForm(brain));
    }
  }, [brain]);

  const setField = (key: keyof typeof form, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    try {
      await updateBrain.mutateAsync({
        name: form.name || undefined,
        skills: textToList(form.skills),
        services: textToList(form.services),
        tools: textToList(form.tools),
        technologies: textToList(form.technologies),
        professional_summary: form.professional_summary || undefined,
        experience: textToExperience(form.experience),
        education: textToExperience(form.education),
        projects: textToExperience(form.projects),
        custom_notes: form.custom_notes || undefined,
        system_prompt: form.system_prompt || undefined,
      });
      toast.success("Brain data saved");
    } catch {
      toast.error("Failed to save brain data");
    }
  };

  const handleImportCv = async () => {
    try {
      const data = await importCv.mutateAsync();
      setForm(brainToForm(data));
      toast.success("CV data imported into brain");
    } catch (err: unknown) {
      toast.error(formatApiError(err, "Failed to import CV"));
    }
  };

  const handleGenerate = async () => {
    try {
      await updateBrain.mutateAsync({
        name: form.name || undefined,
        skills: textToList(form.skills),
        services: textToList(form.services),
        tools: textToList(form.tools),
        technologies: textToList(form.technologies),
        professional_summary: form.professional_summary || undefined,
        experience: textToExperience(form.experience),
        education: textToExperience(form.education),
        projects: textToExperience(form.projects),
        custom_notes: form.custom_notes || undefined,
      });
      const result = await generateBrain.mutateAsync();
      setField("system_prompt", result.system_prompt);
      toast.success("AI Brain prompt generated!");
    } catch (err: unknown) {
      toast.error(formatApiError(err, "Failed to generate brain"));
    }
  };

  const handleCopy = async () => {
    if (!form.system_prompt) return;
    await navigator.clipboard.writeText(form.system_prompt);
    toast.success("Brain prompt copied");
  };

  if (isLoading) return <PageLoader />;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Intelligence"
        title="AI Brain"
        description="CV se local business targets — restaurants, salons, clinics — outreach ke liye Brain train karein"
      >
        <Badge variant={form.system_prompt ? "success" : "secondary"}>
          {form.system_prompt ? "Active" : "Not Built"}
        </Badge>
      </PageHeader>

      <Card className="border-primary/20 bg-primary/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Target className="h-4 w-4" />
            Aap ka workflow (CV → Leads → Message)
          </CardTitle>
          <CardDescription>
            Local businesses jin ki website nahi — restaurant, salon, clinic, shop
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <ol className="list-decimal space-y-2 pl-5">
            <li>
              <strong className="text-foreground">Import CV</strong> ya manually services/skills bharo
            </li>
            <li>
              <strong className="text-foreground">Custom Notes</strong> mein likho: &quot;Target local
              businesses without website in [your city/country]&quot;
            </li>
            <li>
              <strong className="text-foreground">Generate Brain</strong> — AI outreach messages ke
              liye system prompt banayega
            </li>
            <li>
              <Link href="/scraper" className="font-medium text-primary hover:underline">
                Scraper
              </Link>{" "}
              → CV Smart Suggestions → Website filter:{" "}
              <strong className="text-foreground">Only without website</strong>
            </li>
            <li>
              <Link href="/leads" className="font-medium text-primary hover:underline">
                Leads
              </Link>{" "}
              → <strong className="text-foreground">Offer Website</strong> ya WhatsApp button
            </li>
            <li>
              <Link href="/campaigns" className="font-medium text-primary hover:underline">
                Campaigns
              </Link>{" "}
              → bulk AI messages generate karo (phir WhatsApp par send)
            </li>
          </ol>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="overflow-hidden lg:col-span-1">
          <CardHeader>
            <CardTitle>Brain CPU</CardTitle>
            <CardDescription>Your AI processing core — powered by your profile</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="relative rounded-xl border border-border bg-gradient-to-b from-muted/30 to-background p-4">
              <div className="h-40 w-full">
                <CpuArchitecture text="BRAIN" className="h-full w-full" />
              </div>
              <div className="mt-4 space-y-2 text-center">
                <Badge variant={form.system_prompt ? "success" : "secondary"}>
                  {form.system_prompt ? "Brain Active" : "Brain Not Built"}
                </Badge>
                <p className="text-xs text-muted-foreground">
                  {form.name ? `Processor: ${form.name}` : "Add your name to activate"}
                </p>
              </div>
            </div>

            <div className="flex flex-col gap-2 border-t border-border/60 pt-4">
              <Button
                variant="outline"
                onClick={handleImportCv}
                isLoading={importCv.isPending}
                className="w-full gap-2"
              >
                <FileUp className="h-4 w-4" />
                Import CV
              </Button>
              <Button
                variant="outline"
                onClick={handleSave}
                isLoading={updateBrain.isPending}
                className="w-full gap-2"
              >
                <Save className="h-4 w-4" />
                Save Data
              </Button>
              <Button onClick={handleGenerate} isLoading={generateBrain.isPending} className="w-full gap-2">
                <Sparkles className="h-4 w-4" />
                Generate Brain
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>CV Profile Data</CardTitle>
            <CardDescription>Ye data AI brain banane ke liye use hoga</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="name">Full Name</Label>
              <Input
                id="name"
                value={form.name}
                onChange={(e) => setField("name", e.target.value)}
                placeholder="Your name"
              />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="summary">Professional Summary</Label>
              <Textarea
                id="summary"
                value={form.professional_summary}
                onChange={(e) => setField("professional_summary", e.target.value)}
                placeholder="2-3 lines about who you are and what you do"
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="skills">Skills (comma separated)</Label>
              <Input
                id="skills"
                value={form.skills}
                onChange={(e) => setField("skills", e.target.value)}
                placeholder="Python, React, SEO"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="services">Services (comma separated)</Label>
              <Input
                id="services"
                value={form.services}
                onChange={(e) => setField("services", e.target.value)}
                placeholder="Web Design, Lead Gen"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tools">Tools</Label>
              <Input
                id="tools"
                value={form.tools}
                onChange={(e) => setField("tools", e.target.value)}
                placeholder="Figma, HubSpot"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="technologies">Technologies</Label>
              <Input
                id="technologies"
                value={form.technologies}
                onChange={(e) => setField("technologies", e.target.value)}
                placeholder="Next.js, FastAPI"
              />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="experience">Experience (one per line: Title — Company — Duration — Description)</Label>
              <Textarea
                id="experience"
                value={form.experience}
                onChange={(e) => setField("experience", e.target.value)}
                placeholder="Software Engineer — ABC Corp — 2020-2024 — Built web apps"
                rows={4}
              />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="education">Education (one per line: Degree — School — Year)</Label>
              <Textarea
                id="education"
                value={form.education}
                onChange={(e) => setField("education", e.target.value)}
                placeholder="BSc Computer Science — MIT — 2018"
                rows={3}
              />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="projects">Projects (one per line: Name — Tech — Description)</Label>
              <Textarea
                id="projects"
                value={form.projects}
                onChange={(e) => setField("projects", e.target.value)}
                placeholder="E-commerce App — Next.js — Built full-stack store"
                rows={3}
              />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="notes">Custom Notes (optional)</Label>
              <Textarea
                id="notes"
                value={form.custom_notes}
                onChange={(e) => setField("custom_notes", e.target.value)}
                placeholder="Target local restaurants/salons in Lahore without website. Offer web design packages."
                rows={3}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-start justify-between">
          <div>
            <CardTitle>Generated Brain Prompt</CardTitle>
            <CardDescription>
              Ye system prompt AI outreach messages ke liye use hota hai
            </CardDescription>
          </div>
          {form.system_prompt && (
            <Button variant="outline" size="sm" onClick={handleCopy} className="gap-2">
              <Copy className="h-4 w-4" />
              Copy
            </Button>
          )}
        </CardHeader>
        <CardContent>
          <Textarea
            value={form.system_prompt}
            onChange={(e) => setField("system_prompt", e.target.value)}
            placeholder='Click "Generate Brain" to create your AI system prompt from CV data...'
            rows={14}
            className="font-mono text-xs leading-relaxed"
          />
        </CardContent>
      </Card>
    </div>
  );
}
