"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { PageLoader } from "@/components/Loader";
import { useAuth } from "@/hooks/useAuth";

export default function EmailOutreachSettingsRedirectPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();

  useEffect(() => {
    if (isLoading) return;
    if (user?.role === "admin") {
      router.replace("/admin/outreach");
      return;
    }
    router.replace("/email-outreach/accounts");
  }, [isLoading, router, user?.role]);

  return <PageLoader />;
}
