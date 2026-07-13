"use client";

import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

/** Handles ?connected=gmail|outlook after OAuth redirect. */
export function EmailOutreachOAuthHandler() {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();

  useEffect(() => {
    const connected = searchParams.get("connected");
    const error = searchParams.get("error");
    if (!connected && !error) return;

    if (connected === "gmail") {
      toast.success("Gmail connected successfully");
    } else if (connected === "outlook" || connected === "microsoft") {
      toast.success("Outlook connected successfully");
    } else if (error) {
      toast.error(decodeURIComponent(error));
    }

    void queryClient.invalidateQueries({ queryKey: ["email-outreach-dashboard"] });
    void queryClient.invalidateQueries({ queryKey: ["email-accounts"] });
    void queryClient.invalidateQueries({ queryKey: ["email-outreach-settings"] });

    window.history.replaceState({}, "", "/email-outreach");
  }, [searchParams, queryClient]);

  return null;
}
