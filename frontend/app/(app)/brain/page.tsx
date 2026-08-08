"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileUp, Save, Sparkles, Upload } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
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
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { PageLoader } from "@/components/Loader";
import { PageHeader } from "@/components/PageHeader";
import type { BrainProfile, CVProfile } from "@/lib/types";
import { cn, formatApiError } from "@/lib/utils";

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
    pricing_currency: brain?.pricing_currency || "USD",
    pricing_high: brain?.pricing_high != null ? String(brain.pricing_high) : "1000",
    pricing_floor: brain?.pricing_floor != null ? String(brain.pricing_floor) : "300",
  };
}

export default function BrainPage() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const queryClient = useQueryClient();

  const { data: brain, isLoading } = useBrain();
  const updateBrain = useUpdateBrain();
  const importCv = useImportCvToBrain();
  const generateBrain = useGenerateBrain();

  const [form, setForm] = useState(brainToForm(null));

  const { data: cvProfile } = useQuery({
    queryKey: ["cv-profile"],
    queryFn: async () => {
      const { data } = await api.get<CVProfile | null>("/cv/profile");
      return data;
    },
    retry: false,
  });

  useEffect(() => {
    if (brain) {
      setForm(brainToForm(brain));
    }
  }, [brain]);

  const setField = (key: keyof typeof form, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post("/cv/upload", formData, {
        timeout: 120000,
      });
      return data;
    },
    onSuccess: async () => {
      queryClient.invalidateQueries({ queryKey: ["cv-profile"] });
      toast.success("CV uploaded and parsed");
      try {
        const data = await importCv.mutateAsync();
        setForm(brainToForm(data));
        toast.success("CV imported into Brain");
      } catch {
        // Upload succeeded; import can be done manually
      }
    },
    onError: (err: unknown) => {
      toast.error(formatApiError(err, "Upload failed"));
    },
  });

  const handleFile = (file: File) => {
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!["pdf", "docx"].includes(ext || "")) {
      toast.error("Only PDF and DOCX files are supported");
      return;
    }
    uploadMutation.mutate(file);
  };

  const handleSave = async () => {
    const high = Number(form.pricing_high);
    const floor = Number(form.pricing_floor);
    if (!Number.isFinite(high) || !Number.isFinite(floor) || high < 0 || floor < 0) {
      toast.error("Enter valid pricing numbers");
      return;
    }
    if (high < floor) {
      toast.error("Opening (high) price must be ≥ floor price");
      return;
    }
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
        pricing_currency: form.pricing_currency || "USD",
        pricing_high: high,
        pricing_floor: floor,
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
    const high = Number(form.pricing_high);
    const floor = Number(form.pricing_floor);
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
        pricing_currency: form.pricing_currency || "USD",
        pricing_high: Number.isFinite(high) ? high : undefined,
        pricing_floor: Number.isFinite(floor) ? floor : undefined,
      });
      const result = await generateBrain.mutateAsync();
      setField("system_prompt", result.system_prompt);
      toast.success("AI Brain prompt generated!");
    } catch (err: unknown) {
      toast.error(formatApiError(err, "Failed to generate brain"));
    }
  };

  if (isLoading) return <PageLoader />;

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Intelligence" title="CV & Brain">
        <Badge variant={form.system_prompt ? "success" : "secondary"}>
          {form.system_prompt ? "Active" : "Not Built"}
        </Badge>
      </PageHeader>

      <nav className="flex flex-wrap gap-2">
        <a
          href="#cv-upload"
          className="rounded-lg border border-border/70 px-3 py-1.5 text-sm hover:bg-muted/50"
        >
          CV Upload
        </a>
        <a
          href="#brain-profile"
          className="rounded-lg border border-border/70 px-3 py-1.5 text-sm hover:bg-muted/50"
        >
          Brain Profile
        </a>
      </nav>

      <Card id="cv-upload" className="scroll-mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Upload className="h-4 w-4" />
            Upload CV
            {cvProfile ? (
              <Badge variant="success" className="ml-1">
                Uploaded
              </Badge>
            ) : null}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {cvProfile ? (
            <p className="text-sm text-muted-foreground">
              {cvProfile.name || "CV"} · {cvProfile.original_filename} ·{" "}
              {cvProfile.file_type?.toUpperCase()}
            </p>
          ) : null}
          <div
            className={cn(
              "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 transition-colors",
              dragOver
                ? "border-foreground/40 bg-muted/50"
                : "border-border/70 hover:border-foreground/30"
            )}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              const file = e.dataTransfer.files[0];
              if (file) handleFile(file);
            }}
            onClick={() => fileRef.current?.click()}
          >
            <FileUp className="mb-3 h-9 w-9 text-muted-foreground" />
            <p className="mb-1 text-sm font-medium">
              {cvProfile ? "Drop a new CV to replace" : "Drop your CV here or click to browse"}
            </p>
            <p className="text-xs text-muted-foreground">PDF or DOCX up to 10MB</p>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFile(file);
              }}
            />
          </div>
          {uploadMutation.isPending ? (
            <p className="text-center text-sm text-muted-foreground">
              Uploading and parsing with AI…
            </p>
          ) : null}
        </CardContent>
      </Card>

      <div id="brain-profile" className="grid scroll-mt-6 gap-6 lg:grid-cols-3">
        <Card className="overflow-hidden lg:col-span-1">
          <CardHeader>
            <CardTitle>Brain CPU</CardTitle>
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
                Import CV to Brain
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
              <Label htmlFor="experience">
                Experience (one per line: Title — Company — Duration — Description)
              </Label>
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
            <div className="space-y-3 rounded-xl border border-border/70 bg-muted/20 p-4 sm:col-span-2">
              <div>
                <Label className="text-sm font-semibold">Customer pricing</Label>
                <p className="mt-1 text-xs text-muted-foreground">
                  Pehle customer ko high rate batao, phir unke budget ke hisaab se floor tak deal
                  banao — AI isi rule pe chalegi.
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="pricing_currency">Currency</Label>
                  <select
                    id="pricing_currency"
                    value={form.pricing_currency}
                    onChange={(e) => setField("pricing_currency", e.target.value)}
                    className="flex h-10 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <option value="USD">USD</option>
                    <option value="PKR">PKR</option>
                    <option value="EUR">EUR</option>
                    <option value="GBP">GBP</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="pricing_high">Opening / high price</Label>
                  <Input
                    id="pricing_high"
                    type="number"
                    min={0}
                    step="1"
                    value={form.pricing_high}
                    onChange={(e) => setField("pricing_high", e.target.value)}
                    placeholder="1000"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="pricing_floor">Floor / minimum deal</Label>
                  <Input
                    id="pricing_floor"
                    type="number"
                    min={0}
                    step="1"
                    value={form.pricing_floor}
                    onChange={(e) => setField("pricing_floor", e.target.value)}
                    placeholder="300"
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
