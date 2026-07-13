"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Bookmark,
  Bot,
  Brain,
  FileUp,
  LayoutDashboard,
  Megaphone,
  MessageSquare,
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

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/leads", label: "Leads", icon: Users },
  { href: "/leads/saved", label: "Saved", icon: Bookmark },
  { href: "/scraper", label: "Scraper", icon: Search },
  { href: "/campaigns", label: "Campaigns", icon: Megaphone },
  { href: "/email-outreach", label: "Email Outreach", icon: Mail },
  { href: "/messages", label: "Messages", icon: MessageSquare },
  { href: "/ai", label: "AI Generator", icon: Bot },
  { href: "/brain", label: "AI Brain", icon: Brain },
  { href: "/cv", label: "CV Upload", icon: FileUp },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { collapsed } = useSidebar();
  const isAdmin = useAuthStore((s) => s.user?.role === "admin");
  const isMobile = Boolean(onNavigate);
  const isCollapsed = collapsed && !isMobile;

  const adminItems = isAdmin
    ? [{ href: "/admin", label: "Admin Panel", icon: Shield }]
    : [];

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

      <nav className={cn("flex-1 overflow-y-auto", isMobile ? "space-y-1.5 p-4" : "space-y-0.5 p-3")}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            item.href === "/leads"
              ? pathname === "/leads"
              : pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
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
        })}
        {adminItems.length > 0 ? (
          <>
            {!isCollapsed ? (
              <p className="px-3 pt-4 text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                Admin
              </p>
            ) : null}
            {adminItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
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
            })}
          </>
        ) : null}
      </nav>
    </aside>
  );
}
