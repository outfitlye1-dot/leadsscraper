"use client";

import { useState } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut, Menu, Moon, PanelLeftClose, PanelLeftOpen, Settings, Sun, User } from "lucide-react";
import { useTheme } from "@/components/ThemeProvider";
import { useAuth } from "@/hooks/useAuth";
import { useSidebar } from "@/contexts/SidebarContext";
import { Button } from "@/components/ui/Button";

export function Navbar() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { collapsed, toggleCollapsed, toggleMobile } = useSidebar();
  const router = useRouter();
  const [showMenu, setShowMenu] = useState(false);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <header className="liquid-glass flex h-14 items-center justify-between border-b px-4 lg:px-6">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" className="lg:hidden" onClick={toggleMobile}>
          <Menu className="h-5 w-5" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="hidden text-muted-foreground lg:flex"
          onClick={toggleCollapsed}
          aria-label="Toggle sidebar"
        >
          {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </Button>
      </div>

      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="sm"
          className="text-muted-foreground"
          onClick={toggleTheme}
          aria-label="Toggle theme"
        >
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>

        <div className="relative">
          <Button
            variant="ghost"
            size="sm"
            className="gap-2 text-muted-foreground hover:text-foreground"
            onClick={() => setShowMenu((open) => !open)}
            aria-expanded={showMenu}
            aria-haspopup="menu"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-full border border-border/80 bg-muted/50">
              <User className="h-3.5 w-3.5" />
            </div>
            <span className="hidden text-sm font-medium sm:inline">{user?.name || "User"}</span>
          </Button>

          {showMenu &&
            typeof document !== "undefined" &&
            createPortal(
              <>
                <div
                  className="fixed inset-0 z-[200] bg-black/20"
                  aria-hidden
                  onClick={() => setShowMenu(false)}
                />
                <div
                  role="menu"
                  className="fixed right-4 top-[3.75rem] z-[210] w-52 overflow-hidden rounded-xl border border-border bg-card text-card-foreground shadow-2xl lg:right-6"
                >
                  <div className="border-b border-border bg-muted/40 px-3 py-2.5">
                    <p className="text-sm font-semibold text-foreground">{user?.name}</p>
                    <p className="truncate text-xs text-foreground/70">{user?.email}</p>
                  </div>
                  <div className="p-1.5">
                  <Link
                    href="/settings"
                    onClick={() => setShowMenu(false)}
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
                  >
                    <Settings className="h-4 w-4 text-foreground/80" />
                    Settings
                  </Link>
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-destructive transition-colors hover:bg-destructive/15"
                  >
                    <LogOut className="h-4 w-4" />
                    Logout
                  </button>
                  </div>
                </div>
              </>,
              document.body
            )}
        </div>
      </div>
    </header>
  );
}
