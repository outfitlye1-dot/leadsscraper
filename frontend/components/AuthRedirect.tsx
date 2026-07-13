"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

const AUTH_PAGES = ["/login", "/register"];

export function AuthRedirect() {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const onSessionExpired = () => {
      if (AUTH_PAGES.some((p) => pathname.startsWith(p))) return;
      router.replace("/login");
    };

    window.addEventListener("auth:session-expired", onSessionExpired);
    return () => window.removeEventListener("auth:session-expired", onSessionExpired);
  }, [pathname, router]);

  return null;
}
