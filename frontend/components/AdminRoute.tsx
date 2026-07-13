"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { PageLoader } from "@/components/Loader";
import { useAuthStore } from "@/store/authStore";

export function AdminRoute({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const fetchUser = useAuthStore((s) => s.fetchUser);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;

    const verify = async () => {
      if (!useAuthStore.getState().user) {
        await fetchUser();
      }
      if (!active) return;

      if (useAuthStore.getState().user?.role !== "admin") {
        router.replace("/dashboard");
        return;
      }

      setReady(true);
    };

    verify();
    return () => {
      active = false;
    };
  }, [fetchUser, router]);

  return <ProtectedRoute>{ready ? children : <PageLoader />}</ProtectedRoute>;
}
