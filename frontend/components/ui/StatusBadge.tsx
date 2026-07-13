import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";
import type { LeadStatus } from "@/lib/types";

const statusVariant: Record<LeadStatus, "default" | "secondary" | "success" | "warning" | "destructive" | "outline"> = {
  new: "outline",
  contacted: "default",
  interested: "success",
  follow_up: "warning",
  closed: "success",
  lost: "destructive",
};

export function LeadStatusBadge({ status }: { status: LeadStatus }) {
  return (
    <Badge variant={statusVariant[status]} className="capitalize normal-case">
      {status.replace("_", " ")}
    </Badge>
  );
}

export function QualityBadge({ tier }: { tier?: string | null }) {
  if (!tier) return null;
  const variant =
    tier === "high" ? "success" : tier === "medium" ? "warning" : ("outline" as const);
  return (
    <Badge variant={variant} className="capitalize normal-case">
      {tier}
    </Badge>
  );
}

export function IntentBadge({ intent }: { intent?: string | null }) {
  if (!intent) return null;
  const low = intent.toLowerCase();
  const variant =
    low.includes("hot") ? "success" : low.includes("warm") ? "warning" : ("outline" as const);
  return <Badge variant={variant}>{intent}</Badge>;
}

export function JobStatusBadge({
  status,
  className,
}: {
  status: string;
  className?: string;
}) {
  const variant =
    status === "running"
      ? "default"
      : status === "completed"
        ? "success"
        : status === "failed" || status === "cancelled"
          ? "destructive"
          : status === "paused"
            ? "warning"
            : "outline";
  return (
    <Badge variant={variant} className={cn("capitalize normal-case", className)}>
      {status}
    </Badge>
  );
}
