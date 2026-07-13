"use client";

import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileUp, Upload, User } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import type { CVProfile } from "@/lib/types";
import { formatApiError } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { PageLoader } from "@/components/Loader";
import { PageError } from "@/components/PageError";

export default function CVPage() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const queryClient = useQueryClient();

  const { data: profile, isLoading, isError, refetch } = useQuery({
    queryKey: ["cv-profile"],
    queryFn: async () => {
      const { data } = await api.get<CVProfile | null>("/cv/profile");
      return data;
    },
    retry: false,
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post("/cv/upload", formData, {
        timeout: 120000,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cv-profile"] });
      toast.success("CV uploaded and parsed successfully!");
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

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  if (isLoading) return <PageLoader />;
  if (isError) {
    return (
      <div className="mx-auto max-w-4xl space-y-8">
        <PageHeader eyebrow="Profile" title="CV Upload" description="Upload your CV" />
        <PageError message="Could not load CV profile" onRetry={() => refetch()} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <PageHeader
        eyebrow="Profile"
        title="CV Upload"
        description="Upload your CV to power AI message personalization"
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Upload CV
          </CardTitle>
          <CardDescription>Supported formats: PDF, DOCX (max 10MB)</CardDescription>
        </CardHeader>
        <CardContent>
          <div
            className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-12 transition-colors ${
              dragOver ? "border-foreground/40 bg-muted/50" : "border-border/70 hover:border-foreground/30"
            }`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            onClick={() => fileRef.current?.click()}
          >
            <FileUp className="mb-4 h-10 w-10 text-muted-foreground" />
            <p className="mb-1 font-medium">Drop your CV here or click to browse</p>
            <p className="text-sm text-muted-foreground">PDF or DOCX up to 10MB</p>
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
          {uploadMutation.isPending && (
            <p className="mt-4 text-center text-sm text-muted-foreground">
              Uploading and parsing with AI...
            </p>
          )}
        </CardContent>
      </Card>

      {profile && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                {profile.name || "Your Profile"}
              </CardTitle>
              <CardDescription>
                Parsed from {profile.original_filename} • {profile.file_type.toUpperCase()}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {profile.professional_summary && (
                <div>
                  <h4 className="mb-2 font-medium">Professional Summary</h4>
                  <p className="text-sm text-muted-foreground">{profile.professional_summary}</p>
                </div>
              )}

              {profile.skills && profile.skills.length > 0 && (
                <div>
                  <h4 className="mb-2 font-medium">Skills</h4>
                  <div className="flex flex-wrap gap-2">
                    {profile.skills.map((skill) => (
                      <Badge key={skill} variant="secondary">
                        {skill}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {profile.services && profile.services.length > 0 && (
                <div>
                  <h4 className="mb-2 font-medium">Services</h4>
                  <div className="flex flex-wrap gap-2">
                    {profile.services.map((service) => (
                      <Badge key={service} variant="default">
                        {service}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {profile.technologies && profile.technologies.length > 0 && (
                <div>
                  <h4 className="mb-2 font-medium">Technologies</h4>
                  <div className="flex flex-wrap gap-2">
                    {profile.technologies.map((tech) => (
                      <Badge key={tech}>{tech}</Badge>
                    ))}
                  </div>
                </div>
              )}

              {profile.tools && profile.tools.length > 0 && (
                <div>
                  <h4 className="mb-2 font-medium">Tools</h4>
                  <div className="flex flex-wrap gap-2">
                    {profile.tools.map((tool) => (
                      <Badge key={tool} variant="outline">
                        {tool}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {profile.education && profile.education.length > 0 && (
                <div>
                  <h4 className="mb-2 font-medium">Education</h4>
                  <ul className="space-y-1 text-sm text-muted-foreground">
                    {profile.education.map((edu, i) => (
                      <li key={i}>
                        {[edu.degree, edu.institution, edu.year].filter(Boolean).join(" — ")}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {profile.projects && profile.projects.length > 0 && (
                <div>
                  <h4 className="mb-2 font-medium">Projects</h4>
                  <ul className="space-y-1 text-sm text-muted-foreground">
                    {profile.projects.map((proj, i) => (
                      <li key={i}>
                        {[proj.name || proj.title, proj.description].filter(Boolean).join(": ")}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {profile.experience_summary && (
                <div>
                  <h4 className="mb-2 font-medium">Experience Summary</h4>
                  <p className="text-sm text-muted-foreground">{profile.experience_summary}</p>
                </div>
              )}

              {profile.services_summary && (
                <div>
                  <h4 className="mb-2 font-medium">Services Summary</h4>
                  <p className="text-sm text-muted-foreground">{profile.services_summary}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {!profile && !isLoading && !isError && (
        <Card>
          <CardContent className="flex h-32 items-center justify-center text-muted-foreground">
            No CV uploaded yet. Upload your CV to enable AI personalization.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
