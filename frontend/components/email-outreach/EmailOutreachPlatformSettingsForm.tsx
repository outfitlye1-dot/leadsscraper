"use client";

import { toast } from "sonner";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { PageLoader } from "@/components/Loader";
import { useAdminOutreachSettings, useUpdateAdminOutreachSettings } from "@/hooks/useAdmin";
import type { EmailOutreachSettings } from "@/lib/types";

function ToggleRow({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 rounded-lg border border-border/50 px-4 py-3">
      <div>
        <p className="text-sm font-medium">{label}</p>
        {description && <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>}
      </div>
      <input
        type="checkbox"
        className="mt-1 h-4 w-4 shrink-0"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
    </label>
  );
}

export function EmailOutreachPlatformSettingsForm() {
  const { data: settings, isLoading, isError } = useAdminOutreachSettings();
  const updateSettings = useUpdateAdminOutreachSettings();

  const save = (patch: Partial<EmailOutreachSettings>) => {
    updateSettings.mutate(patch, {
      onSuccess: () => toast.success("Platform outreach settings saved for all users"),
      onError: () => toast.error("Failed to save outreach settings"),
    });
  };

  const applyDailyPreset = () => {
    save({
      automation_enabled: true,
      auto_send_enabled: true,
      require_review: false,
      auto_follow_up: true,
      daily_send_limit: 20,
      hourly_send_limit: 5,
      rate_limit_per_minute: 2,
      auto_reply_enabled: true,
      auto_reply_simple_only: false,
      working_hours_start: 9,
      working_hours_end: 18,
      weekends_enabled: false,
      agent_batch_delay_minutes: 10,
    });
  };

  if (isLoading) return <PageLoader />;
  if (isError || !settings) {
    return <p className="text-sm text-destructive">Could not load outreach settings.</p>;
  }

  return (
    <div className="space-y-6">
      <Card className="border-primary/20 bg-primary/5">
        <CardContent className="py-4 text-sm text-muted-foreground">
          These settings apply to <strong className="text-foreground">every user</strong> on the
          platform. Users cannot change limits or automation — only connect their own email accounts.
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Daily outreach preset</CardTitle>
          <CardDescription>
            20 emails per day, auto-send outreach, and AI auto-replies when leads respond.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button type="button" onClick={applyDailyPreset} disabled={updateSettings.isPending}>
            Apply 20/day + auto-reply preset
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Automation</CardTitle>
          <CardDescription>Master switches for automatic email sending across all users.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <ToggleRow
            label="Enable automation"
            description="Master switch for automatic email sending."
            checked={settings.automation_enabled}
            onChange={(v) => save({ automation_enabled: v })}
          />
          <ToggleRow
            label="Auto-send emails"
            description="Send without manual approval. Turns off require review."
            checked={settings.auto_send_enabled}
            onChange={(v) => save({ auto_send_enabled: v, require_review: !v })}
          />
          <ToggleRow
            label="Require review before send"
            description="AI drafts wait for approval on the agent page."
            checked={settings.require_review}
            onChange={(v) => save({ require_review: v, auto_send_enabled: !v })}
          />
          <ToggleRow
            label="Auto follow-up"
            description="Schedule follow-up emails after the first message is sent."
            checked={settings.auto_follow_up ?? true}
            onChange={(v) => save({ auto_follow_up: v })}
          />
          <ToggleRow
            label="Include unsubscribe line"
            description="Adds an opt-out line at the bottom of each email."
            checked={settings.include_unsubscribe ?? false}
            onChange={(v) => save({ include_unsubscribe: v })}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Send limits & schedule</CardTitle>
          <CardDescription>Daily caps, working hours, and batch timing for all users.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <Label>Daily send limit</Label>
              <Input
                type="number"
                min={1}
                max={500}
                defaultValue={settings.daily_send_limit}
                onBlur={(e) => save({ daily_send_limit: Number(e.target.value) || 20 })}
              />
            </div>
            <div>
              <Label>Hourly send limit</Label>
              <Input
                type="number"
                min={1}
                max={100}
                defaultValue={settings.hourly_send_limit}
                onBlur={(e) => save({ hourly_send_limit: Number(e.target.value) || 5 })}
              />
            </div>
            <div>
              <Label>Rate limit (per minute)</Label>
              <Input
                type="number"
                min={1}
                max={30}
                defaultValue={settings.rate_limit_per_minute}
                onBlur={(e) => save({ rate_limit_per_minute: Number(e.target.value) || 5 })}
              />
            </div>
            <div>
              <Label>Batch delay (minutes)</Label>
              <Input
                type="number"
                min={1}
                max={120}
                defaultValue={settings.agent_batch_delay_minutes ?? 10}
                onBlur={(e) =>
                  save({ agent_batch_delay_minutes: Number(e.target.value) || 10 })
                }
              />
            </div>
            <div>
              <Label>Working hours start (0–23)</Label>
              <Input
                type="number"
                min={0}
                max={23}
                defaultValue={settings.working_hours_start ?? 9}
                onBlur={(e) => save({ working_hours_start: Number(e.target.value) || 9 })}
              />
            </div>
            <div>
              <Label>Working hours end (0–23)</Label>
              <Input
                type="number"
                min={0}
                max={23}
                defaultValue={settings.working_hours_end ?? 18}
                onBlur={(e) => save({ working_hours_end: Number(e.target.value) || 18 })}
              />
            </div>
          </div>
          <ToggleRow
            label="Send on weekends"
            description="Allow sending on Saturday and Sunday."
            checked={settings.weekends_enabled ?? false}
            onChange={(v) => save({ weekends_enabled: v })}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>AI replies</CardTitle>
          <CardDescription>When leads reply, the agent can draft or auto-send responses.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <ToggleRow
            label="Auto-reply enabled"
            description="When a lead replies, AI drafts a response and can send it automatically."
            checked={settings.auto_reply_enabled}
            onChange={(v) => save({ auto_reply_enabled: v })}
          />
          <ToggleRow
            label="Safe auto-reply only"
            description="Only auto-send for simple questions and out-of-office."
            checked={settings.auto_reply_simple_only ?? false}
            onChange={(v) => save({ auto_reply_simple_only: v })}
          />
        </CardContent>
      </Card>
    </div>
  );
}
