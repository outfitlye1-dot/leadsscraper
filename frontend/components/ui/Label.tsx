import { cn } from "@/lib/utils";

export function Label({
  className,
  children,
  htmlFor,
}: {
  className?: string;
  children: React.ReactNode;
  htmlFor?: string;
}) {
  return (
    <label
      htmlFor={htmlFor}
      className={cn("text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground", className)}
    >
      {children}
    </label>
  );
}
