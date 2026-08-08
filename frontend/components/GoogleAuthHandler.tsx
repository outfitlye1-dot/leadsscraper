"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { setToken } from "@/lib/auth";
import { getHomePathForRole } from "@/lib/authRedirect";
import { useAuthStore } from "@/store/authStore";

/** Handles ?access_token= or ?error= after Google OAuth redirect. */
function GoogleAuthHandlerInner() {
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const token = searchParams.get("access_token");
    const error = searchParams.get("error");
    if (!token && !error) return;

    if (error) {
      toast.error(decodeURIComponent(error));
      window.history.replaceState({}, "", "/login");
      return;
    }

    if (!token) return;

    void (async () => {
      try {
        setToken(token);
        await useAuthStore.getState().fetchUser();
        const role = useAuthStore.getState().user?.role;
        toast.success(role === "admin" ? "Welcome, Admin!" : "Signed in with Google");
        router.replace(getHomePathForRole(role));
      } catch {
        toast.error("Google sign-in failed. Please try again.");
        window.history.replaceState({}, "", "/login");
      }
    })();
  }, [router, searchParams]);

  return null;
}

export function GoogleAuthHandler() {
  return (
    <Suspense fallback={null}>
      <GoogleAuthHandlerInner />
    </Suspense>
  );
}
