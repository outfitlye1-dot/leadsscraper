import { cn } from "@/lib/utils";
import { ButtonHTMLAttributes, forwardRef } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "secondary" | "outline" | "ghost" | "destructive";
  size?: "sm" | "md" | "lg" | "icon";
  isLoading?: boolean;
}

const variants = {
  default:
    "liquid-glass-btn bg-foreground/90 text-background hover:bg-foreground/80",
  secondary:
    "liquid-glass-btn bg-secondary/70 text-secondary-foreground hover:bg-secondary/85",
  outline:
    "liquid-glass-btn border-border/80 bg-background/40 hover:bg-muted/50",
  ghost: "border-transparent bg-transparent hover:bg-muted/60 hover:text-foreground",
  destructive:
    "liquid-glass-btn border-destructive/30 bg-destructive/85 text-destructive-foreground hover:bg-destructive/75",
};

const sizes = {
  sm: "h-8 px-3 text-xs tracking-wide",
  md: "h-10 px-4 text-sm",
  lg: "h-11 px-6 text-sm tracking-wide",
  icon: "h-8 w-8 p-0",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "md", isLoading, children, disabled, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-150 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        sizes[size],
        className
      )}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
      )}
      {children}
    </button>
  )
);
Button.displayName = "Button";
