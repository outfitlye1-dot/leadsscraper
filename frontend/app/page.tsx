"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";
import { getHomePathForRole } from "@/lib/authRedirect";
import { useAuthStore } from "@/store/authStore";
import { LandingPage } from "@/components/LandingPage";
import { PageLoader } from "@/components/Loader";

export default function Home() {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const redirectIfLoggedIn = async () => {
      if (!getToken()) {
        setReady(true);
        return;
      }
      if (!useAuthStore.getState().user) {
        await useAuthStore.getState().fetchUser();
      }
      router.replace(getHomePathForRole(useAuthStore.getState().user?.role));
    };
    redirectIfLoggedIn();
  }, [router]);

  if (!ready) {
    return <PageLoader />;
  }

  return <LandingPage />;
}
