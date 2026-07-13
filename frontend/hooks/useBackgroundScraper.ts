import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { BackgroundScrapeStatusResponse } from "@/lib/types";
import { useAuthStore } from "@/store/authStore";

const POLL_MS = 3_000;

export function useBackgroundScraperStatus(enabled = true) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  return useQuery({
    queryKey: ["background-scraper-status"],
    queryFn: async () => {
      const { data } = await api.get<BackgroundScrapeStatusResponse>("/scraper/background/status");
      return data;
    },
    enabled: enabled && isAuthenticated,
    refetchInterval: isAuthenticated ? POLL_MS : false,
  });
}
