import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

export type IconBoxTone =
  | "blue"
  | "violet"
  | "emerald"
  | "amber"
  | "rose"
  | "sky"
  | "indigo"
  | "slate";

const toneStyles: Record<IconBoxTone, string> = {
  blue:
    "border-blue-500/25 bg-gradient-to-br from-blue-500/22 via-blue-500/12 to-blue-400/5 text-blue-600 shadow-[inset_0_1px_0_rgba(255,255,255,0.35),0_4px_14px_rgba(59,130,246,0.14)] dark:text-blue-400",
  violet:
    "border-violet-500/25 bg-gradient-to-br from-violet-500/22 via-violet-500/12 to-violet-400/5 text-violet-600 shadow-[inset_0_1px_0_rgba(255,255,255,0.35),0_4px_14px_rgba(139,92,246,0.14)] dark:text-violet-400",
  emerald:
    "border-emerald-500/25 bg-gradient-to-br from-emerald-500/22 via-emerald-500/12 to-emerald-400/5 text-emerald-600 shadow-[inset_0_1px_0_rgba(255,255,255,0.35),0_4px_14px_rgba(16,185,129,0.14)] dark:text-emerald-400",
  amber:
    "border-amber-500/25 bg-gradient-to-br from-amber-500/22 via-amber-500/12 to-amber-400/5 text-amber-600 shadow-[inset_0_1px_0_rgba(255,255,255,0.35),0_4px_14px_rgba(245,158,11,0.14)] dark:text-amber-400",
  rose:
    "border-rose-500/25 bg-gradient-to-br from-rose-500/22 via-rose-500/12 to-rose-400/5 text-rose-600 shadow-[inset_0_1px_0_rgba(255,255,255,0.35),0_4px_14px_rgba(244,63,94,0.14)] dark:text-rose-400",
  sky:
    "border-sky-500/25 bg-gradient-to-br from-sky-500/22 via-sky-500/12 to-sky-400/5 text-sky-600 shadow-[inset_0_1px_0_rgba(255,255,255,0.35),0_4px_14px_rgba(14,165,233,0.14)] dark:text-sky-400",
  indigo:
    "border-indigo-500/25 bg-gradient-to-br from-indigo-500/22 via-indigo-500/12 to-indigo-400/5 text-indigo-600 shadow-[inset_0_1px_0_rgba(255,255,255,0.35),0_4px_14px_rgba(99,102,241,0.14)] dark:text-indigo-400",
  slate:
    "border-border/70 bg-gradient-to-br from-muted/80 via-muted/50 to-background/40 text-muted-foreground shadow-[inset_0_1px_0_rgba(255,255,255,0.3),0_4px_12px_hsl(var(--foreground)/0.06)]",
};

type Props = {
  icon: LucideIcon;
  tone?: IconBoxTone;
  size?: "sm" | "md";
  className?: string;
};

export function IconBox({ icon: Icon, tone = "slate", size = "sm", className }: Props) {
  return (
    <div
      className={cn(
        "icon-box group/icon flex shrink-0 items-center justify-center rounded-lg border transition-all duration-200 group-hover:scale-[1.03] group-hover:brightness-105",
        size === "sm" ? "h-9 w-9" : "h-10 w-10",
        toneStyles[tone],
        className
      )}
    >
      <Icon className={cn("relative z-[1]", size === "sm" ? "h-4 w-4" : "h-5 w-5")} strokeWidth={1.75} />
    </div>
  );
}
