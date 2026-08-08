"use client";

import { usePathname } from "next/navigation";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Sidebar } from "@/components/Sidebar";
import { Navbar } from "@/components/Navbar";
import { SidebarProvider, useSidebar } from "@/contexts/SidebarContext";
import { ScraperJobTracker } from "@/components/ScraperJobTracker";
import { BackgroundScraperHeartbeat } from "@/components/BackgroundScraperHeartbeat";
import { cn } from "@/lib/utils";

function LayoutContent({ children }: { children: React.ReactNode }) {
  const { mobileOpen, setMobileOpen } = useSidebar();
  const pathname = usePathname();
  const isChatPage = pathname === "/chat" || pathname.startsWith("/chat/");

  return (
    <div className="flex h-screen overflow-hidden">
      <div className="hidden lg:block">
        <Sidebar />
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <div className="relative z-10 h-full w-[min(320px,88vw)] shadow-2xl">
            <Sidebar onNavigate={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col min-h-0">
        <Navbar />
        <BackgroundScraperHeartbeat />
        <ScraperJobTracker />
        <main
          className={cn(
            "flex-1 min-h-0",
            isChatPage ? "overflow-hidden p-0" : "overflow-y-auto p-5 lg:p-8"
          )}
        >
          <div
            className={cn(
              isChatPage
                ? "h-full max-w-none"
                : "page-enter mx-auto max-w-7xl space-y-8"
            )}
          >
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <SidebarProvider>
        <LayoutContent>{children}</LayoutContent>
      </SidebarProvider>
    </ProtectedRoute>
  );
}
