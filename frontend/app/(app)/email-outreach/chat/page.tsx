"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { PageLoader } from "@/components/Loader";

/** Old Email Outreach chat URL → standalone Chat page */
export default function EmailOutreachChatRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/chat");
  }, [router]);
  return <PageLoader />;
}
