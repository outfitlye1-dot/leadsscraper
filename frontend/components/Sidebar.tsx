"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  Bookmark,
  Bot,
  Brain,
  LayoutDashboard,
  Megaphone,
  MessageSquare,
  MessageCircle,
  Mail,
  Search,
  Settings,
  Shield,
  Users,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSidebar } from "@/contexts/SidebarContext";
import { useAuthStore } from "@/store/authStore";

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
};

type NavSection = {
  id: string;
  label: string | null;
  items: NavItem[];
};

const navSections: NavSection[] = [
  {
    id: "main",
    label: "Main",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/scraper", label: "Scraper", icon: Search },
      { href: "/leads", label: "Leads", icon: Users },
      { href: "/leads/saved", label: "Saved", icon: Bookmark },
    ],
  },
  {
    id: "outreach",
    label: "Outreach",
    items: [
      { href: "/campaigns", label: "Campaigns", icon: Megaphone },
      { href: "/email-outreach", label: "Email Outreach", icon: Mail },
      { href: "/messages", label: "WhatsApp", icon: MessageSquare },
      { href: "/chat", label: "Support Chat", icon: MessageCircle },
    ],
  },
  {
    id: "ai",
    label: "AI",
    items: [
      { href: "/ai", label: "AI Generator", icon: Bot },
      { href: "/brain", label: "CV & Brain", icon: Brain },
    ],
  },
  {
    id: "account",
    label: "Account",
    items: [
      { href: "/analytics", label: "Analytics", icon: BarChart3 },
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

function isNavActive(href: string, pathname: string): boolean {
  if (href === "/leads") {
    return pathname === "/leads" || /^\/leads\/\d+(\/|$)/.test(pathname);
  }
  if (href === "/leads/saved") {
    return pathname === "/leads/saved" || pathname.startsWith("/leads/saved/");
  }
  if (href === "/chat") {
    return pathname === href || pathname.startsWith(`${href}/`);
  }
  if (href === "/settings") {
    return pathname === "/settings" || pathname.startsWith("/settings/");
  }
  if (href === "/admin") {
    return pathname === "/admin" || pathname.startsWith("/admin/");
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavLink({
  item,
  pathname,
  isCollapsed,
  isMobile,
  onNavigate,
}: {
  item: NavItem;
  pathname: string;
  isCollapsed: boolean;
  isMobile: boolean;
  onNavigate?: () => void;
}) {
  const Icon = item.icon;
  const isActive = isNavActive(item.href, pathname);
  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      title={isCollapsed ? item.label : undefined}
      className={cn(
        "flex items-center gap-3 rounded-xl transition-colors",
        isMobile ? "px-4 py-3.5 text-[15px] leading-snug" : "rounded-lg px-3 py-2.5 text-sm",
        isCollapsed && "justify-center px-2",
        isActive
          ? "liquid-glass-btn bg-foreground/90 text-background shadow-sm"
          : "font-medium text-muted-foreground hover:bg-muted/45 hover:text-foreground"
      )}
    >
      <Icon
        className={cn("shrink-0", isMobile ? "h-5 w-5" : "h-4 w-4")}
        strokeWidth={isActive ? 2.25 : 2}
      />
      {!isCollapsed && <span className="truncate">{item.label}</span>}
    </Link>
  );
}

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { collapsed } = useSidebar();
  const isAdmin = useAuthStore((s) => s.user?.role === "admin");
  const isMobile = Boolean(onNavigate);
  const isCollapsed = collapsed && !isMobile;

  return (
    <aside
      className={cn(
        "liquid-glass flex h-full flex-col border-r transition-all duration-300",
        isMobile ? "w-full" : isCollapsed ? "w-[72px]" : "w-64"
      )}
    >
      <div
        className={cn(
          "flex items-center border-b border-border/60",
          isMobile ? "h-[72px] px-5" : "h-16",
          isCollapsed ? "justify-center px-2" : !isMobile && "px-5"
        )}
      >
        <div className={cn("flex items-center gap-3", isCollapsed && "justify-center")}>
          <div
            className={cn(
              "flex shrink-0 items-center justify-center rounded-lg border border-border/80 bg-foreground",
              isMobile ? "h-10 w-10" : "h-8 w-8"
            )}
          >
            <Zap className={cn("text-background", isMobile ? "h-5 w-5" : "h-4 w-4")} />
          </div>
          {!isCollapsed && (
            <div className="min-w-0">
              <span className={cn("block font-semibold tracking-tight", isMobile ? "text-base" : "text-sm")}>
                LeadGen AI
              </span>
              <span className="block text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                Workspace
              </span>
            </div>
          )}
        </div>
      </div>

      <nav className={cn("flex-1 overflow-y-auto", isMobile ? "space-y-4 p-4" : "space-y-3 p-3")}>
        {navSections.map((section) => (
          <div key={section.id} className={cn(isMobile ? "space-y-1.5" : "space-y-0.5")}>
            {section.label && !isCollapsed ? (
              <p
                className={cn(
                  "px-3 text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground",
                  section.id === "main" ? "pb-1" : "pt-1 pb-1"
                )}
              >
                {section.label}
              </p>
            ) : null}
            {section.items.map((item) => (
              <NavLink
                key={item.href}
                item={item}
                pathname={pathname}
                isCollapsed={isCollapsed}
                isMobile={isMobile}
                onNavigate={onNavigate}
              />
            ))}
          </div>
        ))}

        {isAdmin ? (
          <div className={cn(isMobile ? "space-y-1.5" : "space-y-0.5")}>
            {!isCollapsed ? (
              <p className="px-3 pt-1 pb-1 text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                Admin
              </p>
            ) : null}
            <NavLink
              item={{ href: "/admin", label: "Admin Panel", icon: Shield }}
              pathname={pathname}
              isCollapsed={isCollapsed}
              isMobile={isMobile}
              onNavigate={onNavigate}
            />
          </div>
        ) : null}
      </nav>
    </aside>
  );
}
