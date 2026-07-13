import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";
import { IconBox, type IconBoxTone } from "@/components/ui/IconBox";

type Props = {
  label: string;
  value: string | number;
  hint?: string;
  icon?: LucideIcon;
  iconTone?: IconBoxTone;
  trend?: string;
  className?: string;
};

export function StatCard({ label, value, hint, icon, iconTone, trend, className }: Props) {
  return (
    <div
      className={cn(
        "liquid-glass group relative overflow-hidden rounded-xl p-5 transition-all duration-200 hover:shadow-[0_12px_36px_hsl(var(--foreground)/0.1)]",
        className
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            {label}
          </p>
          <p className="text-2xl font-semibold tabular-nums tracking-tight text-foreground sm:text-3xl">
            {value}
          </p>
          {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
          {trend ? (
            <p className="text-xs font-medium text-emerald-600 dark:text-emerald-400">{trend}</p>
          ) : null}
        </div>
        {icon ? <IconBox icon={icon} tone={iconTone} /> : null}
      </div>
    </div>
  );
}
