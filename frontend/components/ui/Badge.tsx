import { cn } from "@/lib/utils";

export function Badge({
  className,
  variant = "default",
  children,
}: {
  className?: string;
  variant?: "default" | "secondary" | "success" | "warning" | "destructive" | "outline";
  children: React.ReactNode;
}) {
  const variants = {
    default: "liquid-glass border-border/60 bg-muted/45 text-foreground",
    secondary: "liquid-glass border-border/50 bg-secondary/55 text-secondary-foreground",
    success: "liquid-glass border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
    warning: "liquid-glass border-amber-500/25 bg-amber-500/10 text-amber-700 dark:text-amber-400",
    destructive: "liquid-glass border-destructive/25 bg-destructive/10 text-destructive",
    outline: "liquid-glass border-border/70 bg-transparent text-foreground",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide",
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
