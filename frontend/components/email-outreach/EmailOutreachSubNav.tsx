"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bot, Mail, Send, Settings2 } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

const baseTabs = [
  { href: "/email-outreach", label: "AI Agent", icon: Bot, exact: true },
  { href: "/email-outreach/sent", label: "Sent messages", icon: Send },
  { href: "/email-outreach/accounts", label: "Email accounts", icon: Mail },
];

export function EmailOutreachSubNav() {
  const pathname = usePathname();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const tabs = isAdmin
    ? [...baseTabs, { href: "/admin/outreach", label: "Platform settings", icon: Settings2 }]
    : baseTabs;

  return (
    <nav className="flex flex-wrap gap-2 border-b border-border/60 pb-4">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const active = tab.exact
          ? pathname === tab.href
          : pathname === tab.href || pathname.startsWith(`${tab.href}/`);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={cn(
              "inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "bg-foreground text-background"
                : "text-muted-foreground hover:bg-muted/70 hover:text-foreground"
            )}
          >
            <Icon className="h-4 w-4" />
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
