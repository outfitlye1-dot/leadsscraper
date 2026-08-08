"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Cpu, KeyRound, LayoutDashboard, Mail, Search, Settings, Users } from "lucide-react";
import { cn } from "@/lib/utils";

const items = [
  { href: "/admin", label: "Overview", icon: LayoutDashboard, exact: true },
  { href: "/admin/users", label: "Users", icon: Users },
  { href: "/admin/leads", label: "Leads", icon: Search },
  { href: "/admin/outreach", label: "Outreach", icon: Mail },
  { href: "/admin/scraper", label: "Scraper Jobs", icon: Activity },
  { href: "/admin/apis", label: "API Keys", icon: KeyRound },
  { href: "/admin/system", label: "System", icon: Cpu },
];

export function AdminSubNav() {
  const pathname = usePathname();

  return (
    <div className="flex flex-wrap gap-2 border-b border-border/60 pb-4">
      {items.map(({ href, label, icon: Icon, exact }) => {
        const active = exact ? pathname === href : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "liquid-glass-btn bg-foreground/90 text-background"
                : "text-muted-foreground hover:bg-muted/45 hover:text-foreground"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        );
      })}
      <Link
        href="/settings"
        className="ml-auto inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted/45 hover:text-foreground"
      >
        <Settings className="h-4 w-4" />
        Back to app
      </Link>
    </div>
  );
}
