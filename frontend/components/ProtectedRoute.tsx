"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";
import { useAuth } from "@/hooks/useAuth";
import { PageLoader } from "@/components/Loader";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { fetchUser, user, logout } = useAuth();
  const router = useRouter();
  const [ready, setReady] = useState(() => Boolean(getToken() && user));

  useEffect(() => {
    let active = true;

    const verify = async () => {
      const token = getToken();
      if (!token) {
        logout();
        router.replace("/login");
        return;
      }

      // User already in memory — don't block navigation on /auth/me
      if (user) {
        if (active) setReady(true);
        return;
      }

      await fetchUser();

      if (!active) return;

      if (!getToken()) {
        router.replace("/login");
        return;
      }

      setReady(true);
    };

    verify();

    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!ready || !getToken()) {
    return <PageLoader />;
  }

  return <>{children}</>;
}
